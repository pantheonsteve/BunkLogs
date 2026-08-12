"""``GET faculty/classrooms/<group_id>/availability/`` — Step 4_7 AC4.4.

Classroom-scoped read: faculty (or Madrich) authors of a TBE classroom
``AssignmentGroup`` see availability only for the Madrichim who are
``subject`` members of that same classroom -- never the full-org matrix
(that's ``admin_flow.madrich_availability``, admin-only). No CSV export
for faculty in Tier 1.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.utils.dateparse import parse_date
from rest_framework.exceptions import PermissionDenied
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from bunk_logs.core.models import AssignmentGroup
from bunk_logs.core.models import AssignmentGroupMembership
from bunk_logs.core.models import Membership
from bunk_logs.core.models import Person
from bunk_logs.core.scheduling.availability_matrix import build_matrix_rows
from bunk_logs.core.scheduling.availability_matrix import resolve_session_window
from bunk_logs.core.time_utils import get_today

if TYPE_CHECKING:
    from datetime import date

# Same TBE counterpart-to-counselor roles as the classroom branch of
# ``api/dashboards/group_dashboard_common.py``.
CLASSROOM_AUTHOR_ROLES: frozenset[str] = frozenset({"faculty", "madrich"})
_ACCESS_DENIED_MESSAGE = "You do not have access to this classroom."


def _parse_date_param(raw: str | None, *, label: str) -> date | None:
    if not raw:
        return None
    parsed = parse_date(raw)
    if parsed is None:
        msg = f"Invalid '{label}' parameter; expected YYYY-MM-DD."
        raise ValidationError(msg)
    return parsed


class FacultyClassroomAvailabilityView(APIView):
    """Classroom-scoped Madrich availability for a faculty/madrich author."""

    permission_classes = [IsAuthenticated]

    def get(self, request, group_id: int, *args, **kwargs):
        org = getattr(request, "organization", None)
        if org is None:
            msg = "Organization context required."
            raise PermissionDenied(msg)
        if not request.user.is_authenticated:
            msg = "Authentication required."
            raise PermissionDenied(msg)

        person = Person.objects.filter(user=request.user).first()
        if person is None:
            raise PermissionDenied(_ACCESS_DENIED_MESSAGE)

        group = (
            AssignmentGroup.all_objects.filter(
                id=group_id,
                organization=org,
                is_active=True,
                group_type="classroom",
            )
            .select_related("program")
            .first()
        )
        if group is None:
            raise PermissionDenied(_ACCESS_DENIED_MESSAGE)

        is_author = AssignmentGroupMembership.objects.filter(
            person=person, group=group, role_in_group="author", is_active=True,
        ).exists()
        has_classroom_role = is_author and Membership.objects.filter(
            person=person,
            role__in=tuple(CLASSROOM_AUTHOR_ROLES),
            is_active=True,
            program=group.program,
        ).exists()
        if not has_classroom_role:
            raise PermissionDenied(_ACCESS_DENIED_MESSAGE)

        program = group.program
        subject_person_ids = AssignmentGroupMembership.objects.filter(
            group=group, role_in_group="subject", is_active=True,
        ).values_list("person_id", flat=True)
        memberships = list(
            Membership.objects.filter(
                person_id__in=subject_person_ids,
                program=program,
                role="madrich",
                is_active=True,
            )
            .select_related("person")
            .order_by("person__last_name", "person__first_name"),
        )

        from_date = _parse_date_param(request.query_params.get("from"), label="from")
        to_date = _parse_date_param(request.query_params.get("to"), label="to")
        today = get_today(org)
        session_dates = resolve_session_window(
            program, from_date=from_date, to_date=to_date, today=today,
        )
        rows = build_matrix_rows(program, memberships, session_dates)

        return Response({
            "program": {"id": program.id, "name": program.name, "slug": program.slug},
            "group": {"id": group.id, "name": group.name},
            "sessions": [d.isoformat() for d in session_dates],
            "rows": rows,
        })
