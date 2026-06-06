"""Visibility helpers for Reflection querysets.

The single source of truth for "which reflections is this user allowed to see?"
Combines author / subject / admin / unit-scoped supervisor / wellness paths
into one composable Q-builder so that every list / dashboard / export endpoint
applies the same rules.
"""

from __future__ import annotations

from datetime import date
from functools import reduce
from operator import or_

from django.contrib.auth import get_user_model
from django.db.models import Q
from django.db.models import QuerySet

from bunk_logs.core.context import get_current_organization
from bunk_logs.core.models import AssignmentGroup
from bunk_logs.core.models import AssignmentGroupMembership
from bunk_logs.core.models import Membership
from bunk_logs.core.models import Person
from bunk_logs.core.models import Reflection
from bunk_logs.core.permissions.super_admin import is_super_admin

User = get_user_model()

# Roles whose reflection visibility is scoped to a set of units via
# ``Membership.metadata.assigned_unit_slugs`` (with ``metadata.unit_slugs`` as a
# legacy alias). ``unit_head`` is intentionally NOT in this set -- unit heads
# get their cross-bunk visibility through the AssignmentGroup descendant walk
# in ``_author_group_ids_with_descendants``, which is a finer-grained mechanism
# than slug matching. After step 3.21 ``camper_care`` is treated as one of
# these supervisors: senior pastoral/clinical leads for the units they're
# assigned to, not a cross-program wellness specialist.
UNIT_SCOPED_SUPERVISOR_ROLES = frozenset({"faculty", "leadership_team", "camper_care"})

# Memberships in these roles get the wellness-template visibility shortcut:
# they see any reflection whose template carries a role in
# ``WELLNESS_TEMPLATE_ROLES``. Reserved for roles whose work is cross-unit by
# nature (nurses, dietitians). ``camper_care`` is intentionally NOT here -- it
# moved to the unit-scoped supervisor capability in step 3.21.
WELLNESS_ROLES = frozenset({"health_center", "medical", "special_diets"})

# Template.role values that the wellness team can read collectively. Includes
# ``camper_care`` so a nurse / dietitian still has visibility into pastoral
# notes about a camper they're co-caring for, even though camper-care staff
# themselves no longer get this shortcut.
WELLNESS_TEMPLATE_ROLES = frozenset({
    "camper_care", "health_center", "medical", "special_diets",
})


def _person_for_user(user) -> Person | None:
    if user is None or not getattr(user, "is_authenticated", False):
        return None
    return Person.all_objects.filter(user=user).first()


def _has_org_admin_membership(person: Person, organization_id: int | None) -> bool:
    qs = Membership.all_objects.filter(person=person, role="admin", is_active=True)
    if organization_id is not None:
        qs = qs.filter(program__organization_id=organization_id)
    return qs.exists()


def _unit_scoped_supervisor_q(person: Person, organization_id: int | None) -> Q | None:
    """Q filter scoping reflections to the unit slugs a supervisor is assigned to.

    Applies to memberships in ``UNIT_SCOPED_SUPERVISOR_ROLES`` (faculty,
    leadership_team, camper_care). For faculty / leadership_team, empty /
    missing ``assigned_unit_slugs`` means no unit restriction (whole program).
    ``camper_care`` never gets that unrestricted branch — caseload bunks come
    from :func:`_camper_care_caseload_q` instead. When ``assigned_unit_slugs``
    is set on a camper_care membership, reflections about subjects whose
    ``metadata.unit_slug`` matches are included here as well.
    """
    qs = Membership.all_objects.filter(
        person=person,
        role__in=UNIT_SCOPED_SUPERVISOR_ROLES,
        is_active=True,
    )
    if organization_id is not None:
        qs = qs.filter(program__organization_id=organization_id)
    memberships = list(qs)
    if not memberships:
        return None

    program_specs: dict[int, dict] = {}
    for m in memberships:
        pid = m.program_id
        raw = m.metadata.get("assigned_unit_slugs")
        if raw is None:
            raw = m.metadata.get("unit_slugs")
        entry = program_specs.setdefault(pid, {"unrestricted": False, "units": set()})
        if m.role == "camper_care":
            if raw:
                entry["units"].update(str(x) for x in raw)
            continue
        if not raw:
            entry["unrestricted"] = True
        else:
            entry["units"].update(str(x) for x in raw)

    parts: list[Q] = []
    for pid, spec in program_specs.items():
        if spec["unrestricted"]:
            parts.append(Q(program_id=pid))
            continue
        unit_slugs = spec["units"]
        if not unit_slugs:
            continue
        person_ids = [
            mem.person_id
            for mem in Membership.all_objects.filter(program_id=pid, is_active=True)
            if str(mem.metadata.get("unit_slug") or "") in unit_slugs
        ]
        if person_ids:
            parts.append(Q(program_id=pid, subject_id__in=person_ids))

    if not parts:
        return None
    return reduce(or_, parts)


