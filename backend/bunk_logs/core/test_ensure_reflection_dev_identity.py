from io import StringIO

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test.utils import override_settings

from bunk_logs.core.models import Membership
from bunk_logs.core.models import Person

User = get_user_model()


@pytest.mark.django_db
@override_settings(DEBUG=True)
def test_ensure_reflection_dev_identity_creates_person_and_membership():
    call_command("setup_crane_lake", stdout=StringIO())
    user = User.objects.create_user(email="reflect-tester@example.test", password="x")

    call_command(
        "ensure_reflection_dev_identity",
        email="reflect-tester@example.test",
        org_slug="clc",
        program_slug="summer-2026",
        role="counselor",
        stdout=StringIO(),
    )

    person = Person.all_objects.get(user=user)
    assert person.organization.slug == "clc"
    assert Membership.all_objects.filter(person=person, role="counselor", is_active=True).exists()


@pytest.mark.django_db
@override_settings(DEBUG=False)
def test_ensure_reflection_dev_identity_blocked_without_debug():
    with pytest.raises(CommandError, match="DEBUG=True"):
        call_command(
            "ensure_reflection_dev_identity",
            email="any@example.test",
            stdout=StringIO(),
        )
