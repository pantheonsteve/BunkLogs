"""Shared fixtures for the Notes platform test suite (Step 7_19).

Provides a minimal org + program + two persons (counselor + unit head)
with the supervision and assignment-group relationships needed by
audience-resolution and API tests.
"""

from __future__ import annotations

from datetime import date

import pytest

from bunk_logs.core.context import organization_context
from bunk_logs.core.models import AssignmentGroup
from bunk_logs.core.models import AssignmentGroupMembership
from bunk_logs.core.models import Membership
from bunk_logs.core.models import Organization
from bunk_logs.core.models import Person
from bunk_logs.core.models import Program
from bunk_logs.core.models import Supervision


def _user(email):
    from bunk_logs.users.models import User
    return User.objects.create_user(email=email, password="pw")


def _person(org, *, first, last="Test", user=None):
    return Person.all_objects.create(
        organization=org, first_name=first, last_name=last, user=user,
    )


def _member(program, person, *, role, is_active=True):
    return Membership.all_objects.create(
        program=program, person=person, role=role, is_active=is_active,
    )


@pytest.fixture
def org():
    return Organization.objects.create(name="Notes Org", slug="notes-org")


@pytest.fixture
def other_org():
    return Organization.objects.create(name="Other Org", slug="notes-other-org")


@pytest.fixture
def program(org):
    return Program.all_objects.create(
        organization=org,
        name="Notes Org Summer 2026",
        slug="notes-summer-2026",
        program_type="summer_camp",
        start_date=date(2026, 6, 1),
        end_date=date(2026, 8, 31),
    )


@pytest.fixture
def other_program(other_org):
    return Program.all_objects.create(
        organization=other_org,
        name="Other Org Summer 2026",
        slug="other-notes-summer-2026",
        program_type="summer_camp",
        start_date=date(2026, 6, 1),
        end_date=date(2026, 8, 31),
    )


@pytest.fixture
def counselor_user():
    return _user("counselor@notes.test")


@pytest.fixture
def uh_user():
    return _user("uh@notes.test")


@pytest.fixture
def counselor_person(org, counselor_user):
    return _person(org, first="Alice", user=counselor_user)


@pytest.fixture
def uh_person(org, uh_user):
    return _person(org, first="Bob", user=uh_user)


@pytest.fixture
def counselor_membership(program, counselor_person):
    return _member(program, counselor_person, role="counselor")


@pytest.fixture
def uh_membership(program, uh_person):
    return _member(program, uh_person, role="unit_head")


@pytest.fixture
def bunk(org, program):
    return AssignmentGroup.all_objects.create(
        organization=org,
        program=program,
        name="Bunk Maple",
        slug="bunk-maple",
        group_type="bunk",
    )


@pytest.fixture
def counselor_in_bunk(bunk, counselor_person):
    return AssignmentGroupMembership.all_objects.create(
        group=bunk,
        person=counselor_person,
        role_in_group="author",
        is_active=True,
    )


@pytest.fixture
def uh_supervises_counselor(uh_membership, counselor_membership):
    """Supervision row: UH -> counselor (target_type=MEMBERSHIP)."""
    return Supervision.all_objects.create(
        supervisor_membership=uh_membership,
        target_type=Supervision.TargetType.MEMBERSHIP,
        target_membership=counselor_membership,
        start_date=date(2026, 1, 1),
    )
