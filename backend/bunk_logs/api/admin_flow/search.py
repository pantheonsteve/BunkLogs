"""Admin global search (Step 7_13 PR3, Story 60).

``GET /api/v1/admin/search/?q=<query>`` returns the top 25 hits per
content type, ranked by Postgres ``SearchVector`` similarity.

Scope:

* People       -- viewable campers (permission-scoped); links to profile
* Reflections  -- ``answers`` (org admin only)
* Orders       -- org admin only
* Tickets      -- org admin only
* Templates    -- org admin only

Org isolation is enforced via the existing ``OrgScopedManager`` (or
``Membership.program__organization`` for memberships) — never the
``all_objects`` manager. The query also re-asserts ``organization`` in
the ``filter()`` for defence-in-depth in case a future manager change
relaxes the implicit scope.

We do **not** add ``SearchVectorField`` columns or perf indexes here.
At-query-time ``SearchVector`` is good enough for the v1 admin tool;
real fulltext indexes land in Step 7_17 alongside the broader perf
pass.
"""

from __future__ import annotations

from django.contrib.postgres.search import SearchQuery
from django.contrib.postgres.search import SearchRank
from django.contrib.postgres.search import SearchVector
from django.db.models import F
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from bunk_logs.core.models import MaintenanceTicket
from bunk_logs.core.models import Order
from bunk_logs.core.models import Person
from bunk_logs.core.models import Reflection
from bunk_logs.core.models import ReflectionTemplate
from bunk_logs.core.permissions import IsOrgAdminOrSuperuser
from bunk_logs.core.permissions.subject_dashboard import viewable_camper_queryset
from bunk_logs.core.person_search import filter_persons_by_name_query

PER_GROUP_LIMIT = 25
MIN_QUERY_LEN = 2


class AdminGlobalSearchView(APIView):
    """Cross-content search for the admin global search header."""

    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        org = getattr(request, "organization", None)
        if org is None:
            return Response(
                {"detail": "Organization context required."},
                status=status.HTTP_403_FORBIDDEN,
            )
        q = (request.query_params.get("q") or "").strip()
        if len(q) < MIN_QUERY_LEN:
            return Response(
                {"detail": f"q must be at least {MIN_QUERY_LEN} characters."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        viewer = Person.all_objects.filter(user=request.user).first()
        query = SearchQuery(q)
        groups: dict[str, list[dict]] = {
            "people": _search_people(org, viewer, request.user, query, q),
        }
        if IsOrgAdminOrSuperuser().has_permission(request, self):
            groups["reflections"] = _search_reflections(org, query)
            groups["orders"] = _search_orders(org, query)
            groups["tickets"] = _search_tickets(org, query)
            groups["templates"] = _search_templates(org, query)
        return Response({"query": q, "groups": groups})


def _search_people(org, viewer, user, query, raw: str) -> list[dict]:
    """Campers the viewer may open on profile, ranked by name similarity."""
    base = viewable_camper_queryset(viewer, org, user)
    vector = (
        SearchVector("first_name")
        + SearchVector("last_name")
        + SearchVector("preferred_name")
        + SearchVector("email")
    )
    qs = (
        base.annotate(rank=SearchRank(vector, query))
        .filter(rank__gt=0)
        .order_by(F("rank").desc())[:PER_GROUP_LIMIT]
    )
    rows = list(qs)
    if len(rows) < PER_GROUP_LIMIT:
        seen = {p.id for p in rows}
        extra = (
            filter_persons_by_name_query(base, raw)
            .filter(external_ids__icontains=raw)
            .exclude(id__in=seen)[: (PER_GROUP_LIMIT - len(rows))]
        )
        rows.extend(extra)
    return [
        {
            "id": p.id,
            "label": p.full_name,
            "secondary": p.email or "",
            "deep_link": f"/profile/{p.id}",
        }
        for p in rows
    ]


def _search_reflections(org, query) -> list[dict]:
    vector = SearchVector("answers")
    qs = (
        Reflection.all_objects.filter(organization=org)
        .annotate(rank=SearchRank(vector, query))
        .filter(rank__gt=0)
        .select_related("subject", "template")
        .order_by(F("rank").desc())[:PER_GROUP_LIMIT]
    )
    return [
        {
            "id": str(r.id),
            "label": r.template.name if r.template_id else "Reflection",
            "secondary": (
                f"{r.subject.full_name if r.subject_id else 'Unknown'} · "
                f"{r.period_start.isoformat() if r.period_start else ''}"
            ),
            "deep_link": f"/reflections/{r.id}",
        }
        for r in qs
    ]


def _search_orders(org, query) -> list[dict]:
    vector = (
        SearchVector("item")
        + SearchVector("item_note")
        + SearchVector("description")
    )
    qs = (
        Order.all_objects.filter(organization=org)
        .annotate(rank=SearchRank(vector, query))
        .filter(rank__gt=0)
        .order_by(F("rank").desc())[:PER_GROUP_LIMIT]
    )
    return [
        {
            "id": str(o.id),
            "label": o.item or "Camper Care order",
            "secondary": f"{o.get_status_display()} · {o.item_note[:80]}",
            "deep_link": f"/orders/{o.id}",
        }
        for o in qs
    ]


def _search_tickets(org, query) -> list[dict]:
    vector = (
        SearchVector("title")
        + SearchVector("location")
        + SearchVector("description")
    )
    qs = (
        MaintenanceTicket.all_objects.filter(organization=org)
        .annotate(rank=SearchRank(vector, query))
        .filter(rank__gt=0)
        .order_by(F("rank").desc())[:PER_GROUP_LIMIT]
    )
    return [
        {
            "id": str(t.id),
            "label": t.title or "Maintenance ticket",
            "secondary": f"{t.get_status_display()} · {t.location[:80]}",
            "deep_link": f"/maintenance/tickets/{t.id}",
        }
        for t in qs
    ]


def _search_templates(org, query) -> list[dict]:
    vector = SearchVector("name") + SearchVector("description")
    qs = (
        ReflectionTemplate.all_objects.filter(organization=org)
        .annotate(rank=SearchRank(vector, query))
        .filter(rank__gt=0)
        .order_by(F("rank").desc())[:PER_GROUP_LIMIT]
    )
    return [
        {
            "id": t.id,
            "label": t.name,
            "secondary": f"{t.role} · {t.cadence}",
            "deep_link": f"/admin/templates/{t.id}/edit",
        }
        for t in qs
    ]
