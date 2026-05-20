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

from rest_framework import permissions, serializers, status
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.views import APIView

from bunk_logs.core.models import Person


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
