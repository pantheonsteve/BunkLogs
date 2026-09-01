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

from bunk_logs.core.permissions import IsOrgAdminOrSuperuser

from .common import viewer_or_403
from .groups import SUBJECT_BEARING_TYPES
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
        })
