"""Temple Beth-El seat cutover: settings, cohort, classroom seats, supervision."""

from __future__ import annotations

from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from rest_framework.test import APIClient

from bunk_logs.core.context import organization_context
from bunk_logs.core.models import AssignmentGroup
from bunk_logs.core.models import AssignmentGroupMembership
from bunk_logs.core.models import ClassroomChallenge
from bunk_logs.core.models import Membership
from bunk_logs.core.models import Organization
from bunk_logs.core.models import Person
from bunk_logs.core.models import Program
from bunk_logs.core.models import Supervision
from bunk_logs.core.org_config import DEFAULT_GROUP_TYPE_CONFIG
from bunk_logs.core.permissions.subject_note_authoring import can_author_subject_note
from bunk_logs.core.reflection_threads import cohort_group_ids
from bunk_logs.core.tbe_group_cutover import cut_over_tbe
from bunk_logs.core.terminology import term
from bunk_logs.core.time_utils import get_today
from bunk_logs.testing import SEASON_END
from bunk_logs.testing import SEASON_START

User = get_user_model()
pytestmark = pytest.mark.django_db

UNASSIGNED = ("Abrams", "Ettekal", "Magnone", "Taub", "Theriaque")


def _hdr(slug: str) -> dict:
    return {"HTTP_X_ORGANIZATION_SLUG": slug}


def _person(org, first, last, email):
    user = User.objects.create_user(email=email, password="pw")
    person = Person.all_objects.create(
        organization=org, first_name=first, last_name=last, user=user, email=email,
    )
    return user, person


def _member(program, person, role, *, active=True):
    return Membership.all_objects.create(
        program=program, person=person, role=role, is_active=active,
    )


def _group(org, program, name, slug, group_type):
    return AssignmentGroup.all_objects.create(
        organization=org, program=program, name=name, slug=slug, group_type=group_type,
    )


def _seat(group, person, role_in_group, *, active=True):
    return AssignmentGroupMembership.all_objects.create(
        group=group, person=person, role_in_group=role_in_group, is_active=active,
    )


def _fingerprint(org):
    seats = list(
        AssignmentGroupMembership.all_objects.filter(group__organization=org)
        .order_by("group_id", "person_id", "role_in_group")
        .values_list("group_id", "person_id", "role_in_group", "is_active"),
    )
    groups = list(
        AssignmentGroup.all_objects.filter(organization=org)
        .order_by("id")
        .values_list("id", "slug", "group_type"),
    )
    supervision = list(
        Supervision.all_objects.filter(supervisor_membership__program__organization=org)
        .order_by("supervisor_membership_id", "target_group_id", "id")
        .values_list("supervisor_membership_id", "target_group_id", "target_type", "end_date"),
    )
    return {
        "settings": org.settings,
        "groups": groups,
        "seats": seats,
        "supervision": supervision,
    }


@pytest.fixture
def api() -> APIClient:
    return APIClient()


