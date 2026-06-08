"""Tests for scrub_pii multi-tenant model coverage."""

import pytest
from django.core.management import call_command
from django.test import override_settings

from bunk_logs.core.models import Organization
from bunk_logs.core.models import Person
from bunk_logs.core.models import Program
from bunk_logs.core.models import Reflection
from bunk_logs.core.models import ReflectionTemplate
from bunk_logs.notes.models import Observation
from bunk_logs.users.models import User
from bunk_logs.utils.management.commands.scrub_pii import SCRUB_PLACEHOLDER
from bunk_logs.utils.management.commands.scrub_pii import scrub_json_strings


@pytest.mark.django_db
class TestScrubJsonStrings:
    def test_scrubs_nested_strings(self):
        payload = {
            "notes": "real camper name here",
            "scores": [1, 2],
            "nested": {"comment": "private"},
        }
        scrubbed = scrub_json_strings(payload)
        assert scrubbed["notes"] == SCRUB_PLACEHOLDER
        assert scrubbed["scores"] == [1, 2]
        assert scrubbed["nested"]["comment"] == SCRUB_PLACEHOLDER


@pytest.mark.django_db
class TestScrubPiiCommand:
    @pytest.fixture
    def org(self):
        return Organization.objects.create(name="Crane Lake", slug="clc")

    @pytest.fixture
    def program(self, org):
        return Program.all_objects.create(
            organization=org,
            name="Crane Lake Summer 2026",
            slug="summer-2026",
            program_type="summer_camp",
            start_date="2026-06-01",
            end_date="2026-08-15",
        )

    @override_settings(DEBUG=True)
    def test_scrubs_person_observation_and_reflection(self, org, program):
        user = User.objects.create_user(email="staff@example.com", password="pass")
        person = Person.all_objects.create(
            organization=org,
            first_name="Real",
            last_name="Name",
            email="real.name@camp.example",
            notes="private staff note",
            user=user,
        )
        Observation.all_objects.create(
            organization=org,
            program=program,
            author=person,
            body="sensitive observation about camper",
        )
        template = ReflectionTemplate.all_objects.create(
            organization=org,
            name="Daily",
            slug="daily",
            cadence="daily",
            schema={"fields": []},
        )
        Reflection.all_objects.create(
            organization=org,
            program=program,
            author=person,
            subject=person,
            template=template,
            period_start="2026-06-01",
            period_end="2026-06-01",
            answers={"comment": "private reflection text"},
        )

        call_command("scrub_pii", "--confirm")

        person.refresh_from_db()
        obs = Observation.all_objects.get()
        reflection = Reflection.all_objects.get()

        assert person.email == f"user{user.id}@example.test"
        assert person.first_name != "Real"
        assert person.notes == SCRUB_PLACEHOLDER
        assert obs.body == SCRUB_PLACEHOLDER
        assert reflection.answers["comment"] == SCRUB_PLACEHOLDER
