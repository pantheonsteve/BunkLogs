"""Login provisioning for admin People create + invite (identity cleanup Stage 1).

Staff created through the admin flow get a User automatically (linked by
email or created with an unusable password); subject roles (camper, student)
never do. The invite endpoint provisions a login and delivers the email via
the messaging app.
"""

from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from bunk_logs.core.context import organization_context
from bunk_logs.core.models import Membership
from bunk_logs.core.models import Organization
from bunk_logs.core.models import Person
from bunk_logs.core.models import Program

User = get_user_model()
pytestmark = pytest.mark.django_db

URL = "/api/v1/admin/people/"


def _hdr(slug: str) -> dict:
    return {"HTTP_X_ORGANIZATION_SLUG": slug}


@pytest.fixture
def api() -> APIClient:
    return APIClient()


@pytest.fixture
def org():
    return Organization.objects.create(name="Prov Org", slug="prov-org")


@pytest.fixture
def program(org):
    return Program.all_objects.create(
        organization=org, name="Prov Org Fall", slug="prov-org-fall",
        program_type="religious_school",
        start_date=date(2026, 9, 1), end_date=date(2027, 5, 31),
    )


@pytest.fixture
def admin_user(org, program):
    u = User.objects.create_user(email="admin-prov@example.com", password="pw")
    person = Person.all_objects.create(
        organization=org, first_name="Ad", last_name="Min", user=u,
    )
    Membership.all_objects.create(
        program=program, person=person, role="admin", is_active=True,
    )
    return u


class TestCreateProvisionsLogin:
    def test_staff_create_links_new_user(self, api, org, program, admin_user):
        api.force_authenticate(user=admin_user)
        with organization_context(org):
            r = api.post(URL, {
                "first_name": "New",
                "last_name": "Madrich",
                "email": "new-madrich@example.com",
                "membership": {"program_id": program.id, "role": "madrich"},
            }, format="json", **_hdr(org.slug))
        assert r.status_code == 201, r.content
        body = r.json()
        assert body["has_user"] is True
        user = User.objects.get(email="new-madrich@example.com")
        assert body["user_id"] == user.id
        assert not user.has_usable_password()

    def test_camper_create_skips_user(self, api, org, program, admin_user):
        api.force_authenticate(user=admin_user)
        with organization_context(org):
            r = api.post(URL, {
                "first_name": "Young",
                "last_name": "Camper",
                "email": "camper@example.com",
                "membership": {"program_id": program.id, "role": "camper"},
            }, format="json", **_hdr(org.slug))
        assert r.status_code == 201, r.content
        assert r.json()["has_user"] is False
        assert not User.objects.filter(email="camper@example.com").exists()

    def test_student_create_skips_user(self, api, org, program, admin_user):
        api.force_authenticate(user=admin_user)
        with organization_context(org):
            r = api.post(URL, {
                "first_name": "Young",
                "last_name": "Student",
                "email": "student@example.com",
                "membership": {"program_id": program.id, "role": "student"},
            }, format="json", **_hdr(org.slug))
        assert r.status_code == 201, r.content
        assert r.json()["has_user"] is False
        assert not User.objects.filter(email="student@example.com").exists()
        person = Person.all_objects.get(id=r.json()["id"])
        assert person.user_id is None


class TestStudentsAreNotInvitable:
    """Students are subjects, so they never surface as "needs an invitation"."""

    @pytest.fixture
    def student(self, org, program):
        with organization_context(org):
            person = Person.all_objects.create(
                organization=org, first_name="Only", last_name="Student",
                email="only-student@example.com",
            )
            Membership.all_objects.create(
                program=program, person=person, role="student", is_active=True,
            )
        return person

    def test_absent_from_never_invited_filter(
        self, api, org, admin_user, student,
    ):
        api.force_authenticate(user=admin_user)
        with organization_context(org):
            r = api.get(URL, {"invite_status": "never"}, **_hdr(org.slug))
        assert r.status_code == 200, r.content
        ids = [row["id"] for row in r.json()["results"]]
        assert student.id not in ids

    def test_invite_rejected(self, api, org, admin_user, student):
        api.force_authenticate(user=admin_user)
        with organization_context(org):
            r = api.post(
                f"/api/v1/admin/people/{student.id}/invite/", {},
                format="json", **_hdr(org.slug),
            )
        assert r.status_code == 400
        student.refresh_from_db()
        assert student.user_id is None


class TestInvite:
    def test_invite_provisions_user_and_sends_email(
        self, api, org, program, admin_user,
    ):
        with organization_context(org):
            person = Person.all_objects.create(
                organization=org, first_name="In", last_name="Vitee",
                email="invitee@example.com",
            )
            Membership.all_objects.create(
                program=program, person=person, role="faculty", is_active=True,
            )
        api.force_authenticate(user=admin_user)
        service = MagicMock()
        service.send_email.return_value = True
        with patch(
            "bunk_logs.api.admin_flow.people.get_email_service",
            return_value=service,
        ), organization_context(org):
            r = api.post(
                f"/api/v1/admin/people/{person.id}/invite/", {},
                format="json", **_hdr(org.slug),
            )
        assert r.status_code == 200, r.content
        body = r.json()
        assert body["status"] == "sent"
        person.refresh_from_db()
        assert person.user_id is not None
        assert body["user_id"] == person.user_id
        service.send_email.assert_called_once()
        kwargs = service.send_email.call_args.kwargs
        assert kwargs["recipients"] == ["invitee@example.com"]

    def test_invite_without_staff_membership_rejected(
        self, api, org, program, admin_user,
    ):
        with organization_context(org):
            person = Person.all_objects.create(
                organization=org, first_name="Only", last_name="Camper",
                email="only-camper@example.com",
            )
            Membership.all_objects.create(
                program=program, person=person, role="camper", is_active=True,
            )
        api.force_authenticate(user=admin_user)
        with organization_context(org):
            r = api.post(
                f"/api/v1/admin/people/{person.id}/invite/", {},
                format="json", **_hdr(org.slug),
            )
        assert r.status_code == 400
        person.refresh_from_db()
        assert person.user_id is None