def _camper_care_caseload_q(
    person: Person, organization_id: int | None,
) -> Q | None:
    """Q filter scoping camper_care to supervised units/bunks.

    Resolves the same caseload as the Camper Care dashboard: direct bunk
    supervisions, assignment-group supervisions expanded to descendant bunks,
    and author memberships on groups within the program.
    """
    from django.utils import timezone

    from bunk_logs.core.managers import _caseload_bunk_ids_for_membership
    from bunk_logs.core.models import Supervision

    today = timezone.now().date()
    qs = Membership.all_objects.filter(
        person=person,
        role="camper_care",
        is_active=True,
    )
    if organization_id is not None:
        qs = qs.filter(program__organization_id=organization_id)

    parts: list[Q] = []
    for membership in qs:
        bunk_ids = _caseload_bunk_ids_for_membership(
            Supervision.objects, membership, today=today,
        )
        if not bunk_ids:
            continue
        parts.append(
            Q(program_id=membership.program_id, assignment_group_id__in=bunk_ids),
        )
        camper_ids = list(
            AssignmentGroupMembership.all_objects.filter(
                group_id__in=bunk_ids,
                role_in_group="subject",
                is_active=True,
            ).values_list("person_id", flat=True),
        )
        if camper_ids:
            parts.append(
                Q(program_id=membership.program_id, subject_id__in=camper_ids),
            )

    if not parts:
        return None
    return reduce(or_, parts)


def _wellness_q(person: Person) -> Q | None:
    has_wellness = Membership.all_objects.filter(
        person=person,
        role__in=WELLNESS_ROLES,
        is_active=True,
    ).exists()
    if not has_wellness:
        return None
    # The wellness shortcut is a peer-collaboration path -- a private
    # reflection (team_visibility="supervisors_only") must NOT leak through
    # it. Supervisors still see private wellness reflections via paths 1
    # (admin), 2 (author), 4-descendant (ancestor groups), or 5 (unit-scoped
    # supervisor); the gate here only suppresses the cross-program peek.
    return Q(
        template__role__in=WELLNESS_TEMPLATE_ROLES,
        team_visibility=Reflection.TeamVisibility.TEAM,
    )


def _author_group_ids_with_descendants(person: Person) -> set[int]:
    """Return the set of AssignmentGroup ids the person is an author of, plus all
    descendants (children, grandchildren, ...) of those groups.

    Resolved with two bulk queries followed by an in-memory BFS over a parent
    map, so total queries stay constant regardless of group tree depth/size.
    """
    direct, descendants = _author_group_ids_split(person)
    return direct | descendants


