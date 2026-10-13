"""Form audience preview: who writes, who it is about, who can read it."""

from __future__ import annotations

import copy

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

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
from bunk_logs.core.org_config import DEFAULT_GROUP_TYPE_CONFIG
from bunk_logs.testing import SEASON_END
from bunk_logs.testing import SEASON_START

User = get_user_model()
pytestmark = pytest.mark.django_db

SCHEMA = {"fields": [{"key": "note", "type": "textarea", "required": False, "prompts": {"en": "Notes"}}]}


def _program(org, slug="season"):
    return Program.all_objects.create(
        organization=org,
        name=f"{org.name} Season",
        slug=slug,
        program_type="summer_camp",
        start_date=SEASON_START,
        end_date=SEASON_END,
    )


def _person(org, program, first, role):
    person = Person.all_objects.create(
        organization=org,
        first_name=first,
        last_name="Lane",
    )
    Membership.all_objects.create(
        program=program,
        person=person,
        role=role,
        is_active=True,
    )
    return person


def _seat(group, person, role_in_group):
    AssignmentGroupMembership.all_objects.create(
        group=group,
        person=person,
        role_in_group=role_in_group,
        is_active=True,
    )


def _template(org, slug, **kwargs):
    defaults = {
        "organization": org,
        "name": slug,
        "slug": slug,
        "cadence": "daily",
        "role": "counselor",
        "schema": SCHEMA,
        "languages": ["en"],
        "is_active": True,
        "status": ReflectionTemplate.Status.PUBLISHED,
        "version": 1,
        "subject_mode": "single_subject",
        "assignment_scope": "per_subject_in_group",
        "assignment_group_types": ["bunk"],
        "author_role_filter": ["counselor"],
        "subject_role_filter": ["camper"],
    }
    defaults.update(kwargs)
    return ReflectionTemplate.all_objects.create(**defaults)


def _admin(org, program):
    user = User.objects.create_user(email=f"admin@{org.slug}.test", password="pw")
    person = Person.all_objects.create(
        organization=org,
        first_name="Org",
        last_name="Admin",
        user=user,
    )
    Membership.all_objects.create(
        program=program,
        person=person,
        role="admin",
        is_active=True,
    )
    return user


def _client(user, org):
    client = APIClient()
    client.force_authenticate(user=user)
    client.credentials(HTTP_X_ORGANIZATION_SLUG=org.slug)
    return client


def test_bunk_preview_names_writers_subjects_and_parent_supervisor():
    org = Organization.objects.create(
        name="Preview Camp",
        slug="preview-camp",
        settings={
            "group_types": {
                "bunk": copy.deepcopy(DEFAULT_GROUP_TYPE_CONFIG["bunk"]),
                "unit": copy.deepcopy(DEFAULT_GROUP_TYPE_CONFIG["unit"]),
            },
        },
    )
    program = _program(org)
    unit = AssignmentGroup.all_objects.create(
        organization=org,
        program=program,
        name="North",
        slug="north",
        group_type="unit",
    )
    bunk = AssignmentGroup.all_objects.create(
        organization=org,
        program=program,
        name="Maple",
        slug="maple",
        group_type="bunk",
        parent=unit,
    )
    ada = _person(org, program, "Ada", "counselor")
    bea = _person(org, program, "Bea", "counselor")
    _seat(bunk, ada, "author")
    _seat(bunk, bea, "author")
    campers = [_person(org, program, name, "camper") for name in ("Cam", "Dee", "Eli")]
    for camper in campers:
        _seat(bunk, camper, "subject")
    uma = _person(org, program, "Uma", "unit_head")
    _seat(unit, uma, "author")
    template = _template(org, "bunk-daily")
    admin = _admin(org, program)

    with organization_context(org):
        resp = _client(admin, org).get(
            f"/api/v1/leadership-team/templates/{template.id}/audience-preview/",
            {"target_type": "assignment_group", "groups": str(bunk.id)},
        )
    assert resp.status_code == 200, resp.data
    body = resp.data
    audience = group_audience(org, bunk, template)
    assert audience is not None
    writer_ids = {person["id"] for person in body["writers"]}
    subject_ids = {person["id"] for person in body["subjects"]}
    assert writer_ids == set(audience.writers) == {ada.id, bea.id}
    assert subject_ids == set(audience.subjects) == {camper.id for camper in campers}
    stub = TemplateAssignment(
        organization=org,
        program=program,
        template=template,
        target_type=TemplateAssignment.TargetType.ASSIGNMENT_GROUP,
        assignment_group=bunk,
        target_payload={},
    )
    resolved = set(resolve_members(stub, SEASON_START).values_list("person_id", flat=True))
    assert writer_ids == resolved
    assert uma.id in {person["id"] for person in body["supervisors"]}
    assert uma.id not in audience.supervisors
    sentence = body["sentence"]
    for person in (ada, bea, *campers, uma):
        assert str(person) in sentence
    assert body["can_assign"] is True
    assert body["groups"][0]["name"] == "Maple"
    assert {person["role_label"] for person in body["writers"]} == {"Counselor"}


