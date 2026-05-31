"""SubjectNote read visibility — separate from authoring scope.

Authors always see notes they wrote. All other rows follow capability +
visibility-level rules (supervised subjects, org-wide readers, etc.).
"""

from __future__ import annotations

from django.db.models import Q

from bunk_logs.core.models import AssignmentGroupMembership
from bunk_logs.core.models import Membership
from bunk_logs.core.models import Person
from bunk_logs.core.permissions.super_admin import is_super_admin
from bunk_logs.core.permissions.visibility import author_group_ids_with_descendants

NOTE_VIS_BY_CAP: dict[str, set[str]] = {
    "admin": {"team", "supervisors_only", "domain_only", "admin_only"},
    "program_lead": {"team", "supervisors_only", "domain_only"},
    "domain_specialist": {"team", "supervisors_only", "domain_only"},
    "supervisor": {"team", "supervisors_only"},
    "participant": set(),
}


def _viewer_capability(person: Person, org) -> str | None:
    caps = set(
        Membership.all_objects.filter(
            person=person,
            is_active=True,
            program__organization=org,
        ).values_list("capability", flat=True),
    )
    for cap in ("admin", "program_lead", "domain_specialist", "supervisor"):
        if cap in caps:
            return cap
    if "participant" in caps:
        return "participant"
    return None


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


def _supervised_subject_ids(viewer: Person) -> set[int]:
    group_ids = author_group_ids_with_descendants(viewer)
    if not group_ids:
        return set()
    return set(
        AssignmentGroupMembership.all_objects.filter(
            person__isnull=False,
            group_id__in=group_ids,
            role_in_group="subject",
            is_active=True,
        ).values_list("person_id", flat=True),
    )


def subject_note_read_q(
    viewer_person: Person | None,
    org,
    user,
    *,
    subject: Person | None = None,
) -> Q:
    """Return a ``Q`` filter for SubjectNote rows the viewer may read."""
    if is_super_admin(user):
        return Q()
    if viewer_person is None:
        return Q(pk__in=[])

    authored = Q(author_person=viewer_person)
    cap = _viewer_capability(viewer_person, org)
    other = Q(pk__in=[])

    if cap in ("admin", "program_lead", "domain_specialist"):
        other = Q(visibility__in=NOTE_VIS_BY_CAP[cap])
    elif cap in ("supervisor", "participant"):
        if subject is not None:
            if viewer_person.id == subject.id:
                other = Q(subject_visible=True)
            elif _viewer_supervises_subject(viewer_person, subject):
                other = Q(visibility__in=NOTE_VIS_BY_CAP["supervisor"])
        else:
            supervised_ids = _supervised_subject_ids(viewer_person)
            parts = [Q(subject_id=viewer_person.id, subject_visible=True)]
            if supervised_ids:
                parts.append(
                    Q(
                        subject_id__in=supervised_ids,
                        visibility__in=NOTE_VIS_BY_CAP["supervisor"],
                    ),
                )
            other = parts[0]
            for part in parts[1:]:
                other |= part

    return authored | other


def filter_subject_notes_readable(
    notes_qs,
    viewer_person: Person | None,
    org,
    user,
    *,
    subject: Person | None = None,
):
    """Filter a SubjectNote queryset to rows the viewer is allowed to read."""
    if is_super_admin(user):
        return notes_qs
    if viewer_person is None:
        return notes_qs.none()
    return notes_qs.filter(subject_note_read_q(viewer_person, org, user, subject=subject))


__all__ = [
    "NOTE_VIS_BY_CAP",
    "filter_subject_notes_readable",
    "subject_note_read_q",
]
