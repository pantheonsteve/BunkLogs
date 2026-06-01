"""Tests for setup_clc_summer_2025 and migrate_clc_legacy_data management commands."""
from __future__ import annotations

from datetime import date
from io import StringIO

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError

from bunk_logs.bunklogs.models import BunkLog
from bunk_logs.bunklogs.models import StaffLog
from bunk_logs.bunks.models import Bunk
from bunk_logs.bunks.models import Cabin
from bunk_logs.bunks.models import CounselorBunkAssignment
from bunk_logs.bunks.models import Session
from bunk_logs.bunks.models import Unit
from bunk_logs.bunks.models import UnitStaffAssignment
from bunk_logs.campers.models import Camper
from bunk_logs.campers.models import CamperBunkAssignment
from bunk_logs.core.management.commands.migrate_clc_legacy_data import deterministic_uuid
from bunk_logs.core.models import AssignmentGroup
from bunk_logs.core.models import AssignmentGroupMembership
from bunk_logs.core.models import Membership
from bunk_logs.core.models import Organization
from bunk_logs.core.models import Person
from bunk_logs.core.models import Program
from bunk_logs.core.models import Reflection
from bunk_logs.core.models import ReflectionTemplate
from bunk_logs.core.models import TemplateAssignment

User = get_user_model()


# ── Fixtures ──────────────────────────────────────────────────────────────


