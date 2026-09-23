"""Classroom-shaped permission tests: Madrichim observe students, not peers.

A Madrich holds both ``author`` and ``subject`` on their classroom group, which
makes the usual "authors a group, therefore supervises its subjects" walk hand
them their peers. These tests pin the two corrections: no hierarchy read leg
from a group you belong to, and no profile/authoring reach to a co-author.
"""

from __future__ import annotations

import pytest

from bunk_logs.core.models import AssignmentGroup
from bunk_logs.core.models import AssignmentGroupMembership
from bunk_logs.core.models import Membership
from bunk_logs.core.models import Organization
from bunk_logs.core.models import Person
from bunk_logs.core.models import Program
from bunk_logs.core.permissions.observation_authoring import can_author_observation
from bunk_logs.core.permissions.observation_authoring import observation_authorable_subject_queryset
from bunk_logs.core.permissions.observation_read import filter_observations_readable
from bunk_logs.core.permissions.subject_dashboard import can_view_subject_dashboard
from bunk_logs.notes.models import Observation
from bunk_logs.notes.models import ObservationRecipient
from bunk_logs.notes.models import ObservationSubject
from bunk_logs.testing import SEASON_END
from bunk_logs.testing import SEASON_START

pytestmark = pytest.mark.django_db

S = Observation.Sensitivity


@pytest.fixture
def org():
    return Organization.objects.create(name="TBE", slug="tbe-obs")


@pytest.fixture
def program(org):
    return Program.all_objects.create(
        organization=org, name="TBE Religious School", slug="tbe-rs",
        program_type="religious_school",
        start_date=SEASON_START, end_date=SEASON_END,
    )


def _person(org, first, last="X"):
    return Person.all_objects.create(organization=org, first_name=first, last_name=last)


def _member(program, person, role):
    return Membership.all_objects.create(
        program=program, person=person, role=role, is_active=True,
    )


def _group(org, program, slug, group_type):
    return AssignmentGroup.all_objects.create(
        organization=org, program=program, name=slug, slug=slug,
        group_type=group_type,
    )


def _in_group(group, person, role_in_group):
    return AssignmentGroupMembership.all_objects.create(
        group=group, person=person, role_in_group=role_in_group, is_active=True,
    )


def _obs(org, program, author, subjects, sensitivity=S.NORMAL):
    obs = Observation.all_objects.create(
        organization=org, program=program, author=author,
        body="b", sensitivity=sensitivity,
    )
    for s in subjects:
        ObservationSubject.objects.create(observation=obs, subject=s)
    return obs


def _readable_ids(viewer, org):
    base = Observation.all_objects.filter(organization=org)
    return set(
        filter_observations_readable(base, viewer, org, None).values_list("id", flat=True),
    )


@pytest.fixture
def classroom(org, program):
    """Grade 7A as the TBE importer builds it.

    Faculty author. Madrichim author *and* are subjects. Students are subjects.
    """
    group = _group(org, program, "grade-7a", "classroom")
    people = {}

    people["faculty"] = _person(org, "Fran", "Faculty")
    _member(program, people["faculty"], "faculty")
    _in_group(group, people["faculty"], "author")

    for key, name in (("madrich", "Mira"), ("peer", "Pia")):
        people[key] = _person(org, name, "Madrich")
        _member(program, people[key], "madrich")
        _in_group(group, people[key], "subject")
        _in_group(group, people[key], "author")

    people["student"] = _person(org, "Sam", "Student")
    _member(program, people["student"], "student")
    _in_group(group, people["student"], "subject")

    people["group"] = group
    return people


# ---------------------------------------------------------------------------
# Read
# ---------------------------------------------------------------------------
def test_madrich_does_not_read_faculty_observation_about_their_student(org, program, classroom):
    obs = _obs(org, program, classroom["faculty"], [classroom["student"]])
    assert obs.id not in _readable_ids(classroom["madrich"], org)


def test_madrich_does_not_read_observation_about_a_peer(org, program, classroom):
    obs = _obs(org, program, classroom["faculty"], [classroom["peer"]])
    assert obs.id not in _readable_ids(classroom["madrich"], org)


def test_madrich_reads_own_observation_and_ones_they_are_tagged_on(org, program, classroom):
    own = _obs(org, program, classroom["madrich"], [classroom["student"]])
    tagged = _obs(org, program, classroom["faculty"], [classroom["student"]])
    ObservationRecipient.objects.create(
        observation=tagged, person=classroom["madrich"], option_key="specific_person",
    )
    readable = _readable_ids(classroom["madrich"], org)
    assert own.id in readable
    assert tagged.id in readable


def test_faculty_reads_classroom_observations_about_students_and_madrichim(org, program, classroom):
    about_student = _obs(org, program, classroom["madrich"], [classroom["student"]])
    about_madrich = _obs(org, program, classroom["peer"], [classroom["madrich"]])
    readable = _readable_ids(classroom["faculty"], org)
    assert about_student.id in readable
    assert about_madrich.id in readable


def test_counselor_still_reads_observations_about_their_campers(org):
    """Counselors are also ``participant`` capability, but author their bunk
    without being subjects in it, so the hierarchy leg must survive."""
    camp = Program.all_objects.create(
        organization=org, name="TBE Camp", slug="tbe-camp", program_type="summer_camp",
        start_date=SEASON_START, end_date=SEASON_END,
    )
    bunk = _group(org, camp, "bunk-a", "bunk")
    counselor = _person(org, "Cal", "Counselor")
    _member(camp, counselor, "counselor")
    _in_group(bunk, counselor, "author")
    camper = _person(org, "Cam", "Camper")
    _member(camp, camper, "camper")
    _in_group(bunk, camper, "subject")
    uh = _person(org, "Uma", "Head")
    _member(camp, uh, "unit_head")

    obs = _obs(org, camp, uh, [camper], S.SENSITIVE)
    assert obs.id in _readable_ids(counselor, org)


# ---------------------------------------------------------------------------
# Profile access
# ---------------------------------------------------------------------------
def test_madrich_opens_student_profile_but_not_a_peer(org, classroom):
    assert can_view_subject_dashboard(
        classroom["madrich"], classroom["student"], org, None,
    ) is True
    assert can_view_subject_dashboard(
        classroom["madrich"], classroom["peer"], org, None,
    ) is False


def test_faculty_opens_both_student_and_madrich_profiles(org, classroom):
    assert can_view_subject_dashboard(
        classroom["faculty"], classroom["student"], org, None,
    ) is True
    assert can_view_subject_dashboard(
        classroom["faculty"], classroom["madrich"], org, None,
    ) is True


# ---------------------------------------------------------------------------
# Authoring
# ---------------------------------------------------------------------------
def test_madrich_may_tag_a_student_but_not_a_peer(org, classroom):
    assert can_author_observation(
        classroom["madrich"], classroom["student"], org, user=None,
    ) is True
    assert can_author_observation(
        classroom["madrich"], classroom["peer"], org, user=None,
    ) is False

    taggable = set(
        observation_authorable_subject_queryset(
            classroom["madrich"], org,
        ).values_list("id", flat=True),
    )
    assert classroom["student"].id in taggable
    assert classroom["peer"].id not in taggable
    assert classroom["faculty"].id not in taggable
