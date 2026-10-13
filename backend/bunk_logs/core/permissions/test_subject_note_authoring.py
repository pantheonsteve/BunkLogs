"""Unit tests for SubjectNote authoring scope (org role defaults + overrides)."""

from __future__ import annotations

from datetime import date

import pytest

from bunk_logs.core.models import AssignmentGroup
from bunk_logs.core.models import AssignmentGroupMembership
from bunk_logs.core.models import Membership
from bunk_logs.core.models import Organization
from bunk_logs.core.models import Person
from bunk_logs.core.models import Program
from bunk_logs.core.permissions.subject_note_authoring import author_by_role_for_org
from bunk_logs.core.permissions.subject_note_authoring import authorable_subject_queryset
from bunk_logs.core.permissions.subject_note_authoring import can_author_subject_note
from bunk_logs.core.permissions.subject_note_authoring import max_author_scope
from bunk_logs.testing import SEASON_END
from bunk_logs.testing import SEASON_START

pytestmark = pytest.mark.django_db


@pytest.fixture
def org(db):
    return Organization.objects.create(name="Auth Org", slug="auth-org")


@pytest.fixture
def program(org):
    return Program.all_objects.create(
        organization=org,
        name="Auth Org Summer",
        slug="auth-summer",
        program_type="summer_camp",
        start_date=SEASON_START,
        end_date=SEASON_END,
    )


def _person(org, first, last):
    return Person.all_objects.create(organization=org, first_name=first, last_name=last)


def _membership(program, person, role, **kwargs):
    return Membership.all_objects.create(
        program=program,
        person=person,
        role=role,
        is_active=True,
        **kwargs,
    )


def test_specialist_has_program_scope_by_default(org, program):
    specialist = _person(org, "Swim", "Coach")
    _membership(program, specialist, "specialist")
    assert max_author_scope(specialist, org) == "program"


def test_kitchen_staff_has_none_by_default(org, program):
    staff = _person(org, "Kit", "Chen")
    _membership(program, staff, "kitchen_staff")
    assert max_author_scope(staff, org) == "none"


def test_org_settings_override_role(org, program):
    org.settings = {
        "subject_notes": {"author_by_role": {"specialist": "none", "kitchen_staff": "program"}},
    }
    org.save()
    role_map = author_by_role_for_org(org)
    assert role_map["specialist"] == "none"
    assert role_map["kitchen_staff"] == "program"


def test_membership_metadata_override_grants_program(org, program):
    staff = _person(org, "Kit", "Chen")
    _membership(
        program,
        staff,
        "kitchen_staff",
        metadata={"can_author_subject_notes": True},
    )
    assert max_author_scope(staff, org) == "program"


def test_membership_metadata_override_denies(org, program):
    specialist = _person(org, "Swim", "Coach")
    _membership(
        program,
        specialist,
        "specialist",
        metadata={"can_author_subject_notes": False},
    )
    assert max_author_scope(specialist, org) == "none"


def test_specialist_can_author_for_program_camper(org, program):
    bunk = AssignmentGroup.all_objects.create(
        organization=org,
        program=program,
        name="Bunk A",
        slug="auth-bunk",
        group_type="bunk",
    )
    camper = _person(org, "Kim", "Camper")
    _membership(program, camper, "camper")
    AssignmentGroupMembership.all_objects.create(
        group=bunk,
        person=camper,
        role_in_group="subject",
        is_active=True,
    )

    specialist = _person(org, "Swim", "Coach")
    _membership(program, specialist, "specialist")

    assert can_author_subject_note(specialist, camper, org, user=None) is True


def test_specialist_cannot_author_cross_program(org, program):
    other_program = Program.all_objects.create(
        organization=org,
        name="Auth Org Other Session",
        slug="auth-other",
        program_type="summer_camp",
        start_date=date(2026, 7, 1),
        end_date=date(2026, 8, 15),
    )
    camper = _person(org, "Other", "Camper")
    _membership(other_program, camper, "camper")

    specialist = _person(org, "Swim", "Coach")
    _membership(program, specialist, "specialist")

    assert can_author_subject_note(specialist, camper, org, user=None) is False


def test_counselor_supervised_scope(org, program):
    bunk = AssignmentGroup.all_objects.create(
        organization=org,
        program=program,
        name="Bunk B",
        slug="auth-bunk-b",
        group_type="bunk",
    )
    camper = _person(org, "Pat", "Camper")
    _membership(program, camper, "camper")
    AssignmentGroupMembership.all_objects.create(
        group=bunk,
        person=camper,
        role_in_group="subject",
        is_active=True,
    )

    counselor = _person(org, "Ann", "Counselor")
    _membership(program, counselor, "counselor")
    AssignmentGroupMembership.all_objects.create(
        group=bunk,
        person=counselor,
        role_in_group="author",
        is_active=True,
    )

    outsider = _person(org, "Out", "Sider")
    _membership(program, outsider, "camper")
    AssignmentGroupMembership.all_objects.create(
        group=bunk,
        person=outsider,
        role_in_group="subject",
        is_active=True,
    )
    other_bunk = AssignmentGroup.all_objects.create(
        organization=org,
        program=program,
        name="Bunk C",
        slug="auth-bunk-c",
        group_type="bunk",
    )
    other_camper = _person(org, "Far", "Away")
    _membership(program, other_camper, "camper")
    AssignmentGroupMembership.all_objects.create(
        group=other_bunk,
        person=other_camper,
        role_in_group="subject",
        is_active=True,
    )

    assert can_author_subject_note(counselor, camper, org, user=None) is True
    assert can_author_subject_note(counselor, other_camper, org, user=None) is False


