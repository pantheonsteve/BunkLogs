"""Tests for BunkLogsAllByDateViewSet role-based filtering."""

from datetime import date
from datetime import timedelta

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from bunk_logs.bunklogs.models import BunkLog
from bunk_logs.bunks.models import Bunk
from bunk_logs.bunks.models import Cabin
from bunk_logs.bunks.models import CounselorBunkAssignment
from bunk_logs.bunks.models import Session
from bunk_logs.bunks.models import Unit
from bunk_logs.bunks.models import UnitStaffAssignment
from bunk_logs.campers.models import Camper
from bunk_logs.campers.models import CamperBunkAssignment
from bunk_logs.users.models import User

TODAY = date.today()
DATE_STR = TODAY.strftime("%Y-%m-%d")


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def session(db):
    return Session.objects.create(
        name="Summer 2026",
        start_date=TODAY - timedelta(days=30),
        end_date=TODAY + timedelta(days=60),
    )


@pytest.fixture
def cabin_a(db):
    return Cabin.objects.create(name="Cabin A", capacity=10)


@pytest.fixture
def cabin_b(db):
    return Cabin.objects.create(name="Cabin B", capacity=10)


@pytest.fixture
def unit_1(db):
    return Unit.objects.create(name="Unit 1")


@pytest.fixture
def unit_2(db):
    return Unit.objects.create(name="Unit 2")


@pytest.fixture
def bunk_a(db, session, cabin_a, unit_1):
    return Bunk.objects.create(cabin=cabin_a, session=session, unit=unit_1, is_active=True)


@pytest.fixture
def bunk_b(db, session, cabin_b, unit_2):
    return Bunk.objects.create(cabin=cabin_b, session=session, unit=unit_2, is_active=True)


@pytest.fixture
def admin_user(db):
    return User.objects.create_user(
        email="admin@test.com", password="pass", role=User.ADMIN, is_staff=True,
    )


@pytest.fixture
def unit_head_1(db):
    return User.objects.create_user(email="unithead1@test.com", password="pass", role=User.UNIT_HEAD)


@pytest.fixture
def camper_care_1(db):
    return User.objects.create_user(email="cc1@test.com", password="pass", role=User.CAMPER_CARE)


@pytest.fixture
def counselor_a(db):
    return User.objects.create_user(email="counselora@test.com", password="pass", role=User.COUNSELOR)


@pytest.fixture
def counselor_b(db):
    return User.objects.create_user(email="counselorb@test.com", password="pass", role=User.COUNSELOR)


@pytest.fixture
def camper_in_bunk_a(db, bunk_a):
    camper = Camper.objects.create(first_name="Alice", last_name="Smith")
    CamperBunkAssignment.objects.create(
        camper=camper, bunk=bunk_a, start_date=TODAY - timedelta(days=7), is_active=True,
    )
    return camper


@pytest.fixture
def camper_in_bunk_b(db, bunk_b):
    camper = Camper.objects.create(first_name="Bob", last_name="Jones")
    CamperBunkAssignment.objects.create(
        camper=camper, bunk=bunk_b, start_date=TODAY - timedelta(days=7), is_active=True,
    )
    return camper


@pytest.fixture
def log_in_bunk_a(db, camper_in_bunk_a, bunk_a, counselor_a):
    assignment = CamperBunkAssignment.objects.get(camper=camper_in_bunk_a, bunk=bunk_a)
    return BunkLog.objects.create(
        bunk_assignment=assignment,
        date=TODAY,
        counselor=counselor_a,
        social_score=4,
        behavior_score=4,
        participation_score=4,
    )


@pytest.fixture
def log_in_bunk_b(db, camper_in_bunk_b, bunk_b, counselor_b):
    assignment = CamperBunkAssignment.objects.get(camper=camper_in_bunk_b, bunk=bunk_b)
    return BunkLog.objects.create(
        bunk_assignment=assignment,
        date=TODAY,
        counselor=counselor_b,
        social_score=3,
        behavior_score=3,
        participation_score=3,
    )


def _url(date_str=DATE_STR):
    return reverse("api:all-bunk-logs-by-date", kwargs={"date": date_str})


# --- Admin ---

@pytest.mark.django_db
def test_admin_sees_all_logs(api_client, admin_user, log_in_bunk_a, log_in_bunk_b):
    api_client.force_authenticate(user=admin_user)
    response = api_client.get(_url())
    assert response.status_code == status.HTTP_200_OK
    ids = {log["id"] for log in response.data["logs"]}
    assert str(log_in_bunk_a.id) in ids
    assert str(log_in_bunk_b.id) in ids


