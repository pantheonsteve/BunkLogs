from __future__ import annotations

from collections import defaultdict
from datetime import date
from datetime import timedelta
from typing import Any

from django.contrib.auth import get_user_model
from django.db.models import Q
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from bunk_logs.core.models import Membership
from bunk_logs.core.models import Person
from bunk_logs.core.models import Program
from bunk_logs.core.models import Reflection

User = get_user_model()

TEAM_DASHBOARD_ROLES = frozenset({"leadership_team", "admin"})
STAFF_COUNT_EXCLUDED_ROLES = frozenset({"camper", "admin"})
LOW_RATING_MAX = 2
TREND_EPS = 0.02


def _viewer_program_unit_scope(viewer: Person, user) -> dict[int, set[str] | None]:
    """program_id -> None = all units; set = restricted to those slugs."""
    merged: dict[int, set[str] | None] = {}
    for m in Membership.objects.filter(
        person=viewer,
        role__in=TEAM_DASHBOARD_ROLES,
        is_active=True,
    ):
        pid = m.program_id
        if m.role == "admin":
            merged[pid] = None
            continue
        raw = m.metadata.get("assigned_unit_slugs")
        if raw is None:
            raw = m.metadata.get("unit_slugs")
        if not raw:
            merged[pid] = None
            continue
        units = {str(x) for x in raw}
        if pid not in merged:
            merged[pid] = set(units)
        elif merged[pid] is None:
            pass
        else:
            merged[pid] = merged[pid] | units
    if merged:
        return merged
    # Legacy app User.role "Admin" / superuser: full access to all programs in the person's org.
    role = getattr(user, "role", "") or ""
    if user.is_superuser or role == User.ADMIN:
        return {
            p.id: None
            for p in Program.objects.filter(organization_id=viewer.organization_id, is_active=True)
        }
    return {}


def _year_round_filter_q() -> Q:
    return Q(tags__contains=["year_round"]) | Q(metadata__employment_type="year_round")


def _staff_queryset(program_id: int, year_round_only: bool):
    qs = Membership.objects.filter(program_id=program_id, is_active=True).exclude(
        role__in=STAFF_COUNT_EXCLUDED_ROLES,
    )
    if year_round_only:
        qs = qs.filter(_year_round_filter_q())
    return qs


def _unit_slugs_for_program(program_id: int, unit_scope: set[str] | None) -> set[str]:
    qs = _staff_queryset(program_id, year_round_only=False).values_list("metadata", flat=True)
    found: set[str] = set()
    for meta in qs:
        if not meta:
            continue
        u = meta.get("unit_slug")
        if u:
            found.add(str(u))
    if unit_scope is None:
        return found
    return found & unit_scope


def _person_ids_for_unit(program_id: int, unit_slug: str, year_round_only: bool) -> set[int]:
    qs = _staff_queryset(program_id, year_round_only).filter(metadata__unit_slug=unit_slug)
    return set(qs.values_list("person_id", flat=True))


def _parse_bool(val: str | None, default: bool = False) -> bool:
    if val is None or val == "":
        return default
    return val.strip().lower() in ("1", "true", "yes", "on")


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


def _avg_ratings(reflections: list[Reflection]) -> dict[str, float]:
    sums: dict[str, float] = defaultdict(float)
    counts: dict[str, int] = defaultdict(int)
    for ref in reflections:
        pairs = _collect_rating_pairs(ref.template.schema, ref.answers)
        for cat, val in pairs:
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
    submitted = {r.person_id for r in reflections}
    return len(submitted & person_ids) / len(person_ids)


class TeamDashboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        org = getattr(request, "organization", None)
        viewer = Person.objects.filter(user=request.user).first()
        if org is None or viewer is None:
            return Response({"detail": "Organization context and person profile required."}, status=403)

        scope = _viewer_program_unit_scope(viewer, request.user)
        if not scope:
            return Response({"detail": "Leadership Team or Admin membership required."}, status=403)

        year_round_only = _parse_bool(request.query_params.get("year_round_only"))
        cur_start, cur_end, prev_start, prev_end = _parse_period(request)
        program_slug = (request.query_params.get("program") or "").strip()
        program_ids = list(scope.keys())
        if program_slug:
            prog = Program.objects.filter(organization=org, slug=program_slug).first()
            if prog is None:
                return Response({"detail": "Program not found."}, status=404)
            if prog.id not in scope:
                return Response({"detail": "No access to this program."}, status=403)
            program_ids = [prog.id]

        units_out: list[dict[str, Any]] = []
        concerning: list[dict[str, Any]] = []
        open_questions: list[dict[str, Any]] = []

        for program_id in program_ids:
            prog = Program.objects.filter(id=program_id).first()
            if prog is None:
                continue
            unit_scope = scope[program_id]
            for unit_slug in sorted(_unit_slugs_for_program(program_id, unit_scope)):
                cur_pids = _person_ids_for_unit(program_id, unit_slug, year_round_only)
                prev_pids = _person_ids_for_unit(program_id, unit_slug, year_round_only)
                total_staff = len(cur_pids)

                cur_refs = list(
                    Reflection.objects.filter(
                        program_id=program_id,
                        person_id__in=cur_pids,
                        period_end__gte=cur_start,
                        period_end__lte=cur_end,
                        is_complete=True,
                    ).select_related("template", "person", "program"),
                )
                prev_refs = list(
                    Reflection.objects.filter(
                        program_id=program_id,
                        person_id__in=prev_pids,
                        period_end__gte=prev_start,
                        period_end__lte=prev_end,
                        is_complete=True,
                    ).select_related("template", "person", "program"),
                )

                cur_rate = _completion_rate(cur_pids, cur_refs)
                prev_rate = _completion_rate(prev_pids, prev_refs)
                cur_avgs = _avg_ratings(cur_refs)
                prev_avgs = _avg_ratings(prev_refs)
                cur_mean = _mean_of_values(cur_avgs)
                prev_mean = _mean_of_values(prev_avgs)

                units_out.append(
                    {
                        "unit_slug": unit_slug,
                        "program_slug": prog.slug,
                        "total_staff": total_staff,
                        "reflections_submitted": len({r.person_id for r in cur_refs}),
                        "completion_rate": round(cur_rate, 4),
                        "prior_completion_rate": round(prev_rate, 4),
                        "completion_trend": _trend_label(cur_rate, prev_rate),
                        "category_averages": {k: round(v, 3) for k, v in sorted(cur_avgs.items())},
                        "prior_category_averages": {k: round(v, 3) for k, v in sorted(prev_avgs.items())},
                        "rating_trend": _trend_label(cur_mean, prev_mean),
                    },
                )

                for ref in cur_refs:
                    for field in ref.template.schema.get("fields") or []:
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
                                        "person_id": ref.person_id,
                                        "unit_slug": unit_slug,
                                        "program_slug": prog.slug,
                                        "template_slug": ref.template.slug,
                                        "period_end": ref.period_end.isoformat(),
                                        "field_key": fkey,
                                        "category": cat,
                                        "value": float(val),
                                    },
                                )

                    for oq_key in _open_question_field_keys(ref.template.schema):
                        text = ref.answers.get(oq_key)
                        if isinstance(text, str) and text.strip():
                            open_questions.append(
                                {
                                    "reflection_id": ref.id,
                                    "person_id": ref.person_id,
                                    "unit_slug": unit_slug,
                                    "program_slug": prog.slug,
                                    "field_key": oq_key,
                                    "period_end": ref.period_end.isoformat(),
                                    "text": text.strip()[:2000],
                                },
                            )

        payload = {
            "period": {
                "current_start": cur_start.isoformat(),
                "current_end": cur_end.isoformat(),
                "prior_start": prev_start.isoformat(),
                "prior_end": prev_end.isoformat(),
            },
            "year_round_only": year_round_only,
            "units": units_out,
            "concerning": concerning,
            "open_questions": open_questions,
        }
        return Response(payload)
