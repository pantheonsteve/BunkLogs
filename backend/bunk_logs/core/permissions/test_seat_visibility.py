"""Reading follows the seats once an org has saved group_types.

No saved key: the bunk collect and the faculty whole-program shortcut stay.
A saved key: supervisors see subjects and writers, including descendants,
and faculty with no unit slugs do not see the rest of the program.
"""

from __future__ import annotations

from datetime import date

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from bunk_logs.core.context import organization_context
from bunk_logs.core.group_audience import group_audience
from bunk_logs.core.models import AssignmentGroup
from bunk_logs.core.models import AssignmentGroupMembership
from bunk_logs.core.models import Membership
from bunk_logs.core.models import Organization
from bunk_logs.core.models import Person
from bunk_logs.core.models import Program
from bunk_logs.core.models import Reflection
from bunk_logs.core.models import ReflectionTemplate
from bunk_logs.core.models import Supervision
from bunk_logs.core.permissions.visibility import has_supervisor_role
from bunk_logs.core.permissions.visibility import reflections_visible_to
from bunk_logs.testing import SEASON_END
from bunk_logs.testing import SEASON_START

User = get_user_model()
pytestmark = pytest.mark.django_db

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
SCHEMA = {"fields": [{"key": "n", "type": "text", "prompts": {"en": "n"}}]}


@pytest.fixture
def org():
    return Organization.objects.create(name="Seat Vis", slug="seat-vis")


@pytest.fixture
def program(org):
    return Program.all_objects.create(
        organization=org,
        name="Seat Vis Season",
        slug="seat-vis-season",
        program_type="summer_camp",
        start_date=SEASON_START,
        end_date=SEASON_END,
    )


def _user(email):
    return User.objects.create_user(email=email, password="pw")


def _person(org, first, last, user=None):
    return Person.all_objects.create(
        organization=org,
        first_name=first,
        last_name=last,
        user=user,
    )


def _member(program, person, role, **kwargs):
    return Membership.all_objects.create(
        program=program,
        person=person,
        role=role,
        is_active=True,
        **kwargs,
    )


def _group(org, program, name, slug, group_type, parent=None):
    return AssignmentGroup.all_objects.create(
        organization=org,
        program=program,
        name=name,
        slug=slug,
        group_type=group_type,
        parent=parent,
    )


def _seat(group, person, role_in_group):
    return AssignmentGroupMembership.all_objects.create(
        group=group,
        person=person,
        role_in_group=role_in_group,
        is_active=True,
    )


def _template(org, slug, **kwargs):
    return ReflectionTemplate.all_objects.create(
        organization=org,
        name=slug,
        slug=slug,
        cadence="weekly",
        subject_mode=kwargs.pop("subject_mode", "self"),
        assignment_scope="none",
        subject_visible=False,
        schema=SCHEMA,
        **kwargs,
    )


def _reflection(org, program, template, **kwargs):
    return Reflection.all_objects.create(
        organization=org,
        program=program,
        template=template,
        period_start=date(2026, 6, 1),
        period_end=date(2026, 6, 7),
        answers={"n": "x"},
        language="en",
        team_visibility=kwargs.pop(
            "team_visibility",
            Reflection.TeamVisibility.TEAM,
        ),
        **kwargs,
    )


def _visible_ids(user, org):
    with organization_context(org):
        return set(reflections_visible_to(user).values_list("id", flat=True))


def test_unsaved_faculty_with_empty_unit_slugs_sees_the_program(org, program):
    user = _user("faculty-open@seat.test")
    faculty = _person(org, "Fran", "Faculty", user)
    _member(program, faculty, "faculty", metadata={})
    subject = _person(org, "Some", "One")
    _member(program, subject, "counselor")
    tpl = _template(org, "open-note", role="counselor")
    reflection = _reflection(
        org,
        program,
        tpl,
        subject=subject,
        author=subject,
        assignment_group=None,
    )
    assert reflection.id in _visible_ids(user, org)


def test_saved_camp_unit_head_sees_bunk_logs_and_counselor_self(org, program):
    org.settings = {"group_types": CAMP}
    org.save(update_fields=["settings"])

    uh_user = _user("uh@seat.test")
    unit_head = _person(org, "Una", "Head", uh_user)
    _member(program, unit_head, "unit_head")
    unit = _group(org, program, "Unit", "seat-unit", "unit")
    bunk = _group(org, program, "Bunk", "seat-bunk", "bunk", parent=unit)
    _seat(unit, unit_head, "author")

    a_user = _user("counselor-a@seat.test")
    counselor_a = _person(org, "Ann", "Counselor", a_user)
    counselor_b = _person(org, "Bea", "Counselor")
    camper = _person(org, "Cam", "Camper")
    stranger = _person(org, "Str", "Anger")
    for person, role in (
        (counselor_a, "counselor"),
        (counselor_b, "counselor"),
        (camper, "camper"),
    ):
        _member(program, person, role)
    _seat(bunk, counselor_a, "author")
    _seat(bunk, counselor_b, "author")
    _seat(bunk, camper, "subject")

    camper_log = _template(org, "camper-log", role="counselor", subject_mode="single_subject")
    about_camper = _reflection(
        org,
        program,
        camper_log,
        subject=camper,
        author=counselor_a,
        assignment_group=bunk,
        team_visibility=Reflection.TeamVisibility.TEAM,
    )
    # On the bunk, but the subject holds no seat. Only the descendant pipe
    # reaches this; collecting bunk subjects would miss it.
    about_stranger = _reflection(
        org,
        program,
        camper_log,
        subject=stranger,
        author=counselor_a,
        assignment_group=bunk,
        team_visibility=Reflection.TeamVisibility.SUPERVISORS_ONLY,
    )
    self_tpl = _template(org, "counselor-self", role="counselor", subject_mode="self")
    counselor_self = _reflection(
        org,
        program,
        self_tpl,
        subject=counselor_b,
        author=counselor_b,
        assignment_group=None,
        team_visibility=Reflection.TeamVisibility.SUPERVISORS_ONLY,
    )

    with organization_context(org):
        assert has_supervisor_role(uh_user) is True
        assert has_supervisor_role(a_user) is False

    uh_ids = _visible_ids(uh_user, org)
    assert about_camper.id in uh_ids
    assert about_stranger.id in uh_ids
    assert counselor_self.id in uh_ids

    peer_ids = _visible_ids(a_user, org)
    assert about_camper.id in peer_ids
    assert counselor_self.id not in peer_ids