def _supervision_authored_q(person: Person, organization_id: int | None) -> Q | None:
    """Q filter for reflections reachable via the ``core.Supervision`` model.

    Two patterns covered:

    * ``MEMBERSHIP`` supervision (UH → Counselor, LT → Specialist, …):
      viewer's active Memberships are supervisors of one or more target
      Memberships. Each target Membership has a Person; that Person's
      authored ``AssignmentGroup``s carry reflections we want to surface.
      Visibility on those groups is supervisor-pipe semantics — we
      ignore ``team_visibility`` because the whole point of the
      supervisor relationship is to see "supervisors_only" content.
    * ``BUNK`` supervision (Camper Care over caseload bunks): viewer
      directly supervises an ``AssignmentGroup``; reflections on that
      group flow to viewer regardless of authorship.

    Returns ``None`` when the viewer has no active supervisions so the
    OR builder in :func:`reflections_visible_to` can skip the empty
    branch cleanly.
    """
    from bunk_logs.core.models import Supervision

    today = date.today()
    sup_qs = Supervision.all_objects.filter(
        supervisor_membership__person=person,
        supervisor_membership__is_active=True,
        start_date__lte=today,
    ).filter(Q(end_date__isnull=True) | Q(end_date__gte=today))
    if organization_id is not None:
        sup_qs = sup_qs.filter(
            supervisor_membership__program__organization_id=organization_id,
        )

    membership_target_person_ids: set[int] = set()
    bunk_ids: set[int] = set()
    for sup in sup_qs.select_related("target_membership", "target_bunk").only(
        "id", "target_type", "target_membership__person_id", "target_bunk_id",
    ):
        if sup.target_type == "membership" and sup.target_membership_id:
            person_id = getattr(sup.target_membership, "person_id", None)
            if person_id:
                membership_target_person_ids.add(person_id)
        elif sup.target_type == "bunk" and sup.target_bunk_id:
            bunk_ids.add(sup.target_bunk_id)

    parts: list[Q] = []

    if membership_target_person_ids:
        # Find the authored AssignmentGroups for each supervised Person.
        sup_group_ids = set(
            AssignmentGroupMembership.all_objects.filter(
                person_id__in=membership_target_person_ids,
                role_in_group="author",
                is_active=True,
                group__is_active=True,
            ).values_list("group_id", flat=True),
        )
        if sup_group_ids:
            parts.append(Q(assignment_group_id__in=sup_group_ids))
        # Also surface the supervised Persons' OWN self-reflections (UH's
        # supervisor pipe into their counselors' self-reflections).
        parts.append(Q(author_id__in=membership_target_person_ids,
                       subject_id__in=membership_target_person_ids))

    if bunk_ids:
        parts.append(Q(assignment_group_id__in=bunk_ids))

    if not parts:
        return None
    return reduce(or_, parts)


def _author_group_ids_split(person: Person) -> tuple[set[int], set[int]]:
    """Return ``(direct_ids, descendant_only_ids)`` for the person's authoring memberships.

    ``direct_ids`` is the set of groups where the person is a direct author --
    they're a peer of anyone else authoring in the same group.
    ``descendant_only_ids`` is the set of groups that are children /
    grandchildren / ... of a direct-author group BUT are themselves not
    directly authored by the person. They represent the supervisor pipe (unit
    head -> bunk; division head -> unit) and are kept separate so step 3.22
    can gate peer visibility independently of supervisor visibility.

    Same two-query BFS as ``_author_group_ids_with_descendants``; the split is
    bookkeeping over the visited set.
    """
    direct_ids = set(
        AssignmentGroupMembership.all_objects.filter(
            person=person,
            role_in_group="author",
            is_active=True,
        ).values_list("group_id", flat=True),
    )
    if not direct_ids:
        return set(), set()

    children_map: dict[int, list[int]] = {}
    rows = AssignmentGroup.all_objects.filter(
        organization_id=person.organization_id,
        is_active=True,
        parent_id__isnull=False,
    ).values_list("parent_id", "id")
    for parent_id, child_id in rows:
        children_map.setdefault(parent_id, []).append(child_id)

    visited = set(direct_ids)
    queue: list[int] = list(direct_ids)
    while queue:
        node = queue.pop()
        for child_id in children_map.get(node, ()):
            if child_id not in visited:
                visited.add(child_id)
                queue.append(child_id)
    descendant_only_ids = visited - direct_ids
    return direct_ids, descendant_only_ids


