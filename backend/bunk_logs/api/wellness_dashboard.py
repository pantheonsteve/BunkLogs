from __future__ import annotations

from collections import defaultdict
from datetime import date
from datetime import timedelta
from typing import Any

from django.contrib.auth import get_user_model
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from bunk_logs.core.models import Membership
from bunk_logs.core.models import Person
from bunk_logs.core.models import Program
from bunk_logs.core.models import Reflection
from bunk_logs.core.permissions import is_super_admin

User = get_user_model()

WELLNESS_SUB_ROLES = ("camper_care", "health_center", "special_diets")
WELLNESS_ACCESS_ROLES = frozenset(set(WELLNESS_SUB_ROLES) | {"admin"})
NON_WELLNESS_EXCLUDED_ROLES = WELLNESS_ACCESS_ROLES | {"camper"}
WELLNESS_KEYWORDS = (
    "wellness",
    "health center",
    "camper care",
    "special diet",
    "infirmary",
    "nurse",
)
LOW_RATING_MAX = 2
TREND_EPS = 0.02
MAX_TEXT_LEN = 2000


def _viewer_program_scope(viewer: Person, user) -> list[int]:
    """Return program ids the viewer can see for the wellness dashboard."""
    program_ids: set[int] = set(
        Membership.objects.filter(
            person=viewer,
            role__in=WELLNESS_ACCESS_ROLES,
            is_active=True,
        ).values_list("program_id", flat=True),
    )
    if program_ids:
        return list(program_ids)
    role = getattr(user, "role", "") or ""
    if is_super_admin(user) or role == User.ADMIN:
        return list(
            Program.objects.filter(
                organization_id=viewer.organization_id,
                is_active=True,
            ).values_list("id", flat=True),
        )
    return []


def _parse_period(request) -> tuple[date, date, date, date]:
    end_s = (request.query_params.get("period_end") or "").strip()
    days_s = (request.query_params.get("period_days") or "14").strip()
    try:
        days = max(1, min(90, int(days_s)))
    except ValueError:
        days = 14
    if end_s:
        try:
            period_end = date.fromisoformat(end_s)
        except ValueError:
            period_end = date.today()
    else:
        period_end = date.today()
    cur_start = period_end - timedelta(days=days - 1)
    prev_end = cur_start - timedelta(days=1)
    prev_start = prev_end - timedelta(days=days - 1)
    return cur_start, period_end, prev_start, prev_end


def _collect_rating_pairs(schema: dict, answers: dict) -> list[tuple[str, float]]:
    out: list[tuple[str, float]] = []
    for field in schema.get("fields") or []:
        if not isinstance(field, dict) or field.get("type") != "rating_group":
            continue
        key = field.get("key")
        if not key:
            continue
        block = answers.get(key)
        if not isinstance(block, dict):
            continue
        for cat, val in block.items():
            if isinstance(val, bool) or not isinstance(val, (int, float)):
                continue
            out.append((str(cat), float(val)))
    return out


def _open_question_field_keys(schema: dict) -> list[str]:
    keys: list[str] = []
    for field in schema.get("fields") or []:
        if not isinstance(field, dict) or field.get("type") != "textarea":
            continue
        k = field.get("key") or ""
        kl = k.lower()
        if "concern" in kl or "question" in kl:
            keys.append(k)
    if keys:
        return keys
    for field in schema.get("fields") or []:
        if isinstance(field, dict) and field.get("type") == "textarea":
            fk = field.get("key")
            if fk:
                return [fk]
    return []


def _all_textarea_keys(schema: dict) -> list[str]:
    out: list[str] = []
    for field in schema.get("fields") or []:
        if isinstance(field, dict) and field.get("type") == "textarea":
            fk = field.get("key")
            if fk:
                out.append(fk)
    return out


def _avg_ratings(reflections: list[Reflection]) -> dict[str, float]:
    sums: dict[str, float] = defaultdict(float)
    counts: dict[str, int] = defaultdict(int)
    for ref in reflections:
        for cat, val in _collect_rating_pairs(ref.template.schema, ref.answers):
            sums[cat] += val
            counts[cat] += 1
    return {c: sums[c] / counts[c] for c in counts if counts[c]}


