"""``GET /api/v1/admin/nav-badges/`` -- the two counts the sidebar shows.

People and Groups carry a count badge so the two start-of-year problems
are visible without opening the dashboard. The full dashboard endpoint
answers the same question but also builds the activity feed and six
attention cards, which is far too much work to run on every admin page
load just to render two numbers.
"""

from __future__ import annotations

from rest_framework.response import Response
from rest_framework.views import APIView

from bunk_logs.core.models import EntryThread
from bunk_logs.core.models import TemplateAssignment
from bunk_logs.core.permissions import IsOrgAdminOrSuperuser

from .common import viewer_or_403
from .director import ungrouped_madrichim
from .groups import SUBJECT_BEARING_TYPES
from .groups import _program_for_window
from .groups import annotated_groups
from .people import INVITE_NEVER
from .people import by_invite_status
from .people import invitable_people


def groups_needing_attention(organization, today, program_id=None) -> int:
    """Groups that cannot produce a log: no author, or no subjects.

    A group can be broken both ways at once and still only deserves one
    badge tick, so the two sets are unioned rather than added.
    """
    broken = 0
    for g in annotated_groups(organization, today, program_id=program_id):
        no_author = g.author_count == 0
        no_subjects = (
            g.subject_count == 0 and g.group_type in SUBJECT_BEARING_TYPES
        )
        if no_author or no_subjects:
            broken += 1
    return broken


class AdminNavBadgesView(APIView):
    """Counts for the People and Groups sidebar badges."""

    permission_classes = [IsOrgAdminOrSuperuser]

    def get(self, request, *args, **kwargs):
        ctx = viewer_or_403(request)
        program_id = (request.query_params.get("program") or "").strip() or None

        never_invited = by_invite_status(
            invitable_people(ctx.organization), INVITE_NEVER,
        ).count()

        return Response({
            "people_never_invited": never_invited,
            "groups_needing_attention": groups_needing_attention(
                ctx.organization, ctx.today, program_id,
            ),
            "setup_progress": setup_progress(ctx, program_id),
            "questions_for_you": questions_for_director(ctx, program_id),
        })


def questions_for_director(ctx, program_id) -> int:
    """Open threads routed to the Director, for the My work gate."""
    qs = EntryThread.all_objects.filter(
        organization=ctx.organization,
        resolved_at__isnull=True,
        routes_to__in=(
            EntryThread.ROUTES_TO_DIRECTOR,
            EntryThread.ROUTES_TO_BOTH,
        ),
    )
    if program_id:
        qs = qs.filter(program_id=program_id)
    return qs.count()


def setup_progress(ctx, program_id) -> dict:
    """Same six setup checks as the home page, plus ungrouped Madrichim.

    The sidebar badge is ``done/total`` and disappears once every check
    is complete. Ungrouped Madrichim only add a step while there are some,
    matching the home page, which doesn't show a green tick for that row.
    """
    groups = list(annotated_groups(ctx.organization, ctx.today, program_id=program_id))
    groups_total = len(groups)
    subjects = sum(g.subject_count for g in groups)
    no_author = sum(1 for g in groups if g.author_count == 0)
    no_subjects = sum(
        1 for g in groups
        if g.subject_count == 0 and g.group_type in SUBJECT_BEARING_TYPES
    )
    group_ids = [g.id for g in groups]
    assignments = TemplateAssignment.all_objects.filter(
        organization=ctx.organization,
        assignment_group_id__in=group_ids,
        status__in=(
            TemplateAssignment.Status.SCHEDULED,
            TemplateAssignment.Status.ACTIVE,
        ),
    )
    if program_id:
        assignments = assignments.filter(program_id=program_id)
    with_forms = assignments.values("assignment_group_id").distinct().count()
    without_forms = max(0, groups_total - with_forms)

    open_steps = [
        groups_total == 0,
        subjects == 0,
        groups_total > 0 and without_forms > 0,
        no_author > 0,
        no_subjects > 0,
    ]
    program = _program_for_window(ctx.organization, program_id)
    if program is not None and program.program_type == "religious_school":
        if ungrouped_madrichim(program)["count"] > 0:
            open_steps.append(True)

    total = len(open_steps)
    done = sum(1 for open_step in open_steps if not open_step)
    return {"done": done, "total": total}
