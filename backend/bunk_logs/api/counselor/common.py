"""Shared helpers for counselor read endpoints.

Lifted out of the individual view modules so the dashboard, list, and history
endpoints can answer the same questions ("who are my co-counselors?", "what's
the active camper-reflection template?", "is this reflection editable for me?")
the same way. Keep this small — anything counselor-specific that's also useful
to other roles belongs in ``bunk_logs/core`` instead.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date  # noqa: TC003 - used in dataclass field type
from datetime import datetime  # noqa: TC003 - used in keyword-only arg default annotation
from typing import TYPE_CHECKING

from django.core.cache import cache
from django.db.models import Case
from django.db.models import IntegerField
from django.db.models import Q
from django.db.models import When
from rest_framework.exceptions import PermissionDenied

from bunk_logs.core.assignment_resolution import resolve_template_for
from bunk_logs.core.models import AssignmentGroup
from bunk_logs.core.models import AssignmentGroupMembership
from bunk_logs.core.models import CamperDayState
from bunk_logs.core.models import Membership
from bunk_logs.core.models import Person
from bunk_logs.core.models import Reflection
from bunk_logs.core.models import ReflectionTemplate
from bunk_logs.core.program_scope import operational_author_groups_qs
from bunk_logs.core.time_utils import get_today

if TYPE_CHECKING:
    from bunk_logs.core.models import Organization
    from bunk_logs.core.models import Program


COUNSELOR_ROLES: frozenset[str] = frozenset({"counselor", "junior_counselor"})


@dataclass(frozen=True)
class ViewerContext:
    """Resolved request context for a counselor endpoint."""

    person: Person
    organization: Organization
    today: date


def viewer_or_403(request) -> ViewerContext:
    """Resolve viewer Person + org context or raise 403.

    Counselor endpoints require all of: authenticated user, organization
    context (from middleware), and a Person profile in that org.
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
    return ViewerContext(person=person, organization=org, today=get_today(org))


def resolve_submitted_from_bunk(
    *,
    viewer: Person,
    subject_id: int | None = None,
    bunk_id: int | None = None,
) -> AssignmentGroup | None:
    """Pick the bunk context for a counselor-filed Camper Care request.

    When a camper is selected, prefer the bunk where that camper is on the
    viewer's roster. Otherwise honor an explicit ``bunk_id`` from the client,
    or fall back to the viewer's only bunk.
    """
    bunks = viewer_bunk_groups(viewer)
    if not bunks:
        return None
    by_id = {b.id: b for b in bunks}
    if bunk_id is not None and bunk_id in by_id:
        return by_id[bunk_id]
    if subject_id is not None:
        for bunk in bunks:
            if AssignmentGroupMembership.objects.filter(
                group=bunk,
                person_id=subject_id,
                role_in_group="subject",
                is_active=True,
            ).exists():
                return bunk
    if len(bunks) == 1:
        return bunks[0]
    return None


def viewer_bunk_groups(viewer: Person, *, today: date | None = None) -> list[AssignmentGroup]:
    """Active bunk AssignmentGroups the viewer is an author on.

    "Co-counselor" relationships are derived from author-membership on the
    same bunk groups (decision C4). We surface ``group_type == 'bunk'``
    explicitly so a counselor who also authors on a "unit" group doesn't
    accidentally pull units into the bunk roster.

    Only groups in operational programs (active + within date window) are
    returned so ended sessions do not appear on dashboards.
    """
    if today is None:
        today = get_today(viewer.organization)
    bunk_ids = list(
        operational_author_groups_qs(
            viewer,
            today=today,
            group__group_type="bunk",
        ).values_list("group_id", flat=True),
    )
    if not bunk_ids:
        return []
    return list(
        AssignmentGroup.objects.filter(id__in=bunk_ids).order_by("name"),
    )