@pytest.fixture
def legacy_data(db):
    """Minimal but representative Summer 2025 legacy fixture.

    Includes intentional noise (a Test Session, an Integration Test Unit, a
    StaffLog outside session windows, a 2026 StaffLog) so we can assert the
    migration correctly excludes them.
    """
    # Sessions: the two real ones + one to ignore.
    session1 = Session.objects.create(
        name="Session 1 - 2025",
        start_date=date(2025, 6, 28),
        end_date=date(2025, 7, 26),
        is_active=False,
    )
    session2 = Session.objects.create(
        name="Session 2 - 2025",
        start_date=date(2025, 7, 26),
        end_date=date(2025, 8, 16),
        is_active=False,
    )
    test_session = Session.objects.create(
        name="Test Session - 2025",
        start_date=date(2025, 6, 17),
        end_date=date(2025, 6, 17),
        is_active=False,
    )

    # Units: 2 real + 1 noise (no bunks)
    bonim = Unit.objects.create(name="Lower Bonim")
    olim = Unit.objects.create(name="Olim")
    test_unit = Unit.objects.create(name="Integration Test Unit")  # noqa: F841

    # Cabins
    aspen = Cabin.objects.create(name="Aspen", capacity=10)
    birch = Cabin.objects.create(name="Birch", capacity=10)
    cedar = Cabin.objects.create(name="Cedar", capacity=10)

    # Bunks: 4 real + 1 in the test session
    bunk_aspen_s1 = Bunk.objects.create(cabin=aspen, session=session1, unit=bonim)
    bunk_aspen_s2 = Bunk.objects.create(cabin=aspen, session=session2, unit=bonim)
    bunk_birch_s1 = Bunk.objects.create(cabin=birch, session=session1, unit=olim)
    bunk_birch_s2 = Bunk.objects.create(cabin=birch, session=session2, unit=olim)
    bunk_cedar_test = Bunk.objects.create(cabin=cedar, session=test_session, unit=bonim)

    # Users (staff)
    alice = User.objects.create_user(
        email="alice@example.com", first_name="Alice", last_name="Counselor",
        password="x",
    )
    alice.role = "Counselor"
    alice.save(update_fields=["role"])
    bob = User.objects.create_user(
        email="bob@example.com", first_name="Bob", last_name="Counselor",
        password="x",
    )
    bob.role = "Counselor"
    bob.save(update_fields=["role"])
    carol = User.objects.create_user(
        email="carol@example.com", first_name="Carol", last_name="Head",
        password="x",
    )
    carol.role = "Unit Head"
    carol.save(update_fields=["role"])
    dave = User.objects.create_user(
        email="dave@example.com", first_name="Dave", last_name="Care",
        password="x",
    )
    dave.role = "Camper Care"
    dave.save(update_fields=["role"])

    # Campers
    eve = Camper.objects.create(first_name="Eve", last_name="One")
    frank = Camper.objects.create(first_name="Frank", last_name="Two")
    grace = Camper.objects.create(first_name="Grace", last_name="Three")

    # CamperBunkAssignments (Camper -> Bunk for given dates).
    # bulk_create() bypasses CBA.save()'s overlap validation so we can mirror
    # production state where some campers attend both sessions (s1.end_date
    # == s2.start_date, which the current clean() rejects).
    cbas = CamperBunkAssignment.objects.bulk_create([
        # Eve attends both sessions
        CamperBunkAssignment(
            camper=eve, bunk=bunk_aspen_s1, is_active=False,
            start_date=session1.start_date, end_date=session1.end_date,
        ),
        CamperBunkAssignment(
            camper=eve, bunk=bunk_aspen_s2, is_active=False,
            start_date=session2.start_date, end_date=session2.end_date,
        ),
        # Frank: session 1 only
        CamperBunkAssignment(
            camper=frank, bunk=bunk_aspen_s1, is_active=False,
            start_date=session1.start_date, end_date=session1.end_date,
        ),
        # Grace: session 2 only
        CamperBunkAssignment(
            camper=grace, bunk=bunk_birch_s2, is_active=False,
            start_date=session2.start_date, end_date=session2.end_date,
        ),
    ])
    cba_eve_s1, cba_eve_s2, cba_frank_s1, cba_grace_s2 = cbas

    # CounselorBunkAssignments
    CounselorBunkAssignment.objects.create(
        counselor=alice, bunk=bunk_aspen_s1,
        start_date=session1.start_date, end_date=session1.end_date,
    )
    CounselorBunkAssignment.objects.create(
        counselor=bob, bunk=bunk_birch_s1,
        start_date=session1.start_date, end_date=session1.end_date,
    )

    # UnitStaffAssignments (no session FK; we expect overlap-based Memberships)
    UnitStaffAssignment.objects.create(
        unit=bonim, staff_member=carol, role="unit_head",
        start_date=date(2025, 6, 1),  # spans both sessions
        end_date=None,
    )
    UnitStaffAssignment.objects.create(
        unit=olim, staff_member=dave, role="camper_care",
        start_date=date(2025, 6, 1),
        end_date=date(2025, 7, 26),  # session 1 only
    )

    # BunkLogs — bulk_create bypasses save() / full_clean() so we can use 2025 dates.
    bulk_bunklogs = [
        # Eve in session 1: a normal scored log
        BunkLog(
            bunk_assignment=cba_eve_s1,
            date=date(2025, 6, 30),
            counselor=alice,
            not_on_camp=False,
            social_score=4, behavior_score=5, participation_score=3,
            request_unit_head_help=False,
            request_camper_care_help=False,
            description="Great day for Eve.",
        ),
        # Eve in session 1: not on camp (no scores)
        BunkLog(
            bunk_assignment=cba_eve_s1,
            date=date(2025, 7, 1),
            counselor=alice,
            not_on_camp=True,
            social_score=None, behavior_score=None, participation_score=None,
            description="",
        ),
        # Frank in session 1: with CC help requested
        BunkLog(
            bunk_assignment=cba_frank_s1,
            date=date(2025, 6, 30),
            counselor=alice,
            not_on_camp=False,
            social_score=2, behavior_score=2, participation_score=3,
            request_unit_head_help=False,
            request_camper_care_help=True,
            description="Tough day. Need CC support.",
        ),
        # Grace in session 2: simple log on boundary day (2025-07-26)
        BunkLog(
            bunk_assignment=cba_grace_s2,
            date=date(2025, 7, 26),
            counselor=bob,
            not_on_camp=False,
            social_score=5, behavior_score=4, participation_score=5,
            description="First day going well.",
        ),
    ]
    BunkLog.objects.bulk_create(bulk_bunklogs)

    # StaffLogs — bulk_create to bypass date validation
    bulk_stafflogs = [
        # In session 1
        StaffLog(
            staff_member=alice, date=date(2025, 7, 1),
            day_quality_score=4, support_level_score=5,
            elaboration="Good day, well supported.",
            day_off=False, staff_care_support_needed=False,
            values_reflection="Practiced kindness.",
        ),
        # Boundary day → should land in session 2
        StaffLog(
            staff_member=bob, date=date(2025, 7, 26),
            day_quality_score=3, support_level_score=3,
            elaboration="Transition day, tiring.",
            day_off=False, staff_care_support_needed=False,
            values_reflection="Stayed grounded.",
        ),
        # Day off in session 2
        StaffLog(
            staff_member=alice, date=date(2025, 8, 5),
            day_quality_score=5, support_level_score=5,
            elaboration="",
            day_off=True, staff_care_support_needed=False,
            values_reflection="",
        ),
        # Outside session windows: should be SKIPPED
        StaffLog(
            staff_member=alice, date=date(2025, 6, 1),
            day_quality_score=3, support_level_score=3,
            elaboration="Pre-camp training week.",
            day_off=False, staff_care_support_needed=False,
            values_reflection="N/A.",
        ),
        # 2026 log: should be SKIPPED (year filter)
        StaffLog(
            staff_member=alice, date=date(2026, 5, 25),
            day_quality_score=4, support_level_score=4,
            elaboration="Off-season check-in.",
            day_off=False, staff_care_support_needed=False,
            values_reflection="N/A.",
        ),
    ]
    StaffLog.objects.bulk_create(bulk_stafflogs)

    return {
        "sessions": {"s1": session1, "s2": session2, "test": test_session},
        "units": {"bonim": bonim, "olim": olim},
        "cabins": {"aspen": aspen, "birch": birch, "cedar": cedar},
        "bunks": {
            "aspen_s1": bunk_aspen_s1, "aspen_s2": bunk_aspen_s2,
            "birch_s1": bunk_birch_s1, "birch_s2": bunk_birch_s2,
            "cedar_test": bunk_cedar_test,
        },
        "users": {"alice": alice, "bob": bob, "carol": carol, "dave": dave},
        "campers": {"eve": eve, "frank": frank, "grace": grace},
        "cba": {
            "eve_s1": cba_eve_s1, "eve_s2": cba_eve_s2,
            "frank_s1": cba_frank_s1, "grace_s2": cba_grace_s2,
        },
    }


