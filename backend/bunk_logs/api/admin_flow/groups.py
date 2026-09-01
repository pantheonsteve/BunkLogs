"""``GET /api/v1/admin/groups/overview/`` -- one row per group, with counts.

The merged Groups list has to answer "does this group have an author, does
it have subjects, and did its logs come in this week" for every group at
once. Composing that from the group list plus the per-group performance
dashboard meant one request per group, so the counts are annotated here in
a single query instead.

``expected`` is the number of active subjects and ``submitted`` the number
of those subjects with a reflection in the trailing week -- the two numbers
behind the completion bar. A group with zero subjects reports 0/0 rather
than 100%, so a staff-only group doesn't read as "fully caught up".
"""

from __future__ import annotations

from datetime import timedelta

from django.db.models import Count
from django.db.models import Q
from rest_framework.response import Response
from rest_framework.views import APIView

from bunk_logs.core.models import AssignmentGroup
from bunk_logs.core.permissions import IsOrgAdminOrSuperuser

from .common import viewer_or_403

SUBMISSION_WINDOW_DAYS = 7

# A group whose type has no subjects by design (a staff team) shouldn't be
# nagged about having none, so the dashboard's "no subjects" warning only
# looks at the types that exist to hold subjects.
SUBJECT_BEARING_TYPES = frozenset({"bunk", "classroom", "caseload", "cohort"})


def submission_window(today):
    """Trailing week ending today -- the period behind "logs this week"."""
    return today - timedelta(days=SUBMISSION_WINDOW_DAYS - 1), today


def annotated_groups(organization, today, *, program_id=None, group_type=None,
                     include_inactive=False):
    """Groups with subject / author / this-week-submission counts attached.

    Shared by the Groups list and the dashboard so both agree on what
    "has an author" and "submitted this week" mean.
    """
    window_start, window_end = submission_window(today)
    qs = AssignmentGroup.all_objects.filter(organization=organization)
    if program_id:
        qs = qs.filter(program_id=program_id)
    if group_type:
        qs = qs.filter(group_type=group_type)
    if not include_inactive:
        qs = qs.filter(is_active=True)

    active_membership = Q(memberships__is_active=True)
    return (
        qs.select_related("parent", "program")
        .annotate(
            subject_count=Count(
                "memberships",
                filter=active_membership & Q(memberships__role_in_group="subject"),
                distinct=True,
            ),
            author_count=Count(
                "memberships",
                filter=active_membership & Q(memberships__role_in_group="author"),
                distinct=True,
            ),
            submitted_count=Count(
                "reflections__subject",
                filter=Q(
                    reflections__period_end__gte=window_start,
                    reflections__period_end__lte=window_end,
                ),
                distinct=True,
            ),
        )
        .order_by("group_type", "display_order", "name")
    )


def serialize_group_row(group) -> dict:
    return {
        "id": group.id,
        "name": group.name,
        "slug": group.slug,
        "group_type": group.group_type,
        "display_order": group.display_order,
        "is_active": group.is_active,
        "program_id": group.program_id,
        "program_name": group.program.name if group.program_id else None,
        "parent_id": group.parent_id,
        "parent_name": group.parent.name if group.parent_id else None,
        "subject_count": group.subject_count,
        "author_count": group.author_count,
        "submitted": group.submitted_count,
        "expected": group.subject_count,
    }


class AdminGroupsOverviewView(APIView):
    """Groups in a program with subject / author / submission counts."""

    permission_classes = [IsOrgAdminOrSuperuser]

    def get(self, request, *args, **kwargs):
        ctx = viewer_or_403(request)
        window_start, window_end = submission_window(ctx.today)

        groups = annotated_groups(
            ctx.organization,
            ctx.today,
            program_id=(request.query_params.get("program") or "").strip() or None,
            group_type=(request.query_params.get("group_type") or "").strip() or None,
            include_inactive=(
                (request.query_params.get("include_inactive") or "").lower() == "true"
            ),
        )
        results = [serialize_group_row(g) for g in groups]

        return Response({
            "window_start": window_start.isoformat(),
            "window_end": window_end.isoformat(),
            "count": len(results),
            "results": results,
        })
