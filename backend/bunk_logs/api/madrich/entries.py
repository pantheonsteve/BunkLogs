"""Madrich threaded entries and rating trends — Step 4_9 §4.3, §4.4.

GET /api/v1/madrich/entries/            — one card per threaded field
GET /api/v1/madrich/entries/?field_key= — full reverse-chron list for a field
GET /api/v1/madrich/trends/             — rating series for every scored category

Everything here is driven off the template schema. Which fields get a card,
what those cards are called, and which trends exist all come from the
``thread_enabled`` / ``rating_group`` flags, so a Director adding a field to
a template gets a working homepage card with no code change.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from bunk_logs.api.threads.common import entry_body
from bunk_logs.core.models import EntryThread
from bunk_logs.core.models import Reflection
from bunk_logs.core.reflection_threads import excerpt
from bunk_logs.core.reflection_threads import field_prompt
from bunk_logs.core.reflection_threads import threaded_fields
from bunk_logs.core.reflection_threads import trend_fields
from bunk_logs.core.reflection_threads import trend_key_for
from bunk_logs.core.reflection_threads import unread_thread_ids

from .common import assigned_reflections
from .common import viewer_or_403

if TYPE_CHECKING:
    from .common import ViewerContext

CARD_ENTRY_LIMIT = 3


class MadrichEntriesPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


def _assigned_templates(ctx: ViewerContext) -> list:
    """Templates the viewer currently owes, deduplicated by id."""
    seen: set[int] = set()
    templates = []
    for entry in assigned_reflections(ctx):
        if entry.template.id not in seen:
            seen.add(entry.template.id)
            templates.append(entry.template)
    return templates


def _viewer_threads(ctx: ViewerContext):
    """The viewer's own reflection threads, newest activity first."""
    return (
        EntryThread.objects.filter(
            subject_person=ctx.person,
            reflection__isnull=False,
        )
        .select_related("reflection", "reflection__template")
        .order_by("-reflection__period_start", "item_index")
    )


def _entry_row(thread: EntryThread, *, unread: bool) -> dict:
    reflection = thread.reflection
    body = entry_body(thread)
    return {
        "thread_id": thread.id,
        "reflection_id": thread.reflection_id,
        "item_index": thread.item_index,
        "excerpt": excerpt(body),
        "body": body,
        "date": reflection.period_end.isoformat() if reflection else None,
        "period": (
            {
                "start": reflection.period_start.isoformat(),
                "end": reflection.period_end.isoformat(),
            }
            if reflection
            else None
        ),
        "routes_to": thread.routes_to,
        "unread": unread,
        "resolved_at": thread.resolved_at.isoformat() if thread.resolved_at else None,
        "message_count": thread.message_count,
        # §4.3: a teen who routed a question to the Director should be able
        # to tell "nobody has answered yet" from "nothing happened".
        "awaiting_reply": bool(thread.routes_to) and thread.message_count == 0,
    }


def threaded_field_cards(ctx: ViewerContext, limit: int = CARD_ENTRY_LIMIT) -> list[dict]:
    """One card per threaded field on any assigned template.

    Titles come from the template's localized prompt. Ordering follows
    schema order so the homepage matches the form the Madrich filled in.
    """
    from django.db.models import Count

    fields: dict[str, dict] = {}
    for template in _assigned_templates(ctx):
        for field in threaded_fields(template):
            key = field.get("key")
            if key and key not in fields:
                fields[key] = field
    if not fields:
        return []

    threads = list(
        _viewer_threads(ctx)
        .filter(field_key__in=list(fields))
        .annotate(message_count=Count("messages", distinct=True)),
    )
    unread = unread_thread_ids(ctx.person, [t.id for t in threads])

    by_field: dict[str, list[EntryThread]] = {key: [] for key in fields}
    for thread in threads:
        by_field.setdefault(thread.field_key, []).append(thread)

    language = ctx.person.preferred_language or "en"
    cards = []
    for key, field in fields.items():
        rows = by_field.get(key, [])
        cards.append({
            "field_key": key,
            "label": field_prompt(field, language),
            "thread_scope": field.get("thread_scope") or "field",
            "routes_to": field.get("routes_to") or "",
            "total": len(rows),
            "unread_count": sum(1 for t in rows if t.id in unread),
            "entries": [
                _entry_row(t, unread=t.id in unread) for t in rows[:limit]
            ],
        })
    return cards