@pytest.fixture
def world():
    tbe = Organization.objects.create(name="TBE", slug="tbe")
    tbe.settings = {
        "terminology": {
            "camper": {"one": "student", "other": "students"},
            "bunk": {"one": "class", "other": "classes"},
            "counselor": {"one": "faculty", "other": "faculty"},
            "director": {"one": "Ed Team", "other": "Ed Team"},
            "cohort": {"one": "Teaching Team", "other": "Teaching Teams"},
        },
        "branding": {"display_name": "North Star School"},
    }
    tbe.save(update_fields=["settings"])
    program = Program.all_objects.create(
        organization=tbe,
        name="TBE Religious School",
        slug="tbe-rs",
        program_type="religious_school",
        start_date=SEASON_START,
        end_date=SEASON_END,
    )

    cohort = _group(tbe, program, "Madrichim", "madrichim", "classroom")
    grade3 = _group(tbe, program, "Grade 3", "grade-3", "classroom")
    client = _group(tbe, program, "Test class", "test-class", "classroom")

    _maya_user, maya = _person(tbe, "Maya", "Class", "maya@tbe.test")
    _member(program, maya, "madrich")
    _seat(grade3, maya, "author")
    _seat(cohort, maya, "subject")
    _seat(cohort, maya, "author", active=False)

    _student_user, student = _person(tbe, "Ari", "Student", "ari@tbe.test")
    _member(program, student, "student")
    _seat(grade3, student, "subject")

    faculty_user, faculty = _person(tbe, "Fay", "Faculty", "fay@tbe.test")
    faculty_membership = _member(program, faculty, "faculty")
    _seat(grade3, faculty, "author")
    _seat(cohort, faculty, "author")

    _client_user, client_madrich = _person(tbe, "Tess", "Client", "tess@tbe.test")
    _member(program, client_madrich, "madrich")
    _seat(client, client_madrich, "subject")
    _seat(client, client_madrich, "author")

    unassigned = []
    for last in UNASSIGNED:
        _user, person = _person(tbe, "Uno", last, f"{last.lower()}@tbe.test")
        _member(program, person, "madrich")
        _seat(cohort, person, "subject")
        _seat(cohort, person, "author", active=False)
        unassigned.append(person)

    _old_user, retired = _person(tbe, "Dan", "Retired", "dan@tbe.test")
    _member(program, retired, "madrich", active=False)
    _seat(grade3, retired, "subject", active=False)
    _seat(grade3, retired, "author", active=False)

    sunday = get_today(tbe)
    sunday = sunday + timedelta(days=(6 - sunday.weekday()) % 7)
    challenge = ClassroomChallenge.all_objects.create(
        organization=tbe,
        program=program,
        assignment_group=cohort,
        author=maya,
        session_date=sunday,
        category=ClassroomChallenge.CATEGORY_BEHAVIOR,
        body="Filed while this group was still a class.",
        status=ClassroomChallenge.STATUS_ACKNOWLEDGED,
    )

    clc = Organization.objects.create(name="CLC", slug="clc")
    clc_program = Program.all_objects.create(
        organization=clc,
        name="CLC Summer",
        slug="clc-summer",
        program_type="summer_camp",
        start_date=SEASON_START,
        end_date=SEASON_END,
    )
    clc_bunk = _group(clc, clc_program, "Bunk 1", "bunk-1", "bunk")
    _clc_user, camper = _person(clc, "Cam", "Camper", "cam@clc.test")
    _member(clc_program, camper, "camper")
    clc_seat = _seat(clc_bunk, camper, "subject")

    cut_over_tbe()
    tbe.refresh_from_db()
    clc.refresh_from_db()
    cohort.refresh_from_db()
    return {
        "tbe": tbe,
        "program": program,
        "cohort": cohort,
        "grade3": grade3,
        "client": client,
        "maya": maya,
        "maya_user": _maya_user,
        "student": student,
        "faculty": faculty,
        "faculty_user": faculty_user,
        "faculty_membership": faculty_membership,
        "client_madrich": client_madrich,
        "unassigned": unassigned,
        "retired": retired,
        "challenge": challenge,
        "clc": clc,
        "clc_bunk": clc_bunk,
        "clc_seat": clc_seat,
    }


def test_cutover_seats_supervision_and_words_and_rerun_is_a_noop(world):
    tbe = world["tbe"]
    cohort = world["cohort"]
    grade3 = world["grade3"]
    client = world["client"]
    maya = world["maya"]

    assert cohort.group_type == "cohort"
    assert AssignmentGroupMembership.all_objects.filter(
        group=cohort, person=maya, role_in_group="subject", is_active=True,
    ).exists()
    assert AssignmentGroupMembership.all_objects.filter(
        group=cohort, person=maya, role_in_group="author", is_active=True,
    ).exists()
    for person in world["unassigned"]:
        assert AssignmentGroupMembership.all_objects.filter(
            group=cohort, person=person, role_in_group="subject", is_active=True,
        ).exists()
        assert AssignmentGroupMembership.all_objects.filter(
            group=cohort, person=person, role_in_group="author", is_active=True,
        ).exists()
        assert not AssignmentGroupMembership.all_objects.filter(
            person=person, group__group_type="classroom", is_active=True,
        ).exists()

    assert not AssignmentGroupMembership.all_objects.filter(
        group=client, person=world["client_madrich"], role_in_group="subject", is_active=True,
    ).exists()
    assert AssignmentGroupMembership.all_objects.filter(
        group=client, person=world["client_madrich"], role_in_group="author", is_active=True,
    ).exists()
    assert AssignmentGroupMembership.all_objects.filter(
        group=grade3, person=maya, role_in_group="author", is_active=True,
    ).exists()
    assert not AssignmentGroupMembership.all_objects.filter(
        group=grade3, person=world["retired"], role_in_group="author", is_active=True,
    ).exists()

    supervised = set(
        Supervision.all_objects.filter(
            supervisor_membership=world["faculty_membership"],
            target_type=Supervision.TargetType.ASSIGNMENT_GROUP,
        ).values_list("target_group_id", flat=True),
    )
    assert supervised == {grade3.id}

    assert tbe.settings["group_types"]["bunk"] == DEFAULT_GROUP_TYPE_CONFIG["bunk"]
    assert tbe.settings["group_types"]["unit"] == DEFAULT_GROUP_TYPE_CONFIG["unit"]
    classroom_roles = {
        (member["role"], member["placed_as"], member["supervises_group"])
        for member in tbe.settings["group_types"]["classroom"]["members"]
    }
    assert ("madrich", "subject", False) not in classroom_roles
    assert ("faculty", "author", True) in classroom_roles
    cohort_supervisors = [
        member for member in tbe.settings["group_types"]["cohort"]["members"]
        if member["supervises_group"]
    ]
    assert cohort_supervisors == []
    assert term(tbe, "counselor", plural=True) == "madrichim"
    assert term(tbe, "unit_head") == "faculty"
    assert term(tbe, "group", plural=True) == "classes"
    assert term(tbe, "program") == "school year"
    assert term(tbe, "camper") == "student"
    assert term(tbe, "cohort") == "Teaching Team"
    assert tbe.settings["branding"]["display_name"] == "North Star School"

    world["challenge"].refresh_from_db()
    assert world["challenge"].assignment_group_id == cohort.id
    assert world["challenge"].status == ClassroomChallenge.STATUS_ACKNOWLEDGED
    with pytest.raises(ValidationError):
        world["challenge"].full_clean()

    before = _fingerprint(tbe)
    cut_over_tbe()
    tbe.refresh_from_db()
    assert _fingerprint(tbe) == before


