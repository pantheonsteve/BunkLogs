from __future__ import annotations

import csv
import io
from collections import Counter
from collections import defaultdict
from datetime import date
from datetime import timedelta
from typing import Any

from django.contrib.auth import get_user_model
from django.http import HttpResponse
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from bunk_logs.core.models import Membership
from bunk_logs.core.models import Person
from bunk_logs.core.models import Reflection
from bunk_logs.core.models import ReflectionTemplate

User = get_user_model()

TREND_EPS = 0.02
MAX_TEXT_ITEMS = 50
META_FIELD_TYPES = frozenset({"section_header", "instructions"})

# viewer roles that may access templates by template role
_LT_ACCESS = frozenset({"leadership_team", "admin"})
_WELLNESS_ACCESS = frozenset({"camper_care", "health_center", "special_diets", "admin"})
_ADMIN_ONLY = frozenset({"admin"})

TEMPLATE_ROLE_VIEWER_ROLES: dict[str, frozenset[str]] = {
    "leadership_team": _LT_ACCESS,
    "camper_care": _WELLNESS_ACCESS,
    "health_center": _WELLNESS_ACCESS,
    "special_diets": _WELLNESS_ACCESS,
    "wellness": _WELLNESS_ACCESS,
}


def _parse_period(request) -> tuple[date, date, date, date]:
    start_s = (request.query_params.get("period_start") or "").strip()
    end_s = (request.query_params.get("period_end") or "").strip()
    days_s = (request.query_params.get("period_days") or "14").strip()
    try:
        days = max(1, min(90, int(days_s)))
    except ValueError:
        days = 14
    cur_end = date.today()
    if end_s:
        try:
            cur_end = date.fromisoformat(end_s)
        except ValueError:
            pass
    if start_s:
        try:
            cur_start = date.fromisoformat(start_s)
        except ValueError:
            cur_start = cur_end - timedelta(days=days - 1)
    else:
        cur_start = cur_end - timedelta(days=days - 1)
    prev_end = cur_start - timedelta(days=1)
    prev_start = prev_end - timedelta(days=days - 1)
    return cur_start, cur_end, prev_start, prev_end


def _trend_label(current: float | None, prior: float | None) -> str:
    if current is None or prior is None:
        return "flat"
    delta = current - prior
    if delta > TREND_EPS:
        return "up"
    if delta < -TREND_EPS:
        return "down"
    return "flat"


def _viewer_can_access_template(viewer: Person, user, template: ReflectionTemplate) -> bool:
    user_role = getattr(user, "role", "") or ""
    if user.is_superuser or user_role == User.ADMIN:
        return True
    allowed_viewer_roles = TEMPLATE_ROLE_VIEWER_ROLES.get(template.role or "", _ADMIN_ONLY)
    return Membership.objects.filter(
        person=viewer,
        role__in=allowed_viewer_roles,
        is_active=True,
        program__organization_id=viewer.organization_id,
    ).exists()


def _get_reflections(
    template: ReflectionTemplate,
    org_id: int,
    start: date,
    end: date,
) -> list[Reflection]:
    return list(
        Reflection.objects.filter(
            template=template,
            organization_id=org_id,
            period_end__gte=start,
            period_end__lte=end,
            is_complete=True,
        ).select_related("person"),
    )


def _eligible_person_count(template: ReflectionTemplate, org_id: int) -> int:
    qs = Membership.objects.filter(
        program__organization_id=org_id,
        is_active=True,
    )
    if template.role:
        qs = qs.filter(role=template.role)
    if template.program_type:
        qs = qs.filter(program__program_type=template.program_type)
    return qs.values("person_id").distinct().count()


# ── per-field aggregators ─────────────────────────────────────────────────────


