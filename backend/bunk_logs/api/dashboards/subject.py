"""Per-subject detail dashboard.

GET /api/v1/dashboards/subject/{person_id}/?date_start=&date_end=

Returns all reflections about ``person_id`` (visible to viewer), grouped by
template, plus per-rating-field time series, recent text responses, and a
``concerning_patterns`` array (low ratings + downward trends) — used to surface
campers who may need a check-in.

No scipy dependency: trend detection is a simple two-window average compare.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date
from datetime import timedelta
from typing import Any

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from bunk_logs.core.filters import reflections_visible_for_user
from bunk_logs.core.models import AssignmentGroupMembership
from bunk_logs.core.models import Membership
from bunk_logs.core.models import Person
from bunk_logs.core.models import Reflection
from bunk_logs.core.models import SubjectNote
from bunk_logs.core.permissions.observation_read import filter_observations_readable
from bunk_logs.core.permissions.subject_note_authoring import can_author_subject_note
from bunk_logs.core.permissions.subject_note_read import filter_subject_notes_readable
from bunk_logs.core.permissions.super_admin import is_super_admin
from bunk_logs.core.permissions.visibility import author_group_ids_with_descendants
from bunk_logs.notes.models import Observation

DEFAULT_WINDOW_DAYS = 30
MAX_WINDOW_DAYS = 90
MAX_REFLECTIONS_PER_SUBJECT = 200
LOW_RATING_LOOKBACK_DAYS = 14
TREND_LOOKBACK_DAYS = 14
TREND_DELTA_THRESHOLD = 0.5
MIN_REFLECTIONS_PER_HALF_FOR_TREND = 3
RECENT_TEXT_LIMIT = 30


def _parse_date(s: str | None, default: date) -> date:
    if not s:
        return default
    try:
        return date.fromisoformat(s)
    except ValueError:
        return default


# Re-export the canonical helper from ``core.reflection_scores`` so existing
# call sites in this module keep working without touching the rest of the
# file. New callers should import directly from
# ``bunk_logs.core.reflection_scores``.
from bunk_logs.core.reflection_scores import resolve_rating_cells as _resolve_rating


def _subject_profile(subject: Person, organization) -> dict[str, Any]:
    """Non-PII profile block safe to expose to any viewer with reflection
    visibility. Emails / DOB stay in the admin-only people endpoint.
    """
    memberships = list(
        Membership.all_objects.filter(person=subject, is_active=True)
        .select_related("program")
        .order_by("-created_at"),
    )
    programs = [
        {
            "id": m.program_id,
            "name": m.program.name if m.program_id else None,
            "role": m.role,
        }
        for m in memberships
        if m.program_id is None or m.program.organization_id == organization.id
    ]
    primary_role = programs[0]["role"] if programs else None
    group_rows = list(
        AssignmentGroupMembership.all_objects.filter(
            person=subject, is_active=True, role_in_group="subject",
        )
        .select_related("group")
        .order_by("group__name"),
    )
    assignment_groups = [
        {
            "id": gm.group_id,
            "name": gm.group.name,
            "group_type": gm.group.group_type,
        }
        for gm in group_rows
        if gm.group and gm.group.organization_id == organization.id
    ]
    return {
        "id": subject.id,
        "full_name": subject.full_name,
        "preferred_name": subject.preferred_name or subject.first_name,
        "preferred_language": subject.preferred_language,
        "primary_role": primary_role,
        "programs": programs,
        "assignment_groups": assignment_groups,
    }


def _is_yes_no_field(field: dict) -> bool:
    """Two-option ``single_choice`` field with yes/no values (case-insensitive)."""
    if field.get("type") != "single_choice":
        return False
    options = field.get("options") or []
    if len(options) != 2:
        return False
    values = {str(o.get("value", "")).lower() for o in options if isinstance(o, dict)}
    return values == {"yes", "no"}


def _viewer_capability(person: Person, org) -> str | None:
    """Highest-privilege capability the person holds in this org (across all programs)."""
    caps = set(
        Membership.all_objects.filter(
            person=person,
            is_active=True,
            program__organization=org,
        ).values_list("capability", flat=True),
    )
    for cap in ("admin", "program_lead", "domain_specialist", "supervisor"):
        if cap in caps:
            return cap
    if "participant" in caps:
        return "participant"
    return None


def _viewer_supervises_subject(viewer: Person, subject: Person) -> bool:
    """True if viewer authors a group (or any ancestor group) that contains subject."""
    group_ids = author_group_ids_with_descendants(viewer)
    if not group_ids:
        return False
    return AssignmentGroupMembership.all_objects.filter(
        person=subject,
        group_id__in=group_ids,
        role_in_group="subject",
        is_active=True,
    ).exists()


def _can_view_subject_dashboard(
    viewer_person: Person | None,
    subject: Person,
    org,
    user,
) -> bool:
    """Explicit capability gate for the subject dashboard.

    Allowed paths:
    - Super admin (no Person required)
    - admin / program_lead / domain_specialist membership in org
    - supervisor capability with a supervises-subject relationship
    - participant capability with a supervises-subject relationship (covers
      counselors accessing their campers) or self-view
    - program-scoped authoring roles (e.g. activity specialists) via
      ``can_author_subject_note`` org role defaults
    """
    if is_super_admin(user):
        return True
    if viewer_person is None:
        return False
    cap = _viewer_capability(viewer_person, org)
    if cap in ("admin", "program_lead", "domain_specialist"):
        return True
    if cap in ("supervisor", "participant"):
        if viewer_person.id == subject.id or _viewer_supervises_subject(viewer_person, subject):
            return True
    # Program-scoped roles (e.g. activity specialists) and per-membership overrides.
    return can_author_subject_note(viewer_person, subject, org, user)


def _subject_notes_for_viewer(
    viewer_person: Person | None,
    subject: Person,
    org,
    user,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Return SubjectNote rows visible to viewer, newest first."""
    qs = (
        SubjectNote.objects.filter(subject=subject)
        .select_related("author_person")
        .order_by("-created_at")
    )
    notes = list(
        filter_subject_notes_readable(
            qs,
            viewer_person,
            org,
            user,
            subject=subject,
        ).order_by("-created_at")[:limit],
    )

    return [
        {
            "id": n.id,
            "body": n.body,
            "context": n.context,
            "visibility": n.visibility,
            "is_sensitive": n.is_sensitive,
            "subject_visible": n.subject_visible,
            "amendment_of": n.amendment_of_id,
            "author": (
                {"id": n.author_person_id, "name": n.author_person.full_name}
                if n.author_person_id and n.author_person else None
            ),
            "created_at": n.created_at.isoformat() if n.created_at else None,
        }
        for n in notes
    ]


