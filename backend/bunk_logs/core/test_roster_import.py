"""Tests for import_campminder_roster and import_tbe_roster management commands."""
from __future__ import annotations

import textwrap
from datetime import date
from io import StringIO

import pytest
from django.core.management import call_command

from bunk_logs.core.campminder_csv import infer_role_from_position
from bunk_logs.core.campminder_csv import normalize_campminder_row
from bunk_logs.core.models import AssignmentGroup
from bunk_logs.core.models import AssignmentGroupMembership
from bunk_logs.core.models import Membership
from bunk_logs.core.models import Organization
from bunk_logs.core.models import Person
from bunk_logs.core.models import Program
from bunk_logs.core.models import RosterImportLog


@pytest.fixture
def org(db):
    return Organization.objects.create(name="Test Camp", slug="test-camp")


@pytest.fixture
def program(org):
    return Program.all_objects.create(
        organization=org,
        name="Test Camp - Summer 2026",
        slug="summer-2026",
        program_type="summer_camp",
        start_date=date(2026, 6, 28),
        end_date=date(2026, 8, 16),
    )


@pytest.fixture
def tbe_org(db):
    return Organization.objects.create(name="Temple Beth El", slug="tbe")


@pytest.fixture
def tbe_program(tbe_org):
    return Program.all_objects.create(
        organization=tbe_org,
        name="Temple Beth El - Religious School 2026",
        slug="religious-school-2026",
        program_type="religious_school",
        start_date=date(2025, 9, 1),
        end_date=date(2026, 6, 15),
    )


def _write_csv(tmp_path, content: str, filename="roster.csv") -> str:
    p = tmp_path / filename
    p.write_text(textwrap.dedent(content).strip())
    return str(p)


def _run_campminder(tmp_path, content: str, org_slug="test-camp", program_slug="summer-2026", **kwargs):
    csv_path = _write_csv(tmp_path, content)
    out = StringIO()
    call_command(
        "import_campminder_roster",
        csv_path=csv_path,
        org_slug=org_slug,
        program_slug=program_slug,
        stdout=out,
        **kwargs,
    )
    return out


def _run_tbe(tmp_path, content: str, org_slug="tbe", program_slug="religious-school-2026", **kwargs):
    csv_path = _write_csv(tmp_path, content)
    out = StringIO()
    call_command(
        "import_tbe_roster",
        csv_path=csv_path,
        org_slug=org_slug,
        program_slug=program_slug,
        stdout=out,
        **kwargs,
    )
    return out


# ---------------------------------------------------------------------------
# Campminder: bunk hierarchy
# ---------------------------------------------------------------------------

CAMPMINDER_BUNK_CSV = """
campminder_id,first_name,last_name,role,bunk_name,unit_name,division_name,email
CM001,Alice,Smith,camper,Bunk Maple,Sophomores,Upper Camp,alice@example.com
CM002,Bob,Jones,camper,Bunk Maple,Sophomores,Upper Camp,
CM003,Carol,Lee,counselor,Bunk Maple,Sophomores,Upper Camp,carol@example.com
"""

CAMPMINDER_STAFF_ONLY_CSV = """
campminder_id,first_name,last_name,role,email
CM010,Dave,Park,unit_head,dave@example.com
"""

CAMPMINDER_CAMPER_EXPORT_CSV = """
Last Name,Preferred Name,PersonID
Abraham,Allie,20476515
Cohen,Sam,20476516
"""

CAMPMINDER_CAMPER_EXPORT_BOM_CSV = """
\ufeffLast Name,Preferred Name,PersonID
Abraham,Allie,20476515
"""

CAMPMINDER_CAMPER_EXPORT_ALT_HEADERS_CSV = """
LastName,PreferredName,PersonID
Abraham,Allie,20476515
"""