def test_class_with_no_students_is_named_and_cannot_be_assigned():
    org = Organization.objects.create(name="Preview School", slug="preview-school")
    program = _program(org, "school-season")
    classroom = AssignmentGroup.all_objects.create(
        organization=org,
        program=program,
        name="Grade 3",
        slug="grade-3",
        group_type="classroom",
    )
    faculty = _person(org, program, "Fay", "faculty")
    _seat(classroom, faculty, "author")
    about_others = _template(
        org,
        "class-log",
        role="faculty",
        assignment_group_types=["classroom"],
        author_role_filter=["faculty"],
        subject_role_filter=["student"],
    )
    about_self = _template(
        org,
        "faculty-self",
        role="faculty",
        subject_mode="self",
        assignment_scope="none",
        assignment_group_types=[],
        author_role_filter=["faculty"],
        subject_role_filter=[],
    )
    admin = _admin(org, program)
    client = _client(admin, org)

    with organization_context(org):
        preview = client.get(
            f"/api/v1/leadership-team/templates/{about_others.id}/audience-preview/",
            {"target_type": "assignment_group", "groups": str(classroom.id)},
        )
        blocked = client.post(
            "/api/v1/leadership-team/assignments/",
            data={
                "template": about_others.id,
                "target_type": "assignment_group",
                "assignment_group": classroom.id,
                "target_payload": {},
                "start_date": SEASON_START.isoformat(),
            },
            format="json",
        )
        self_preview = client.get(
            f"/api/v1/leadership-team/templates/{about_self.id}/audience-preview/",
            {"target_type": "assignment_group", "groups": str(classroom.id)},
        )
        allowed = client.post(
            "/api/v1/leadership-team/assignments/",
            data={
                "template": about_self.id,
                "target_type": "assignment_group",
                "assignment_group": classroom.id,
                "target_payload": {},
                "start_date": SEASON_START.isoformat(),
            },
            format="json",
        )

    assert preview.status_code == 200, preview.data
    assert "Grade 3" in preview.data["sentence"]
    assert "student" in preview.data["sentence"]
    assert preview.data["can_assign"] is False
    assert preview.data["groups"][0]["missing"] == ["subjects"]
    assert blocked.status_code == 400
    assert "Grade 3" in str(blocked.data)

    assert self_preview.status_code == 200, self_preview.data
    assert self_preview.data["can_assign"] is True
    assert "Fay Lane" in self_preview.data["sentence"]
    assert "themselves" in self_preview.data["sentence"]
    assert allowed.status_code == 201, allowed.data


def test_role_labels_use_terminology():
    plain = Organization.objects.create(name="Camp Words", slug="camp-words")
    renamed = Organization.objects.create(
        name="School Words",
        slug="school-words",
        settings={"terminology": {"counselor": {"one": "madrich", "other": "madrichim"}}},
    )
    for org in (plain, renamed):
        program = _program(org, f"{org.slug}-season")
        bunk = AssignmentGroup.all_objects.create(
            organization=org,
            program=program,
            name="Cabin",
            slug="cabin",
            group_type="bunk",
        )
        template = _template(org, f"{org.slug}-log")
        admin = _admin(org, program)
        with organization_context(org):
            resp = _client(admin, org).get(
                f"/api/v1/leadership-team/templates/{template.id}/audience-preview/",
                {"target_type": "assignment_group", "groups": str(bunk.id)},
            )
        assert resp.status_code == 200, resp.data
        sentence = resp.data["sentence"].lower()
        assert "cabin" in sentence
        if org is plain:
            assert "counselor" in sentence
            assert "madrich" not in sentence
        else:
            assert "madrich" in sentence
            assert "counselor" not in sentence


def test_builder_rejects_writer_role_the_group_type_does_not_configure():
    org = Organization.objects.create(name="Filter Camp", slug="filter-camp")
    program = _program(org, "filter-season")
    admin = _admin(org, program)
    client = _client(admin, org)
    base = {
        "name": "Bunk log",
        "slug": "bunk-log-filter",
        "cadence": "daily",
        "role": "counselor",
        "schema": SCHEMA,
        "languages": ["en"],
        "subject_mode": "single_subject",
        "assignment_scope": "per_subject_in_group",
        "assignment_group_types": ["bunk"],
        "subject_role_filter": ["camper"],
    }
    with organization_context(org):
        rejected = client.post(
            "/api/v1/leadership-team/templates/",
            data={**base, "author_role_filter": ["faculty"]},
            format="json",
        )
        accepted = client.post(
            "/api/v1/leadership-team/templates/",
            data={**base, "slug": "bunk-log-ok", "author_role_filter": ["counselor"]},
            format="json",
        )
    assert rejected.status_code == 400
    assert "Faculty" in str(rejected.data)
    assert accepted.status_code == 201, accepted.data
    assert accepted.data["author_role_filter"] == ["counselor"]


def test_preview_requires_an_admin():
    org = Organization.objects.create(name="Preview Auth", slug="preview-auth")
    program = _program(org, "auth-season")
    user = User.objects.create_user(email="counselor@preview-auth.test", password="pw")
    person = _person(org, program, "Cam", "counselor")
    person.user = user
    person.save(update_fields=["user"])
    template = _template(org, "auth-log")
    with organization_context(org):
        resp = _client(user, org).get(
            f"/api/v1/leadership-team/templates/{template.id}/audience-preview/",
            {"target_type": "role", "role": "counselor"},
        )
    assert resp.status_code == 403


def test_preview_includes_a_global_template():
    org = Organization.objects.create(name="Preview Global", slug="preview-global")
    program = _program(org, "global-season")
    admin = _admin(org, program)
    template = _template(
        None,
        "global-weekly",
        subject_mode="self",
        assignment_scope="none",
        assignment_group_types=[],
    )
    with organization_context(org):
        resp = _client(admin, org).get(
            f"/api/v1/leadership-team/templates/{template.id}/audience-preview/",
            {"target_type": "role", "role": "counselor"},
        )
    assert resp.status_code == 200
    assert isinstance(resp.data["sentence"], str)