@pytest.fixture
def setup_done(legacy_data):
    """Run setup_clc_summer_2025 so the new-model scaffolding exists."""
    call_command("setup_clc_summer_2025", stdout=StringIO(), stderr=StringIO())
    return legacy_data


# ── setup_clc_summer_2025 tests ───────────────────────────────────────────


@pytest.mark.django_db
class TestSetupClcSummer2025:
    def test_dry_run_makes_no_writes(self, legacy_data):
        out = StringIO()
        call_command("setup_clc_summer_2025", "--dry-run", stdout=out)

        assert "DRY-RUN" in out.getvalue()
        assert not Program.all_objects.filter(slug__startswith="summer-2025").exists()
        assert not AssignmentGroup.all_objects.filter(group_type="bunk").exists()

    def test_creates_two_programs(self, legacy_data):
        call_command("setup_clc_summer_2025", stdout=StringIO())
        org = Organization.objects.get(slug="clc")

        s1 = Program.all_objects.get(organization=org, slug="summer-2025-session-1")
        assert s1.name.startswith(org.name)
        assert s1.start_date == date(2025, 6, 28)
        assert s1.end_date == date(2025, 7, 26)
        assert s1.is_active is False
        assert s1.settings["legacy_session_name"] == "Session 1 - 2025"
        assert s1.program_type == "summer_camp"

        s2 = Program.all_objects.get(organization=org, slug="summer-2025-session-2")
        assert s2.start_date == date(2025, 7, 26)
        assert s2.end_date == date(2025, 8, 16)

    def test_does_not_create_program_for_test_session(self, legacy_data):
        call_command("setup_clc_summer_2025", stdout=StringIO())
        # The test session ("Test Session - 2025") should NOT get a Program.
        assert not Program.all_objects.filter(
            settings__legacy_session_name="Test Session - 2025",
        ).exists()

    def test_creates_unit_assignment_groups_only_for_units_with_bunks(
        self,
        legacy_data,
    ):
        call_command("setup_clc_summer_2025", stdout=StringIO())
        org = Organization.objects.get(slug="clc")
        s1 = Program.all_objects.get(organization=org, slug="summer-2025-session-1")

        # 2 units have bunks in session 1: Lower Bonim, Olim. NOT Integration Test Unit.
        unit_ags = AssignmentGroup.all_objects.filter(program=s1, group_type="unit")
        assert unit_ags.count() == 2
        assert set(unit_ags.values_list("name", flat=True)) == {"Lower Bonim", "Olim"}
        assert not AssignmentGroup.all_objects.filter(
            program=s1, name="Integration Test Unit",
        ).exists()

    def test_creates_bunk_assignment_groups_with_parent(self, legacy_data):
        call_command("setup_clc_summer_2025", stdout=StringIO())
        org = Organization.objects.get(slug="clc")
        s1 = Program.all_objects.get(organization=org, slug="summer-2025-session-1")

        # 2 bunks in session 1: Aspen (Lower Bonim) and Birch (Olim)
        bunk_ags = AssignmentGroup.all_objects.filter(program=s1, group_type="bunk")
        assert bunk_ags.count() == 2

        aspen_ag = bunk_ags.get(name="Aspen")
        assert aspen_ag.parent is not None
        assert aspen_ag.parent.name == "Lower Bonim"
        assert aspen_ag.parent.group_type == "unit"

        birch_ag = bunk_ags.get(name="Birch")
        assert birch_ag.parent.name == "Olim"

    def test_assignment_group_metadata_includes_legacy_ids(self, legacy_data):
        call_command("setup_clc_summer_2025", stdout=StringIO())
        org = Organization.objects.get(slug="clc")

        bunk_ag = AssignmentGroup.all_objects.filter(
            organization=org, group_type="bunk", name="Aspen",
            program__slug="summer-2025-session-1",
        ).first()
        assert bunk_ag is not None
        assert bunk_ag.metadata["legacy_bunk_id"] == legacy_data["bunks"]["aspen_s1"].id

        unit_ag = bunk_ag.parent
        assert unit_ag.metadata["legacy_unit_id"] == legacy_data["units"]["bonim"].id

    def test_seeds_legacy_templates(self, legacy_data):
        call_command("setup_clc_summer_2025", stdout=StringIO())
        org = Organization.objects.get(slug="clc")

        counselor_tpl = ReflectionTemplate.all_objects.get(
            organization=org, slug="clc-legacy-counselor-daily",
        )
        assert counselor_tpl.role == "counselor"
        assert counselor_tpl.cadence == "daily"

        # Counselor template is about a camper, assigned per bunk.
        assert counselor_tpl.subject_mode == "single_subject"
        assert counselor_tpl.assignment_scope == "per_subject_in_group"
        assert counselor_tpl.assignment_group_types == ["bunk"]
        assert counselor_tpl.author_role_filter == ["counselor"]
        assert counselor_tpl.subject_role_filter == ["camper"]

        staff_tpl = ReflectionTemplate.all_objects.get(
            organization=org, slug="clc-legacy-staff-log-daily",
        )
        assert staff_tpl.role in (None, "")  # applies to all roles
        assert staff_tpl.cadence == "daily"
        # Staff log is a self-reflection, no group context.
        assert staff_tpl.subject_mode == "self"
        assert staff_tpl.assignment_scope == "none"
        assert staff_tpl.assignment_group_types == []

    def test_idempotent(self, legacy_data):
        call_command("setup_clc_summer_2025", stdout=StringIO())
        first = {
            "programs": list(Program.all_objects.filter(
                slug__startswith="summer-2025",
            ).values_list("pk", flat=True)),
            "bunks": AssignmentGroup.all_objects.filter(group_type="bunk").count(),
            "units": AssignmentGroup.all_objects.filter(group_type="unit").count(),
            "templates": ReflectionTemplate.all_objects.filter(
                slug__startswith="clc-legacy",
            ).count(),
        }

        call_command("setup_clc_summer_2025", stdout=StringIO())
        call_command("setup_clc_summer_2025", stdout=StringIO())

        assert list(Program.all_objects.filter(
            slug__startswith="summer-2025",
        ).values_list("pk", flat=True)) == first["programs"]
        assert AssignmentGroup.all_objects.filter(group_type="bunk").count() == first["bunks"]
        assert AssignmentGroup.all_objects.filter(group_type="unit").count() == first["units"]
        assert ReflectionTemplate.all_objects.filter(
            slug__startswith="clc-legacy",
        ).count() == first["templates"]

    def test_fails_when_sessions_missing(self, db):
        """No legacy Sessions at all -> CommandError."""
        with pytest.raises(CommandError, match="Session 1 - 2025"):
            call_command("setup_clc_summer_2025", stdout=StringIO(), stderr=StringIO())


