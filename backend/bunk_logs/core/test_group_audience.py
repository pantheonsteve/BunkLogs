"""One audience rule for a group and a form.

No saved group_types: bunk resolution stays counselors writing and
campers as the subjects. A saved classroom config opts the org in.
"""

from __future__ import annotations

from datetime import date

import pytest

from bunk_logs.api.dashboards.performance import _completion_for_assignment
from bunk_logs.api.dashboards.performance import _subject_ids_for_template
from bunk_logs.api.reflections import _subjects_for_submission
from bunk_logs.core.assignment_resolution import active_assignments_for
from bunk_logs.core.assignment_resolution import resolve_members
from bunk_logs.core.context import organization_context
from bunk_logs.core.group_audience import group_audience
from bunk_logs.core.models import AssignmentGroup
from bunk_logs.core.models import AssignmentGroupMembership
from bunk_logs.core.models import Membership
from bunk_logs.core.models import Organization
from bunk_logs.core.models import Person
from bunk_logs.core.models import Program
from bunk_logs.core.models import ReflectionTemplate
from bunk_logs.core.models import TemplateAssignment
from bunk_logs.testing import SEASON_END
from bunk_logs.testing import SEASON_START

pytestmark = pytest.mark.django_db

TODAY = date.today()
SCHEMA = {"fields": [{"key": "note", "type": "textarea", "required": False, "prompts": {"en": "Notes"}}]}
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


def _program(org, slug):
    return Program.all_objects.create(
        organization=org,
        name=f"{org.name} Season",
        slug=slug,
        program_type="religious_school",
        start_date=SEASON_START,
        end_date=SEASON_END,
    )


def _person(org, program, first, role):
    person = Person.all_objects.create(
        organization=org,
        first_name=first,
        last_name="Person",
    )
    Membership.all_objects.create(
        program=program,
        person=person,
        role=role,
        is_active=True,
    )
    return person


def _seat(group, person, role_in_group, *, is_active=True):
    return AssignmentGroupMembership.all_objects.create(
        group=group,
        person=person,
        role_in_group=role_in_group,
        is_active=is_active,
    )


def _template(org, slug, **kwargs):
    defaults = {
        "organization": org,
        "name": slug,
        "slug": slug,
        "cadence": "daily",
        "subject_mode": "single_subject",
        "assignment_group_types": ["classroom"],
        "schema": SCHEMA,
        "languages": ["en"],
        "is_active": True,
        "author_role_filter": ["madrich", "faculty"],
        "subject_role_filter": [],
    }
    defaults.update(kwargs)
    return ReflectionTemplate.all_objects.create(**defaults)


def _assignment(org, program, template, group):
    return TemplateAssignment.all_objects.create(
        organization=org,
        program=program,
        template=template,
        target_type=TemplateAssignment.TargetType.ASSIGNMENT_GROUP,
        assignment_group=group,
        start_date=SEASON_START,
        status=TemplateAssignment.Status.ACTIVE,
    )


def test_unsaved_group_types_keeps_bunk_resolution():
    org = Organization.objects.create(name="Plain Camp", slug="plain-camp")
    program = _program(org, "plain-season")
    bunk = AssignmentGroup.all_objects.create(
        organization=org,
        program=program,
        name="Bunk Maple",
        slug="bunk-maple",
        group_type="bunk",
        is_active=True,
    )
    counselor = _person(org, program, "Sam", "counselor")
    camper = _person(org, program, "Cam", "camper")
    _seat(bunk, counselor, "author")
    _seat(bunk, camper, "subject")

    log = _template(
        org,
        "bunk-log",
        assignment_group_types=["bunk"],
        author_role_filter=["counselor"],
        subject_role_filter=["camper"],
        subject_mode="single_subject",
    )
    assert group_audience(org, bunk, log) is None
    writers = set(
        resolve_members(_assignment(org, program, log, bunk), TODAY).values_list("person_id", flat=True),
    )
    assert writers == {counselor.id}
    assert _subject_ids_for_template(bunk, log) == {camper.id}
    with organization_context(org):
        listed = _subjects_for_submission([bunk], log, org)
    assert {person.id for person in listed[bunk.id]} == {camper.id}

    # Legacy self templates still count a counselor who only sits as subject.
    subject_counselor = _person(org, program, "Jo", "counselor")
    _seat(bunk, subject_counselor, "subject")
    self_tpl = _template(
        org,
        "counselor-self",
        assignment_group_types=["bunk"],
        author_role_filter=["counselor"],
        subject_mode="self",
        role="counselor",
    )
    self_writers = set(
        resolve_members(_assignment(org, program, self_tpl, bunk), TODAY).values_list("person_id", flat=True),
    )
    assert self_writers == {counselor.id, subject_counselor.id}