def co_counselor_person_ids(viewer: Person, bunks: list[AssignmentGroup]) -> set[int]:
    """Person IDs of OTHER active authors on the viewer's bunks (decision C4).

    Excludes the viewer themselves so "is_self" attribution stays clean.
    """
    if not bunks:
        return set()
    return set(
        AssignmentGroupMembership.objects.filter(
            group__in=bunks,
            role_in_group="author",
            is_active=True,
        )
        .exclude(person=viewer)
        .values_list("person_id", flat=True),
    )


def bunk_camper_persons(bunks: list[AssignmentGroup]) -> dict[int, list[Person]]:
    """Active subject (camper) Persons keyed by bunk ID.

    Sort order is alphabetical by last name + first name (Story 3 criterion 9
    fallback). The optional "bunk-defined position" lives in AGM metadata and
    is not surfaced yet — see Story 58 for the admin-configurable surface.
    """
    if not bunks:
        return {}
    rows = (
        AssignmentGroupMembership.objects.filter(
            group__in=bunks,
            role_in_group="subject",
            is_active=True,
        )
        .select_related("person", "group")
        .order_by("person__last_name", "person__first_name")
    )
    out: dict[int, list[Person]] = {b.id: [] for b in bunks}
    for agm in rows:
        out.setdefault(agm.group_id, []).append(agm.person)
    return out


def off_camp_camper_ids(
    organization: Organization,
    target_date: date,
    camper_ids: list[int] | set[int] | None = None,
) -> set[int]:
    """IDs of campers flagged off-camp on ``target_date`` (Story 3 criterion 8)."""
    qs = CamperDayState.objects.filter(
        organization=organization,
        date=target_date,
        is_off_camp=True,
    )
    if camper_ids is not None:
        qs = qs.filter(camper_id__in=list(camper_ids))
    return set(qs.values_list("camper_id", flat=True))


def _resolve_template(
    qs,
    *,
    organization: Organization,
    program_type: str | None,
) -> ReflectionTemplate | None:
    """Apply the org-shadows-global ordering used throughout Step 7_6.

    Retained as a public helper for legacy call sites (a few tests and
    management commands import it directly). Per-role dashboards now go
    through :func:`resolve_template_for` instead.
    """
    qs = qs.filter(
        Q(organization=organization) | Q(organization__isnull=True),
        is_active=True,
    )
    if program_type:
        qs = qs.filter(Q(program_type=program_type) | Q(program_type__isnull=True))
    return (
        qs.annotate(
            _org_priority=Case(
                When(organization__isnull=True, then=1),
                default=0,
                output_field=IntegerField(),
            ),
        )
        .order_by("_org_priority", "-version")
        .first()
    )


def camper_reflection_template(
    organization: Organization,
    program: Program,
    *,
    viewer: Person | None = None,
    bunk: AssignmentGroup | None = None,
    as_of: date | None = None,
) -> ReflectionTemplate | None:
    """Active daily camper-reflection template for a bunk roster (Story 3).

    Resolves via :func:`resolve_template_for` (Step 7_21): returns the
    template bound by an active ``TemplateAssignment`` for the
    (org, program, ``counselor``, ``single_subject``, ``daily``)
    tuple. When ``bunk`` is supplied, a group-specific assignment is
    preferred; otherwise a program-wide role assignment is used.

    Returns ``None`` when no assignment is active — the dashboard
    surfaces that as the ``no_template`` empty state.
    """
    return resolve_template_for(
        organization=organization,
        program=program,
        as_of=as_of or get_today(organization),
        role="counselor",
        subject_mode="single_subject",
        cadence="daily",
        viewer=viewer,
        assignment_group=bunk,
    )