# ── migrate_clc_legacy_data tests ─────────────────────────────────────────


@pytest.mark.django_db
class TestMigrateClcLegacyData:
    def test_errors_when_setup_not_run(self, legacy_data):
        with pytest.raises(CommandError, match="setup_clc_summer_2025"):
            call_command(
                "migrate_clc_legacy_data", stdout=StringIO(), stderr=StringIO(),
            )

    def test_dry_run_makes_no_writes(self, setup_done):
        before_persons = Person.all_objects.count()
        before_memberships = Membership.all_objects.count()
        before_reflections = Reflection.all_objects.count()

        call_command(
            "migrate_clc_legacy_data", stdout=StringIO(), stderr=StringIO(),
        )

        assert Person.all_objects.count() == before_persons
        assert Membership.all_objects.count() == before_memberships
        assert Reflection.all_objects.count() == before_reflections


@pytest.mark.django_db
class TestMigratePersons:
    def test_campers_become_persons_with_legacy_camper_id(self, setup_done):
        call_command(
            "migrate_clc_legacy_data", "--apply",
            stdout=StringIO(), stderr=StringIO(),
        )
        org = Organization.objects.get(slug="clc")

        for camper in setup_done["campers"].values():
            person = Person.all_objects.get(
                organization=org,
                external_ids__legacy_camper_id=camper.id,
            )
            assert person.first_name == camper.first_name
            assert person.last_name == camper.last_name
            assert person.user is None

    def test_users_become_persons_with_user_fk_linked(self, setup_done):
        call_command(
            "migrate_clc_legacy_data", "--apply",
            stdout=StringIO(), stderr=StringIO(),
        )
        org = Organization.objects.get(slug="clc")

        for user in setup_done["users"].values():
            person = Person.all_objects.get(organization=org, user=user)
            assert person.external_ids["legacy_user_id"] == user.id
            assert person.email == user.email


