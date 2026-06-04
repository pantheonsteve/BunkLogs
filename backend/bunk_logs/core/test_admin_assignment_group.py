"""Regression: AssignmentGroup admin must save for staff without a Person and with membership inlines."""

from datetime import date

import pytest
from django.contrib.auth import get_user_model
from django.test import Client

from bunk_logs.core.models import AssignmentGroup
from bunk_logs.core.models import AssignmentGroupMembership
from bunk_logs.core.models import Organization
from bunk_logs.core.models import Person
from bunk_logs.core.models import Program

User = get_user_model()


@pytest.fixture
def org(db):
    return Organization.objects.create(name="AG Admin Org", slug="ag-admin-org")


@pytest.fixture
def program(org):
    return Program.all_objects.create(
        organization=org,
        name="AG Admin Org Summer",
        slug="ag-admin-prog",
        program_type="summer_camp",
        start_date=date(2026, 6, 1),
        end_date=date(2026, 8, 31),
    )


@pytest.fixture
def person(org):
    return Person.all_objects.create(organization=org, first_name="Sam", last_name="Staff")


@pytest.fixture
def group(org, program):
    return AssignmentGroup.all_objects.create(
        organization=org,
        program=program,
        name="Bunk Test",
        slug="bunk-test",
        group_type="bunk",
    )


@pytest.fixture
def membership(group, person):
    return AssignmentGroupMembership.all_objects.create(
        group=group,
        person=person,
        role_in_group="author",
        is_active=True,
    )


@pytest.fixture
def superuser_without_person(db):
    return User.objects.create_superuser(email="ag-admin-su@example.test", password="pw")


def _assignment_group_post(group, memberships):
    post = {
        "organization": str(group.organization_id),
        "program": str(group.program_id),
        "name": group.name,
        "slug": group.slug,
        "group_type": group.group_type,
        "parent": str(group.parent_id) if group.parent_id else "",
        "metadata": "{}",
        "is_active": "on",
        "_save": "Save",
        "memberships-TOTAL_FORMS": str(len(memberships)),
        "memberships-INITIAL_FORMS": str(len(memberships)),
        "memberships-MIN_NUM_FORMS": "0",
        "memberships-MAX_NUM_FORMS": "1000",
    }
    for i, m in enumerate(memberships):
        post[f"memberships-{i}-id"] = str(m.id)
        post[f"memberships-{i}-person"] = str(m.person_id)
        post[f"memberships-{i}-role_in_group"] = m.role_in_group
        post[f"memberships-{i}-is_active"] = "on" if m.is_active else ""
        post[f"memberships-{i}-start_date"] = ""
        post[f"memberships-{i}-end_date"] = ""
    return post


@pytest.mark.django_db
def test_change_assignment_group_with_memberships_for_superuser_without_person(
    superuser_without_person,
    group,
    membership,
):
    memberships = list(AssignmentGroupMembership.all_objects.filter(group=group))
    client = Client()
    client.force_login(superuser_without_person)
    url = f"/admin/core/assignmentgroup/{group.id}/change/"

    get_resp = client.get(url)
    assert get_resp.status_code == 200, get_resp.content

    post = _assignment_group_post(group, memberships)
    post["name"] = "Bunk Test Updated"
    post_resp = client.post(url, post)
    assert post_resp.status_code == 302, post_resp.content

    group.refresh_from_db()
    assert group.name == "Bunk Test Updated"


@pytest.mark.django_db
def test_assignment_group_admin_rejects_program_from_other_org(
    superuser_without_person,
    org,
    program,
    group,
    membership,
):
    other = Organization.objects.create(name="Other AG Org", slug="other-ag-org")
    other_program = Program.all_objects.create(
        organization=other,
        name="Other AG Org Summer",
        slug="other-ag-prog",
        program_type="summer_camp",
        start_date=date(2026, 6, 1),
        end_date=date(2026, 8, 31),
    )
    memberships = list(AssignmentGroupMembership.all_objects.filter(group=group))
    client = Client()
    client.force_login(superuser_without_person)
    url = f"/admin/core/assignmentgroup/{group.id}/change/"
    post = _assignment_group_post(group, memberships)
    post["program"] = str(other_program.id)

    post_resp = client.post(url, post)
    assert post_resp.status_code == 200, post_resp.content
    assert b"Program must belong to the selected organization" in post_resp.content