CAMPMINDER_STAFF_EXPORT_TSV = """
PersonID\tLast Name\tFirst Name\tLogin/Email\tPosition Types\tPosition
5927217\tAllen\tChristopher\tdrchrisa@gmail.com\tAdministrative Staff\tDriver
5201139\tHermann\tCory\tCorysoop@aol.com\tLeadership Team\tAllergies and Special Food Coordinator
6904465\tNadel\tJennifer\tjnadel13@gmail.com\tLeadership Team\tCamper Care Associate
5927256\tHernandez\tNino Benjie\ttaongkahoy@gmail.com\tLeadership Team\tDirector: Arts & Crafts
5200995\tFriedman\tShain\tshainfriedman11@gmail.com\tLeadership Team\tDirector: Athletics
"""


class TestCampminderCsvNormalization:
    def test_bom_prefixed_header_key(self):
        row = {"\ufeffLast Name": "Abraham", "Preferred Name": "Allie", "PersonID": "20476515"}
        normalized = normalize_campminder_row(row)
        assert normalized["last_name"] == "Abraham"
        assert normalized["preferred_name"] == "Allie"
        assert normalized["campminder_id"] == "20476515"

    def test_login_email_header_maps_to_email(self):
        row = {
            "PersonID": "5927217",
            "Last Name": "Allen",
            "First Name": "Christopher",
            "Login/Email": "drchrisa@gmail.com",
            "Position Types": "Administrative Staff",
            "Position": "Driver",
        }
        normalized = normalize_campminder_row(row)
        assert normalized["email"] == "drchrisa@gmail.com"
        assert normalized["role"] == "maintenance"
        assert normalized["position_type"] == "Administrative Staff"
        assert normalized["position"] == "Driver"

    def test_position_role_mapping(self):
        assert infer_role_from_position("Leadership Team", "Camper Care Associate") == "camper_care"
        assert infer_role_from_position("Leadership Team", "Director: Athletics") == "specialist"
        assert infer_role_from_position("Administrative Staff", "Driver") == "maintenance"
        assert infer_role_from_position("Leadership Team", "Allergies and Special Food Coordinator") == "special_diets"


@pytest.mark.django_db
class TestCampminderCamperExport:
    def test_imports_persons_with_preferred_name(self, tmp_path, program):
        _run_campminder(tmp_path, CAMPMINDER_CAMPER_EXPORT_CSV)

        allie = Person.all_objects.get(external_ids__campminder_id="20476515")
        assert allie.last_name == "Abraham"
        assert allie.preferred_name == "Allie"
        assert allie.first_name == "Allie"
        assert allie.full_name == "Allie Abraham"

        sam = Person.all_objects.get(external_ids__campminder_id="20476516")
        assert sam.last_name == "Cohen"
        assert sam.preferred_name == "Sam"

        assert Membership.all_objects.filter(program=program, role="camper").count() == 2

    def test_idempotent_rerun(self, tmp_path, program):
        _run_campminder(tmp_path, CAMPMINDER_CAMPER_EXPORT_CSV)
        _run_campminder(tmp_path, CAMPMINDER_CAMPER_EXPORT_CSV)
        assert Person.all_objects.filter(organization=program.organization).count() == 2

    def test_bom_prefixed_first_header(self, tmp_path, program):
        _run_campminder(tmp_path, CAMPMINDER_CAMPER_EXPORT_BOM_CSV)
        allie = Person.all_objects.get(external_ids__campminder_id="20476515")
        assert allie.last_name == "Abraham"
        assert allie.preferred_name == "Allie"

    def test_compact_header_names(self, tmp_path, program):
        _run_campminder(tmp_path, CAMPMINDER_CAMPER_EXPORT_ALT_HEADERS_CSV)
        allie = Person.all_objects.get(external_ids__campminder_id="20476515")
        assert allie.last_name == "Abraham"
        assert allie.preferred_name == "Allie"