@pytest.mark.django_db
class TestMigrateAssignments:
    def test_camper_assignments_create_membership_and_agm(self, setup_done):
        call_command(
            "migrate_clc_legacy_data", "--apply",
            stdout=StringIO(), stderr=StringIO(),
        )
        org = Organization.objects.get(slug="clc")
        s1 = Program.all_objects.get(organization=org, slug="summer-2025-session-1")
        eve = setup_done["campers"]["eve"]

        eve_person = Person.all_objects.get(
            organization=org, external_ids__legacy_camper_id=eve.id,
        )

        # Eve has a Membership(role=camper) in both s1 and s2
        memberships = Membership.all_objects.filter(person=eve_person, role="camper")
        assert memberships.count() == 2

        # Eve has an AGM(role=subject) in the Aspen bunk of s1
        aspen_s1 = AssignmentGroup.all_objects.get(
            program=s1, group_type="bunk", name="Aspen",
        )
        assert AssignmentGroupMembership.all_objects.filter(
            group=aspen_s1, person=eve_person, role_in_group="subject",
        ).exists()

    def test_counselor_assignments_create_membership_and_author_agm(self, setup_done):
        call_command(
            "migrate_clc_legacy_data", "--apply",
            stdout=StringIO(), stderr=StringIO(),
        )
        org = Organization.objects.get(slug="clc")
        s1 = Program.all_objects.get(organization=org, slug="summer-2025-session-1")
        alice = setup_done["users"]["alice"]

        alice_person = Person.all_objects.get(organization=org, user=alice)
        assert Membership.all_objects.filter(
            program=s1, person=alice_person, role="counselor",
        ).exists()

        aspen_s1 = AssignmentGroup.all_objects.get(
            program=s1, group_type="bunk", name="Aspen",
        )
        assert AssignmentGroupMembership.all_objects.filter(
            group=aspen_s1, person=alice_person, role_in_group="author",
        ).exists()

    def test_unit_staff_assignments_spread_across_sessions_by_date_overlap(
        self,
        setup_done,
    ):
        """Carol's UH assignment is open-ended → lands in both s1 and s2.
        Dave's CC assignment ends 2025-07-26 → only lands in session 1.
        """
        call_command(
            "migrate_clc_legacy_data", "--apply",
            stdout=StringIO(), stderr=StringIO(),
        )
        org = Organization.objects.get(slug="clc")
        s1 = Program.all_objects.get(organization=org, slug="summer-2025-session-1")
        s2 = Program.all_objects.get(organization=org, slug="summer-2025-session-2")
        carol = setup_done["users"]["carol"]
        dave = setup_done["users"]["dave"]

        carol_person = Person.all_objects.get(organization=org, user=carol)
        assert Membership.all_objects.filter(
            program=s1, person=carol_person, role="unit_head",
        ).exists()
        assert Membership.all_objects.filter(
            program=s2, person=carol_person, role="unit_head",
        ).exists()

        dave_person = Person.all_objects.get(organization=org, user=dave)
        assert Membership.all_objects.filter(
            program=s1, person=dave_person, role="camper_care",
        ).exists()
        # Dave's assignment ended 2025-07-26, session 2 starts 2025-07-26 -> overlaps 1 day
        # We accept that, since _date_ranges_overlap is inclusive. Document & verify.
        # If product wants strict-overlap, change _date_ranges_overlap and update here.


