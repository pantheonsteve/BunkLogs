"""Viewer resolution, permission gates, and payloads for entry threads.

The permission table in Step 4_9 §7 is implemented here and nowhere else.
Reading it top to bottom:

* A Madrich sees threads on their own entries, and cohort-share threads in
  their own cohort. Never a peer's reflection entry.
* Faculty see threads on Madrichim they supervise, except entries routed to
  the Director -- those are deliberately not theirs to read.
* Admin (the Director capability) sees everything inside their program.

Faculty supervision resolves through classroom authorship, which is how TBE
models it, with :func:`viewer_supervises_subject` as the fallback so an
admin-configured ``Supervision`` row also grants access.
"""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field as dataclass_field
from typing import TYPE_CHECKING

from rest_framework.exceptions import PermissionDenied

from bunk_logs.api.classroom_challenges.common import classroom_group_ids_for_role
from bunk_logs.core.models import AssignmentGroupMembership
from bunk_logs.core.models import EntryThread
from bunk_logs.core.models import Membership
from bunk_logs.core.models import Person
from bunk_logs.core.permissions.subject_dashboard import viewer_supervises_subject
from bunk_logs.core.permissions.super_admin import is_super_admin
from bunk_logs.core.program_scope import operational_memberships_qs
from bunk_logs.core.reflection_threads import cohort_group_ids
from bunk_logs.core.reflection_threads import excerpt
from bunk_logs.core.reflection_threads import field_prompt
from bunk_logs.core.reflection_threads import schema_fields
from bunk_logs.core.terminology import term
from bunk_logs.core.time_utils import get_today

if TYPE_CHECKING:
    from datetime import date

    from bunk_logs.core.models import CohortShare
    from bunk_logs.core.models import Organization
    from bunk_logs.core.models import Program
    from bunk_logs.core.models import ThreadMessage

MADRICH = "madrich"
FACULTY = "faculty"
ADMIN = "admin"
SUBJECT = "subject"
AUTHOR = "author"


def display_name(person: Person | None) -> str:
    """Preferred-or-first name plus last name.

    Matches the naming used by the availability matrix and faculty
    dashboard so the same person reads the same on every surface.
    """
    if person is None:
        return ""
    first = (person.preferred_name or person.first_name or "").strip()
    last = (person.last_name or "").strip()
    return f"{first} {last}".strip()


@dataclass
class ThreadViewer:
    """Resolved request context for any thread or cohort endpoint.

    Unlike the per-role contexts, this one serves all three roles: the
    thread endpoints are shared, so the role comes out of the context
    rather than out of which module you are in.
    """

    person: Person
    organization: Organization
    program: Program | None
    today: date
    roles: set[str]
    is_admin: bool
    membership: Membership | None = None
    _supervised_ids: set[int] | None = dataclass_field(default=None, repr=False)
    _cohort_ids: list[int] | None = dataclass_field(default=None, repr=False)

    @property
    def is_faculty(self) -> bool:
        return FACULTY in self.roles

    @property
    def is_madrich(self) -> bool:
        return MADRICH in self.roles

    @property
    def supervised_ids(self) -> set[int]:
        """Person ids of Madrichim this viewer supervises, computed once."""
        if self._supervised_ids is None:
            self._supervised_ids = supervised_subject_ids(self.person, self.program)
        return self._supervised_ids

    @property
    def cohort_ids(self) -> list[int]:
        """Classroom group ids the viewer belongs to as a subject."""
        if self._cohort_ids is None:
            self._cohort_ids = (
                cohort_group_ids(self.person, self.program) if self.program else []
            )
        return self._cohort_ids

    def role_label(self) -> str:
        for role in (ADMIN, FACULTY, MADRICH):
            if role in self.roles:
                return role
        return next(iter(self.roles), "")


