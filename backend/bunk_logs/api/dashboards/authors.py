"""Author Attribution dashboard.

GET /api/v1/dashboards/authors/?date_start=&date_end=&assignment_group=&template=

Returns a list of authors with how many reflections they've submitted in the
window, plus per-day completion counts. Locked behind ``has_supervisor_role``
because raw "who logged the most" leaderboards are easy to misuse — only
supervisors (org admin, leadership, or any author of a group with descendants)
can pull this view up.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date
from datetime import timedelta

from django.db.models import Count
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from bunk_logs.core.filters import reflections_visible_for_user
from bunk_logs.core.models import Reflection
from bunk_logs.core.permissions.visibility import has_supervisor_role

DEFAULT_WINDOW_DAYS = 14
MAX_WINDOW_DAYS = 90


def _parse_date(s: str | None, default: date) -> date:
    if not s:
        return default
    try:
        return date.fromisoformat(s)
    except ValueError:
        return default


class AuthorAttributionView(APIView):
    """Per-author submission counts and timeline. Supervisor-gated."""

    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        org = getattr(request, "organization", None)
        if org is None:
            return Response({"detail": "Organization context required."}, status=403)

        if not has_supervisor_role(request.user):
            return Response(
                {"detail": "Author attribution requires supervisor or admin permissions."},
                status=403,
            )

        today = date.today()
        cur_end = _parse_date(request.query_params.get("date_end"), today)
        cur_start = _parse_date(
            request.query_params.get("date_start"),
            cur_end - timedelta(days=DEFAULT_WINDOW_DAYS - 1),
        )
        if cur_end < cur_start:
            cur_start, cur_end = cur_end, cur_start
        if (cur_end - cur_start).days > MAX_WINDOW_DAYS - 1:
            cur_start = cur_end - timedelta(days=MAX_WINDOW_DAYS - 1)

        base = Reflection.objects.filter(
            period_end__gte=cur_start,
            period_end__lte=cur_end,
            is_complete=True,
            author__isnull=False,
        )
        group_q = (request.query_params.get("assignment_group") or "").strip()
        if group_q.isdigit():
            base = base.filter(assignment_group_id=int(group_q))
        template_q = (request.query_params.get("template") or "").strip()
        if template_q.isdigit():
            base = base.filter(template_id=int(template_q))

        scoped = reflections_visible_for_user(request.user, base)

        # Per-author totals
        author_rows = list(
            scoped.values("author_id", "author__first_name", "author__last_name")
            .annotate(total=Count("id"), subjects=Count("subject_id", distinct=True))
            .order_by("-total"),
        )

        # Per-author per-day counts for the bar chart
        per_day_rows = list(
            scoped.values("author_id", "period_end")
            .annotate(c=Count("id"))
            .values_list("author_id", "period_end", "c"),
        )
        per_author_days: dict[int, dict[str, int]] = defaultdict(dict)
        for author_id, day, c in per_day_rows:
            per_author_days[author_id][day.isoformat()] = c

        days = []
        d = cur_start
        while d <= cur_end:
            days.append(d.isoformat())
            d += timedelta(days=1)

        authors_out = []
        for row in author_rows:
            author_id = row["author_id"]
            authors_out.append({
                "author_id": author_id,
                "name": f"{row['author__first_name']} {row['author__last_name']}".strip(),
                "total_reflections": row["total"],
                "distinct_subjects": row["subjects"],
                "per_day": [
                    {"date": d, "count": per_author_days[author_id].get(d, 0)}
                    for d in days
                ],
            })

        return Response({
            "period": {"start": cur_start.isoformat(), "end": cur_end.isoformat()},
            "days": days,
            "authors": authors_out,
        })