def _agg_single_rating(
    field: dict,
    refs: list[Reflection],
    prev_refs: list[Reflection],
) -> dict[str, Any]:
    key = field["key"]
    scale = field.get("scale", [1, 5])
    scale_min, scale_max = int(scale[0]), int(scale[-1])

    def _vals(rlist: list[Reflection]) -> list[float]:
        out = []
        for r in rlist:
            v = r.answers.get(key)
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                out.append(float(v))
        return out

    cur_vals = _vals(refs)
    prev_vals = _vals(prev_refs)
    cur_mean = sum(cur_vals) / len(cur_vals) if cur_vals else None
    prev_mean = sum(prev_vals) / len(prev_vals) if prev_vals else None
    dist = {str(i): 0 for i in range(scale_min, scale_max + 1)}
    for v in cur_vals:
        k = str(int(round(v)))
        if k in dist:
            dist[k] += 1
    return {
        "mean": round(cur_mean, 3) if cur_mean is not None else None,
        "prior_mean": round(prev_mean, 3) if prev_mean is not None else None,
        "trend": _trend_label(cur_mean, prev_mean),
        "response_count": len(cur_vals),
        "distribution": dist,
    }


def _agg_rating_group(
    field: dict,
    refs: list[Reflection],
    prev_refs: list[Reflection],
) -> dict[str, Any]:
    key = field["key"]
    categories = field.get("categories") or []
    scale = field.get("scale", [1, 5])
    scale_min, scale_max = int(scale[0]), int(scale[-1])

    def _collect(rlist: list[Reflection]):
        sums: dict[str, float] = defaultdict(float)
        counts: dict[str, int] = defaultdict(int)
        dists: dict[str, dict[str, int]] = {
            cat["key"]: {str(i): 0 for i in range(scale_min, scale_max + 1)}
            for cat in categories
        }
        for r in rlist:
            block = r.answers.get(key)
            if not isinstance(block, dict):
                continue
            for cat in categories:
                ck = cat["key"]
                v = block.get(ck)
                if isinstance(v, (int, float)) and not isinstance(v, bool):
                    sums[ck] += float(v)
                    counts[ck] += 1
                    sk = str(int(round(float(v))))
                    if sk in dists.get(ck, {}):
                        dists[ck][sk] += 1
        return sums, counts, dists

    cur_sums, cur_counts, cur_dists = _collect(refs)
    prev_sums, prev_counts, _ = _collect(prev_refs)

    cat_data = []
    for cat in categories:
        ck = cat["key"]
        cur_mean = cur_sums[ck] / cur_counts[ck] if cur_counts[ck] else None
        prev_mean = prev_sums[ck] / prev_counts[ck] if prev_counts[ck] else None
        cat_data.append(
            {
                "key": ck,
                "mean": round(cur_mean, 3) if cur_mean is not None else None,
                "prior_mean": round(prev_mean, 3) if prev_mean is not None else None,
                "trend": _trend_label(cur_mean, prev_mean),
                "response_count": cur_counts[ck],
                "distribution": cur_dists.get(ck, {}),
            },
        )
    return {"categories": cat_data}


def _agg_text_list(field: dict, refs: list[Reflection]) -> dict[str, Any]:
    key = field["key"]
    counter: Counter[str] = Counter()
    for r in refs:
        v = r.answers.get(key)
        if isinstance(v, list):
            for item in v:
                if isinstance(item, str) and item.strip():
                    counter[item.strip()] += 1
    items = [{"text": t, "count": c} for t, c in counter.most_common(MAX_TEXT_ITEMS)]
    return {"items": items, "total_mentions": sum(counter.values())}


def _agg_text(field: dict, refs: list[Reflection]) -> dict[str, Any]:
    key = field["key"]
    items = []
    for r in refs:
        v = r.answers.get(key)
        if isinstance(v, str) and v.strip():
            items.append(
                {
                    "reflection_id": r.id,
                    "person_id": r.person_id,
                    "period_end": r.period_end.isoformat(),
                    "text": v.strip()[:2000],
                    "is_read": False,
                },
            )
    items.sort(key=lambda x: x["period_end"], reverse=True)
    return {"items": items[:MAX_TEXT_ITEMS], "total": len(items)}


