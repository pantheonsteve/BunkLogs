"""Regression: Membership admin must let a superuser without a Person edit FK fields.

When the logged-in admin user has no Person record, OrganizationMiddleware can't
infer an org, so request.organization is None and OrgScopedManager.objects.none()
returns nothing. Admin form FK validation must bypass that scope (the admin is
privileged staff territory) or saving an existing Membership fails with
"Select a valid choice" on Program/Person.
"""

from datetime import date

import pytest
from django.contrib.auth import get_user_model
from django.test import Client

from bunk_logs.core.models import Membership
from bunk_logs.core.models import Organization
from bunk_logs.core.models import Person
from bunk_logs.core.models import Program

User = get_user_model()


@pytest.fixture
def org(db):
    return Organization.objects.create(name="Admin Form Org", slug="admin-form-org")


@pytest.fixture
def program(org):
    return Program.all_objects.create(
        organization=org,
        name="Admin Form Org Summer",
        slug="admin-form-prog",
        program_type="summer_camp",
        start_date=date(2026, 6, 1),
        end_date=date(2026, 8, 31),
    )


@pytest.fixture
def person(org):
    return Person.all_objects.create(organization=org, first_name="A", last_name="P")


@pytest.fixture
def superuser_without_person(db):
    return User.objects.create_superuser(email="orphan-su@example.test", password="pw")


@pytest.mark.django_db
def test_change_membership_works_for_superuser_without_person(
    superuser_without_person,
    org,
    program,
    person,
):
    membership = Membership.all_objects.create(
        program=program,
        person=person,
        role="counselor",
        is_active=True,
        tags=[],
    )

    client = Client()
    client.force_login(superuser_without_person)
    url = f"/admin/core/membership/{membership.id}/change/"

    get_resp = client.get(url)
    assert get_resp.status_code == 200, get_resp.content

    post_resp = client.post(
        url,
        {
            "program": str(program.id),
            "person": str(person.id),
            "role": "counselor",
            "grade_level": "",
            "tags": "international, waterfront",
            "start_date": "",
            "end_date": "",
            "is_active": "on",
            "metadata": "{}",
            "_save": "Save",
        },
    )
    # Admin redirects to the changelist on success (302); on a validation error it
    # re-renders the change form with status 200 and a "Please correct" banner.
    assert post_resp.status_code == 302, post_resp.content

    membership.refresh_from_db()
    assert membership.tags == ["international", "waterfront"]
