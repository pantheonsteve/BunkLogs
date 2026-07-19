"""Per-user preference endpoints (Step 7_5 — i18n foundation).

Exposes the two reader-controlled i18n fields on ``Person``:

* ``preferred_language`` — UI language. Persisted server-side so it follows
  the user across devices and is the source of truth for outbound emails.
* ``translation_preference`` — bilingual-content rendering order
  (translation-first vs. original-first).

The picker lives in the frontend and writes through this endpoint
(``GET`` / ``PATCH /api/v1/me/preferences/``). Authenticated users without a
``Person`` row get ``404`` so callers can fall back to a localStorage-only
preference — Person rows are required for org-scoped writes anyway and the
LanguagePicker handles that gracefully.

Audit trail: changes here are reader preferences (no business-meaningful
state), so we deliberately do NOT emit ``AuditEvent`` rows — see
``docs/user_stories/00_cross_cutting/audit_trail.md`` ("what we do NOT log").
"""
from __future__ import annotations

from datetime import date

from django.db.models import Max
from django.db.models import Min
from django.utils import timezone
from rest_framework import permissions
from rest_framework import serializers
from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.views import APIView

from bunk_logs.core.context import get_current_organization
from bunk_logs.core.models import Membership
from bunk_logs.core.models import Person
from bunk_logs.core.models import Program


class MePreferencesSerializer(serializers.ModelSerializer):
    """Whitelist of reader-controlled i18n fields on ``Person``.

    Kept intentionally narrow: this endpoint is hot, public-ish (any
    authenticated user can hit it), and must never be a side-channel for
    editing PII like ``first_name`` or ``email``.
    """

    class Meta:
        model = Person
        fields = ["preferred_language", "translation_preference"]


class MePreferencesView(APIView):
    """``GET`` / ``PATCH`` the current user's i18n preferences."""

    permission_classes = [permissions.IsAuthenticated]

    def _get_person(self, request) -> Person:
        person = (
            Person.all_objects.filter(user=request.user)
            .order_by("created_at")
            .first()
        )
        if person is None:
            raise NotFound(
                detail=(
                    "No Person record is linked to this account. "
                    "Language preference will be stored locally only."
                ),
            )
        return person

    def get(self, request):
        person = self._get_person(request)
        return Response(MePreferencesSerializer(person).data)

    def patch(self, request):
        person = self._get_person(request)
        serializer = MePreferencesSerializer(person, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)


def _permissive_date_range() -> dict[str, str | None]:
    today = timezone.localdate()
    return {
        "start_date": date(today.year, 1, 1).isoformat(),
        "end_date": None,
    }


class MeDateRangeView(APIView):
    """``GET`` the current user's allowed calendar window for date pickers."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        if user.is_staff or user.is_superuser:
            return Response(_permissive_date_range())

        person = (
            Person.all_objects.filter(user=user)
            .order_by("created_at")
            .first()
        )
        if person is None:
            today = timezone.localdate().isoformat()
            return Response({"start_date": today, "end_date": None})

        org = get_current_organization()
        memberships = Membership.all_objects.filter(
            person=person,
            is_active=True,
        ).select_related("program")
        if org is not None:
            memberships = memberships.filter(program__organization=org)

        if memberships.filter(role="admin").exists():
            return Response(_permissive_date_range())

        starts: list[date] = []
        ends: list[date] = []
        open_ended = False
        for membership in memberships:
            program = membership.program
            start = membership.start_date or program.start_date
            end = membership.end_date or program.end_date
            if start:
                starts.append(start)
            if end:
                ends.append(end)
            elif membership.end_date is None and program.end_date is None:
                open_ended = True

        if starts:
            payload: dict[str, str | None] = {
                "start_date": min(starts).isoformat(),
                "end_date": None if open_ended or not ends else max(ends).isoformat(),
            }
            return Response(payload)

        programs = Program.all_objects.filter(is_active=True)
        if org is not None:
            programs = programs.filter(organization=org)
        agg = programs.aggregate(
            min_start=Min("start_date"),
            max_end=Max("end_date"),
        )
        if agg["min_start"]:
            return Response(
                {
                    "start_date": agg["min_start"].isoformat(),
                    "end_date": (
                        agg["max_end"].isoformat() if agg["max_end"] else None
                    ),
                },
            )

        today = timezone.localdate().isoformat()
        return Response({"start_date": today, "end_date": None})