def _agg_yes_no(field: dict, refs: list[Reflection]) -> dict[str, Any]:
    key = field["key"]
    yes = no = 0
    for r in refs:
        v = r.answers.get(key)
        if v is True or v in ("true", "yes", 1):
            yes += 1
        elif v is False or v in ("false", "no", 0):
            no += 1
    total = yes + no
    return {
        "yes_count": yes,
        "no_count": no,
        "yes_pct": round(yes / total, 4) if total else None,
    }


def _agg_choice(field: dict, refs: list[Reflection]) -> dict[str, Any]:
    key = field["key"]
    counter: Counter[str] = Counter()
    for r in refs:
        v = r.answers.get(key)
        if isinstance(v, str) and v.strip():
            counter[v.strip()] += 1
        elif isinstance(v, list):
            for item in v:
                if isinstance(item, str) and item.strip():
                    counter[item.strip()] += 1
    raw_options = field.get("options") or []
    option_keys = []
    for o in raw_options:
        ok = o.get("key") if isinstance(o, dict) else str(o)
        if ok:
            option_keys.append(ok)
    bars: list[dict[str, Any]] = []
    seen = set()
    for ok in option_keys:
        bars.append({"option": ok, "count": counter.get(ok, 0)})
        seen.add(ok)
    for k, v in counter.most_common():
        if k not in seen:
            bars.append({"option": k, "count": v})
    bars.sort(key=lambda x: -x["count"])
    return {"choices": bars, "response_count": sum(counter.values())}


def _agg_number(field: dict, refs: list[Reflection]) -> dict[str, Any]:
    key = field["key"]
    vals: list[float] = []
    for r in refs:
        v = r.answers.get(key)
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            vals.append(float(v))
    if not vals:
        return {"mean": None, "min": None, "max": None, "response_count": 0}
    return {
        "mean": round(sum(vals) / len(vals), 3),
        "min": min(vals),
        "max": max(vals),
        "response_count": len(vals),
    }


def _agg_date_field(field: dict, refs: list[Reflection]) -> dict[str, Any]:
    key = field["key"]
    values: list[str] = []
    for r in refs:
        v = r.answers.get(key)
        if isinstance(v, str) and v.strip():
            values.append(v.strip())
    values.sort()
    return {"values": values[:MAX_TEXT_ITEMS], "response_count": len(values)}


def _aggregate_field(
    field: dict,
    refs: list[Reflection],
    prev_refs: list[Reflection],
) -> dict[str, Any] | None:
    ftype = field.get("type", "")
    if ftype in META_FIELD_TYPES:
        return None
    if ftype == "single_rating":
        return _agg_single_rating(field, refs, prev_refs)
    if ftype == "rating_group":
        return _agg_rating_group(field, refs, prev_refs)
    if ftype == "text_list":
        return _agg_text_list(field, refs)
    if ftype in ("text", "textarea"):
        return _agg_text(field, refs)
    if ftype == "yes_no":
        return _agg_yes_no(field, refs)
    if ftype in ("single_choice", "multiple_choice"):
        return _agg_choice(field, refs)
    if ftype == "number":
        return _agg_number(field, refs)
    if ftype == "date":
        return _agg_date_field(field, refs)
    return None


# ── CSV export ────────────────────────────────────────────────────────────────


def _build_csv(template: ReflectionTemplate, refs: list[Reflection]) -> str:
    schema_fields = [
        f
        for f in (template.schema.get("fields") or [])
        if isinstance(f, dict) and f.get("type") not in META_FIELD_TYPES
    ]
    out = io.StringIO()
    writer = csv.writer(out)
    headers = ["person_name", "person_id", "period_end", "language"]
    for field in schema_fields:
        ftype = field.get("type", "")
        fkey = field.get("key", "")
        if ftype == "rating_group":
            for cat in field.get("categories") or []:
                headers.append(f"{fkey}__{cat['key']}")
        else:
            headers.append(fkey)
    writer.writerow(headers)
    for r in sorted(refs, key=lambda x: (x.period_end, x.person_id)):
        person_name = ""
        if r.person:
            person_name = f"{r.person.first_name} {r.person.last_name}".strip()
        row: list[Any] = [person_name, r.person_id, r.period_end.isoformat(), r.language]
        for field in schema_fields:
            ftype = field.get("type", "")
            fkey = field.get("key", "")
            v = r.answers.get(fkey)
            if ftype == "rating_group":
                block = v if isinstance(v, dict) else {}
                for cat in field.get("categories") or []:
                    row.append(block.get(cat["key"], ""))
            elif ftype == "text_list":
                row.append("; ".join(str(x) for x in v if x) if isinstance(v, list) else (v or ""))
            else:
                row.append("" if v is None else v)
        writer.writerow(row)
    return out.getvalue()


