"""Tests for UserSerializer's membership-derived payload."""

from datetime import date
from datetime import timedelta

import pytest

from bunk_logs.core.models import Membership
from bunk_logs.core.models import Organization
from bunk_logs.core.models import Person
from bunk_logs.core.models import Program
from bunk_logs.users.models import User
from bunk_logs.users.serializers import UserSerializer

TODAY = date.today()


@pytest.fixture
def org(db):
    return Organization.objects.create(name="Serializer Camp", slug="serializer-camp")


@pytest.fixture
def program(db, org):
    return Program.all_objects.create(
        organization=org,
        name="Serializer Camp Summer",
        slug="summer",
        program_type="summer_camp",
        start_date=TODAY - timedelta(days=30),
        end_date=TODAY + timedelta(days=60),
        is_active=True,
    )


@pytest.mark.django_db
def test_membership_roles_and_organizations_for_member(org, program):
    user = User.objects.create_user(email="c@test.com", password="pass")
    person = Person.all_objects.create(
        organization=org, first_name="Cara", last_name="C", user=user,
    )
    Membership.all_objects.create(
        program=program, person=person, role="counselor", is_active=True,
    )

    data = UserSerializer(user).data
    assert data["membership_roles"] == ["counselor"]
    assert len(data["organizations"]) == 1
    assert data["organizations"][0]["slug"] == "serializer-camp"
    assert data["organizations"][0]["capability"] == "participant"
    assert data["organizations"][0]["program_types"] == ["summer_camp"]


@pytest.mark.django_db
def test_program_types_for_religious_school_member(db):
    school = Organization.objects.create(name="Serializer Shul", slug="serializer-shul")
    school_program = Program.all_objects.create(
        organization=school,
        name="Serializer Shul Religious School",
        slug="religious-school",
        program_type="religious_school",
        start_date=TODAY - timedelta(days=30),
        end_date=TODAY + timedelta(days=60),
        is_active=True,
    )
    user = User.objects.create_user(email="madrich@test.com", password="pass")
    person = Person.all_objects.create(
        organization=school, first_name="Maya", last_name="M", user=user,
    )
    Membership.all_objects.create(
        program=school_program, person=person, role="madrich", is_active=True,
    )

    data = UserSerializer(user).data
    assert data["organizations"][0]["program_types"] == ["religious_school"]


@pytest.mark.django_db
def test_program_types_fall_back_to_org_programs_without_memberships(org, program):
    """Between memberships, the org's own active programs still identify its shape."""
    user = User.objects.create_user(email="between@test.com", password="pass")
    Person.all_objects.create(
        organization=org, first_name="Between", last_name="Jobs", user=user,
    )

    data = UserSerializer(user).data
    assert data["organizations"][0]["capability"] is None
    assert data["organizations"][0]["program_types"] == ["summer_camp"]


@pytest.mark.django_db
def test_inactive_membership_excluded(org, program):
    user = User.objects.create_user(email="x@test.com", password="pass")
    person = Person.all_objects.create(
        organization=org, first_name="Ex", last_name="Member", user=user,
    )
    Membership.all_objects.create(
        program=program, person=person, role="counselor", is_active=False,
    )

    data = UserSerializer(user).data
    assert data["membership_roles"] == []
    assert data["organizations"][0]["capability"] is None


@pytest.mark.django_db
def test_user_without_person_has_empty_context(db):
    user = User.objects.create_user(email="lonely@test.com", password="pass")
    data = UserSerializer(user).data
    assert data["membership_roles"] == []
    assert data["organizations"] == []