# --- Unit Head ---

@pytest.mark.django_db
def test_unit_head_sees_only_own_unit_logs(
    api_client, unit_head_1, unit_1, unit_2, log_in_bunk_a, log_in_bunk_b,
):
    UnitStaffAssignment.objects.create(
        unit=unit_1,
        staff_member=unit_head_1,
        role="unit_head",
        start_date=TODAY - timedelta(days=10),
    )
    api_client.force_authenticate(user=unit_head_1)
    response = api_client.get(_url())
    assert response.status_code == status.HTTP_200_OK
    ids = {log["id"] for log in response.data["logs"]}
    assert str(log_in_bunk_a.id) in ids
    assert str(log_in_bunk_b.id) not in ids


@pytest.mark.django_db
def test_unit_head_with_no_assignment_sees_nothing(api_client, unit_head_1, log_in_bunk_a):
    api_client.force_authenticate(user=unit_head_1)
    response = api_client.get(_url())
    assert response.status_code == status.HTTP_200_OK
    assert response.data["total_logs"] == 0


# --- Camper Care ---

@pytest.mark.django_db
def test_camper_care_sees_only_own_unit_logs(
    api_client, camper_care_1, unit_1, log_in_bunk_a, log_in_bunk_b,
):
    UnitStaffAssignment.objects.create(
        unit=unit_1,
        staff_member=camper_care_1,
        role="camper_care",
        start_date=TODAY - timedelta(days=10),
    )
    api_client.force_authenticate(user=camper_care_1)
    response = api_client.get(_url())
    assert response.status_code == status.HTTP_200_OK
    ids = {log["id"] for log in response.data["logs"]}
    assert str(log_in_bunk_a.id) in ids
    assert str(log_in_bunk_b.id) not in ids


# --- Counselor ---

@pytest.mark.django_db
def test_counselor_sees_only_own_bunk_logs(
    api_client, counselor_a, bunk_a, log_in_bunk_a, log_in_bunk_b,
):
    CounselorBunkAssignment.objects.create(
        counselor=counselor_a,
        bunk=bunk_a,
        start_date=TODAY - timedelta(days=10),
    )
    api_client.force_authenticate(user=counselor_a)
    response = api_client.get(_url())
    assert response.status_code == status.HTTP_200_OK
    ids = {log["id"] for log in response.data["logs"]}
    assert str(log_in_bunk_a.id) in ids
    assert str(log_in_bunk_b.id) not in ids


@pytest.mark.django_db
def test_counselor_with_no_assignment_sees_nothing(api_client, counselor_a, log_in_bunk_a):
    api_client.force_authenticate(user=counselor_a)
    response = api_client.get(_url())
    assert response.status_code == status.HTTP_200_OK
    assert response.data["total_logs"] == 0


@pytest.mark.django_db
def test_counselor_expired_assignment_sees_nothing(
    api_client, counselor_a, bunk_a, log_in_bunk_a,
):
    CounselorBunkAssignment.objects.create(
        counselor=counselor_a,
        bunk=bunk_a,
        start_date=TODAY - timedelta(days=30),
        end_date=TODAY - timedelta(days=1),
    )
    api_client.force_authenticate(user=counselor_a)
    response = api_client.get(_url())
    assert response.status_code == status.HTTP_200_OK
    assert response.data["total_logs"] == 0


# --- Error cases ---

@pytest.mark.django_db
def test_unauthenticated_request_is_rejected(api_client):
    response = api_client.get(_url())
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
def test_unknown_role_gets_403(api_client):
    user = User.objects.create_user(email="other@test.com", password="pass", role="Kitchen Staff")
    api_client.force_authenticate(user=user)
    response = api_client.get(_url())
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_invalid_date_format_returns_400(api_client, admin_user):
    api_client.force_authenticate(user=admin_user)
    response = api_client.get(_url("not-a-date"))
    assert response.status_code == status.HTTP_400_BAD_REQUEST


# --- Response shape ---

@pytest.mark.django_db
def test_response_includes_bunk_id(api_client, admin_user, log_in_bunk_a):
    api_client.force_authenticate(user=admin_user)
    response = api_client.get(_url())
    assert response.status_code == status.HTTP_200_OK
    log = response.data["logs"][0]
    assert "bunk_id" in log
    assert "bunk_name" in log
    assert "camper_first_name" in log
    assert "camper_last_name" in log
