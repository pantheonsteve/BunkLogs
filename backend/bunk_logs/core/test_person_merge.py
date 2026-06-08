"""Tests for duplicate identity audit and Person merge tooling."""

from io import StringIO

import pytest
from django.core.management import call_command

from bunk_logs.core.models import AssignmentGroup
from bunk_logs.core.models import AssignmentGroupMembership
from bunk_logs.core.models import Membership
from bunk_logs.core.models import Organization
from bunk_logs.core.models import Person
from bunk_logs.core.models import Program
from bunk_logs.core.person_merge import merge_persons
from bunk_logs.core.person_merge import plan_person_merge
from bunk_logs.users.models import User


@pytest.fixture
def org(db):
    return Organization.objects.create(name="Crane Lake", slug="clc")


@pytest.fixture
def program(org):
    return Program.all_objects.create(
        organization=org,
        name="Crane Lake Summer 2026",
        slug="summer-2026",
        program_type="summer_camp",
        start_date="2026-06-01",
        end_date="2026-08-15",
    )


@pytest.mark.django_db
class TestAuditDuplicateIdentities:
    def test_finds_duplicate_person_emails(self, org, program):
        user = User.objects.create_user(email="staff@example.com", password="pass")
        Person.all_objects.create(
            organization=org,
            first_name="Legacy",
            last_name="Staff",
            email="staff@example.com",
            user=user,
            external_ids={"legacy_user_id": user.id},
        )
        Person.all_objects.create(
            organization=org,
            first_name="Legacy",
            last_name="Staff",
            email="Staff@example.com",
            external_ids={"campminder_id": "12345"},
        )

        out = StringIO()
        call_command("audit_duplicate_identities", org_slug="clc", stdout=out)
        output = out.getvalue()
        assert "Duplicate Person emails (1 groups)" in output
        assert "staff@example.com" in output


@pytest.mark.django_db
class TestMergePersons:
    def test_merge_repoints_membership_and_deletes_loser(self, org, program):
        user = User.objects.create_user(email="counselor@example.com", password="pass")
        winner = Person.all_objects.create(
            organization=org,
            first_name="Chris",
            last_name="Allen",
            email="drchrisa@gmail.com",
            user=user,
            external_ids={"legacy_user_id": user.id},
        )
        loser = Person.all_objects.create(
            organization=org,
            first_name="Christopher",
            last_name="Allen",
            email="drchrisa@gmail.com",
            external_ids={"campminder_id": "5927217"},
        )
        Membership.all_objects.create(program=program, person=loser, role="counselor")

        plan = plan_person_merge(winner=winner, loser=loser)
        assert plan.ok

        merge_persons(winner=winner, loser=loser)

        winner.refresh_from_db()
        assert not Person.all_objects.filter(pk=loser.pk).exists()
        assert Membership.all_objects.filter(person=winner, role="counselor").exists()
        assert winner.external_ids.get("campminder_id") == "5927217"
        assert winner.user_id == user.id

    def test_merge_keeps_winner_membership_when_roles_conflict(self, org, program):
        winner = Person.all_objects.create(
            organization=org, first_name="A", last_name="B", email="a@example.com",
        )
        loser = Person.all_objects.create(
            organization=org, first_name="A", last_name="B", email="a@example.com",
            external_ids={"campminder_id": "999"},
        )
        Membership.all_objects.create(program=program, person=winner, role="counselor", is_active=True)
        Membership.all_objects.create(
            program=program, person=loser, role="counselor", is_active=True,
        )

        merge_persons(winner=winner, loser=loser)
        loser_id = loser.pk

        assert not Person.all_objects.filter(pk=loser_id).exists()
        assert Membership.all_objects.filter(
            person=winner, role="counselor", is_active=True,
        ).exists()
        assert not Membership.all_objects.filter(person_id=loser_id).exists()

    def test_merge_blocks_different_campminder_ids(self, org):
        winner = Person.all_objects.create(
            organization=org,
            first_name="A",
            last_name="B",
            external_ids={"campminder_id": "111"},
        )
        loser = Person.all_objects.create(
            organization=org,
            first_name="A",
            last_name="B",
            external_ids={"campminder_id": "222"},
        )
        plan = plan_person_merge(winner=winner, loser=loser)
        assert not plan.ok
        assert "campminder_id" in plan.blockers[0]

    def test_merge_force_user_unlinks_loser_and_keeps_winner_user(self, org, program):
        winner_user = User.objects.create_user(email="winner@example.com", password="pass")
        loser_user = User.objects.create_user(email="loser@example.com", password="pass")
        winner = Person.all_objects.create(
            organization=org,
            first_name="Charlie",
            last_name="Capewell",
            email="winner@example.com",
            user=winner_user,
            external_ids={"campminder_id": "18045818"},
        )
        loser = Person.all_objects.create(
            organization=org,
            first_name="Charles",
            last_name="Capewell",
            email="loser@example.com",
            user=loser_user,
        )
        Membership.all_objects.create(program=program, person=loser, role="counselor")

        plan = plan_person_merge(winner=winner, loser=loser, force_user=True)
        assert plan.ok
        assert any(action.model == "Person.user" for action in plan.actions)

        merge_persons(winner=winner, loser=loser, force_user=True)

        winner.refresh_from_db()
        assert winner.user_id == winner_user.id
        assert not Person.all_objects.filter(pk=loser.pk).exists()
        assert Membership.all_objects.filter(person=winner, role="counselor").exists()
        assert Person.all_objects.filter(user=loser_user).count() == 0

    def test_merge_command_force_user_dry_run_succeeds(self, org):
        winner_user = User.objects.create_user(email="winner@example.com", password="pass")
        loser_user = User.objects.create_user(email="loser@example.com", password="pass")
        winner = Person.all_objects.create(
            organization=org,
            first_name="Charlie",
            last_name="Capewell",
            user=winner_user,
        )
        loser = Person.all_objects.create(
            organization=org,
            first_name="Charles",
            last_name="Capewell",
            user=loser_user,
        )

        out = StringIO()
        call_command(
            "merge_persons",
            org_slug="clc",
            winner=winner.pk,
            loser=loser.pk,
            force_user=True,
            stdout=out,
        )
        assert "BLOCKER" not in out.getvalue()
        assert "Dry-run only" in out.getvalue()

    def test_merge_repoints_group_membership(self, org, program):
        winner = Person.all_objects.create(
            organization=org, first_name="Sam", last_name="Lee",
        )
        loser = Person.all_objects.create(
            organization=org,
            first_name="Sam",
            last_name="Lee",
            external_ids={"campminder_id": "555"},
        )
        group = AssignmentGroup.all_objects.create(
            organization=org,
            program=program,
            name="Bunk 1",
            slug="bunk-1",
            group_type="bunk",
        )
        agm = AssignmentGroupMembership.all_objects.create(
            group=group, person=loser, role_in_group="author",
        )

        merge_persons(winner=winner, loser=loser)

        agm.refresh_from_db()
        assert agm.person_id == winner.id