def test_saved_classroom_config_names_writers_subjects_and_supervisors():
    org = Organization.objects.create(
        name="Saved School",
        slug="saved-school",
        settings={"group_types": CLASSROOM},
    )
    program = _program(org, "saved-season")
    classroom = AssignmentGroup.all_objects.create(
        organization=org,
        program=program,
        name="Kitah Alef",
        slug="kitah-alef",
        group_type="classroom",
        is_active=True,
    )
    madrich = _person(org, program, "Noa", "madrich")
    madrich_on_subject_seat = _person(org, program, "Ari", "madrich")
    faculty = _person(org, program, "Rabbi", "faculty")
    faculty_on_subject_seat = _person(org, program, "Leah", "faculty")
    student = _person(org, program, "Maya", "student")
    student_on_author_seat = _person(org, program, "Eli", "student")
    counselor = _person(org, program, "Sam", "counselor")
    retired = _person(org, program, "Old", "madrich")
    Membership.all_objects.filter(person=retired).update(is_active=False)

    _seat(classroom, madrich, "author")
    _seat(classroom, madrich_on_subject_seat, "subject")
    _seat(classroom, faculty, "author")
    _seat(classroom, faculty_on_subject_seat, "subject")
    _seat(classroom, student, "subject")
    _seat(classroom, student_on_author_seat, "author")
    _seat(classroom, counselor, "author")
    _seat(classroom, retired, "author")

    audience = group_audience(org, classroom)
    assert audience is not None
    assert audience.writers == {madrich.id, faculty.id}
    assert audience.subjects == {student.id}
    assert audience.supervisors == {faculty.id}

    # The Members tab is still the subject seat, not the form's subject list.
    roster_subjects = set(
        AssignmentGroupMembership.all_objects.filter(
            group=classroom,
            role_in_group="subject",
            is_active=True,
        ).values_list("person_id", flat=True),
    )
    assert madrich_on_subject_seat.id in roster_subjects
    assert madrich_on_subject_seat.id not in audience.subjects

    log = _template(org, "class-log", subject_role_filter=["student"])
    assert _subject_ids_for_template(classroom, log) == {student.id}
    with organization_context(org):
        listed = _subjects_for_submission([classroom], log, org)
    assert {person.id for person in listed[classroom.id]} == {student.id}
    expected, _submitted, _refs = _completion_for_assignment(
        classroom,
        _assignment(org, program, log, classroom),
        TODAY,
    )
    assert expected == 1

    # A bunk left out of the saved map does not fall back to the defaults.
    bunk = AssignmentGroup.all_objects.create(
        organization=org,
        program=program,
        name="Odd Bunk",
        slug="odd-bunk",
        group_type="bunk",
        is_active=True,
    )
    _seat(bunk, counselor, "author")
    bunk_audience = group_audience(org, bunk)
    assert bunk_audience is not None
    assert bunk_audience.writers == frozenset()
    assert bunk_audience.subjects == frozenset()