@pytest.mark.django_db
class TestCampminderStaffExport:
    def test_imports_staff_with_roles_and_email(self, tmp_path, program):
        _run_campminder(tmp_path, CAMPMINDER_STAFF_EXPORT_TSV)

        chris = Person.all_objects.get(external_ids__campminder_id="5927217")
        assert chris.email == "drchrisa@gmail.com"
        assert Membership.all_objects.filter(program=program, person=chris, role="maintenance").exists()

        jennifer = Person.all_objects.get(external_ids__campminder_id="6904465")
        membership = Membership.all_objects.get(program=program, person=jennifer)
        assert membership.role == "camper_care"
        assert membership.metadata["campminder_position"] == "Camper Care Associate"

        shain = Person.all_objects.get(external_ids__campminder_id="5200995")
        assert Membership.all_objects.get(program=program, person=shain).role == "specialist"

    def test_merge_existing_person_by_name(self, tmp_path, program, org):
        existing = Person.all_objects.create(
            organization=org,
            first_name="Christopher",
            last_name="Allen",
            email="",
        )
        _run_campminder(tmp_path, CAMPMINDER_STAFF_EXPORT_TSV)

        chris = Person.all_objects.get(external_ids__campminder_id="5927217")
        assert chris.id == existing.id
        assert chris.email == "drchrisa@gmail.com"
        assert Person.all_objects.filter(organization=org).count() == 5

    def test_flags_ambiguous_name_duplicates(self, tmp_path, program, org):
        Person.all_objects.create(organization=org, first_name="Christopher", last_name="Allen")
        Person.all_objects.create(organization=org, first_name="Christopher", last_name="Allen")
        out = _run_campminder(tmp_path, CAMPMINDER_STAFF_EXPORT_TSV)
        assert "ambiguous name match" in out.getvalue()
        assert not Person.all_objects.filter(external_ids__campminder_id="5927217").exists()


@pytest.mark.django_db
class TestCampminderBunkHierarchy:
    def test_creates_hierarchy(self, tmp_path, program):
        _run_campminder(tmp_path, CAMPMINDER_BUNK_CSV)

        division = AssignmentGroup.all_objects.get(program=program, group_type="division", slug="upper-camp")
        unit = AssignmentGroup.all_objects.get(program=program, group_type="unit", slug="sophomores")
        bunk = AssignmentGroup.all_objects.get(program=program, group_type="bunk", slug="bunk-maple")

        assert unit.parent == division
        assert bunk.parent == unit

    def test_campers_are_subjects(self, tmp_path, program):
        _run_campminder(tmp_path, CAMPMINDER_BUNK_CSV)
        bunk = AssignmentGroup.all_objects.get(program=program, slug="bunk-maple")
        alice = Person.all_objects.get(external_ids__campminder_id="CM001")
        assert AssignmentGroupMembership.all_objects.filter(
            group=bunk, person=alice, role_in_group="subject",
        ).exists()

    def test_counselors_are_authors(self, tmp_path, program):
        _run_campminder(tmp_path, CAMPMINDER_BUNK_CSV)
        bunk = AssignmentGroup.all_objects.get(program=program, slug="bunk-maple")
        carol = Person.all_objects.get(external_ids__campminder_id="CM003")
        assert AssignmentGroupMembership.all_objects.filter(
            group=bunk, person=carol, role_in_group="author",
        ).exists()

    def test_staff_only_rows_no_group(self, tmp_path, program):
        _run_campminder(tmp_path, CAMPMINDER_STAFF_ONLY_CSV)
        assert not AssignmentGroup.all_objects.filter(program=program).exists()
        assert Membership.all_objects.filter(program=program).count() == 1


@pytest.mark.django_db
class TestCampminderIdempotency:
    def test_rerun_no_duplicates(self, tmp_path, program):
        _run_campminder(tmp_path, CAMPMINDER_BUNK_CSV)
        _run_campminder(tmp_path, CAMPMINDER_BUNK_CSV)

        assert Person.all_objects.filter(organization=program.organization).count() == 3
        assert AssignmentGroup.all_objects.filter(program=program).count() == 3
        bunk = AssignmentGroup.all_objects.get(program=program, slug="bunk-maple")
        assert AssignmentGroupMembership.all_objects.filter(group=bunk).count() == 3  # 2 subjects + 1 author