# ── Views ─────────────────────────────────────────────────────────────────────


class TemplateDashboardView(APIView):
    permission_classes = [IsAuthenticated]

    def _get_template_or_error(self, org, template_id: int):
        tmpl = ReflectionTemplate.objects.filter(id=template_id, organization=org).first()
        if tmpl is None:
            tmpl = ReflectionTemplate.objects.filter(
                id=template_id,
                organization__isnull=True,
            ).first()
        return tmpl

    def get(self, request, template_id: int, *args, **kwargs):
        org = getattr(request, "organization", None)
        viewer = Person.objects.filter(user=request.user).first()
        if org is None or viewer is None:
            return Response(
                {"detail": "Organization context and person profile required."},
                status=403,
            )

        template = self._get_template_or_error(org, template_id)
        if template is None:
            return Response({"detail": "Template not found."}, status=404)

        if not _viewer_can_access_template(viewer, request.user, template):
            return Response({"detail": "Access denied for this template."}, status=403)

        cur_start, cur_end, prev_start, prev_end = _parse_period(request)
        cur_refs = _get_reflections(template, org.id, cur_start, cur_end)
        prev_refs = _get_reflections(template, org.id, prev_start, prev_end)

        person_ids = {r.person_id for r in cur_refs}
        eligible = _eligible_person_count(template, org.id)

        fields_out = []
        for field in template.schema.get("fields") or []:
            if not isinstance(field, dict):
                continue
            ftype = field.get("type", "")
            if ftype in META_FIELD_TYPES:
                continue
            agg = _aggregate_field(field, cur_refs, prev_refs)
            fields_out.append(
                {
                    "key": field.get("key", ""),
                    "type": ftype,
                    "dashboard_role": field.get("dashboard_role"),
                    "data": agg,
                },
            )

        payload: dict[str, Any] = {
            "template": {
                "id": template.id,
                "name": template.name,
                "slug": template.slug,
                "role": template.role,
                "schema": template.schema,
            },
            "period": {
                "current_start": cur_start.isoformat(),
                "current_end": cur_end.isoformat(),
                "prior_start": prev_start.isoformat(),
                "prior_end": prev_end.isoformat(),
            },
            "summary": {
                "person_count": len(person_ids),
                "response_count": len(cur_refs),
                "eligible_count": eligible,
                "completion_rate": round(len(person_ids) / eligible, 4) if eligible else 0.0,
            },
            "fields": fields_out,
        }
        return Response(payload)


class TemplateDashboardExportView(TemplateDashboardView):
    def get(self, request, template_id: int, *args, **kwargs):
        org = getattr(request, "organization", None)
        viewer = Person.objects.filter(user=request.user).first()
        if org is None or viewer is None:
            return Response(
                {"detail": "Organization context and person profile required."},
                status=403,
            )

        template = self._get_template_or_error(org, template_id)
        if template is None:
            return Response({"detail": "Template not found."}, status=404)

        if not _viewer_can_access_template(viewer, request.user, template):
            return Response({"detail": "Access denied for this template."}, status=403)

        cur_start, cur_end, _, __ = _parse_period(request)
        cur_refs = _get_reflections(template, org.id, cur_start, cur_end)
        csv_text = _build_csv(template, cur_refs)
        filename = f"{template.slug}_{cur_start}_{cur_end}.csv"
        response = HttpResponse(csv_text, content_type="text/csv")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response