def _observations_for_viewer(
    viewer_person: Person | None,
    subject: Person,
    org,
    user,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Return Observations about ``subject`` the viewer may read, newest first.

    Step 7_23 Profile feed: every observation the viewer may read about this
    person, replacing the SubjectNote block as callers migrate.
    """
    base = (
        Observation.all_objects.filter(organization=org, subject_links__subject=subject)
        .select_related("author")
        .prefetch_related("subject_links__subject")
    )
    observations = list(
        filter_observations_readable(base, viewer_person, org, user).order_by("-created_at")[:limit],
    )
    return [
        {
            "id": o.id,
            "body": o.body,
            "context": o.context,
            "sensitivity": o.sensitivity,
            "subject_visible": o.subject_visible,
            "amendment_of": o.amendment_of_id,
            "author": (
                {"id": o.author_id, "name": o.author.full_name}
                if o.author_id and o.author else None
            ),
            "created_at": o.created_at.isoformat() if o.created_at else None,
        }
        for o in observations
    ]


def _detect_concerning_patterns(
    series_by_label: dict[str, list[tuple[date, float, int, int | None]]],
    today: date,
) -> list[dict[str, Any]]:
    """Two-rule detection: any rating==1 in last 14d, or recent half lower than prior half.

    series_by_label[label] is a list of (date, value, reflection_id, scale_max, team_visibility).
    """
    patterns: list[dict[str, Any]] = []
    low_cutoff = today - timedelta(days=LOW_RATING_LOOKBACK_DAYS - 1)
    for label, points in series_by_label.items():
        # Any rating of 1 in last 14 days
        for d, v, ref_id, _scale, team_visibility in points:
            if d >= low_cutoff and v is not None and v <= 1.0:
                patterns.append({
                    "kind": "low_rating",
                    "field_label": label,
                    "date": d.isoformat(),
                    "value": v,
                    "reflection_id": ref_id,
                    "team_visibility": team_visibility,
                })
        # Downward trend: split last 14 days in half, require >=3 each
        recent_cutoff = today - timedelta(days=TREND_LOOKBACK_DAYS - 1)
        midpoint = today - timedelta(days=(TREND_LOOKBACK_DAYS // 2) - 1)
        recent_vals = [v for d, v, *_ in points if d >= midpoint and v is not None]
        prior_vals = [
            v for d, v, *_ in points
            if recent_cutoff <= d < midpoint and v is not None
        ]
        if (
            len(recent_vals) >= MIN_REFLECTIONS_PER_HALF_FOR_TREND
            and len(prior_vals) >= MIN_REFLECTIONS_PER_HALF_FOR_TREND
        ):
            recent_mean = sum(recent_vals) / len(recent_vals)
            prior_mean = sum(prior_vals) / len(prior_vals)
            if recent_mean < prior_mean - TREND_DELTA_THRESHOLD:
                patterns.append({
                    "kind": "downward_trend",
                    "field_label": label,
                    "recent_mean": round(recent_mean, 2),
                    "prior_mean": round(prior_mean, 2),
                })
    return patterns


class SubjectDetailView(APIView):
    """Cross-template aggregation for one subject Person."""

    permission_classes = [IsAuthenticated]

    def get(self, request, person_id: int, *args, **kwargs):
        org = getattr(request, "organization", None)
        if org is None:
            return Response({"detail": "Organization context required."}, status=403)

        subject = Person.objects.filter(id=person_id).first()
        if subject is None:
            return Response({"detail": "Subject not found."}, status=404)

        # Defense-in-depth: OrgScopedManager already enforces this, but be explicit.
        if subject.organization_id != org.id:
            return Response({"detail": "Subject not found."}, status=404)

        viewer_person = Person.all_objects.filter(user=request.user).first()
        if not _can_view_subject_dashboard(viewer_person, subject, org, request.user):
            return Response(
                {"detail": "You do not have permission to view this subject's dashboard."},
                status=403,
            )

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

        # Pull reflections about this subject within window, scoped to viewer.
        # Cap at MAX_REFLECTIONS_PER_SUBJECT to prevent unbounded queries on
        # subjects with long histories; the 90-day window already constrains most cases.
        refs = list(
            reflections_visible_for_user(
                request.user,
                Reflection.objects.filter(
                    subject_id=person_id,
                    period_end__gte=cur_start,
                    period_end__lte=cur_end,
                    is_complete=True,
                ).select_related("template", "author", "assignment_group"),
            ).order_by("period_end")[:MAX_REFLECTIONS_PER_SUBJECT],
        )

        if not refs:
            # 403 vs empty: if viewer has zero visible reflections of any kind for this
            # subject, that may legitimately be empty (subject not in a visible group).
            # We don't 403 — empty result is informative. Caller can render empty state.
            pass

        # Group by template
        by_template: dict[int, dict[str, Any]] = {}
        # series_by_label across ALL templates: used for concerning-pattern detection
        all_series: dict[str, list[tuple[date, float, int, int | None, str]]] = defaultdict(list)
        recent_texts: list[dict[str, Any]] = []

        for r in refs:
            tpl = r.template
            tpl_entry = by_template.get(tpl.id)
            schema_fields = (tpl.schema or {}).get("fields") or []
            if tpl_entry is None:
                flag_keys = [
                    f.get("key")
                    for f in schema_fields
                    if isinstance(f, dict) and _is_yes_no_field(f)
                ]
                tpl_entry = {
                    "template": {
                        "id": tpl.id,
                        "name": tpl.name,
                        "slug": tpl.slug,
                        "subject_mode": tpl.subject_mode,
                    },
                    "schema_fields": schema_fields,
                    "summary": {
                        "total_reflections": 0,
                        "flag_counts": {
                            k: {"yes": 0, "no": 0, "total": 0} for k in flag_keys
                        },
                    },
                    "rating_series": defaultdict(list),
                    "reflections": [],
                }
                by_template[tpl.id] = tpl_entry
            tpl_entry["summary"]["total_reflections"] += 1
            for fkey, counts in tpl_entry["summary"]["flag_counts"].items():
                raw = (r.answers or {}).get(fkey)
                val = str(raw).lower() if raw is not None else ""
                if val == "yes":
                    counts["yes"] += 1
                    counts["total"] += 1
                elif val == "no":
                    counts["no"] += 1
                    counts["total"] += 1
            for field in schema_fields:
                if not isinstance(field, dict):
                    continue
                ftype = field.get("type")
                if ftype not in ("single_rating", "rating_group"):
                    if ftype in ("text", "textarea"):
                        v = r.answers.get(field.get("key"))
                        if isinstance(v, str) and v.strip():
                            recent_texts.append({
                                "reflection_id": r.id,
                                "template_id": tpl.id,
                                "template_name": tpl.name,
                                "field_key": field.get("key"),
                                "dashboard_role": field.get("dashboard_role"),
                                "text": v.strip()[:1000],
                                "date": r.period_end.isoformat(),
                                "author_name": r.author.full_name if r.author else None,
                                "team_visibility": r.team_visibility,
                            })
                    continue
                ratings = _resolve_rating(field, r.answers)
                scale = field.get("scale") or [1, 5]
                try:
                    scale_max = int(scale[-1])
                except (IndexError, ValueError, TypeError):
                    scale_max = 5
                for label, value in ratings.items():
                    tpl_entry["rating_series"][label].append({
                        "date": r.period_end.isoformat(),
                        "value": value,
                        "reflection_id": r.id,
                        "scale_max": scale_max,
                        "team_visibility": r.team_visibility,
                    })
                    if value is not None:
                        all_series[label].append(
                            (r.period_end, value, r.id, scale_max, r.team_visibility),
                        )
            tpl_entry["reflections"].append({
                "id": r.id,
                "date": r.period_end.isoformat(),
                "author_name": r.author.full_name if r.author else None,
                "team_visibility": r.team_visibility,
                "language": r.language,
                "answers": r.answers or {},
                "assignment_group": (
                    {"id": r.assignment_group_id, "name": r.assignment_group.name}
                    if r.assignment_group_id else None
                ),
            })

        # Convert defaultdicts to lists for JSON serialization
        templates_out = []
        for entry in by_template.values():
            series = []
            for label, points in entry["rating_series"].items():
                series.append({
                    "label": label,
                    "scale_max": (points[0]["scale_max"] if points else 5),
                    "points": points,
                })
            entry["rating_series"] = series
            templates_out.append(entry)

        recent_texts.sort(key=lambda x: x["date"], reverse=True)
        recent_texts = recent_texts[:RECENT_TEXT_LIMIT]

        concerns = _detect_concerning_patterns(all_series, today)

        notes = _subject_notes_for_viewer(viewer_person, subject, org, request.user)
        observations = _observations_for_viewer(viewer_person, subject, org, request.user)

        return Response({
            "subject": {
                "id": subject.id,
                "name": subject.full_name,
                "preferred_name": subject.preferred_name or subject.first_name,
            },
            "subject_profile": _subject_profile(subject, org),
            "period": {"start": cur_start.isoformat(), "end": cur_end.isoformat()},
            "templates": templates_out,
            "recent_texts": recent_texts,
            "concerning_patterns": concerns,
            "notes": notes,
            "observations": observations,
        })