def supervised_subject_ids(person: Person, program: Program | None) -> set[int]:
    """Madrichim supervised by ``person``: subjects of classrooms they author.

    Two queries regardless of classroom count, so roster and queue rows
    never fan out into an N+1.
    """
    if person is None or program is None:
        return set()
    group_ids = classroom_group_ids_for_role(person, program, role_in_group=AUTHOR)
    if not group_ids:
        return set()
    return set(
        AssignmentGroupMembership.all_objects.filter(
            group_id__in=group_ids,
            role_in_group=SUBJECT,
            is_active=True,
        ).values_list("person_id", flat=True),
    )


def supervises(viewer: ThreadViewer, subject: Person) -> bool:
    """Whether ``viewer`` supervises ``subject``.

    Classroom authorship first (the TBE shape), then the general
    hierarchy/Supervision resolver so a manually configured supervision
    row is honored too.
    """
    if subject is None:
        return False
    if subject.id in viewer.supervised_ids:
        return True
    return viewer_supervises_subject(viewer.person, subject)


def viewer_from_role_ctx(ctx, role: str) -> ThreadViewer:
    """Build a :class:`ThreadViewer` from an already-resolved per-role context.

    Lets the Madrich, Faculty, and Director dashboards reuse the thread
    scoping helpers without resolving the viewer's memberships a second
    time.
    """
    return ThreadViewer(
        person=ctx.person,
        organization=ctx.organization,
        program=ctx.program,
        today=ctx.today,
        roles={role},
        is_admin=role == ADMIN,
        membership=getattr(ctx, "membership", None),
    )


def routed_queue_qs(viewer: ThreadViewer, routes_to: str):
    """Open threads routed to ``routes_to``, oldest first.

    Takes a routing value (``faculty`` / ``director``), not a role name --
    the Director capability is the ``admin`` role, and conflating the two
    would silently return an empty queue.

    Oldest-first is the point of the surface: the failure mode it exists to
    prevent is a question sitting unanswered for three weeks, so the list
    has to surface age rather than recency.
    """
    return (
        readable_threads_qs(viewer)
        .filter(
            routes_to__in=[routes_to, EntryThread.ROUTES_TO_BOTH],
            resolved_at__isnull=True,
        )
        .order_by("created_at")
    )


def viewer_or_403(request) -> ThreadViewer:
    """Resolve any authenticated org member, or raise 403.

    Deliberately permissive about role -- the thread endpoints are shared
    across all three homepages, and the per-object gates below are what
    actually decide access.
    """
    org = getattr(request, "organization", None)
    if org is None:
        msg = "Organization context required."
        raise PermissionDenied(msg)
    if not request.user.is_authenticated:
        msg = "Authentication required."
        raise PermissionDenied(msg)
    person = Person.objects.filter(user=request.user).first()
    if person is None:
        msg = "Person profile required."
        raise PermissionDenied(msg)

    today = get_today(org)
    memberships = list(
        operational_memberships_qs(person, today=today)
        .select_related("program", "program__organization")
        .order_by("-created_at"),
    )
    roles = {m.role for m in memberships}
    super_admin = is_super_admin(request.user)
    if not memberships and not super_admin:
        msg = "An active membership in this organization is required."
        raise PermissionDenied(msg)

    # Prefer the membership whose role actually owns a homepage, so a
    # person holding both madrich and faculty rows resolves to the
    # supervising program rather than whichever row was created last.
    preferred = next(
        (m for role in (ADMIN, FACULTY, MADRICH) for m in memberships if m.role == role),
        memberships[0] if memberships else None,
    )
    return ThreadViewer(
        person=person,
        organization=org,
        program=preferred.program if preferred else None,
        today=today,
        roles=roles,
        is_admin=ADMIN in roles or super_admin,
        membership=preferred,
    )


# ---------------------------------------------------------------------------
# Permission gates (§7)
# ---------------------------------------------------------------------------