def test_crane_lake_is_unchanged(world):
    clc = world["clc"]
    assert "group_types" not in (clc.settings or {})
    world["clc_bunk"].refresh_from_db()
    world["clc_seat"].refresh_from_db()
    assert world["clc_bunk"].group_type == "bunk"
    assert world["clc_seat"].is_active is True
    assert world["clc_seat"].role_in_group == "subject"
    assert Supervision.all_objects.filter(
        supervisor_membership__program__organization=clc,
    ).count() == 0


def test_faculty_sees_the_class_and_not_the_unassigned(api, world):
    tbe = world["tbe"]
    api.force_authenticate(user=world["faculty_user"])
    with organization_context(tbe):
        opened = api.get(
            f"/api/v1/dashboards/group/{world['grade3'].id}/",
            **_hdr(tbe.slug),
        )
        roster = api.get("/api/v1/faculty/roster/", **_hdr(tbe.slug))
    assert opened.status_code == 200, opened.content
    names = [row["name"] for row in opened.json()["roster"]]
    assert "Ari Student" in names
    assert "Maya Class" in names
    for last in UNASSIGNED:
        assert all(last not in name for name in names)

    assert roster.status_code == 200, roster.content
    roster_names = [row["display_name"] for row in roster.json()["results"]]
    assert "Maya Class" in roster_names
    for last in UNASSIGNED:
        assert all(last not in name for name in roster_names)
    assert roster.json()["roster_term"] == "counselor"


def test_madrich_opens_the_class_logs_on_a_student_and_files_a_challenge(api, world):
    tbe = world["tbe"]
    maya = world["maya"]
    api.force_authenticate(user=world["maya_user"])
    with organization_context(tbe):
        opened = api.get(
            f"/api/v1/dashboards/group/{world['grade3'].id}/",
            **_hdr(tbe.slug),
        )
    assert opened.status_code == 200, opened.content
    assert can_author_subject_note(maya, world["student"], tbe, world["maya_user"]) is True

    with organization_context(tbe):
        created = api.post(
            "/api/v1/madrich/challenges/",
            {
                "assignment_group_id": world["grade3"].id,
                "category": ClassroomChallenge.CATEGORY_BEHAVIOR,
                "body": "The room was too loud.",
            },
            format="json",
            **_hdr(tbe.slug),
        )
    assert created.status_code == 201, created.content

    api.force_authenticate(user=world["faculty_user"])
    with organization_context(tbe):
        challenges = api.get("/api/v1/faculty/challenges/", **_hdr(tbe.slug))
    assert challenges.status_code == 200, challenges.content
    bodies = [row["body_preview"] for row in challenges.json()["results"]]
    assert any("too loud" in body for body in bodies)


def test_teaching_team_still_includes_the_cohort(api, world):
    tbe = world["tbe"]
    maya = world["maya"]
    assert cohort_group_ids(maya, world["program"]) == [world["cohort"].id]

    api.force_authenticate(user=world["maya_user"])
    with organization_context(tbe):
        members = api.get("/api/v1/cohort/members/", **_hdr(tbe.slug))
    assert members.status_code == 200, members.content
    assert [cohort["name"] for cohort in members.json()["cohorts"]] == ["Madrichim"]
    names = [row["display_name"] for row in members.json()["results"]]
    assert "Maya Class" in names
    for last in UNASSIGNED:
        assert any(last in name for name in names)
