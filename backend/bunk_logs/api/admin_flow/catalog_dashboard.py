"""Planning dashboard aggregation for the configurable catalog (PR3).

``GET /api/v1/admin/catalog/planning/`` sums :class:`RequestLineItem`
quantities (and request counts) so admins can plan purchasing/staffing.

Query params:

* ``start`` / ``end``   ISO dates; filter on the parent request's local date.
* ``status``            ``all`` (default) | ``fulfilled`` | ``open``.
* ``store``             store id filter.
* ``group_by``          ``item`` (default) | ``request_type`` | ``store``.
* ``export``            ``csv`` triggers a CSV download (else JSON).

Aggregation runs in Python over a ``select_related`` queryset — request
volumes at a single camp are small, and joining across two parent models
(Order + MaintenanceTicket) in one ORM aggregate is not worth the complexity.
"""

from __future__ import annotations

import csv
import io

from django.http import HttpResponse
from django.utils.dateparse import parse_date
from rest_framework.response import Response
from rest_framework.views import APIView

from bunk_logs.core.models import RequestLineItem
from bunk_logs.core.permissions import IsOrgAdminOrSuperuser
from bunk_logs.core.state_machine import OrderStateMachine

from .common import viewer_or_403

_OPEN_STATUSES = (OrderStateMachine.NEW, OrderStateMachine.IN_PROGRESS)


def _parent_of(line: RequestLineItem):
    return line.order if line.order_id else line.ticket


class AdminCatalogPlanningView(APIView):
    permission_classes = [IsOrgAdminOrSuperuser]

    def get(self, request, *args, **kwargs):
        ctx = viewer_or_403(request)
        org = ctx.organization

        start = parse_date(request.query_params.get("start") or "")
        end = parse_date(request.query_params.get("end") or "")
        status_filter = (request.query_params.get("status") or "all").strip().lower()
        store_filter = request.query_params.get("store")
        group_by = (request.query_params.get("group_by") or "item").strip().lower()
        if group_by not in {"item", "request_type", "store"}:
            group_by = "item"

        qs = (
            RequestLineItem.all_objects.filter(organization=org)
            .select_related(
                "item",
                "item__request_type",
                "item__request_type__store",
                "order",
                "ticket",
            )
        )

        buckets: dict[str, dict] = {}
        total_quantity = 0
        total_requests = 0
        seen_parents: set[str] = set()

        for line in qs:
            parent = _parent_of(line)
            if parent is None:
                continue
            created = getattr(parent, "created_at", None)
            created_date = created.date() if created else None
            if start and created_date and created_date < start:
                continue
            if end and created_date and created_date > end:
                continue
            pstatus = getattr(parent, "status", "")
            if status_filter == "fulfilled" and pstatus != OrderStateMachine.FULFILLED:
                continue
            if status_filter == "open" and pstatus not in _OPEN_STATUSES:
                continue

            item = line.item
            rt = item.request_type if item else None
            store = rt.store if rt else None
            if store_filter and (not store or str(store.id) != str(store_filter)):
                continue

            if group_by == "store":
                key = f"store:{store.id}" if store else "store:none"
                label = store.name if store else "Uncategorized"
            elif group_by == "request_type":
                key = f"rt:{rt.id}" if rt else "rt:none"
                label = rt.name if rt else "Uncategorized"
            else:  # item
                key = f"item:{item.id}" if item else f"label:{line.item_label.lower()}"
                label = item.name if item else (line.item_label or "Free text")

            bucket = buckets.setdefault(key, {
                "key": key,
                "label": label,
                "store": store.name if store else None,
                "request_type": rt.name if rt else None,
                "quantity": 0,
                "request_count": 0,
            })
            bucket["quantity"] += line.quantity
            total_quantity += line.quantity

            parent_key = f"{key}|{line.order_id or line.ticket_id}"
            if parent_key not in seen_parents:
                seen_parents.add(parent_key)
                bucket["request_count"] += 1

        rows = sorted(buckets.values(), key=lambda b: (-b["quantity"], b["label"].lower()))
        total_requests = sum(b["request_count"] for b in rows)

        # Use ``export`` rather than ``format``: DRF reserves the ``format``
        # query param for content negotiation and 404s on unknown values.
        if (request.query_params.get("export") or "").strip().lower() == "csv":
            return self._csv_response(rows, group_by)

        return Response({
            "group_by": group_by,
            "status": status_filter,
            "start": start.isoformat() if start else None,
            "end": end.isoformat() if end else None,
            "totals": {
                "quantity": total_quantity,
                "request_count": total_requests,
                "group_count": len(rows),
            },
            "rows": rows,
        })

    @staticmethod
    def _csv_response(rows: list[dict], group_by: str) -> HttpResponse:
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(["label", "store", "request_type", "quantity", "request_count"])
        for r in rows:
            writer.writerow([
                r["label"], r.get("store") or "", r.get("request_type") or "",
                r["quantity"], r["request_count"],
            ])
        response = HttpResponse(buf.getvalue(), content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = (
            f'attachment; filename="catalog_planning_by_{group_by}.csv"'
        )
        return response
