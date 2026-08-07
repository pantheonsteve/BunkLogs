"""Multi-org identity: Person.user as FK (identity cleanup Stage 2).

One human (User) may hold a Person record in several organizations, but at
most one per org. Tenant resolution must never guess for multi-org users.
"""

from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError

from bunk_logs.core.campminder_user_link import UserLinkAction
from bunk_logs.core.campminder_user_link import ensure_user_for_imported_person
from bunk_logs.core.context import organization_context
from bunk_logs.core.identity import person_for_user
from bunk_logs.core.middleware import _org_from_linked_person
from bunk_logs.core.models import Organization
from bunk_logs.core.models import Person

User = get_user_model()
pytestmark = pytest.mark.django_db


@pytest.fixture
def orgs():
    return (
        Organization.objects.create(name="Org A", slug="multi-a"),
        Organization.objects.create(name="Org B", slug="multi-b"),
    )


@pytest.fixture
def user():
    return User.objects.create_user(email="multi-org@example.com", password="pw")


def test_user_can_hold_person_in_two_orgs(orgs, user):
    org_a, org_b = orgs
    pa = Person.all_objects.create(
        organization=org_a, first_name="Multi", last_name="Org", user=user,
    )
    pb = Person.all_objects.create(
        organization=org_b, first_name="Multi", last_name="Org", user=user,
    )
    assert person_for_user(user, organization=org_a) == pa
    assert person_for_user(user, organization=org_b) == pb
    with organization_context(org_b):
        assert person_for_user(user) == pb


def test_duplicate_org_user_rejected(orgs, user):
    org_a, _ = orgs
    Person.all_objects.create(
        organization=org_a, first_name="First", last_name="Copy", user=user,
    )
    with pytest.raises(IntegrityError):
        Person.all_objects.create(
            organization=org_a, first_name="Second", last_name="Copy", user=user,
        )


def test_middleware_declines_to_guess_for_multi_org_user(orgs, user):
    org_a, org_b = orgs
    Person.all_objects.create(
        organization=org_a, first_name="Multi", last_name="Org", user=user,
    )
    assert _org_from_linked_person(user) == org_a
    Person.all_objects.create(
        organization=org_b, first_name="Multi", last_name="Org", user=user,
    )
    assert _org_from_linked_person(user) is None


def test_campminder_link_second_org_is_linked_not_conflict(orgs, user):
    org_a, org_b = orgs
    Person.all_objects.create(
        organization=org_a, first_name="Multi", last_name="Org",
        email=user.email, user=user,
    )
    person_b = Person.all_objects.create(
        organization=org_b, first_name="Multi", last_name="Org",
        email=user.email,
    )
    result = ensure_user_for_imported_person(person_b, membership_role="madrich")
    assert result.action == UserLinkAction.LINKED
    person_b.refresh_from_db()
    assert person_b.user_id == user.id


def test_campminder_same_org_still_conflicts(orgs, user):
    org_a, _ = orgs
    Person.all_objects.create(
        organization=org_a, first_name="Already", last_name="Linked",
        email=user.email, user=user,
    )
    other = Person.all_objects.create(
        organization=org_a, first_name="Other", last_name="Person",
        email=user.email,
    )
    result = ensure_user_for_imported_person(other, membership_role="counselor")
    assert result.action == UserLinkAction.CONFLICT