def can_read_thread(viewer: ThreadViewer, thread: EntryThread) -> bool:
    """§7 rows 1-4: who may open this thread at all."""
    if thread.organization_id != viewer.organization.id:
        return False
    if thread.subject_person_id == viewer.person.id:
        return True
    if viewer.is_admin:
        return True

    if thread.cohort_share_id:
        share = thread.cohort_share
        if share.assignment_group_id and share.assignment_group_id in viewer.cohort_ids:
            return True
        return viewer.is_faculty and supervises(viewer, share.person)

    # A director-routed entry is not faculty's to read; "both" is.
    if thread.routes_to == EntryThread.ROUTES_TO_DIRECTOR:
        return False
    return viewer.is_faculty and supervises(viewer, thread.subject_person)


def can_post_to_thread(viewer: ThreadViewer, thread: EntryThread) -> bool:
    """§7 rows 5 and 8: the subject, their supervisor, an admin, or a cohort peer."""
    if not can_read_thread(viewer, thread):
        return False
    # Anyone who can read a cohort post can comment on it, so read access is
    # the whole gate; a resolved thread is closed to everyone.
    return thread.resolved_at is None


def can_resolve_thread(viewer: ThreadViewer, thread: EntryThread) -> bool:
    """§7 row 6: admins always; faculty only on entries routed to them."""
    if not can_read_thread(viewer, thread):
        return False
    if thread.cohort_share_id:
        return False
    if viewer.is_admin:
        return True
    if not viewer.is_faculty:
        return False
    return thread.routes_to in (
        EntryThread.ROUTES_TO_FACULTY,
        EntryThread.ROUTES_TO_BOTH,
    )


def readable_threads_qs(viewer: ThreadViewer):
    """Threads the viewer may read, as a queryset for list endpoints.

    Mirrors :func:`can_read_thread` in bulk. Kept adjacent to it so the two
    cannot drift; the object-level check remains authoritative for detail
    views.
    """
    from django.db.models import Q

    qs = EntryThread.objects.filter(organization=viewer.organization).select_related(
        "subject_person", "reflection", "reflection__template", "cohort_share",
    )
    if viewer.is_admin:
        return qs.filter(program=viewer.program) if viewer.program else qs

    allowed = Q(subject_person=viewer.person)
    if viewer.cohort_ids:
        allowed |= Q(cohort_share__assignment_group_id__in=viewer.cohort_ids)
    if viewer.is_faculty and viewer.supervised_ids:
        allowed |= Q(
            subject_person_id__in=viewer.supervised_ids,
            cohort_share__isnull=True,
        ) & ~Q(routes_to=EntryThread.ROUTES_TO_DIRECTOR)
        allowed |= Q(cohort_share__person_id__in=viewer.supervised_ids)
    return qs.filter(allowed).distinct()


# ---------------------------------------------------------------------------
# Payload builders
# ---------------------------------------------------------------------------


def entry_field_label(
    thread: EntryThread,
    language: str = "en",
    org: Organization | None = None,
) -> str:
    """Human label for the answer a thread hangs off, from the template schema."""
    if thread.cohort_share_id:
        return f"{term(org, 'cohort', capitalize=True)} post"
    reflection = thread.reflection
    if reflection is None or reflection.template is None:
        return thread.field_key
    for field in schema_fields(reflection.template):
        if field.get("key") == thread.field_key:
            return field_prompt(field, language)
    return thread.field_key


def entry_body(thread: EntryThread) -> str:
    """The answer text a thread hangs off, resolved through the item index."""
    if thread.cohort_share_id:
        return thread.cohort_share.body
    reflection = thread.reflection
    if reflection is None:
        return ""
    value = (reflection.answers or {}).get(thread.field_key)
    if thread.item_index is not None and isinstance(value, list):
        if 0 <= thread.item_index < len(value):
            item = value[thread.item_index]
            return item.strip() if isinstance(item, str) else str(item)
        return ""
    if isinstance(value, list):
        return "\n".join(str(v) for v in value)
    return value.strip() if isinstance(value, str) else ("" if value is None else str(value))