def counselor_self_template(
    viewer: Person,
    organization: Organization,
    program: Program,
    *,
    as_of: date | None = None,
) -> ReflectionTemplate | None:
    """Active daily self-reflection template that applies to the viewer's role.

    Resolves via :func:`resolve_template_for` (Step 7_21): the viewer's
    active Memberships are inspected and the first assignment whose
    template targets one of those roles (``role`` field or
    ``author_role_filter``) wins. Junior counselors share the counselor
    template by virtue of ``author_role_filter`` matching either role.
    """
    viewer_roles = list(
        Membership.objects.filter(
            person=viewer, program=program, is_active=True,
        ).values_list("role", flat=True),
    )
    if not viewer_roles:
        return None
    anchor = as_of or get_today(organization)
    for role in viewer_roles:
        template = resolve_template_for(
            organization=organization,
            program=program,
            as_of=anchor,
            role=role,
            subject_mode="self",
            cadence="daily",
            viewer=viewer,
        )
        if template is not None:
            return template
    return None


def is_editable_today(
    reflection: Reflection,
    organization: Organization,
    *,
    now: datetime | None = None,
) -> bool:
    """Edit window per Stories 4 & 6: edits allowed iff still within today.

    "Today" is rollover-hour aware (``get_today(org)``). Once the boundary
    passes, the row is locked. Beyond the window, write endpoints (7_6c)
    return 403 — this helper just tells the UI whether to render the Edit
    affordance.
    """
    target_date = get_today(organization, now=now)
    return reflection.period_start <= target_date <= reflection.period_end


def is_truthy_yes_no(value: object) -> bool:
    """Return whether a yes/no schema answer is affirmative.

    Form submissions store ``day_off`` as ``True`` for day-off shortcuts and
    ``"no"`` for normal daily logs (see frontend ``buildReflectionSubmitPayload``).
    """
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"yes", "true", "1"}
    return False


def is_day_off_answer(reflection: Reflection | None) -> bool:
    """A reflection counts as 'day off' if the seeded ``day_off`` field is truthy.

    The counselor self-reflection schema (seeded in 7_6c) includes a ``day_off``
    boolean as the first field. When set, the rest of the schema is hidden
    on the client but the reflection still counts as "complete" for the all-set
    state (Story 5 criterion 3 + Story 9 criterion 1.ii).
    """
    if reflection is None:
        return False
    answers = reflection.answers or {}
    return is_truthy_yes_no(answers.get("day_off"))


def latest_camper_reflection_per_subject(
    template: ReflectionTemplate,
    bunks: list[AssignmentGroup],
    period_start: date,
    period_end: date,
) -> dict[int, Reflection]:
    """Map ``subject_id -> Reflection`` for the period.

    Uses ``Reflection.all_objects`` because the global ``RoleVisibilityFilterBackend``
    on ReflectionViewSet does not run here; we scope by ``assignment_group`` +
    ``template`` + period which is already the visibility surface for an
    author on the bunk.

    Only ``is_complete=True`` rows count toward "submitted" (matching the
    behavior of dashboards/coverage and Story 3's "submitted" definition —
    drafts should not appear as someone else's submission to a co-counselor).
    """
    if not bunks:
        return {}
    rows = (
        Reflection.all_objects.filter(
            template=template,
            assignment_group__in=bunks,
            period_start=period_start,
            period_end=period_end,
            is_complete=True,
        )
        .select_related("author", "assignment_group")
        .order_by("subject_id", "-submitted_at")
    )
    out: dict[int, Reflection] = {}
    for r in rows:
        if r.subject_id and r.subject_id not in out:
            out[r.subject_id] = r
    return out


def latest_self_reflection(
    viewer: Person,
    template: ReflectionTemplate,
    period_start: date,
    period_end: date,
) -> Reflection | None:
    """Most recent ``is_complete=True`` self-reflection for the period."""
    return (
        Reflection.all_objects.filter(
            author=viewer,
            subject=viewer,
            template=template,
            period_start=period_start,
            period_end=period_end,
            is_complete=True,
        )
        .order_by("-submitted_at")
        .first()
    )