def test_form_filters_only_narrow_configured_seats():
    org = Organization.objects.create(
        name="Filter School",
        slug="filter-school",
        settings={"group_types": CLASSROOM},
    )
    program = _program(org, "filter-season")
    classroom = AssignmentGroup.all_objects.create(
        organization=org,
        program=program,
        name="Kitah Bet",
        slug="kitah-bet",
        group_type="classroom",
        is_active=True,
    )
    madrich = _person(org, program, "Noa", "madrich")
    faculty = _person(org, program, "Rabbi", "faculty")
    student = _person(org, program, "Maya", "student")
    counselor = _person(org, program, "Sam", "counselor")
    _seat(classroom, madrich, "author")
    _seat(classroom, faculty, "author")
    _seat(classroom, student, "subject")
    _seat(classroom, counselor, "author")

    madrich_only = _template(org, "madrich-log", author_role_filter=["madrich"])
    audience = group_audience(org, classroom, madrich_only)
    assert audience.writers == {madrich.id}
    assert audience.supervisors == {faculty.id}
    writer_roles = set(
        resolve_members(_assignment(org, program, madrich_only, classroom), TODAY).values_list("role", flat=True),
    )
    assert writer_roles == {"madrich"}

    # Empty author_role_filter falls back to template.role.
    by_role = _template(org, "by-role", author_role_filter=[], role="faculty")
    assert group_audience(org, classroom, by_role).writers == {faculty.id}

    # A role the classroom does not place in that seat adds nobody.
    unknown_author = _template(org, "unknown-author", author_role_filter=["counselor"])
    assert group_audience(org, classroom, unknown_author).writers == frozenset()
    unknown_subject = _template(org, "unknown-subject", subject_role_filter=["madrich"])
    narrowed = group_audience(org, classroom, unknown_subject)
    assert narrowed.subjects == frozenset()
    assert madrich.id not in narrowed.subjects


def test_self_template_resolves_to_the_writers():
    org = Organization.objects.create(
        name="Self School",
        slug="self-school",
        settings={"group_types": CLASSROOM},
    )
    program = _program(org, "self-season")
    classroom = AssignmentGroup.all_objects.create(
        organization=org,
        program=program,
        name="Kitah Gimel",
        slug="kitah-gimel",
        group_type="classroom",
        is_active=True,
    )
    madrich = _person(org, program, "Noa", "madrich")
    madrich_subject = _person(org, program, "Ari", "madrich")
    faculty = _person(org, program, "Rabbi", "faculty")
    student = _person(org, program, "Maya", "student")
    both = _person(org, program, "Dual", "madrich")
    Membership.all_objects.create(
        program=program,
        person=both,
        role="student",
        is_active=True,
    )
    _seat(classroom, madrich, "author")
    _seat(classroom, madrich_subject, "subject")
    _seat(classroom, faculty, "author")
    _seat(classroom, student, "subject")
    _seat(classroom, both, "author")

    self_tpl = _template(
        org,
        "class-self",
        subject_mode="self",
        author_role_filter=["madrich", "faculty"],
        subject_role_filter=["student"],
    )
    audience = group_audience(org, classroom, self_tpl)
    assert audience.writers == {madrich.id, faculty.id, both.id}
    assert audience.subjects == audience.writers
    assert student.id not in audience.subjects
    assert madrich_subject.id not in audience.writers

    assignment = _assignment(org, program, self_tpl, classroom)
    memberships = list(resolve_members(assignment, TODAY))
    assert {row.person_id for row in memberships} == audience.writers
    assert {row.role for row in memberships if row.person_id == both.id} == {"madrich"}

    expected, _submitted, _refs = _completion_for_assignment(classroom, assignment, TODAY)
    assert expected == 3

    for person in (madrich, faculty, both):
        found = active_assignments_for(
            viewer=person,
            organization=org,
            program=program,
            as_of=TODAY,
        )
        assert assignment in found
    for person in (student, madrich_subject):
        found = active_assignments_for(
            viewer=person,
            organization=org,
            program=program,
            as_of=TODAY,
        )
        assert found == []
