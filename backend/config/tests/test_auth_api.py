"""Tests for config.auth_api ORM drift fix (step 1_3)."""

from datetime import date
from datetime import timedelta

import pytest
from django.test import RequestFactory

from bunk_logs.bunks.models import Bunk
from bunk_logs.bunks.models import Cabin
from bunk_logs.bunks.models import CounselorBunkAssignment
from bunk_logs.bunks.models import Session
from bunk_logs.bunks.models import Unit
from bunk_logs.bunks.models import UnitStaffAssignment
from bunk_logs.users.models import User
from config.auth_api import get_auth_status

TODAY = date.today()


@pytest.fixture
def rf():
    return RequestFactory()


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
    return User.objects.create_user(
        email="c@test.com", password="pass", role=User.COUNSELOR,
        first_name="Cara", last_name="C",
    )


@pytest.fixture
def unit_head(db):
    return User.objects.create_user(
        email="uh@test.com", password="pass", role=User.UNIT_HEAD,
        first_name="Uma", last_name="H",
    )


@pytest.mark.django_db
def test_unauthenticated_returns_not_authenticated(rf):
    from django.contrib.auth.models import AnonymousUser
    request = rf.get("/fake/")
    request.user = AnonymousUser()
    response = get_auth_status(request)
    import json
    data = json.loads(response.content)
    assert data["isAuthenticated"] is False


@pytest.mark.django_db
def test_counselor_bunks_use_counselor_bunk_assignment(rf, counselor, bunk):
    CounselorBunkAssignment.objects.create(
        counselor=counselor,
        bunk=bunk,
        start_date=TODAY - timedelta(days=7),
    )
    request = rf.get("/fake/")
    request.user = counselor
    response = get_auth_status(request)
    import json
    data = json.loads(response.content)
    assert data["isAuthenticated"] is True
    assert len(data["user"]["bunks"]) == 1
    assert data["user"]["bunks"][0]["id"] == str(bunk.id)


@pytest.mark.django_db
def test_counselor_expired_assignment_not_included(rf, counselor, bunk):
    CounselorBunkAssignment.objects.create(
        counselor=counselor,
        bunk=bunk,
        start_date=TODAY - timedelta(days=30),
        end_date=TODAY - timedelta(days=1),
    )
    request = rf.get("/fake/")
    request.user = counselor
    response = get_auth_status(request)
    import json
    data = json.loads(response.content)
    assert data["user"]["bunks"] == []


@pytest.mark.django_db
def test_unit_head_units_use_unit_staff_assignment(rf, unit_head, unit):
    UnitStaffAssignment.objects.create(
        unit=unit,
        staff_member=unit_head,
        role="unit_head",
        start_date=TODAY - timedelta(days=7),
    )
    request = rf.get("/fake/")
    request.user = unit_head
    response = get_auth_status(request)
    import json
    data = json.loads(response.content)
    assert data["isAuthenticated"] is True
    assert len(data["user"]["units"]) == 1
    assert data["user"]["units"][0]["id"] == str(unit.id)
    assert data["user"]["units"][0]["name"] == unit.name


@pytest.mark.django_db
def test_unit_head_expired_assignment_not_included(rf, unit_head, unit):
    UnitStaffAssignment.objects.create(
        unit=unit,
        staff_member=unit_head,
        role="unit_head",
        start_date=TODAY - timedelta(days=30),
        end_date=TODAY - timedelta(days=1),
    )
    request = rf.get("/fake/")
    request.user = unit_head
    response = get_auth_status(request)
    import json
    data = json.loads(response.content)
    assert data["user"]["units"] == []