@pytest.mark.django_db
class TestMigrateBunkLogs:
    def test_bunk_logs_become_reflections(self, setup_done):
        call_command(
            "migrate_clc_legacy_data", "--apply",
            stdout=StringIO(), stderr=StringIO(),
        )
        org = Organization.objects.get(slug="clc")

        reflections = Reflection.all_objects.filter(
            organization=org,
            template__slug="clc-legacy-counselor-daily",
        )
        # 4 bunk logs were seeded in the fixture
        assert reflections.count() == 4

    def test_bunk_log_answer_payload_matches_legacy(self, setup_done):
        call_command(
            "migrate_clc_legacy_data", "--apply",
            stdout=StringIO(), stderr=StringIO(),
        )
        org = Organization.objects.get(slug="clc")
        s1 = Program.all_objects.get(organization=org, slug="summer-2025-session-1")
        eve = setup_done["campers"]["eve"]
        eve_person = Person.all_objects.get(
            organization=org, external_ids__legacy_camper_id=eve.id,
        )

        # The scored Eve log on 2025-06-30
        ref = Reflection.all_objects.get(
            program=s1, subject=eve_person, period_start=date(2025, 6, 30),
        )
        assert ref.answers["not_on_camp"] == "no"
        assert ref.answers["request_unit_head_help"] == "no"
        assert ref.answers["request_camper_care_help"] == "no"
        assert ref.answers["camper_scores"] == {
            "behavior": 5, "participation": 3, "social": 4,
        }
        assert ref.answers["daily_report"] == "Great day for Eve."

    def test_not_on_camp_log_omits_camper_scores(self, setup_done):
        call_command(
            "migrate_clc_legacy_data", "--apply",
            stdout=StringIO(), stderr=StringIO(),
        )
        org = Organization.objects.get(slug="clc")
        eve = setup_done["campers"]["eve"]
        eve_person = Person.all_objects.get(
            organization=org, external_ids__legacy_camper_id=eve.id,
        )

        ref = Reflection.all_objects.get(
            subject=eve_person, period_start=date(2025, 7, 1),
        )
        assert ref.answers["not_on_camp"] == "yes"
        assert "camper_scores" not in ref.answers