@pytest.mark.django_db
class TestCampminderReconcile:
    def test_reconcile_deactivates_removed_members(self, tmp_path, program):
        _run_campminder(tmp_path, CAMPMINDER_BUNK_CSV)
        bunk = AssignmentGroup.all_objects.get(program=program, slug="bunk-maple")
        assert AssignmentGroupMembership.all_objects.filter(group=bunk, is_active=True).count() == 3

        # Bob (CM002) removed from CSV
        updated_csv = """
campminder_id,first_name,last_name,role,bunk_name,unit_name,division_name,email
CM001,Alice,Smith,camper,Bunk Maple,Sophomores,Upper Camp,alice@example.com
CM003,Carol,Lee,counselor,Bunk Maple,Sophomores,Upper Camp,carol@example.com
"""
        _run_campminder(tmp_path, updated_csv, reconcile=True)
        active_subjects = AssignmentGroupMembership.all_objects.filter(
            group=bunk, role_in_group="subject", is_active=True,
        ).count()
        assert active_subjects == 1  # Only Alice remains active

    def test_additive_by_default(self, tmp_path, program):
        _run_campminder(tmp_path, CAMPMINDER_BUNK_CSV)
        bunk = AssignmentGroup.all_objects.get(program=program, slug="bunk-maple")

        updated_csv = """
campminder_id,first_name,last_name,role,bunk_name,unit_name,division_name,email
CM001,Alice,Smith,camper,Bunk Maple,Sophomores,Upper Camp,alice@example.com
"""
        _run_campminder(tmp_path, updated_csv)
        # Without --reconcile, Bob's membership is not deactivated
        assert AssignmentGroupMembership.all_objects.filter(group=bunk, is_active=True).count() == 3


@pytest.mark.django_db
class TestCampminderCaseload:
    CASELOAD_CSV = """
campminder_id,first_name,last_name,role,caseload_name,caseload_owner_campminder_id,email
CM020,Wellness,Staff,camper_care,Senior Caseload,,wellness@example.com
CM021,Camper,One,camper,Senior Caseload,CM020,
"""

    def test_caseload_missing_owner_warns(self, tmp_path, program):
        out = _run_campminder(tmp_path, self.CASELOAD_CSV)
        assert "caseload_owner_campminder_id missing" in out.getvalue()

    def test_caseload_created_with_owner_first(self, tmp_path, program):
        # Correct order: owner row first, then subject
        # Import owner first (no caseload), then camper with caseload
        csv2 = """
campminder_id,first_name,last_name,role,caseload_name,caseload_owner_campminder_id,email
CM020,Wellness,Staff,camper_care,,
"""
        _run_campminder(tmp_path, csv2)
        owner = Person.all_objects.get(external_ids__campminder_id="CM020")

        csv3 = """
campminder_id,first_name,last_name,role,caseload_name,caseload_owner_campminder_id,email
CM021,Camper,One,camper,Senior Caseload,CM020,
"""
        _run_campminder(tmp_path, csv3)
        caseload = AssignmentGroup.all_objects.get(program=program, group_type="caseload", slug="senior-caseload")
        camper = Person.all_objects.get(external_ids__campminder_id="CM021")

        assert AssignmentGroupMembership.all_objects.filter(group=caseload, person=owner, role_in_group="author").exists()
        assert AssignmentGroupMembership.all_objects.filter(group=caseload, person=camper, role_in_group="subject").exists()


@pytest.mark.django_db
class TestCampminderRosterImportLog:
    def test_log_created_and_completed(self, tmp_path, program):
        _run_campminder(tmp_path, CAMPMINDER_BUNK_CSV)
        log = RosterImportLog.all_objects.filter(
            program=program, importer_type="campminder",
        ).first()
        assert log is not None
        assert log.status == "completed"
        assert log.summary["persons_created"] == 3


