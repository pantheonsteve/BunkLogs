"""Tests for Organization subject-note authoring admin UI."""

from __future__ import annotations

import json

import pytest
from django.contrib.auth import get_user_model
from django.test import Client

from bunk_logs.core.admin_organization import AUTHOR_SCOPE_FIELD_PREFIX
from bunk_logs.core.admin_organization import OrganizationAdminForm
from bunk_logs.core.models import Membership
from bunk_logs.core.models import Organization
from bunk_logs.core.permissions.subject_note_authoring import author_by_role_for_org

User = get_user_model()


@pytest.fixture
def org(db):
    return Organization.objects.create(
        name="Admin Org",
        slug="admin-org",
        settings={
            "timezone": "America/New_York",
            "subject_notes": {"author_by_role": {"specialist": "none"}},
        },
    )


@pytest.fixture
def superuser(db):
    return User.objects.create_superuser(email="org-admin@test.com", password="pw")


def _role_field_data(overrides: dict[str, str]) -> dict[str, str]:
    """Build POST data for all role scope fields."""
    from bunk_logs.core.permissions.subject_note_authoring import DEFAULT_AUTHOR_BY_ROLE

    data = {}
    for role_value, _ in Membership.ROLES:
        field = f"{AUTHOR_SCOPE_FIELD_PREFIX}{role_value}"
        data[field] = overrides.get(role_value, DEFAULT_AUTHOR_BY_ROLE.get(role_value, "none"))
    return data


@pytest.mark.django_db
def test_organization_admin_form_loads_effective_scopes(org):
    form = OrganizationAdminForm(instance=org)
    assert form.fields[f"{AUTHOR_SCOPE_FIELD_PREFIX}specialist"].initial == "none"
    assert "timezone" in form.fields["settings_json"].initial


@pytest.mark.django_db
def test_organization_admin_form_saves_override_and_preserves_other_settings(org):
    data = {
        "name": org.name,
        "slug": org.slug,
        "is_active": True,
        "settings_json": json.dumps({"timezone": "America/New_York", "locale_default": "en"}),
        **_role_field_data({"specialist": "program", "kitchen_staff": "program"}),
    }
    form = OrganizationAdminForm(data=data, instance=org)
    assert form.is_valid(), form.errors
    saved = form.save()
    assert saved.settings["timezone"] == "America/New_York"
    assert saved.settings["subject_notes"]["author_by_role"] == {
        "kitchen_staff": "program",
    }
    assert author_by_role_for_org(saved)["specialist"] == "program"


@pytest.mark.django_db
def test_organization_admin_change_page_renders(superuser, org):
    client = Client()
    client.force_login(superuser)
    url = f"/admin/core/organization/{org.id}/change/"
    response = client.get(url)
    assert response.status_code == 200
    content = response.content.decode()
    assert "Subject note authoring by role" in content
    assert "Specialist" in content
    assert f'name="{AUTHOR_SCOPE_FIELD_PREFIX}specialist"' in content


@pytest.mark.django_db
def test_organization_admin_post_updates_author_by_role(superuser, org):
    client = Client()
    client.force_login(superuser)
    url = f"/admin/core/organization/{org.id}/change/"
    post_data = {
        "name": org.name,
        "slug": org.slug,
        "is_active": "on",
        "settings_json": json.dumps({"timezone": "America/New_York"}),
        **_role_field_data({"specialist": "program"}),
        "programs-TOTAL_FORMS": "0",
        "programs-INITIAL_FORMS": "0",
        "programs-MIN_NUM_FORMS": "0",
        "programs-MAX_NUM_FORMS": "1000",
        "_save": "Save",
    }
    response = client.post(url, post_data)
    assert response.status_code == 302, response.content
    org.refresh_from_db()
    # specialist=program matches the product default, so the old override is cleared
    assert org.settings.get("subject_notes", {}).get("author_by_role") in (None, {})
    assert author_by_role_for_org(org)["specialist"] == "program"


@pytest.mark.django_db
def test_organization_admin_post_with_program_inlines(superuser, org, program):
    """Regression: Program inline must not require organization field on POST."""
    client = Client()
    client.force_login(superuser)
    url = f"/admin/core/organization/{org.id}/change/"
    response = client.post(
        url,
        {
            "name": org.name,
            "slug": org.slug,
            "is_active": "on",
            "settings_json": json.dumps({"timezone": "America/New_York"}),
            **_role_field_data({"kitchen_staff": "program"}),
            "programs-TOTAL_FORMS": "1",
            "programs-INITIAL_FORMS": "1",
            "programs-MIN_NUM_FORMS": "0",
            "programs-MAX_NUM_FORMS": "1000",
            "programs-0-id": str(program.id),
            "programs-0-name": program.name,
            "programs-0-slug": program.slug,
            "programs-0-program_type": program.program_type,
            "programs-0-start_date": program.start_date.isoformat(),
            "programs-0-end_date": program.end_date.isoformat(),
            "programs-0-is_active": "on",
            "_save": "Save",
        },
    )
    assert response.status_code == 302, response.content[:500]
    org.refresh_from_db()
    assert org.settings["subject_notes"]["author_by_role"] == {"kitchen_staff": "program"}
    assert org.settings["timezone"] == "America/New_York"


@pytest.fixture
def program(org):
    from datetime import date

    from bunk_logs.core.models import Program

    return Program.all_objects.create(
        organization=org,
        name="Admin Org Summer",
        slug="admin-org-summer",
        program_type="summer_camp",
        start_date=date(2026, 6, 1),
        end_date=date(2026, 8, 31),
    )


@pytest.mark.django_db
def test_membership_admin_subject_note_override_field(superuser, org, program):
    from bunk_logs.core.models import Person as PersonModel

    person = PersonModel.all_objects.create(organization=org, first_name="Kit", last_name="Chen")
    membership = Membership.all_objects.create(
        program=program,
        person=person,
        role="kitchen_staff",
        is_active=True,
    )
    client = Client()
    client.force_login(superuser)
    url = f"/admin/core/membership/{membership.id}/change/"
    response = client.post(
        url,
        {
            "program": str(program.id),
            "person": str(person.id),
            "role": "kitchen_staff",
            "grade_level": "",
            "tags": "",
            "start_date": "",
            "end_date": "",
            "is_active": "on",
            "subject_note_author_override": "true",
            "metadata": "{}",
            "_save": "Save",
        },
    )
    assert response.status_code == 302, response.content
    membership.refresh_from_db()
    assert membership.metadata["can_author_subject_notes"] is True