def _mean_of_values(d: dict[str, float]) -> float | None:
    if not d:
        return None
    return sum(d.values()) / len(d)


def _trend_label(current: float | None, prior: float | None) -> str:
    if current is None or prior is None:
        return "flat"
    delta = current - prior
    if delta > TREND_EPS:
        return "up"
    if delta < -TREND_EPS:
        return "down"
    return "flat"


def _completion_rate(person_ids: set[int], reflections: list[Reflection]) -> float:
    if not person_ids:
        return 0.0
    submitted = {r.subject_id for r in reflections}
    return len(submitted & person_ids) / len(person_ids)


def _person_ids_for_role(program_id: int, role: str) -> set[int]:
    return set(
        Membership.objects.filter(
            program_id=program_id,
            role=role,
            is_active=True,
        ).values_list("person_id", flat=True),
    )


def _looks_like_wellness(text: Any) -> bool:
    if not isinstance(text, str):
        return False
    lowered = text.lower()
    return any(kw in lowered for kw in WELLNESS_KEYWORDS)


class WellnessDashboardView(APIView):
    """Wellness team dashboard: reflections by sub-role, cross-team patterns, completion."""

    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        org = getattr(request, "organization", None)
        viewer = Person.objects.filter(user=request.user).first()
        if org is None or viewer is None:
            return Response(
                {"detail": "Organization context and person profile required."},
                status=403,
            )

        program_ids = _viewer_program_scope(viewer, request.user)
        if not program_ids:
            return Response(
                {"detail": "Wellness team or admin membership required."},
                status=403,
            )

        sub_role_filter = (request.query_params.get("sub_role") or "").strip()
        if sub_role_filter and sub_role_filter not in WELLNESS_SUB_ROLES:
            return Response(
                {
                    "detail": (
                        "Invalid sub_role. Allowed: " + ", ".join(WELLNESS_SUB_ROLES)
                    ),
                },
                status=400,
            )

        program_slug = (request.query_params.get("program") or "").strip()
        if program_slug:
            prog = Program.objects.filter(organization=org, slug=program_slug).first()
            if prog is None:
                return Response({"detail": "Program not found."}, status=404)
            if prog.id not in set(program_ids):
                return Response({"detail": "No access to this program."}, status=403)
            program_ids = [prog.id]

        cur_start, cur_end, prev_start, prev_end = _parse_period(request)
        sub_roles_to_show: tuple[str, ...] = (
            (sub_role_filter,) if sub_role_filter else WELLNESS_SUB_ROLES
        )

        by_sub_role: list[dict[str, Any]] = []
        cross_team_patterns: list[dict[str, Any]] = []
        completion_buckets: list[dict[str, Any]] = []
        total_staff_overall = 0
        total_submitted_overall = 0

        for program_id in program_ids:
            prog = Program.objects.filter(id=program_id).first()
            if prog is None:
                continue

            for role in sub_roles_to_show:
                role_pids = _person_ids_for_role(program_id, role)
                cur_refs = list(
                    Reflection.objects.filter(
                        program_id=program_id,
                        subject_id__in=role_pids,
                        period_end__gte=cur_start,
                        period_end__lte=cur_end,
                        is_complete=True,
                    ).select_related("template", "subject", "program"),
                )
                prev_refs = list(
                    Reflection.objects.filter(
                        program_id=program_id,
                        subject_id__in=role_pids,
                        period_end__gte=prev_start,
                        period_end__lte=prev_end,
                        is_complete=True,
                    ).select_related("template"),
                )

                cur_rate = _completion_rate(role_pids, cur_refs)
                prev_rate = _completion_rate(role_pids, prev_refs)
                cur_avgs = _avg_ratings(cur_refs)
                prev_avgs = _avg_ratings(prev_refs)
                cur_mean = _mean_of_values(cur_avgs)
                prev_mean = _mean_of_values(prev_avgs)

                concerning: list[dict[str, Any]] = []
                open_questions: list[dict[str, Any]] = []
                for ref in cur_refs:
                    schema = ref.template.schema
                    for field in schema.get("fields") or []:
                        if not isinstance(field, dict) or field.get("type") != "rating_group":
                            continue
                        fkey = field.get("key")
                        block = ref.answers.get(fkey) if fkey else None
                        if not isinstance(block, dict):
                            continue
                        for cat, val in block.items():
                            if isinstance(val, bool) or not isinstance(val, (int, float)):
                                continue
                            if float(val) <= LOW_RATING_MAX:
                                concerning.append(
                                    {
                                        "reflection_id": ref.id,
                                        "person_id": ref.subject_id,
                                        "field_key": fkey,
                                        "category": cat,
                                        "value": float(val),
                                        "period_end": ref.period_end.isoformat(),
                                    },
                                )
                    for oq_key in _open_question_field_keys(schema):
                        text = ref.answers.get(oq_key)
                        if isinstance(text, str) and text.strip():
                            open_questions.append(
                                {
                                    "reflection_id": ref.id,
                                    "person_id": ref.subject_id,
                                    "field_key": oq_key,
                                    "period_end": ref.period_end.isoformat(),
                                    "text": text.strip()[:MAX_TEXT_LEN],
                                },
                            )

                submitted_count = len({r.subject_id for r in cur_refs})
                total_staff_overall += len(role_pids)
                total_submitted_overall += submitted_count

                row = {
                    "role": role,
                    "program_slug": prog.slug,
                    "total_staff": len(role_pids),
                    "reflections_submitted": submitted_count,
                    "completion_rate": round(cur_rate, 4),
                    "prior_completion_rate": round(prev_rate, 4),
                    "completion_trend": _trend_label(cur_rate, prev_rate),
                    "category_averages": {
                        k: round(v, 3) for k, v in sorted(cur_avgs.items())
                    },
                    "prior_category_averages": {
                        k: round(v, 3) for k, v in sorted(prev_avgs.items())
                    },
                    "rating_trend": _trend_label(cur_mean, prev_mean),
                    "concerning": concerning,
                    "open_questions": open_questions,
                }
                by_sub_role.append(row)
                completion_buckets.append(
                    {
                        "role": role,
                        "program_slug": prog.slug,
                        "total_staff": len(role_pids),
                        "reflections_submitted": submitted_count,
                        "completion_rate": round(cur_rate, 4),
                    },
                )

            # Cross-team patterns: scan reflections from non-wellness staff
            # for textarea answers that mention wellness keywords.
            non_wellness_pids = set(
                Membership.objects.filter(
                    program_id=program_id,
                    is_active=True,
                )
                .exclude(role__in=NON_WELLNESS_EXCLUDED_ROLES)
                .values_list("person_id", flat=True),
            )
            if non_wellness_pids:
                other_refs = Reflection.objects.filter(
                    program_id=program_id,
                    subject_id__in=non_wellness_pids,
                    period_end__gte=cur_start,
                    period_end__lte=cur_end,
                    is_complete=True,
                ).select_related("template")
                for ref in other_refs:
                    schema = ref.template.schema
                    for fkey in _all_textarea_keys(schema):
                        text = ref.answers.get(fkey)
                        if _looks_like_wellness(text):
                            cross_team_patterns.append(
                                {
                                    "reflection_id": ref.id,
                                    "person_id": ref.subject_id,
                                    "program_slug": prog.slug,
                                    "field_key": fkey,
                                    "template_slug": ref.template.slug,
                                    "template_role": ref.template.role,
                                    "period_end": ref.period_end.isoformat(),
                                    "text": text.strip()[:MAX_TEXT_LEN],
                                },
                            )

        completion_rate_overall = (
            total_submitted_overall / total_staff_overall if total_staff_overall else 0.0
        )

        payload = {
            "period": {
                "current_start": cur_start.isoformat(),
                "current_end": cur_end.isoformat(),
                "prior_start": prev_start.isoformat(),
                "prior_end": prev_end.isoformat(),
            },
            "sub_role_filter": sub_role_filter or None,
            "by_sub_role": by_sub_role,
            "cross_team_patterns": cross_team_patterns,
            "completion": {
                "total_staff": total_staff_overall,
                "reflections_submitted": total_submitted_overall,
                "completion_rate": round(completion_rate_overall, 4),
                "by_sub_role": completion_buckets,
            },
        }
        return Response(payload)