class MadrichEntriesView(APIView):
    """Threaded entries for the caller.

    Without ``field_key`` this returns the homepage cards. With one it
    returns that field's full reverse-chronological history, paginated.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        ctx = viewer_or_403(request)
        field_key = (request.query_params.get("field_key") or "").strip()
        if not field_key:
            return Response({"cards": threaded_field_cards(ctx)})

        from django.db.models import Count

        field = _field_by_key(ctx, field_key)
        qs = (
            _viewer_threads(ctx)
            .filter(field_key=field_key)
            .annotate(message_count=Count("messages", distinct=True))
        )
        paginator = MadrichEntriesPagination()
        page = list(paginator.paginate_queryset(qs, request, view=self))
        unread = unread_thread_ids(ctx.person, [t.id for t in page])
        response = paginator.get_paginated_response([
            _entry_row(t, unread=t.id in unread) for t in page
        ])
        response.data["field_key"] = field_key
        response.data["label"] = (
            field_prompt(field, ctx.person.preferred_language or "en")
            if field
            else field_key
        )
        return response


def _field_by_key(ctx: ViewerContext, field_key: str) -> dict | None:
    for template in _assigned_templates(ctx):
        for field in threaded_fields(template):
            if field.get("key") == field_key:
                return field
    return None


class MadrichTrendsView(APIView):
    """Rating series for the caller, one per scored category.

    Series are discovered from every ``rating_group`` field on every
    assigned template -- no category is named in code. ``trend_key``
    namespaces the series so renaming a field does not break history.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        ctx = viewer_or_403(request)
        templates = _assigned_templates(ctx)
        if not templates:
            return Response({"series": []})

        reflections = list(
            Reflection.objects.filter(
                author=ctx.person,
                subject=ctx.person,
                is_complete=True,
                template_id__in=[t.id for t in templates],
            ).order_by("period_start"),
        )
        by_template: dict[int, list[Reflection]] = {}
        for reflection in reflections:
            by_template.setdefault(reflection.template_id, []).append(reflection)

        language = ctx.person.preferred_language or "en"
        series = []
        for template in templates:
            rows = by_template.get(template.id, [])
            for field in trend_fields(template):
                series.extend(_field_series(field, rows, language))
        return Response({"series": series})


def _field_series(field: dict, reflections: list[Reflection], language: str) -> list[dict]:
    """One series per category on a ``rating_group`` field."""
    base_key = trend_key_for(field)
    field_key = field.get("key")
    scale = field.get("scale") or [1, 5]
    scale_min, scale_max = scale[0], scale[-1]

    out = []
    for category in field.get("categories") or []:
        cat_key = category.get("key")
        if not cat_key:
            continue
        labels = category.get("labels") or {}
        points = []
        for reflection in reflections:
            value = ((reflection.answers or {}).get(field_key) or {})
            if not isinstance(value, dict):
                continue
            raw = value.get(cat_key)
            if isinstance(raw, (int, float)) and not isinstance(raw, bool):
                points.append({
                    "date": reflection.period_end.isoformat(),
                    "value": raw,
                    "reflection_id": reflection.id,
                })
        out.append({
            "trend_key": f"{base_key}.{cat_key}",
            "field_key": field_key,
            "category_key": cat_key,
            "label": labels.get(language) or labels.get("en") or cat_key,
            "scale_min": scale_min,
            "scale_max": scale_max,
            "points": points,
        })
    return out