@pytest.mark.django_db
class TestCampminderDryRun:
    def test_dry_run_writes_nothing(self, tmp_path, program):
        _run_campminder(tmp_path, CAMPMINDER_BUNK_CSV, dry_run=True)
        assert Person.all_objects.filter(organization=program.organization).count() == 0
        assert AssignmentGroup.all_objects.filter(program=program).count() == 0


# ---------------------------------------------------------------------------
# TBE classroom importer
# ---------------------------------------------------------------------------

TBE_CSV = """
first_name,last_name,role,classroom_name,grade_level,email
Noah,Cohen,madrich,Tzedakah 101,10,noah@tbe.org
Maya,Levy,madrich,Tzedakah 101,10,maya@tbe.org
Rabbi,Gold,faculty,Tzedakah 101,,rgold@tbe.org
Ari,Klein,madrich,Chesed 201,11,ari@tbe.org
"""


@pytest.mark.django_db
class TestTBEClassroomImport:
    def test_creates_classrooms(self, tmp_path, tbe_program):
        _run_tbe(tmp_path, TBE_CSV)
        assert AssignmentGroup.all_objects.filter(program=tbe_program, group_type="classroom").count() == 2

    def test_madrichim_are_subjects_and_authors(self, tmp_path, tbe_program):
        _run_tbe(tmp_path, TBE_CSV)
        classroom = AssignmentGroup.all_objects.get(program=tbe_program, slug="tzedakah-101")
        noah = Person.all_objects.get(first_name="Noah", last_name="Cohen", organization=tbe_program.organization)
        assert AssignmentGroupMembership.all_objects.filter(group=classroom, person=noah, role_in_group="subject").exists()
        assert AssignmentGroupMembership.all_objects.filter(group=classroom, person=noah, role_in_group="author").exists()

    def test_faculty_are_authors(self, tmp_path, tbe_program):
        _run_tbe(tmp_path, TBE_CSV)
        classroom = AssignmentGroup.all_objects.get(program=tbe_program, slug="tzedakah-101")
        rabbi = Person.all_objects.get(first_name="Rabbi", last_name="Gold", organization=tbe_program.organization)
        assert AssignmentGroupMembership.all_objects.filter(group=classroom, person=rabbi, role_in_group="author").exists()
        assert not AssignmentGroupMembership.all_objects.filter(group=classroom, person=rabbi, role_in_group="subject").exists()

    def test_tbe_idempotent(self, tmp_path, tbe_program):
        _run_tbe(tmp_path, TBE_CSV)
        _run_tbe(tmp_path, TBE_CSV)
        assert Person.all_objects.filter(organization=tbe_program.organization).count() == 4
        assert AssignmentGroup.all_objects.filter(program=tbe_program, group_type="classroom").count() == 2

    def test_grade_level_stored(self, tmp_path, tbe_program):
        _run_tbe(tmp_path, TBE_CSV)
        noah = Person.all_objects.get(first_name="Noah", last_name="Cohen", organization=tbe_program.organization)
        membership = Membership.all_objects.get(program=tbe_program, person=noah, role="madrich")
        assert membership.grade_level == 10

    def test_missing_classroom_skipped(self, tmp_path, tbe_program):
        csv = """
first_name,last_name,role,classroom_name,grade_level,email
Noah,Cohen,madrich,,10,noah@tbe.org
"""
        out = _run_tbe(tmp_path, csv)
        assert "missing classroom_name" in out.getvalue()
        assert Person.all_objects.filter(organization=tbe_program.organization).count() == 0

    def test_tbe_log_created(self, tmp_path, tbe_program):
        _run_tbe(tmp_path, TBE_CSV)
        log = RosterImportLog.all_objects.filter(program=tbe_program, importer_type="tbe_shulcloud").first()
        assert log is not None
        assert log.status == "completed"