def message_payload(message: ThreadMessage, thread: EntryThread) -> dict:
    """One message. ``is_self_update`` drives the visual distinction only."""
    return {
        "id": message.id,
        "author": {
            "id": message.author_id,
            "display_name": display_name(message.author),
            "role": message.author_role_at_write,
        },
        "body": message.body,
        "is_self_update": message.author_id == thread.subject_person_id,
        "created_at": message.created_at.isoformat() if message.created_at else None,
        "edited_at": message.edited_at.isoformat() if message.edited_at else None,
    }


def thread_list_item(
    thread: EntryThread,
    *,
    unread: bool,
    message_count: int = 0,
    last_message: ThreadMessage | None = None,
    today: date | None = None,
    org: Organization | None = None,
) -> dict:
    """A queue or list row: enough to render without opening the thread."""
    body = entry_body(thread)
    age_days = None
    if today is not None and thread.created_at is not None:
        age_days = (today - thread.created_at.date()).days
    return {
        "id": thread.id,
        "subject_person": {
            "id": thread.subject_person_id,
            "display_name": display_name(thread.subject_person),
        },
        "field_key": thread.field_key,
        "field_label": entry_field_label(thread, org=org),
        "item_index": thread.item_index,
        "excerpt": excerpt(body),
        "routes_to": thread.routes_to,
        "resolved_at": thread.resolved_at.isoformat() if thread.resolved_at else None,
        "created_at": thread.created_at.isoformat() if thread.created_at else None,
        "last_message_at": (
            thread.last_message_at.isoformat() if thread.last_message_at else None
        ),
        "last_message_preview": excerpt(last_message.body, 90) if last_message else "",
        "message_count": message_count,
        "unread": unread,
        "age_days": age_days,
        "reflection_id": thread.reflection_id,
        "cohort_share_id": thread.cohort_share_id,
        # Nobody has answered a routed entry yet -- the Madrich should be
        # able to see that it went somewhere (§4.3).
        "awaiting_reply": bool(thread.routes_to) and message_count == 0,
    }


def thread_detail(thread: EntryThread, messages: list[ThreadMessage], viewer: ThreadViewer) -> dict:
    """Full thread: the entry it hangs off, then the conversation."""
    return {
        "id": thread.id,
        "subject_person": {
            "id": thread.subject_person_id,
            "display_name": display_name(thread.subject_person),
        },
        "field_key": thread.field_key,
        "field_label": entry_field_label(thread, org=viewer.organization),
        "item_index": thread.item_index,
        "body": entry_body(thread),
        "routes_to": thread.routes_to,
        "resolved_at": thread.resolved_at.isoformat() if thread.resolved_at else None,
        "created_at": thread.created_at.isoformat() if thread.created_at else None,
        "reflection_id": thread.reflection_id,
        "cohort_share_id": thread.cohort_share_id,
        "period": (
            {
                "start": thread.reflection.period_start.isoformat(),
                "end": thread.reflection.period_end.isoformat(),
            }
            if thread.reflection_id
            else None
        ),
        "can_post": can_post_to_thread(viewer, thread),
        "can_resolve": can_resolve_thread(viewer, thread),
        "messages": [message_payload(m, thread) for m in messages],
    }


def share_payload(
    share: CohortShare,
    *,
    viewer: ThreadViewer,
    like_count: int,
    liked_by_me: bool,
    comment_count: int,
    thread_id: int | None,
    unread: bool = False,
) -> dict:
    """One cohort feed post."""
    is_mine = share.person_id == viewer.person.id
    return {
        "id": share.id,
        "author": {
            "id": share.person_id,
            "display_name": display_name(share.person),
        },
        "is_mine": is_mine,
        "body": share.body,
        "field_key": share.field_key,
        "created_at": share.created_at.isoformat() if share.created_at else None,
        "like_count": like_count,
        "liked_by_me": liked_by_me,
        # Own posts are visible and likeable by others, but not self-likeable.
        "can_like": not is_mine,
        "comment_count": comment_count,
        "thread_id": thread_id,
        "unread": unread,
        "is_hidden": share.is_hidden,
        "can_hide": viewer.is_admin,
    }
