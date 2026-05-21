"""``GET /api/v1/counselor/requests/`` — Stories 7, 8 combined requests list.

Returns the viewer's + their co-counselors' submitted requests on the
viewer's bunks (decision C4). Combines camper-care Orders and Maintenance
tickets into a single list with a ``type`` discriminator, sorted by
``submitted_at`` desc so the freshest activity sits on top.

Default returns OPEN requests (NEW + IN_PROGRESS). Pass ``?status=all`` to
include closed states for the request history pane.
"""

from __future__ import annotations

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from bunk_logs.core.models import MaintenanceTicket
from bunk_logs.core.models import Membership
from bunk_logs.core.models import Order
from bunk_logs.core.state_machine import OrderStateMachine

from .common import co_counselor_person_ids
from .common import person_display_name
from .common import viewer_bunk_groups
from .common import viewer_or_403

OPEN_STATUSES: tuple[str, ...] = (OrderStateMachine.NEW, OrderStateMachine.IN_PROGRESS)


class CounselorRequestsListView(APIView):
    """Combined camper-care + maintenance request list."""

    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        ctx = viewer_or_403(request)
        viewer = ctx.person
        org = ctx.organization

        primary_membership = (
            Membership.objects.filter(person=viewer, is_active=True)
            .select_related("program")
            .order_by("-created_at")
            .first()
        )
        if primary_membership is None or primary_membership.program is None:
            return Response({"requests": []})
        program = primary_membership.program

        bunks = viewer_bunk_groups(viewer)
        co_ids = co_counselor_person_ids(viewer, bunks)
        eligible_person_ids = list(co_ids | {viewer.id})

        membership_id_to_person_id: dict[int, int] = dict(
            Membership.all_objects.filter(
                person_id__in=eligible_person_ids,
                program=program,
            ).values_list("id", "person_id"),
        )
        if not membership_id_to_person_id:
            return Response({"requests": []})

        status_filter = (request.query_params.get("status") or "open").lower()
        if status_filter == "all":
            status_kwargs: dict = {}
        else:
            status_kwargs = {"status__in": OPEN_STATUSES}

        eligible_membership_ids = list(membership_id_to_person_id.keys())

        order_rows = list(
            Order.all_objects.filter(
                organization=org,
                program=program,
                submitted_by_id__in=eligible_membership_ids,
                **status_kwargs,
            )
            .select_related("subject", "submitted_by", "submitted_by__person")
            .order_by("-created_at"),
        )
        ticket_rows = list(
            MaintenanceTicket.all_objects.filter(
                organization=org,
                program=program,
                submitted_by_id__in=eligible_membership_ids,
                **status_kwargs,
            )
            .select_related("submitted_by", "submitted_by__person")
            .order_by("-created_at"),
        )

        results: list[dict] = []
        for o in order_rows:
            submitter_person = o.submitted_by.person if o.submitted_by else None
            is_self = submitter_person == viewer if submitter_person else False
            results.append({
                "type": "camper_care",
                "id": str(o.id),
                "status": o.status,
                "status_label": o.get_status_display(),
                "subject": (
                    {
                        "id": o.subject.id,
                        "name": person_display_name(o.subject),
                    }
                    if o.subject
                    else None
                ),
                "item": o.item or "",
                "item_note": o.item_note or "",
                "submitter": {
                    "is_self": is_self,
                    "name": person_display_name(submitter_person) if not is_self else None,
                },
                "submitted_at": o.created_at.isoformat() if o.created_at else None,
                "updated_at": o.updated_at.isoformat() if o.updated_at else None,
            })
        for t in ticket_rows:
            submitter_person = t.submitted_by.person if t.submitted_by else None
            is_self = submitter_person == viewer if submitter_person else False
            results.append({
                "type": "maintenance",
                "id": str(t.id),
                "status": t.status,
                "status_label": t.get_status_display(),
                "location": t.location or "",
                "category": t.category or "",
                "category_label": t.get_category_display() if t.category else "",
                "urgency": t.urgency or "",
                "urgency_label": t.get_urgency_display() if t.urgency else "",
                "description": t.description or "",
                "photo_count": t.photos.count(),
                "submitter": {
                    "is_self": is_self,
                    "name": person_display_name(submitter_person) if not is_self else None,
                },
                "submitted_at": t.created_at.isoformat() if t.created_at else None,
                "updated_at": t.updated_at.isoformat() if t.updated_at else None,
            })

        # Newest first across the combined list.
        results.sort(key=lambda r: r["submitted_at"] or "", reverse=True)
        return Response({"requests": results})