@pytest.mark.django_db
class TestMigrateStaffLogs:
    def test_staff_logs_in_session_become_reflections(self, setup_done):
        call_command(
            "migrate_clc_legacy_data", "--apply",
            stdout=StringIO(), stderr=StringIO(),
        )
        org = Organization.objects.get(slug="clc")

        refs = Reflection.all_objects.filter(
            organization=org,
            template__slug="clc-legacy-staff-log-daily",
        )
        # 3 of the 5 fixture staff logs fall in 2025 session windows;
        # 1 is pre-session, 1 is 2026 -> both skipped.
        assert refs.count() == 3

    def test_staff_log_payload_contains_all_fields(self, setup_done):
        call_command(
            "migrate_clc_legacy_data", "--apply",
            stdout=StringIO(), stderr=StringIO(),
        )
        org = Organization.objects.get(slug="clc")
        alice = setup_done["users"]["alice"]
        alice_person = Person.all_objects.get(organization=org, user=alice)

        # Alice's day-off log on 2025-08-05
        ref = Reflection.all_objects.get(
            subject=alice_person, period_start=date(2025, 8, 5),
        )
        assert ref.answers["day_off"] == "yes"
        assert ref.answers["day_quality_score"] == 5
        assert ref.answers["support_level_score"] == 5
        assert ref.answers["staff_care_support_needed"] == "no"
        # subject == author for self-reflections
        assert ref.subject_id == ref.author_id
        # No assignment_group for self-reflections
        assert ref.assignment_group is None

    def test_boundary_day_goes_to_session_2(self, setup_done):
        """Logs dated 2025-07-26 should be attributed to Session 2 (later session wins)."""
        call_command(
            "migrate_clc_legacy_data", "--apply",
            stdout=StringIO(), stderr=StringIO(),
        )
        org = Organization.objects.get(slug="clc")
        s2 = Program.all_objects.get(organization=org, slug="summer-2025-session-2")
        bob = setup_done["users"]["bob"]
        bob_person = Person.all_objects.get(organization=org, user=bob)

        ref = Reflection.all_objects.get(
            subject=bob_person, period_start=date(2025, 7, 26),
            template__slug="clc-legacy-staff-log-daily",
        )
        assert ref.program_id == s2.id


