"""Observation authoring scope (Step 7_23).

Subject tagging for observations is intentionally broader than SubjectNotes:
any staff member who may write observations at all can tag any ``Person`` in
the organization. Roster assignment (``AssignmentGroupMembership``) still
governs who sees what on dashboards; sensitivity + recipient gates constrain
distribution after submit.

Recipient tagging still uses the capability / sensitivity map.
"""

from __future__ import annotations

from bunk_logs.core.models import Membership
from bunk_logs.core.models import Person
from bunk_logs.core.permissions.observation_read import view_by_capability_for_org
from bunk_logs.core.permissions.subject_note_authoring import authorable_subject_queryset
from bunk_logs.core.permissions.subject_note_authoring import can_author_subject_note
from bunk_logs.core.permissions.subject_note_authoring import max_author_scope
from bunk_logs.core.permissions.super_admin import is_super_admin


def observation_authorable_subject_queryset(viewer_person: Person, org):
    """Person queryset taggable as subjects on an observation."""
    if max_author_scope(viewer_person, org) == "none":
        return Person.all_objects.none()
    return Person.all_objects.filter(organization=org)


def can_author_observation(
    viewer_person: Person | None,
    subject: Person,
    org,
    user,
) -> bool:
    """Return True if ``viewer_person`` may tag ``subject`` on an observation."""
    if is_super_admin(user):
        return True
    if viewer_person is None:
        return False
    if subject.organization_id != org.id:
        return False
    return max_author_scope(viewer_person, org) != "none"


def recipients_clearing_sensitivity(viewer_person: Person, org, sensitivity: str):
    """Person queryset eligible to be tagged as a recipient at ``sensitivity``.

    A Person clears the tier if any of their active org memberships has a
    capability whose org sensitivity map includes the tier. The author is
    excluded (you don't tag yourself).
    """
    base = Person.all_objects.filter(organization=org)
    vis_map = view_by_capability_for_org(org)
    clearing_caps = {cap for cap, tiers in vis_map.items() if sensitivity in tiers}
    if not clearing_caps:
        return base.none()
    person_ids = Membership.all_objects.filter(
        is_active=True,
        program__organization=org,
        capability__in=clearing_caps,
    ).values_list("person_id", flat=True)
    qs = base.filter(id__in=person_ids)
    if viewer_person is not None:
        qs = qs.exclude(id=viewer_person.id)
    return qs


def can_tag_recipient(viewer_person: Person, recipient: Person, org, sensitivity: str) -> bool:
    """True if ``recipient`` may be tagged on an observation at ``sensitivity``."""
    return recipients_clearing_sensitivity(viewer_person, org, sensitivity).filter(
        id=recipient.id,
    ).exists()


__all__ = [
    "authorable_subject_queryset",
    "can_author_observation",
    "can_author_subject_note",
    "can_tag_recipient",
    "max_author_scope",
    "observation_authorable_subject_queryset",
    "recipients_clearing_sensitivity",
]
