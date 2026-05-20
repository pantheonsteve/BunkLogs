"""Concerns Inbox dashboard.

GET /api/v1/dashboards/concerns/?date_start=&date_end=&include_read=
POST /api/v1/dashboards/concerns/<reflection_id>/<field_key>/read/

Surfaces every "concern" item (textarea answers on dashboard_role=open_concern
fields, plus low_rating events) the viewer is permitted to see, with per-user
read state stored in ConcernReadState. Items default to unread; calling the
mark-read endpoint creates a row keyed by (user, reflection, field_key) so the
inbox can hide them on the next fetch.
"""

from __future__ import annotations

from datetime import date
from datetime import timedelta

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from bunk_logs.core.filters import reflections_visible_for_user
from bunk_logs.core.models import ConcernReadState
from bunk_logs.core.models import Reflection

DEFAULT_WINDOW_DAYS = 14
MAX_WINDOW_DAYS = 60
LOW_RATING_THRESHOLD = 1


def _parse_date(s: str | None, default: date) -> date:
    if not s:
        return default
    try:
        return date.fromisoformat(s)
    except ValueError:
        return default


def _extract_concerns_from_reflection(r: Reflection) -> list[dict]:
    """Walk r.template.schema and pull out every concerning item present in answers."""
    items: list[dict] = []
    schema = (r.template.schema or {}).get("fields") or []
    for f in schema:
        if not isinstance(f, dict):
            continue
        ftype = f.get("type")
        fkey = f.get("key")
        role = f.get("dashboard_role")
        v = r.answers.get(fkey)
        if role == "open_concern" and ftype in ("text", "textarea"):
            if isinstance(v, str) and v.strip():
                items.append({
                    "kind": "open_concern",
                    "field_key": fkey,
                    "field_label": f.get("prompts", {}).get("en") or fkey,
                    "value": v.strip()[:1000],
                })
        if ftype in ("single_rating",) and (
            f.get("dashboard_role") == "primary_rating"
        ):
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                if float(v) <= LOW_RATING_THRESHOLD:
                    items.append({
                        "kind": "low_rating",
                        "field_key": fkey,
                        "field_label": f.get("prompts", {}).get("en") or fkey,
                        "value": float(v),
                    })
        if ftype == "rating_group":
            block = v if isinstance(v, dict) else {}
            for cat in f.get("categories") or []:
                if not isinstance(cat, dict):
                    continue
                ck = cat.get("key")
                cv = block.get(ck)
                if isinstance(cv, (int, float)) and not isinstance(cv, bool):
                    if float(cv) <= LOW_RATING_THRESHOLD:
                        items.append({
                            "kind": "low_rating",
                            "field_key": f"{fkey}__{ck}",
                            "field_label": (
                                cat.get("labels", {}).get("en") or f"{fkey} · {ck}"
                            ),
                            "value": float(cv),
                        })
    return items


class ConcernsInboxView(APIView):
    """List concerns visible to the viewer with read-state filtering."""

    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        org = getattr(request, "organization", None)
        if org is None:
            return Response({"detail": "Organization context required."}, status=403)

        today = date.today()
        cur_end = _parse_date(request.query_params.get("date_end"), today)
        cur_start = _parse_date(
            request.query_params.get("date_start"),
            cur_end - timedelta(days=DEFAULT_WINDOW_DAYS - 1),
        )
        if cur_end < cur_start:
            cur_start, cur_end = cur_end, cur_start
        if (cur_end - cur_start).days > MAX_WINDOW_DAYS - 1:
            cur_start = cur_end - timedelta(days=MAX_WINDOW_DAYS - 1)

        include_read = (request.query_params.get("include_read") or "").lower() in (
            "1", "true", "yes",
        )

        refs = list(
            reflections_visible_for_user(
                request.user,
                Reflection.objects.filter(
                    period_end__gte=cur_start,
                    period_end__lte=cur_end,
                    is_complete=True,
                ).select_related("subject", "author", "template", "assignment_group"),
            ).order_by("-period_end"),
        )

        # Pull this viewer's read states for all candidate reflections in one query
        read_pairs: set[tuple[int, str]] = set(
            ConcernReadState.objects.filter(
                user=request.user,
                reflection_id__in=[r.id for r in refs],
            ).values_list("reflection_id", "field_key"),
        )

        items: list[dict] = []
        for r in refs:
            for c in _extract_concerns_from_reflection(r):
                read = (r.id, c["field_key"]) in read_pairs
                if read and not include_read:
                    continue
                items.append({
                    "reflection_id": r.id,
                    "date": r.period_end.isoformat(),
                    "subject_id": r.subject_id,
                    "subject_name": r.subject.full_name if r.subject else None,
                    "author_name": r.author.full_name if r.author else None,
                    "template_name": r.template.name,
                    "team_visibility": r.team_visibility,
                    "assignment_group": (
                        {"id": r.assignment_group_id, "name": r.assignment_group.name}
                        if r.assignment_group_id else None
                    ),
                    "kind": c["kind"],
                    "field_key": c["field_key"],
                    "field_label": c["field_label"],
                    "value": c["value"],
                    "read": read,
                })
        return Response({
            "period": {"start": cur_start.isoformat(), "end": cur_end.isoformat()},
            "include_read": include_read,
            "items": items,
        })


class ConcernMarkReadView(APIView):
    """POST mark a (reflection, field_key) concern as read for this user."""

    permission_classes = [IsAuthenticated]

    def post(self, request, reflection_id: int, field_key: str, *args, **kwargs):
        if not isinstance(field_key, str) or len(field_key) > 64:
            return Response({"detail": "Invalid field_key."}, status=400)

        # Reuse visibility helper so a viewer who can't see the reflection can't
        # cause read-rows to leak it via 200/4xx timing.
        ref = (
            reflections_visible_for_user(
                request.user,
                Reflection.objects.filter(id=reflection_id),
            ).first()
        )
        if ref is None:
            return Response({"detail": "Reflection not found."}, status=404)

        ConcernReadState.objects.get_or_create(
            user=request.user,
            reflection_id=reflection_id,
            field_key=field_key,
        )
        return Response({"reflection_id": reflection_id, "field_key": field_key, "read": True})

    def delete(self, request, reflection_id: int, field_key: str, *args, **kwargs):
        ConcernReadState.objects.filter(
            user=request.user,
            reflection_id=reflection_id,
            field_key=field_key,
        ).delete()
        return Response({"reflection_id": reflection_id, "field_key": field_key, "read": False})