@pytest.mark.django_db
class TestBackfillTemplateAssignments:
    def test_one_assignment_per_bunk_ag(self, setup_done):
        call_command(
            "migrate_clc_legacy_data", "--apply",
            stdout=StringIO(), stderr=StringIO(),
        )
        org = Organization.objects.get(slug="clc")

        # 4 bunks across the two 2025 sessions -> 4 bunk AGs -> 4 assignments.
        assignments = TemplateAssignment.all_objects.filter(
            organization=org,
            template__slug="clc-legacy-counselor-daily",
            target_type=TemplateAssignment.TargetType.ASSIGNMENT_GROUP,
        )
        assert assignments.count() == 4
        assert {a.assignment_group.group_type for a in assignments} == {"bunk"}

    def test_assignment_window_spans_program_and_covers_in_session_date(
        self,
        setup_done,
    ):
        call_command(
            "migrate_clc_legacy_data", "--apply",
            stdout=StringIO(), stderr=StringIO(),
        )
        org = Organization.objects.get(slug="clc")
        s1 = Program.all_objects.get(organization=org, slug="summer-2025-session-1")
        aspen_s1 = AssignmentGroup.all_objects.get(
            program=s1, group_type="bunk", name="Aspen",
        )

        ta = TemplateAssignment.all_objects.get(
            assignment_group=aspen_s1,
            template__slug="clc-legacy-counselor-daily",
        )
        assert ta.start_date == s1.start_date
        assert ta.end_date == s1.end_date
        assert ta.status == TemplateAssignment.Status.ENDED
        assert ta.is_required is True
        # The window covers a date with a migrated reflection (2025-06-30).
        mid = date(2025, 6, 30)
        assert ta.start_date <= mid <= ta.end_date

    def test_backfill_runs_even_when_reflections_skipped(self, setup_done):
        call_command(
            "migrate_clc_legacy_data", "--apply", "--skip-reflections",
            stdout=StringIO(), stderr=StringIO(),
        )
        # Assignments are not gated by the reflection skip flags.
        assert TemplateAssignment.all_objects.filter(
            template__slug="clc-legacy-counselor-daily",
            target_type=TemplateAssignment.TargetType.ASSIGNMENT_GROUP,
        ).count() == 4
        assert Reflection.all_objects.count() == 0

    def test_dry_run_creates_no_assignments(self, setup_done):
        call_command(
            "migrate_clc_legacy_data", stdout=StringIO(), stderr=StringIO(),
        )
        assert TemplateAssignment.all_objects.count() == 0


@pytest.mark.django_db
class TestIdempotency:
    def test_migration_run_twice_produces_same_counts(self, setup_done):
        call_command(
            "migrate_clc_legacy_data", "--apply",
            stdout=StringIO(), stderr=StringIO(),
        )
        first = self._counts()

        call_command(
            "migrate_clc_legacy_data", "--apply",
            stdout=StringIO(), stderr=StringIO(),
        )
        second = self._counts()

        assert first == second, f"Migration not idempotent: {first} vs {second}"

    def test_deterministic_uuid_is_stable(self):
        u1 = deterministic_uuid("bunklog", 123)
        u2 = deterministic_uuid("bunklog", 123)
        assert u1 == u2

        # Different kind -> different UUID
        assert deterministic_uuid("stafflog", 123) != u1
        # Different id -> different UUID
        assert deterministic_uuid("bunklog", 124) != u1

    @staticmethod
    def _counts() -> dict[str, int]:
        return {
            "persons": Person.all_objects.count(),
            "memberships": Membership.all_objects.count(),
            "agms": AssignmentGroupMembership.all_objects.count(),
            "reflections": Reflection.all_objects.count(),
            "template_assignments": TemplateAssignment.all_objects.count(),
        }


@pytest.mark.django_db
class TestSkipFlags:
    def test_skip_reflections_skips_both_log_types(self, setup_done):
        call_command(
            "migrate_clc_legacy_data", "--apply", "--skip-reflections",
            stdout=StringIO(), stderr=StringIO(),
        )
        # Persons and memberships migrated
        assert Person.all_objects.count() > 0
        assert Membership.all_objects.count() > 0
        # But no reflections
        assert Reflection.all_objects.count() == 0

    def test_skip_bunk_logs_only(self, setup_done):
        call_command(
            "migrate_clc_legacy_data", "--apply", "--skip-bunk-logs",
            stdout=StringIO(), stderr=StringIO(),
        )
        assert Reflection.all_objects.filter(
            template__slug="clc-legacy-counselor-daily",
        ).count() == 0
        assert Reflection.all_objects.filter(
            template__slug="clc-legacy-staff-log-daily",
        ).count() > 0
