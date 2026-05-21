"""``GET /api/v1/counselor/self-reflection/history/`` — Story 6 history view.

Returns the viewer's prior self-reflections in reverse-chronological order,
with explicit "day off" and "no submission" indicators (Story 6 criterion 6).

Pagination: simple page-number scheme. Default 14 entries (~2 weeks) since
the dashboard's self-reflection section is daily; clients fetch more via
``?page=2``.
"""

from __future__ import annotations

from datetime import date as date_type
from datetime import timedelta

from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from bunk_logs.core.models import Membership
from bunk_logs.core.models import Reflection

from .common import counselor_self_template
from .common import is_day_off_answer
from .common import viewer_or_403


class SelfReflectionHistoryPagination(PageNumberPagination):
    page_size = 14
    page_size_query_param = "page_size"
    max_page_size = 60


def _preview_from_answers(answers: dict | None, max_len: int = 120) -> str:
    """Pull the first meaningful text answer for the history row preview.

    Story 6 criterion 3 calls for "date and a preview line"; we don't yet
    know which field a tenant will treat as the "headline", so we just take
    the first non-empty string-typed value we find. The seeded counselor
    template puts ``elaboration`` early, so this works fine in practice.
    """
    if not answers:
        return ""
    for value in answers.values():
        if isinstance(value, str) and value.strip():
            text = value.strip()
            return text if len(text) <= max_len else text[: max_len - 1] + "\u2026"
    return ""


class SelfReflectionHistoryView(APIView):
    """Paginated history of the viewer's own self-reflections."""

    permission_classes = [IsAuthenticated]
    pagination_class = SelfReflectionHistoryPagination

    def get(self, request, *args, **kwargs):
        ctx = viewer_or_403(request)
        viewer = ctx.person
        org = ctx.organization
        today = ctx.today

        primary_membership = (
            Membership.objects.filter(person=viewer, is_active=True)
            .select_related("program")
            .order_by("-created_at")
            .first()
        )
        if primary_membership is None or primary_membership.program is None:
            return Response({"results": [], "count": 0, "next": None, "previous": None})
        program = primary_membership.program

        template = counselor_self_template(viewer, org, program)
        if template is None:
            return Response({"results": [], "count": 0, "next": None, "previous": None})

        # Page covers ``page_size`` consecutive calendar days ending at
        # ``today``. We materialize one row per day so "no submission" gaps
        # render as their own row (Story 6 criterion 6), not as missing data.
        paginator = self.pagination_class()
        page_size = paginator.get_page_size(request) or paginator.page_size
        try:
            page_num = max(1, int(request.query_params.get("page", "1")))
        except (TypeError, ValueError):
            page_num = 1

        # Lower bound: 60 days back (the max page * a few pages). We don't
        # paginate infinitely; counselors who need older data hit the admin
        # surface, not this list.
        max_days = paginator.max_page_size * 5
        oldest = today - timedelta(days=max_days - 1)

        start_offset = (page_num - 1) * page_size
        end_offset = start_offset + page_size - 1
        period_end_window = today - timedelta(days=start_offset)
        period_start_window = today - timedelta(days=end_offset)
        period_start_window = max(period_start_window, oldest)

        reflections_qs = (
            Reflection.all_objects.filter(
                author=viewer,
                subject=viewer,
                template=template,
                period_start__gte=period_start_window,
                period_end__lte=period_end_window,
            )
            .order_by("-period_start", "-submitted_at")
        )

        by_date: dict[date_type, Reflection] = {}
        for r in reflections_qs:
            # If multiple rows exist for one day (shouldn't happen post-7_6c
            # idempotency), the most recent submission wins because of the
            # ordering above.
            if r.period_start not in by_date:
                by_date[r.period_start] = r

        results = []
        cursor = period_end_window
        while cursor >= period_start_window and len(results) < page_size:
            reflection = by_date.get(cursor)
            results.append({
                "date": cursor.isoformat(),
                "submitted": reflection is not None and reflection.is_complete,
                "is_day_off": is_day_off_answer(reflection) if reflection else False,
                "reflection_id": reflection.id if reflection else None,
                "submitted_at": (
                    reflection.submitted_at.isoformat()
                    if reflection and reflection.submitted_at
                    else None
                ),
                "preview": (
                    _preview_from_answers(reflection.answers)
                    if reflection and not is_day_off_answer(reflection)
                    else ""
                ),
                "editable": reflection is not None and cursor == today,
            })
            cursor -= timedelta(days=1)

        total_count = max_days
        has_next = page_num * page_size < total_count
        has_previous = page_num > 1
        return Response({
            "count": total_count,
            "next": page_num + 1 if has_next else None,
            "previous": page_num - 1 if has_previous else None,
            "page": page_num,
            "page_size": page_size,
            "results": results,
        })
