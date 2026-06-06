"""SubjectNote authoring scope — org-configurable, separate from capability.

Who may *write* a SubjectNote about a subject is controlled by:

1. Global defaults in ``DEFAULT_AUTHOR_BY_ROLE`` (code).
2. Per-org overrides in ``Organization.settings["subject_notes"]["author_by_role"]``.
3. Optional per-membership override in
   ``Membership.metadata["can_author_subject_notes"]`` (bool).

Scopes (most → least permissive): ``org`` > ``program`` > ``supervised`` > ``none``.
When a viewer holds multiple active memberships, the broadest scope wins.
"""

from __future__ import annotations

from typing import Literal

from bunk_logs.core.models import AssignmentGroupMembership
from bunk_logs.core.models import Membership
from bunk_logs.core.models import Person
from bunk_logs.core.permissions.super_admin import is_super_admin
from bunk_logs.core.permissions.visibility import author_group_ids_with_descendants

AuthorScope = Literal["none", "supervised", "program", "org"]

_SCOPE_RANK: dict[str, int] = {
    "none": 0,
    "supervised": 1,
    "program": 2,
    "org": 3,
}

# Code defaults; orgs may override individual roles via Organization.settings.
DEFAULT_AUTHOR_BY_ROLE: dict[str, AuthorScope] = {
    "admin": "org",
    "leadership_team": "org",
    "health_center": "org",
    "medical": "org",
    "special_diets": "org",
    "unit_head": "supervised",
    "faculty": "supervised",
    "camper_care": "supervised",
    "counselor": "supervised",
    "junior_counselor": "supervised",
    "general_counselor": "supervised",
    "madrich": "supervised",
    "specialist": "program",
    "kitchen_staff": "none",
    "maintenance": "none",
    "administrative_staff": "none",
    "housekeeping": "none",
    "camper": "none",
}

VALID_SCOPES = frozenset(_SCOPE_RANK)


def author_by_role_for_org(org) -> dict[str, AuthorScope]:
    """Merged role → scope map: org settings overlay code defaults."""
    merged = dict(DEFAULT_AUTHOR_BY_ROLE)
    settings = getattr(org, "settings", None) or {}
    overrides = (settings.get("subject_notes") or {}).get("author_by_role") or {}
    merged.update({role: scope for role, scope in overrides.items() if scope in VALID_SCOPES})
    return merged


def _scope_for_membership(org, membership: Membership) -> AuthorScope | None:
    """Return the scope one membership contributes, or None when force-disabled."""
    metadata = membership.metadata or {}
    override = metadata.get("can_author_subject_notes")
    if override is False:
        return None
    if override is True:
        return "program"
    role_map = author_by_role_for_org(org)
    return role_map.get(membership.role, "none")


def max_author_scope(viewer_person: Person, org) -> AuthorScope:
    """Broadest authoring scope across the viewer's active org memberships."""
    memberships = Membership.all_objects.filter(
        person=viewer_person,
        is_active=True,
        program__organization=org,
    )
    scopes: list[AuthorScope] = []
    for m in memberships:
        scope = _scope_for_membership(org, m)
        if scope is not None:
            scopes.append(scope)
    if not scopes:
        return "none"
    return max(scopes, key=lambda s: _SCOPE_RANK[s])


def _viewer_supervises_subject(viewer: Person, subject: Person) -> bool:
    group_ids = author_group_ids_with_descendants(viewer)
    if not group_ids:
        return False
    return AssignmentGroupMembership.all_objects.filter(
        person=subject,
        group_id__in=group_ids,
        role_in_group="subject",
        is_active=True,
    ).exists()


def _shares_program(viewer: Person, subject: Person, org) -> bool:
    viewer_program_ids = set(
        Membership.all_objects.filter(
            person=viewer,
            is_active=True,
            program__organization=org,
        ).values_list("program_id", flat=True),
    )
    if not viewer_program_ids:
        return False
    return Membership.all_objects.filter(
        person=subject,
        is_active=True,
        program_id__in=viewer_program_ids,
    ).exists()


def can_author_subject_note(
    viewer_person: Person | None,
    subject: Person,
    org,
    user,
) -> bool:
    """Return True if ``viewer_person`` may POST a SubjectNote about ``subject``."""
    if is_super_admin(user):
        return True
    if viewer_person is None:
        return False
    if subject.organization_id != org.id:
        return False

    scope = max_author_scope(viewer_person, org)
    if scope == "org":
        return True
    if scope == "program":
        return _shares_program(viewer_person, subject, org)
    if scope == "supervised":
        return (
            viewer_person.id == subject.id
            or _viewer_supervises_subject(viewer_person, subject)
        )
    return False


def authorable_subject_queryset(viewer_person: Person, org):
    """Person queryset the viewer may write SubjectNotes about."""
    scope = max_author_scope(viewer_person, org)
    base = Person.all_objects.filter(organization=org)

    if scope == "org":
        return base
    if scope == "program":
        program_ids = list(
            Membership.all_objects.filter(
                person=viewer_person,
                is_active=True,
                program__organization=org,
            ).values_list("program_id", flat=True),
        )
        if not program_ids:
            return base.none()
        subject_ids = Membership.all_objects.filter(
            program_id__in=program_ids,
            is_active=True,
        ).values_list("person_id", flat=True)
        return base.filter(id__in=subject_ids)
    if scope == "supervised":
        group_ids = author_group_ids_with_descendants(viewer_person)
        supervised_ids: set[int] = set()
        if group_ids:
            supervised_ids = set(
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
            supervised_ids.update(
                AssignmentGroupMembership.all_objects.filter(
                    group_id__in=bunk_ids,
                    role_in_group="subject",
                    is_active=True,
                ).values_list("person_id", flat=True),
            )
        supervised_ids.add(viewer_person.id)
        return base.filter(id__in=supervised_ids)
    return base.none()


__all__ = [
    "DEFAULT_AUTHOR_BY_ROLE",
    "AuthorScope",
    "author_by_role_for_org",
    "authorable_subject_queryset",
    "can_author_subject_note",
    "max_author_scope",
]
