"""Subject profile dashboard visibility (view permission).

Who may open ``GET /api/v1/dashboards/subject/{id}/`` is separate from
observation read access and from observation authoring scope.
"""

from __future__ import annotations

from bunk_logs.core.models import ROLE_TO_CAPABILITY
from bunk_logs.core.models import AssignmentGroupMembership
from bunk_logs.core.models import Membership
from bunk_logs.core.models import Person
from bunk_logs.core.permissions.subject_note_authoring import authorable_subject_queryset
from bunk_logs.core.permissions.subject_note_authoring import can_author_subject_note
from bunk_logs.core.permissions.super_admin import is_super_admin
from bunk_logs.core.permissions.visibility import author_group_ids_with_descendants


def _membership_capabilities(person: Person, org) -> set[str]:
    """Capability tiers for active memberships in ``org`` (stored + role-derived)."""
    caps: set[str] = set()
    for role, capability in Membership.all_objects.filter(
        person=person,
        is_active=True,
        program__organization=org,
    ).values_list("role", "capability"):
        if capability:
            caps.add(capability)
        mapped = ROLE_TO_CAPABILITY.get(role)
        if mapped:
            caps.add(mapped)
    return caps


def _has_org_admin_membership(person: Person, org) -> bool:
    return Membership.all_objects.filter(
        person=person,
        role="admin",
        is_active=True,
        program__organization=org,
    ).exists()


def _has_legacy_user_role_admin(user, person: Person, org) -> bool:
    """Bridge legacy ``User.role`` until auth exposes ``Membership.capability``."""
    role = (getattr(user, "role", None) or "").strip().lower()
    if role != "admin":
        return False
    return Membership.all_objects.filter(
        person=person,
        is_active=True,
        program__organization=org,
    ).exists()


def viewer_capability(person: Person, org) -> str | None:
    """Highest-privilege capability the person holds in this org."""
    caps = _membership_capabilities(person, org)
    for cap in ("admin", "program_lead", "domain_specialist", "supervisor"):
        if cap in caps:
            return cap
    if "participant" in caps:
        return "participant"
    return None


def viewer_supervises_subject(viewer: Person, subject: Person) -> bool:
    """True if viewer authors a group (or descendant) that contains subject."""
    group_ids = author_group_ids_with_descendants(viewer)
    if not group_ids:
        return False
    return AssignmentGroupMembership.all_objects.filter(
        person=subject,
        group_id__in=group_ids,
        role_in_group="subject",
        is_active=True,
    ).exists()


def can_view_subject_dashboard(
    viewer_person: Person | None,
    subject: Person,
    org,
    user,
) -> bool:
    """Explicit capability gate for the subject dashboard."""
    if is_super_admin(user):
        return True
    if viewer_person is None:
        return False
    if _has_org_admin_membership(viewer_person, org):
        return True
    if _has_legacy_user_role_admin(user, viewer_person, org):
        return True
    cap = viewer_capability(viewer_person, org)
    if cap in ("admin", "program_lead", "domain_specialist"):
        return True
    if cap in ("supervisor", "participant"):
        if viewer_person.id == subject.id or viewer_supervises_subject(viewer_person, subject):
            return True
    return can_author_subject_note(viewer_person, subject, org, user)


def _supervised_subject_ids(viewer_person: Person, org) -> set[int]:
    """Person ids the viewer supervises via group hierarchy (+ self)."""
    ids: set[int] = {viewer_person.id}
    group_ids = author_group_ids_with_descendants(viewer_person)
    if group_ids:
        ids.update(
            AssignmentGroupMembership.all_objects.filter(
                group_id__in=group_ids,
                role_in_group="subject",
                is_active=True,
                group__organization_id=org.id,
            ).values_list("person_id", flat=True),
        )
    bunk_ids = list(
        AssignmentGroupMembership.all_objects.filter(
            person=viewer_person,
            role_in_group="author",
            is_active=True,
            group__is_active=True,
            group__group_type="bunk",
            group__organization_id=org.id,
        ).values_list("group_id", flat=True),
    )
    if bunk_ids:
        ids.update(
            AssignmentGroupMembership.all_objects.filter(
                group_id__in=bunk_ids,
                role_in_group="subject",
                is_active=True,
            ).values_list("person_id", flat=True),
        )
    return ids


def viewable_subject_queryset(viewer_person: Person | None, org, user):
    """Person queryset whose profile dashboard the viewer may open."""
    base = Person.all_objects.filter(organization=org)
    if is_super_admin(user):
        return base
    if viewer_person is None:
        return base.none()

    cap = viewer_capability(viewer_person, org)
    if cap in ("admin", "program_lead", "domain_specialist"):
        return base

    ids: set[int] = set()
    if cap in ("supervisor", "participant"):
        ids.update(_supervised_subject_ids(viewer_person, org))
    ids.update(
        authorable_subject_queryset(viewer_person, org).values_list("id", flat=True),
    )
    if not ids:
        return base.none()
    return base.filter(id__in=ids)


def camper_subject_person_ids_subquery(org):
    """Active assignment-group subjects (campers) in the org."""
    return AssignmentGroupMembership.all_objects.filter(
        role_in_group="subject",
        is_active=True,
        group__organization_id=org.id,
        group__is_active=True,
    ).values("person_id")


def viewable_camper_queryset(viewer_person: Person | None, org, user):
    """Viewable persons who are active campers (assignment-group subjects)."""
    camper_ids = camper_subject_person_ids_subquery(org)
    return viewable_subject_queryset(viewer_person, org, user).filter(
        id__in=camper_ids,
    )


__all__ = [
    "camper_subject_person_ids_subquery",
    "can_view_subject_dashboard",
    "viewable_camper_queryset",
    "viewable_subject_queryset",
    "viewer_capability",
    "viewer_supervises_subject",
]
