"""Tests for UserSerializer ORM drift fix (step 1_3)."""

from datetime import date
from datetime import timedelta

import pytest

from bunk_logs.bunks.models import Bunk
from bunk_logs.bunks.models import Cabin
from bunk_logs.bunks.models import CounselorBunkAssignment
from bunk_logs.bunks.models import Session
from bunk_logs.bunks.models import Unit
from bunk_logs.bunks.models import UnitStaffAssignment
from bunk_logs.users.models import User
from bunk_logs.users.serializers import UserSerializer

TODAY = date.today()


@pytest.fixture
def session(db):
    return Session.objects.create(
        name="Summer 2026",
        start_date=TODAY - timedelta(days=30),
        end_date=TODAY + timedelta(days=60),
    )


@pytest.fixture
def cabin(db):
    return Cabin.objects.create(name="Cabin A", capacity=10)


@pytest.fixture
def unit(db):
    return Unit.objects.create(name="Unit 1")


@pytest.fixture
def bunk(db, session, cabin, unit):
    return Bunk.objects.create(cabin=cabin, session=session, unit=unit, is_active=True)


@pytest.fixture
def counselor(db):
    return User.objects.create_user(email="c@test.com", password="pass", role=User.COUNSELOR)


@pytest.fixture
def unit_head(db):
    return User.objects.create_user(email="uh@test.com", password="pass", role=User.UNIT_HEAD)


@pytest.fixture
def admin_user(db):
    return User.objects.create_user(email="a@test.com", password="pass", role=User.ADMIN)


# --- get_bunks ---

@pytest.mark.django_db
def test_get_bunks_returns_active_assignment_for_counselor(counselor, bunk):
    CounselorBunkAssignment.objects.create(
        counselor=counselor,
        bunk=bunk,
        start_date=TODAY - timedelta(days=7),
    )
    data = UserSerializer(counselor).data
    assert len(data["bunks"]) == 1
    assert data["bunks"][0]["id"] == str(bunk.id)
    assert "name" in data["bunks"][0]


@pytest.mark.django_db
def test_get_bunks_excludes_expired_assignment(counselor, bunk):
    CounselorBunkAssignment.objects.create(
        counselor=counselor,
        bunk=bunk,
        start_date=TODAY - timedelta(days=30),
        end_date=TODAY - timedelta(days=1),
    )
    data = UserSerializer(counselor).data
    assert data["bunks"] == []


@pytest.mark.django_db
def test_get_bunks_returns_empty_for_non_counselor(admin_user):
    data = UserSerializer(admin_user).data
    assert data["bunks"] == []


# --- get_units ---

@pytest.mark.django_db
def test_get_units_returns_active_assignment_for_unit_head(unit_head, unit):
    UnitStaffAssignment.objects.create(
        unit=unit,
        staff_member=unit_head,
        role="unit_head",
        start_date=TODAY - timedelta(days=7),
    )
    data = UserSerializer(unit_head).data
    assert len(data["units"]) == 1
    assert data["units"][0]["id"] == str(unit.id)
    assert data["units"][0]["name"] == unit.name


@pytest.mark.django_db
def test_get_units_excludes_expired_assignment(unit_head, unit):
    UnitStaffAssignment.objects.create(
        unit=unit,
        staff_member=unit_head,
        role="unit_head",
        start_date=TODAY - timedelta(days=30),
        end_date=TODAY - timedelta(days=1),
    )
    data = UserSerializer(unit_head).data
    assert data["units"] == []


@pytest.mark.django_db
def test_get_units_returns_empty_for_non_unit_head(counselor):
    data = UserSerializer(counselor).data
    assert data["units"] == []