def enforce_edit_window(
    reflection: Reflection,
    organization: Organization,
    *,
    now: datetime | None = None,
) -> None:
    """Raise ``PermissionDenied`` if the reflection is outside today's edit window.

    Companion to ``is_editable_today`` for write endpoints. Stories 4 & 6:
    edits allowed iff the reflection's period still includes "today" (rollover
    aware). The bool helper lights up the Edit affordance on the read side;
    this helper enforces it on the write side.
    """
    if is_editable_today(reflection, organization, now=now):
        return
    msg = "This reflection can no longer be edited (the edit window has closed)."
    raise PermissionDenied(msg)


def viewer_can_edit_camper_reflection(
    viewer: Person,
    reflection: Reflection,
) -> bool:
    """Story 4 criterion 2: any active bunk author may edit today's submissions.

    Not just the original author — the second counselor on the same bunk also
    has Edit. Permission is gated on current author-membership of the
    reflection's ``assignment_group``; the viewer does not need to have been
    an author when the row was created.
    """
    if reflection.assignment_group_id is None:
        return False
    return AssignmentGroupMembership.objects.filter(
        group_id=reflection.assignment_group_id,
        person=viewer,
        role_in_group="author",
        is_active=True,
    ).exists()


def dashboard_cache_key(viewer_id: int, organization_id: int, today: date) -> str:
    """Canonical key for the counselor dashboard cache.

    Single source of truth so write paths can target the same keys the
    dashboard view writes. Format mirrors the prior inline key in
    ``dashboard.py``; the prefix exists so future flush hooks can wildcard
    on ``counselor_dashboard:`` if we add a cache backend that supports it.
    """
    return f"counselor_dashboard:{organization_id}:{viewer_id}:{today.isoformat()}"


def invalidate_dashboard_for_viewers(
    organization: Organization,
    viewer_ids: list[int] | set[int],
    today: date,
) -> None:
    """Delete dashboard cache entries for the given viewers on ``today``.

    Write endpoints call this after a successful create/update so the
    affected counselor (and any co-counselors whose all-set state changed)
    see fresh data within seconds. Deliberately limited to "today" — past
    cache entries are TTL-expired well before being meaningful.
    """
    if not viewer_ids:
        return
    keys = [dashboard_cache_key(vid, organization.id, today) for vid in viewer_ids]
    cache.delete_many(keys)


def find_existing_by_client_submission_id(
    manager,
    *,
    program,
    client_submission_id,
):
    """Idempotent replay lookup for write endpoints.

    Returns the existing row if ``(program, client_submission_id)`` already
    has one, else ``None``. Prefer :func:`bunk_logs.core.submission.idempotent_create`
    for new writes — it also handles concurrent duplicate inserts.

    Uses ``all_objects`` so soft-deleted rows still match and block silent
    duplicate creation; if you need to handle resurrection that's a separate
    contract.
    """
    if not client_submission_id or program is None:
        return None
    base = getattr(manager, "all_objects", manager)
    return base.filter(program=program, client_submission_id=client_submission_id).first()


def person_display_name(person: Person | None) -> str:
    """Counselor-facing display: preferred-or-first name + last initial.

    Matches Story 3 criterion 2 ("camper preferred-or-first name + last initial").
    Used for both camper rows and co-counselor attribution.
    """
    if person is None:
        return ""
    first = (person.preferred_name or person.first_name or "").strip()
    last_initial = (person.last_name or "").strip()[:1]
    if first and last_initial:
        return f"{first} {last_initial}."
    return first or last_initial or ""


def person_full_name(person: Person | None) -> str:
    """Full "First Last" name (preferred-or-first + full last name).

    Used where a supervisor needs to identify staff unambiguously (e.g. the
    bunk dashboard's counselor list), unlike :func:`person_display_name` which
    abbreviates the surname to an initial.
    """
    if person is None:
        return ""
    first = (person.preferred_name or person.first_name or "").strip()
    last = (person.last_name or "").strip()
    return f"{first} {last}".strip()