def test_saved_class_faculty_sees_own_class_only(org, program):
    org.settings = {"group_types": CLASSROOM}
    org.save(update_fields=["settings"])

    faculty_user = _user("faculty@seat.test")
    faculty = _person(org, "Fran", "Faculty", faculty_user)
    _member(program, faculty, "faculty", metadata={})

    madrich_user = _user("madrich-a@seat.test")
    madrich_a = _person(org, "Mia", "Madrich", madrich_user)
    madrich_b = _person(org, "Bea", "Madrich")
    student = _person(org, "Sam", "Student")
    other_student = _person(org, "Ora", "Student")
    outsider = _person(org, "Out", "Sider")
    for person, role in (
        (madrich_a, "madrich"),
        (madrich_b, "madrich"),
        (student, "student"),
        (other_student, "student"),
        (outsider, "counselor"),
    ):
        _member(program, person, role)

    grade3 = _group(org, program, "Grade 3", "grade-3", "classroom")
    grade4 = _group(org, program, "Grade 4", "grade-4", "classroom")
    _seat(grade3, faculty, "author")
    _seat(grade3, madrich_a, "author")
    _seat(grade3, madrich_b, "author")
    _seat(grade3, student, "subject")
    _seat(grade4, other_student, "subject")

    audience = group_audience(org, grade3)
    assert student.id in audience.subjects
    assert madrich_a.id not in audience.subjects
    assert madrich_b.id not in audience.subjects
    assert madrich_a.id in audience.writers

    student_log = _template(org, "student-log", role="madrich", subject_mode="single_subject")
    about_student = _reflection(
        org,
        program,
        student_log,
        subject=student,
        author=madrich_b,
        assignment_group=grade3,
        team_visibility=Reflection.TeamVisibility.TEAM,
    )
    about_grade4 = _reflection(
        org,
        program,
        student_log,
        subject=other_student,
        author=madrich_b,
        assignment_group=grade4,
        team_visibility=Reflection.TeamVisibility.TEAM,
    )
    self_tpl = _template(org, "madrich-self", role="madrich", subject_mode="self")
    madrich_self = _reflection(
        org,
        program,
        self_tpl,
        subject=madrich_b,
        author=madrich_b,
        assignment_group=None,
        team_visibility=Reflection.TeamVisibility.SUPERVISORS_ONLY,
    )
    program_note = _template(org, "outsider-note", role="counselor")
    whole_program = _reflection(
        org,
        program,
        program_note,
        subject=outsider,
        author=outsider,
        assignment_group=None,
    )

    with organization_context(org):
        assert has_supervisor_role(faculty_user) is True
        assert has_supervisor_role(madrich_user) is False

    faculty_ids = _visible_ids(faculty_user, org)
    assert about_student.id in faculty_ids
    assert madrich_self.id in faculty_ids
    assert about_grade4.id not in faculty_ids
    assert whole_program.id not in faculty_ids

    madrich_ids = _visible_ids(madrich_user, org)
    assert about_student.id in madrich_ids
    assert madrich_self.id not in madrich_ids


def test_saved_classroom_supervision_lists_people(org, program):
    """A classroom Supervision row lists the class, not zero people."""
    org.settings = {"group_types": CLASSROOM}
    org.save(update_fields=["settings"])

    admin_user = _user("admin@seat.test")
    admin = _person(org, "Ad", "Min", admin_user)
    _member(program, admin, "admin")

    faculty = _person(org, "Fran", "Faculty")
    faculty_membership = _member(program, faculty, "faculty")
    classroom = _group(org, program, "Grade 3", "status-grade-3", "classroom")
    student = _person(org, "Sam", "Student")
    madrich = _person(org, "Mia", "Madrich")
    _member(program, student, "student")
    _member(program, madrich, "madrich")
    _seat(classroom, student, "subject")
    _seat(classroom, madrich, "author")
    Supervision.all_objects.create(
        supervisor_membership=faculty_membership,
        target_type=Supervision.TargetType.ASSIGNMENT_GROUP,
        target_group=classroom,
        start_date=date(2026, 1, 1),
    )

    client = APIClient()
    client.force_authenticate(user=admin_user)
    with organization_context(org):
        response = client.get(
            "/api/v1/admin/assignments/supervisor-status/",
            {"person": faculty.id},
            HTTP_X_ORGANIZATION_SLUG=org.slug,
        )
    assert response.status_code == 200, response.content
    body = response.json()
    assert body["supervised_entities"]["supervisions"][0]["target_name"] == "Grade 3"
    people_ids = {p["id"] for p in body["supervised_people"]["people"]}
    assert student.id in people_ids
    assert madrich.id in people_ids
