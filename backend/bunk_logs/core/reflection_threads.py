"""Turn flagged reflection answers into threads, cohort shares, and trends.

The role homepages (Step 4_9) render whatever the template schema says is
threadable, shareable, or trendable -- no role or field name is hardcoded.
This module is the single place that reads those flags:

* :func:`threadable_entries` / :func:`shareable_entries` walk a schema and
  an answer dict into concrete (field, item) entries.
* :func:`materialize_threads_and_shares` runs on submit and on edit, and is
  idempotent so re-submission refreshes snapshots instead of duplicating.
* :func:`unread_thread_ids` implements the one unread rule every indicator
  on all three homepages uses.

Key invariant: ``EntryThread.routes_to`` is snapshotted at materialize
time. Editing a template must never reroute items already in a queue.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Any

from bunk_logs.core.models import AssignmentGroupMembership
from bunk_logs.core.models import CohortShare
from bunk_logs.core.models import EntryThread
from bunk_logs.core.models import ThreadRead

if TYPE_CHECKING:
    from bunk_logs.core.models import Person
    from bunk_logs.core.models import Program
    from bunk_logs.core.models import Reflection

CLASSROOM = "classroom"
SUBJECT = "subject"

EXCERPT_LEN = 160


def excerpt(text: str, limit: int = EXCERPT_LEN) -> str:
    text = (text or "").strip()
    return text if len(text) <= limit else text[: limit - 1] + "\u2026"


# ---------------------------------------------------------------------------
# Schema flag readers
# ---------------------------------------------------------------------------


def schema_fields(template) -> list[dict]:
    schema = getattr(template, "schema", None) or {}
    fields = schema.get("fields")
    return [f for f in fields if isinstance(f, dict)] if isinstance(fields, list) else []


def field_prompt(field: dict, language: str = "en") -> str:
    """Localized label for a field, falling back to English then the key."""
    prompts = field.get("prompts")
    if isinstance(prompts, dict) and prompts:
        return prompts.get(language) or prompts.get("en") or next(iter(prompts.values()))
    return field.get("key") or ""


def trend_fields(template) -> list[dict]:
    """``rating_group`` fields on a template, in schema order."""
    return [f for f in schema_fields(template) if f.get("type") == "rating_group"]


def trend_key_for(field: dict) -> str:
    """Stable series key: the explicit ``trend_key`` or the field key."""
    declared = field.get("trend_key")
    if isinstance(declared, str) and declared.strip():
        return declared.strip()
    return field.get("key") or ""


def threaded_fields(template) -> list[dict]:
    return [f for f in schema_fields(template) if f.get("thread_enabled") is True]


def _answer_entries(field: dict, value: Any) -> list[tuple[int | None, str]]:
    """Split one answer into ``(item_index, body)`` pairs.

    ``thread_scope="item"`` on a ``text_list`` yields one entry per
    non-empty item; everything else yields a single entry with a null
    index. Empty answers yield nothing, which is what keeps a skipped
    optional field from creating a dangling thread.
    """
    if field.get("thread_scope") == "item" and isinstance(value, list):
        entries = []
        for index, item in enumerate(value):
            body = item.strip() if isinstance(item, str) else ""
            if body:
                entries.append((index, body))
        return entries

    if isinstance(value, list):
        body = "\n".join(str(v).strip() for v in value if str(v).strip())
    elif isinstance(value, str):
        body = value.strip()
    elif value is None or isinstance(value, bool):
        body = ""
    else:
        body = str(value).strip()
    return [(None, body)] if body else []


def threadable_entries(reflection: Reflection) -> list[dict]:
    """Entries on this reflection that should carry a thread.

    Each dict is ``{field, field_key, item_index, body, routes_to}``.
    """
    answers = reflection.answers or {}
    entries: list[dict] = []
    for field in threaded_fields(reflection.template):
        key = field.get("key")
        if not key:
            continue
        routes_to = field.get("routes_to") or ""
        for item_index, body in _answer_entries(field, answers.get(key)):
            entries.append({
                "field": field,
                "field_key": key,
                "item_index": item_index,
                "body": body,
                "routes_to": routes_to,
            })
    return entries


def shareable_entries(reflection: Reflection) -> list[dict]:
    """Entries flagged ``share_with_cohort`` with a non-empty answer."""
    answers = reflection.answers or {}
    entries: list[dict] = []
    for field in schema_fields(reflection.template):
        if field.get("share_with_cohort") is not True:
            continue
        key = field.get("key")
        if not key:
            continue
        for item_index, body in _answer_entries(field, answers.get(key)):
            entries.append({
                "field": field,
                "field_key": key,
                "item_index": item_index,
                "body": body,
            })
    return entries


# ---------------------------------------------------------------------------
# Cohort resolution
# ---------------------------------------------------------------------------


def cohort_group_ids(person: Person, program: Program) -> list[int]:
    """Classroom groups where ``person`` is a subject -- their cohort(s).

    A Madrich in several classrooms has a union feed; callers dedupe on
    the share id rather than picking one group.
    """
    return list(
        AssignmentGroupMembership.all_objects.filter(
            person=person,
            role_in_group=SUBJECT,
            is_active=True,
            group__group_type=CLASSROOM,
            group__program=program,
            group__is_active=True,
        )
        .order_by("group_id")
        .values_list("group_id", flat=True),
    )


# ---------------------------------------------------------------------------
# Materialization
# ---------------------------------------------------------------------------


def materialize_threads_and_shares(reflection: Reflection) -> dict:
    """Create or refresh the threads and cohort shares for one reflection.

    Called from every reflection write path. Returns a small count dict for
    logging and tests. Safe to call repeatedly: threads are keyed on
    ``(reflection, field_key, item_index)`` and share bodies are updated in
    place, so an edit refreshes the snapshot instead of orphaning it.

    A reflection whose template flags nothing creates no rows at all.
    """
    if reflection is None or reflection.template_id is None:
        return {"threads": 0, "shares": 0}

    author = reflection.author or reflection.subject
    if author is None:
        return {"threads": 0, "shares": 0}

    created_threads = 0
    created_shares = 0

    # Cohort shares first: a shared field may also be threaded, and its
    # thread hangs off the reflection entry, not the share, so the share
    # only needs to exist for the feed.
    group_ids = None
    for entry in shareable_entries(reflection):
        if group_ids is None:
            group_ids = cohort_group_ids(author, reflection.program)
        share, was_created = CohortShare.all_objects.update_or_create(
            reflection=reflection,
            field_key=entry["field_key"],
            item_index=entry["item_index"],
            defaults={
                "organization": reflection.organization,
                "program": reflection.program,
                "person": author,
                "assignment_group_id": group_ids[0] if group_ids else None,
                "body": entry["body"],
            },
        )
        created_shares += int(was_created)

    for entry in threadable_entries(reflection):
        _thread, was_created = EntryThread.all_objects.get_or_create(
            reflection=reflection,
            field_key=entry["field_key"],
            item_index=entry["item_index"],
            defaults={
                "organization": reflection.organization,
                "program": reflection.program,
                "subject_person": author,
                "routes_to": entry["routes_to"],
            },
        )
        created_threads += int(was_created)

    # An edit that empties a previously-answered optional field leaves a
    # thread with no subject text. Drop those, but only when nobody has
    # said anything -- a conversation outlives the wording it started on.
    live_keys = {
        (e["field_key"], e["item_index"]) for e in threadable_entries(reflection)
    }
    stale = EntryThread.all_objects.filter(
        reflection=reflection, last_message_at__isnull=True,
    )
    for thread in stale:
        if (thread.field_key, thread.item_index) not in live_keys:
            thread.delete()

    live_share_keys = {
        (e["field_key"], e["item_index"]) for e in shareable_entries(reflection)
    }
    stale_shares = CohortShare.all_objects.filter(reflection=reflection)
    for share in stale_shares:
        if (share.field_key, share.item_index) not in live_share_keys:
            share.delete()

    return {"threads": created_threads, "shares": created_shares}


# ---------------------------------------------------------------------------
# Unread
# ---------------------------------------------------------------------------


def unread_thread_ids(person: Person, thread_ids: list[int] | None = None) -> set[int]:
    """Ids of threads unread by ``person``, optionally narrowed to a set.

    Unread means either a message arrived after their read cursor, or they
    have no cursor at all and somebody else has spoken. A thread whose only
    message is their own is not unread to them.

    Resolved in a fixed number of queries regardless of how many threads
    are passed, so roster and queue rows can be annotated without an N+1.
    """
    if person is None:
        return set()

    threads = EntryThread.all_objects.filter(last_message_at__isnull=False)
    if thread_ids is not None:
        if not thread_ids:
            return set()
        threads = threads.filter(id__in=thread_ids)

    cursors = dict(
        ThreadRead.all_objects.filter(person=person, thread__in=threads)
        .values_list("thread_id", "last_read_at"),
    )
    rows = threads.values_list("id", "last_message_at")

    # Threads with no cursor only count as unread when somebody else wrote
    # the traffic; a Madrich's own self-update shouldn't badge their own page.
    uncursored = [tid for tid, _ in rows if tid not in cursors]
    authored_by_person: set[int] = set()
    if uncursored:
        authored_by_person = set(
            EntryThread.all_objects.filter(
                id__in=uncursored, messages__author=person,
            ).values_list("id", flat=True),
        )

    unread: set[int] = set()
    for thread_id, last_message_at in rows:
        cursor = cursors.get(thread_id)
        if cursor is None:
            if thread_id not in authored_by_person:
                unread.add(thread_id)
        elif last_message_at > cursor:
            unread.add(thread_id)
    return unread
