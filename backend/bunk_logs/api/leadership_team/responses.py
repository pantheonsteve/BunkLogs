"""LT Template Responses view (Step 7_12 PR B — Story 53).

``GET /api/v1/leadership-team/templates/<id>/responses/`` returns either:

* ``tab=individual`` — paginated reflections under a template (across
  versions), with filters: date range, respondent multi-select,
  language_of_authorship, ``rating_le``, ``has_free_text``.
* ``tab=aggregate`` — per-dimension rating distributions and averages
  for the filtered date window, plus ``avg_rating_over_time`` (composite
  daily average across all scored fields, computed from the full visible
  reflection set so day filtering does not hide the trend line).

``combine_assignments=true`` includes responses from all assignments of
the same template slug rather than only the matching version chain.
"""

from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING
from typing import Any

from django.db.models import Count
from django.db.models import Q
from django.utils.dateparse import parse_date
from rest_framework.exceptions import NotFound
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from bunk_logs.core.filters import reflections_visible_for_user
from bunk_logs.core.models import AssignmentGroup
from bunk_logs.core.models import AssignmentGroupMembership
from bunk_logs.core.models import Membership
from bunk_logs.core.models import Reflection
from bunk_logs.core.models import ReflectionTemplate
from bunk_logs.core.reflection_scores import _as_float
from bunk_logs.core.reflection_scores import iter_scored_fields
from bunk_logs.core.reflection_scores import scale_max

from .common import admin_only_or_403

if TYPE_CHECKING:
    from datetime import date


MAX_PAGE_SIZE = 100

# Operational placement group types shown under staff names on self-reflection
# responses. Mirrors the admin Assignments sub-tabs (counselor_bunk,
# uh_unit, staff_team) so cohort/custom roster groups are excluded.
_STAFF_ASSIGNMENT_GROUP_TYPES: dict[str, tuple[str, ...]] = {
    "counselor": ("bunk",),
    "junior_counselor": ("bunk",),
    "general_counselor": ("bunk",),
    "unit_head": ("unit",),
    "camper_care": ("unit", "caseload"),
    "kitchen_staff": ("team",),
    "leadership_team": ("team",),
    "specialist": ("team", "specialty"),
    "madrich": ("classroom",),
    "maintenance": ("team",),
    "housekeeping": ("team",),
    "wellness": ("team",),
    "health_center": ("team",),
}
_DEFAULT_STAFF_ASSIGNMENT_GROUP_TYPES = (
    "bunk", "unit", "caseload", "classroom", "team", "specialty",
)


def _allowed_staff_assignment_group_types(
    membership_role: str | None,
    template_role: str | None,
) -> frozenset[str]:
    if membership_role and membership_role in _STAFF_ASSIGNMENT_GROUP_TYPES:
        return frozenset(_STAFF_ASSIGNMENT_GROUP_TYPES[membership_role])
    if template_role and template_role in _STAFF_ASSIGNMENT_GROUP_TYPES:
        return frozenset(_STAFF_ASSIGNMENT_GROUP_TYPES[template_role])
    return frozenset(_DEFAULT_STAFF_ASSIGNMENT_GROUP_TYPES)


def _template_versions(
    organization, template: ReflectionTemplate, *, combine: bool,
):
    """Return queryset of templates this response view covers.

    Without ``combine``, only the explicit template id (single version).
    With ``combine``, all versions under the same slug + org.
    """
    if not combine:
        return ReflectionTemplate.all_objects.filter(pk=template.pk)
    if template.organization_id is None:
        return ReflectionTemplate.all_objects.filter(
            organization__isnull=True, slug=template.slug,
        )
    return ReflectionTemplate.all_objects.filter(
        organization=organization, slug=template.slug,
    )


def _parse_filter_date(raw: str | None, *, field: str) -> date | None:
    if raw is None or not raw.strip():
        return None
    parsed = parse_date(raw)
    if parsed is None:
        msg = f"Invalid '{field}' filter — expected YYYY-MM-DD."
        raise ValidationError(msg)
    return parsed


