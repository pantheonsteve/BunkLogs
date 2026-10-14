"""Cut one organization over to class and cohort seats.

Temple Beth-El is the only caller. The group slug ``madrichim`` becomes
a cohort, classroom madrichim sit as authors, and faculty supervision
follows that placement. Historical challenges and cohort posts are not
saved, so a cohort that used to be a class keeps the rows it already has.
"""
from __future__ import annotations

import copy

from bunk_logs.core.group_supervision import apply_group_supervision
from bunk_logs.core.group_supervision import plan_group_supervision
from bunk_logs.core.models import AssignmentGroup
from bunk_logs.core.models import AssignmentGroupMembership
from bunk_logs.core.models import Membership
from bunk_logs.core.models import Organization
from bunk_logs.core.org_config import DEFAULT_GROUP_TYPE_CONFIG
from bunk_logs.core.time_utils import get_today

TBE_SLUG = "tbe"
COHORT_GROUP_SLUG = "madrichim"

_FILL_IF_MISSING = {
    "unit_head": {"one": "faculty", "other": "faculty"},
    "group": {"one": "class", "other": "classes"},
    "program": {"one": "school year", "other": "school years"},
}


def tbe_group_types() -> dict:
    """Full map. A saved dict replaces defaults, so bunk and unit stay."""
    config = copy.deepcopy(DEFAULT_GROUP_TYPE_CONFIG)
    config["classroom"] = {
        "enabled": True,
        "members": [
            {"role": "madrich", "placed_as": "author", "supervises_group": False},
            {"role": "student", "placed_as": "subject", "supervises_group": False},
            {"role": "faculty", "placed_as": "author", "supervises_group": True},
        ],
    }
    config["cohort"] = {
        "enabled": True,
        "members": [
            {"role": "madrich", "placed_as": "author", "supervises_group": False},
            {"role": "madrich", "placed_as": "subject", "supervises_group": False},
        ],
    }
    return config


def cut_over_tbe() -> None:
    """Apply the cutover. Missing org is a no-op. A second call changes nothing."""
    org = Organization.objects.filter(slug=TBE_SLUG).first()
    if org is None:
        return
    _save_settings(org)
    _retype_cohort(org)
    _fix_classrooms(org)
    today = get_today(org)
    apply_group_supervision(plan_group_supervision(org, today=today), today=today)


def _save_settings(org: Organization) -> None:
    settings = dict(org.settings or {})
    settings["group_types"] = tbe_group_types()
    terminology = dict(settings.get("terminology") or {})
    terminology["counselor"] = {"one": "madrich", "other": "madrichim"}
    for key, forms in _FILL_IF_MISSING.items():
        if key not in terminology:
            terminology[key] = dict(forms)
    settings["terminology"] = terminology
    org.settings = settings
    org.save(update_fields=["settings"])


def _active_madrich_ids(program_id: int) -> set[int]:
    return set(
        Membership.all_objects.filter(
            program_id=program_id,
            role="madrich",
            is_active=True,
        ).values_list("person_id", flat=True),
    )


def _retype_cohort(org: Organization) -> None:
    groups = list(
        AssignmentGroup.all_objects.filter(organization=org, slug=COHORT_GROUP_SLUG),
    )
    if not groups:
        return
    # Queryset update skips model validation. Challenges on this group
    # require a classroom, and they stay where they were filed.
    AssignmentGroup.all_objects.filter(pk__in=[group.pk for group in groups]).update(
        group_type="cohort",
    )
    for group in groups:
        _activate_madrich_authors(group, _active_madrich_ids(group.program_id))


def _activate_madrich_authors(group, person_ids: set[int]) -> None:
    if not person_ids:
        return
    AssignmentGroupMembership.all_objects.filter(
        group=group,
        role_in_group="author",
        is_active=False,
        person_id__in=person_ids,
    ).update(is_active=True)
    subject_ids = set(
        AssignmentGroupMembership.all_objects.filter(
            group=group,
            role_in_group="subject",
            is_active=True,
            person_id__in=person_ids,
        ).values_list("person_id", flat=True),
    )
    have_author = set(
        AssignmentGroupMembership.all_objects.filter(
            group=group,
            role_in_group="author",
            person_id__in=subject_ids,
        ).values_list("person_id", flat=True),
    )
    for person_id in subject_ids - have_author:
        AssignmentGroupMembership.all_objects.create(
            group=group,
            person_id=person_id,
            role_in_group="author",
            is_active=True,
        )


def _fix_classrooms(org: Organization) -> None:
    classrooms = AssignmentGroup.all_objects.filter(
        organization=org,
        group_type="classroom",
    )
    for group in classrooms:
        person_ids = _active_madrich_ids(group.program_id)
        if not person_ids:
            continue
        subject_ids = set(
            AssignmentGroupMembership.all_objects.filter(
                group=group,
                role_in_group="subject",
                is_active=True,
                person_id__in=person_ids,
            ).values_list("person_id", flat=True),
        )
        if not subject_ids:
            continue
        AssignmentGroupMembership.all_objects.filter(
            group=group,
            role_in_group="subject",
            is_active=True,
            person_id__in=subject_ids,
        ).update(is_active=False)
        for person_id in subject_ids:
            author = AssignmentGroupMembership.all_objects.filter(
                group=group,
                person_id=person_id,
                role_in_group="author",
            ).first()
            if author is None:
                AssignmentGroupMembership.all_objects.create(
                    group=group,
                    person_id=person_id,
                    role_in_group="author",
                    is_active=True,
                )
            elif not author.is_active:
                AssignmentGroupMembership.all_objects.filter(pk=author.pk).update(is_active=True)