CAMP = {
    "bunk": {
        "enabled": True,
        "members": [
            {"role": "counselor", "placed_as": "author", "supervises_group": False},
            {"role": "camper", "placed_as": "subject", "supervises_group": False},
        ],
    },
    "unit": {
        "enabled": True,
        "members": [
            {"role": "unit_head", "placed_as": "author", "supervises_group": True},
        ],
    },
}
CLASSROOM = {
    "classroom": {
        "enabled": True,
        "members": [
            {"role": "madrich", "placed_as": "author", "supervises_group": False},
            {"role": "student", "placed_as": "subject", "supervises_group": False},
            {"role": "faculty", "placed_as": "author", "supervises_group": True},
        ],
    },
}


def _save_types(org, group_types):
    org.settings = {"group_types": group_types}
    org.save(update_fields=["settings"])


def test_saved_camp_writers_log_on_subjects_supervisors_also_on_writers(org, program):
    _save_types(org, CAMP)
    unit = AssignmentGroup.all_objects.create(
        organization=org,
        program=program,
        name="Unit",
        slug="note-unit",
        group_type="unit",
    )
    bunk = AssignmentGroup.all_objects.create(
        organization=org,
        program=program,
        name="Bunk",
        slug="note-bunk",
        group_type="bunk",
        parent=unit,
    )
    unit_head = _person(org, "Una", "Head")
    counselor = _person(org, "Ann", "Counselor")
    peer = _person(org, "Bea", "Counselor")
    camper = _person(org, "Cam", "Camper")
    _membership(program, unit_head, "unit_head")
    _membership(program, counselor, "counselor")
    _membership(program, peer, "counselor")
    _membership(program, camper, "camper")
    AssignmentGroupMembership.all_objects.create(
        group=unit,
        person=unit_head,
        role_in_group="author",
        is_active=True,
    )
    AssignmentGroupMembership.all_objects.create(
        group=bunk,
        person=counselor,
        role_in_group="author",
        is_active=True,
    )
    AssignmentGroupMembership.all_objects.create(
        group=bunk,
        person=peer,
        role_in_group="author",
        is_active=True,
    )
    AssignmentGroupMembership.all_objects.create(
        group=bunk,
        person=camper,
        role_in_group="subject",
        is_active=True,
    )

    assert can_author_subject_note(counselor, camper, org, user=None) is True
    assert can_author_subject_note(counselor, peer, org, user=None) is False
    assert can_author_subject_note(unit_head, camper, org, user=None) is True
    assert can_author_subject_note(unit_head, counselor, org, user=None) is True


def test_saved_class_faculty_logs_on_students_and_madrichim(org, program):
    _save_types(org, CLASSROOM)
    grade3 = AssignmentGroup.all_objects.create(
        organization=org,
        program=program,
        name="Grade 3",
        slug="note-g3",
        group_type="classroom",
    )
    grade4 = AssignmentGroup.all_objects.create(
        organization=org,
        program=program,
        name="Grade 4",
        slug="note-g4",
        group_type="classroom",
    )
    faculty = _person(org, "Fran", "Faculty")
    madrich = _person(org, "Mia", "Madrich")
    peer = _person(org, "Bea", "Madrich")
    student = _person(org, "Sam", "Student")
    other = _person(org, "Ora", "Student")
    _membership(program, faculty, "faculty")
    _membership(program, madrich, "madrich")
    _membership(program, peer, "madrich")
    _membership(program, student, "student")
    _membership(program, other, "student")
    for group, person, seat in (
        (grade3, faculty, "author"),
        (grade3, madrich, "author"),
        (grade3, peer, "author"),
        (grade3, student, "subject"),
        (grade4, other, "subject"),
    ):
        AssignmentGroupMembership.all_objects.create(
            group=group,
            person=person,
            role_in_group=seat,
            is_active=True,
        )

    assert can_author_subject_note(madrich, student, org, user=None) is True
    assert can_author_subject_note(madrich, peer, org, user=None) is False
    assert can_author_subject_note(faculty, student, org, user=None) is True
    assert can_author_subject_note(faculty, madrich, org, user=None) is True
    assert can_author_subject_note(faculty, other, org, user=None) is False

    noteable = set(
        authorable_subject_queryset(faculty, org).values_list("id", flat=True),
    )
    assert student.id in noteable
    assert madrich.id in noteable
    assert other.id not in noteable