class LeadershipTeamTemplateResponsesView(APIView):
    """Single endpoint with two tabs: ``individual`` and ``aggregate``."""

    permission_classes = [IsAuthenticated]

    def get(self, request, template_id: int, *args, **kwargs):
        ctx = admin_only_or_403(request)
        try:
            template = ReflectionTemplate.all_objects.get(pk=template_id)
        except ReflectionTemplate.DoesNotExist as exc:
            raise NotFound from exc

        combine = (
            request.query_params.get("combine_assignments") or ""
        ).lower() in {"1", "true"}
        templates_qs = _template_versions(
            ctx.organization, template, combine=combine,
        )

        reflections = reflections_visible_for_user(
            request.user,
            Reflection.objects.filter(
                organization=ctx.organization, template__in=templates_qs,
            ).select_related("template", "author", "subject"),
        )

        date_from = _parse_filter_date(
            request.query_params.get("date_from"), field="date_from",
        )
        date_to = _parse_filter_date(
            request.query_params.get("date_to"), field="date_to",
        )
        reflections_for_trend = reflections
        if date_from:
            reflections = reflections.filter(period_end__gte=date_from)
        if date_to:
            reflections = reflections.filter(period_start__lte=date_to)

        tab = (request.query_params.get("tab") or "individual").lower()
        if tab == "aggregate":
            return Response(
                self._aggregate(
                    reflections,
                    list(templates_qs),
                    reflections_for_trend,
                ),
            )
        return Response(self._individual(request, reflections, template))

    # ------------------------------------------------------------------
    # Individual tab
    # ------------------------------------------------------------------

    def _individual(self, request, reflections, template) -> dict[str, Any]:
        respondents = request.query_params.getlist("respondent")
        if respondents:
            reflections = reflections.filter(
                author_id__in=[r for r in respondents if r.isdigit()],
            )
        language = (request.query_params.get("language") or "").strip()
        if language:
            reflections = reflections.filter(language=language)
        rating_le_raw = request.query_params.get("rating_le")
        if rating_le_raw and rating_le_raw.lstrip("-").isdigit():
            rating_le = int(rating_le_raw)
            reflections = reflections.filter(
                pk__in=self._rating_filter_ids(reflections, rating_le),
            )
        has_free_text = (request.query_params.get("has_free_text") or "").lower()
        if has_free_text in {"1", "true"}:
            reflections = reflections.exclude(answers={})

        page = max(int(request.query_params.get("page") or 1), 1)
        size_raw = int(request.query_params.get("page_size") or 25)
        size = min(max(size_raw, 1), MAX_PAGE_SIZE)
        ordered = reflections.order_by("-period_end", "-updated_at")
        total = ordered.count()
        start = (page - 1) * size
        rows = list(ordered[start:start + size])
        role_in_group = (
            "author"
            if getattr(template, "subject_mode", None) == "self"
            else "subject"
        )
        groups_by_person = self._active_groups_by_person(rows, role_in_group=role_in_group)
        staff_ctx = None
        if getattr(template, "subject_mode", None) == "self":
            staff_ctx = {
                "membership_roles": self._membership_roles_for_rows(rows),
                "template_role": template.role,
            }

        return {
            "tab": "individual",
            "template": {"id": template.pk, "slug": template.slug},
            "total": total,
            "page": page,
            "page_size": size,
            "results": [
                self._serialize_row(r, groups_by_person, staff_ctx=staff_ctx)
                for r in rows
            ],
        }

    @staticmethod
    def _membership_roles_for_rows(rows) -> dict[tuple[int, int], str]:
        """Map ``(person_id, program_id)`` -> active program membership role."""
        keys = {
            (r.subject_id, r.program_id)
            for r in rows
            if r.subject_id and r.program_id
        }
        if not keys:
            return {}
        person_ids = {person_id for person_id, _ in keys}
        program_ids = {program_id for _, program_id in keys}
        lookup: dict[tuple[int, int], str] = {}
        for membership in Membership.all_objects.filter(
            person_id__in=person_ids,
            program_id__in=program_ids,
            is_active=True,
        ).order_by("person_id", "program_id", "-start_date", "id"):
            key = (membership.person_id, membership.program_id)
            lookup.setdefault(key, membership.role)
        return lookup

    @staticmethod
    def _active_groups_by_person(rows, *, role_in_group: str) -> dict[int, list]:
        """Map person_id -> their active group memberships for one page.

        Self-reflection templates use ``role_in_group='author'`` so staff
        see bunk / unit / team assignments under their names. Camper log
        templates use ``role_in_group='subject'`` for the Bunk column.

        One bulk query for the whole page (no N+1). Date-window filtering
        is applied per row at serialization time so a person who changed
        groups mid-summer shows the right assignment for the reflection date.
        """
        person_ids = {r.subject_id for r in rows if r.subject_id}
        if not person_ids:
            return {}
        org_ids = {r.organization_id for r in rows}
        out: dict[int, list] = defaultdict(list)
        memberships = (
            AssignmentGroupMembership.all_objects.filter(
                person_id__in=person_ids,
                role_in_group=role_in_group,
                is_active=True,
                group__is_active=True,
                group__organization_id__in=org_ids,
            )
            .select_related("group")
            .order_by("group__group_type", "group__name")
        )
        for m in memberships:
            out[m.person_id].append(m)
        return out

    @staticmethod
    def _membership_active_on(membership, on_date) -> bool:
        if on_date is None:
            return True
        if membership.start_date and membership.start_date > on_date:
            return False
        return not (membership.end_date and membership.end_date < on_date)

    @staticmethod
    def _rating_filter_ids(reflections, threshold: int) -> list[int]:
        """Return IDs whose primary rating or any scored answer is <= threshold."""
        ids: list[int] = []
        for r in reflections.select_related("template").iterator():
            answers = r.answers or {}
            scored = list(iter_scored_fields(r.template))
            if not scored:
                continue
            for _f, _label, _scale in scored:
                val = _as_float(answers.get(_f.get("key")))
                if val is not None and val <= threshold:
                    ids.append(r.pk)
                    break
        return ids

    @classmethod
    def _serialize_row(
        cls,
        r: Reflection,
        groups_by_person=None,
        *,
        staff_ctx: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        groups_by_person = groups_by_person or {}
        row_date = r.period_end or r.period_start
        if staff_ctx is not None:
            groups = cls._staff_assignment_groups_for_row(
                r,
                groups_by_person.get(r.subject_id, []),
                row_date,
                staff_ctx,
            )
        else:
            groups = [
                {
                    "id": m.group_id,
                    "name": m.group.name,
                    "group_type": m.group.group_type,
                }
                for m in groups_by_person.get(r.subject_id, [])
                if cls._membership_active_on(m, row_date)
            ]
        return {
            "id": r.pk,
            "period_start": r.period_start.isoformat() if r.period_start else None,
            "period_end": r.period_end.isoformat() if r.period_end else None,
            "language": r.language,
            "author": {
                "id": r.author_id,
                "name": r.author.full_name if r.author_id else None,
            } if r.author_id else None,
            "subject": {
                "id": r.subject_id,
                "name": r.subject.full_name if r.subject_id else None,
            } if r.subject_id else None,
            "groups": groups,
            "template_version": r.template.version if r.template_id else None,
            "answers": r.answers or {},
        }

    @classmethod
    def _staff_assignment_groups_for_row(
        cls,
        reflection: Reflection,
        memberships: list[AssignmentGroupMembership],
        row_date,
        staff_ctx: dict[str, Any],
    ) -> list[dict[str, Any]]:
        membership_roles = staff_ctx.get("membership_roles") or {}
        template_role = staff_ctx.get("template_role")
        program_role = membership_roles.get(
            (reflection.subject_id, reflection.program_id),
        )
        allowed_types = _allowed_staff_assignment_group_types(
            program_role, template_role,
        )
        seen_ids: set[int] = set()
        groups: list[dict[str, Any]] = []
        for membership in memberships:
            if not cls._membership_active_on(membership, row_date):
                continue
            group = membership.group
            if group.group_type not in allowed_types:
                continue
            if group.pk in seen_ids:
                continue
            seen_ids.add(group.pk)
            groups.append(
                {
                    "id": group.pk,
                    "name": group.name,
                    "group_type": group.group_type,
                },
            )
        return groups

    # ------------------------------------------------------------------
    # Aggregate tab
    # ------------------------------------------------------------------

    def _aggregate(
        self,
        reflections,
        templates,
        reflections_for_trend,
    ) -> dict[str, Any]:
        row_fields = ("pk", "language", "period_start", "answers", "template_id")
        rows = list(reflections.values(*row_fields))
        trend_rows = list(reflections_for_trend.values(*row_fields))

        per_period: dict[date, int] = defaultdict(int)
        per_language: dict[str, int] = defaultdict(int)
        for r in rows:
            per_period[r["period_start"]] += 1
            per_language[r["language"] or "en"] += 1

        avg_per_dimension = _avg_rating_per_dimension(rows, templates)

        return {
            "tab": "aggregate",
            "total_responses": len(rows),
            "response_volume_per_period": [
                {"period_start": k.isoformat(), "count": v}
                for k, v in sorted(per_period.items()) if k is not None
            ],
            "language_distribution": [
                {"language": k, "count": v}
                for k, v in sorted(per_language.items())
            ],
            "avg_rating_per_dimension": avg_per_dimension,
            "avg_rating_over_time": _avg_rating_over_time(trend_rows, templates),
            "completion_rate_over_time": _completion_rate_over_time(reflections),
        }


def _extract_scored_values(
    answers: dict,
    field: dict,
    label: str,
) -> float | None:
    """Return the numeric rating for ``label`` on this answers blob."""
    key = field.get("key")
    ftype = field.get("type")
    if ftype == "single_rating":
        return _as_float(answers.get(key))
    if ftype != "rating_group":
        return None
    block = answers.get(key) or {}
    if not isinstance(block, dict):
        return None
    suffix = f"{key}__"
    if not label.startswith(suffix):
        return None
    cat_key = label[len(suffix):]
    return _as_float(block.get(cat_key))


def _distribution_for_field(field: dict) -> dict[str, int]:
    scale = field.get("scale") or [1, 5]
    scale_min, scale_max_val = int(scale[0]), int(scale[-1])
    return {str(i): 0 for i in range(scale_min, scale_max_val + 1)}


def _avg_rating_per_dimension(
    rows: list[dict[str, Any]],
    templates: list,
) -> list[dict[str, Any]]:
    ratings_by_key: dict[str, list[float]] = defaultdict(list)
    dists_by_key: dict[str, dict[str, int]] = {}
    scale_by_key: dict[str, int] = {}
    field_by_label: dict[str, dict] = {}
    valid_versions_by_key: dict[str, set[int]] = defaultdict(set)
    templates_by_id = {t.pk: t for t in templates}

    for tpl in templates:
        for field, label, sm in iter_scored_fields(tpl):
            scale_by_key[label] = sm
            field_by_label.setdefault(label, field)
            valid_versions_by_key[label].add(tpl.version)
            if label not in dists_by_key:
                dists_by_key[label] = _distribution_for_field(field)

    for r in rows:
        tpl = templates_by_id.get(r["template_id"])
        if tpl is None:
            continue
        answers = r["answers"] or {}
        for field, label, _sm in iter_scored_fields(tpl):
            val = _extract_scored_values(answers, field, label)
            if val is None:
                continue
            ratings_by_key[label].append(val)
            scale = field.get("scale") or [1, 5]
            scale_min, scale_max_val = int(scale[0]), int(scale[-1])
            bucket = str(max(scale_min, min(scale_max_val, int(round(val)))))
            if bucket in dists_by_key[label]:
                dists_by_key[label][bucket] += 1

    out: list[dict[str, Any]] = []
    for label in sorted(field_by_label.keys()):
        values = ratings_by_key.get(label, [])
        out.append(
            {
                "key": label,
                "avg": (sum(values) / len(values)) if values else None,
                "count": len(values),
                "scale_max": scale_by_key.get(label, scale_max(field_by_label[label])),
                "distribution": dists_by_key.get(label, {}),
                "versions": sorted(valid_versions_by_key.get(label, set())),
            },
        )
    return out


def _avg_rating_over_time(
    rows: list[dict[str, Any]],
    templates: list,
) -> list[dict[str, Any]]:
    """Composite average of every scored value submitted on each day."""
    by_date: dict[date, list[float]] = defaultdict(list)
    templates_by_id = {t.pk: t for t in templates}

    for r in rows:
        tpl = templates_by_id.get(r["template_id"])
        if tpl is None:
            continue
        day = r["period_start"]
        if day is None:
            continue
        answers = r["answers"] or {}
        for field, label, _sm in iter_scored_fields(tpl):
            val = _extract_scored_values(answers, field, label)
            if val is not None:
                by_date[day].append(val)

    return [
        {
            "date": day.isoformat(),
            "avg": (sum(values) / len(values)) if values else None,
            "count": len(values),
        }
        for day, values in sorted(by_date.items())
    ]


def _completion_rate_over_time(reflections) -> list[dict[str, Any]]:
    """Crude completion-rate slice: completed / total grouped by week-of-period_start."""
    rows = (
        reflections.values("period_start")
        .annotate(
            total=Count("pk"),
            done=Count("pk", filter=Q(is_complete=True)),
        )
        .order_by("period_start")
    )
    return [
        {
            "period_start": row["period_start"].isoformat() if row["period_start"] else None,
            "completion_rate": (row["done"] / row["total"]) if row["total"] else 0,
            "total": row["total"],
            "done": row["done"],
        }
        for row in rows
    ]