def reflections_visible_to(
    user,
    queryset: QuerySet[Reflection] | None = None,
) -> QuerySet[Reflection]:
    """Return the set of reflections this user is permitted to see.

    Visibility paths (combined with OR):

    1. Superuser or active org-admin Membership -> everything in current org.
    2. Author of the reflection -> always.
    3. Subject of the reflection AND template.subject_visible=True -> always.
    4. Either (a) author of an ANCESTOR of the reflection's AssignmentGroup
       (the supervisor pipe -- unit head sees their bunks via the descendant
       walk), or (b) direct author of the same group when the reflection's
       ``team_visibility == "team"`` (the peer-collaboration path; private
       entries opt out).
    5. Unit-scoped supervisor membership (faculty / leadership_team /
       camper_care) -> reflections about subjects whose Membership.metadata
       declares one of the assigned unit slugs; faculty / leadership_team
       with empty ``assigned_unit_slugs`` see the whole program.
    5b. Camper Care caseload -> reflections on supervised bunks (via
       ``Supervision`` / author memberships) or about campers in those bunks.
    6. Wellness membership (health_center / special_diets) -> reflections
       whose template carries one of the wellness roles AND
       ``team_visibility == "team"`` (private wellness entries are gated to
       paths 1/2/4-descendant/5).

    All paths are scoped to ``request.organization`` (or whatever the current
    org context is). Cross-tenant rows are unreachable because the base queryset
    uses ``Reflection.objects`` (org-scoped manager).
    """
    if queryset is None:
        queryset = Reflection.objects.all()

    if user is None or not getattr(user, "is_authenticated", False):
        return queryset.none()

    person = _person_for_user(user)
    if person is None:
        # Super Admin without a Person profile still gets full org visibility.
        if is_super_admin(user):
            org = get_current_organization()
            if org is None:
                return queryset.none()
            return queryset.filter(organization=org)
        return queryset.none()

    org_id = person.organization_id

    if is_super_admin(user) or _has_org_admin_membership(person, org_id):
        return queryset.filter(organization_id=org_id)

    parts: list[Q] = [Q(author=person), Q(subject=person, template__subject_visible=True)]

    direct_group_ids, descendant_group_ids = _author_group_ids_split(person)
    if direct_group_ids:
        # Peer visibility: same-group co-authors see each other only when
        # the reflection is team-visible.
        parts.append(Q(
            assignment_group_id__in=direct_group_ids,
            team_visibility=Reflection.TeamVisibility.TEAM,
        ))
    if descendant_group_ids:
        # Supervisor pipe: authors of ancestor groups always see, regardless
        # of team_visibility -- that's the whole point of marking something
        # "supervisors only".
        parts.append(Q(assignment_group_id__in=descendant_group_ids))

    sq = _unit_scoped_supervisor_q(person, org_id)
    if sq is not None:
        parts.append(sq)

    ccq = _camper_care_caseload_q(person, org_id)
    if ccq is not None:
        parts.append(ccq)

    # Supervision-based supervisor pipe (Step 7_3 / 7_7). Covers UH → Counselor,
    # LT → team-role, Camper Care → BUNK targets, etc. Independent of the
    # AssignmentGroup descendant walk: the Supervision row is the source of
    # truth for who supervises whom, and that's what binds visibility here.
    supq = _supervision_authored_q(person, org_id)
    if supq is not None:
        parts.append(supq)

    wq = _wellness_q(person)
    if wq is not None:
        parts.append(wq)

    expr = reduce(or_, parts)
    return queryset.filter(organization_id=org_id).filter(expr).distinct()


def is_org_admin(user) -> bool:
    """True if user is a Super Admin or has an active admin Membership in their org."""
    if user is None or not getattr(user, "is_authenticated", False):
        return False
    if is_super_admin(user):
        return True
    person = _person_for_user(user)
    if person is None:
        return False
    return _has_org_admin_membership(person, person.organization_id)


def author_group_ids_with_descendants(person: Person) -> set[int]:
    """Public alias for the descendant-aware author-group set; used by dashboards."""
    return _author_group_ids_with_descendants(person)


def has_supervisor_role(user) -> bool:
    """True if user has any path that lets them see beyond their own self-reflections.

    Used by author-attribution view to lock that view down to supervisors only.
    Specifically: org admin, OR author of a group with at least one descendant
    (parent of a child group), OR any unit-scoped supervisor role
    (faculty / leadership_team / camper_care).
    """
    if user is None or not getattr(user, "is_authenticated", False):
        return False
    if is_super_admin(user):
        return True
    person = _person_for_user(user)
    if person is None:
        return False
    if _has_org_admin_membership(person, person.organization_id):
        return True
    if _unit_scoped_supervisor_q(person, person.organization_id) is not None:
        return True

    direct_ids = list(
        AssignmentGroupMembership.all_objects.filter(
            person=person,
            role_in_group="author",
            is_active=True,
        ).values_list("group_id", flat=True),
    )
    if not direct_ids:
        return False
    return AssignmentGroup.all_objects.filter(
        parent_id__in=direct_ids,
        is_active=True,
    ).exists()
