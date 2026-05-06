"""Tests for the import_campminder_staff management command."""
from __future__ import annotations

import textwrap
from datetime import date
from io import StringIO

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from bunk_logs.core.models import Membership
from bunk_logs.core.models import Organization
from bunk_logs.core.models import Person
from bunk_logs.core.models import Program


@pytest.fixture
def org(db):
    return Organization.objects.create(name="Test Camp", slug="test-camp")


@pytest.fixture
def program(org):
    return Program.objects.create(
        organization=org,
        name="Test Camp - Summer 2026 (full program)",
        slug="summer-2026",
        program_type="summer_camp",
        start_date=date(2026, 6, 28),
        end_date=date(2026, 8, 16),
    )


def _write_csv(tmp_path, content: str) -> str:
    p = tmp_path / "staff.csv"
    p.write_text(textwrap.dedent(content).strip())
    return str(p)


def _run(tmp_path, content: str, org_slug="test-camp", program_slug="summer-2026", **kwargs) -> StringIO:
    csv_path = _write_csv(tmp_path, content)
    out = StringIO()
    call_command(
        "import_campminder_staff",
        csv_path=csv_path,
        org_slug=org_slug,
        program_slug=program_slug,
        stdout=out,
        **kwargs,
    )
    return out


CSV_SINGLE = """
    campminder_id,first_name,last_name,email,role,language_preference,tags
    CM001,Alice,Smith,alice@example.com,counselor,en,"nature,arts"
"""

CSV_TWO = """
    campminder_id,first_name,last_name,email,role,language_preference,tags
    CM001,Alice,Smith,alice@example.com,counselor,en,"nature,arts"
    CM002,Bob,Jones,bob@example.com,unit_head,es,leadership
"""


@pytest.mark.django_db
class TestImportCreatesPersons:
    def test_creates_person_and_membership(self, tmp_path, program):
        _run(tmp_path, CSV_SINGLE)

        person = Person.all_objects.get(external_ids__campminder_id="CM001")
        assert person.first_name == "Alice"
        assert person.last_name == "Smith"
        assert person.email == "alice@example.com"
        assert person.external_ids["campminder_id"] == "CM001"

        membership = Membership.all_objects.get(person=person, program=program, role="counselor")
        assert membership.tags == ["arts", "nature"]
        assert membership.metadata["language_preference"] == "en"

    def test_creates_multiple_rows(self, tmp_path, program):
        _run(tmp_path, CSV_TWO)
        assert Person.all_objects.filter(organization=program.organization).count() == 2
        assert Membership.all_objects.filter(program=program).count() == 2


@pytest.mark.django_db
class TestImportUpdatesExistingPersons:
    def test_updates_name_and_email(self, tmp_path, program):
        org = program.organization
        Person.objects.create(
            organization=org,
            first_name="Alicia",
            last_name="Smyth",
            email="old@example.com",
            external_ids={"campminder_id": "CM001"},
        )

        _run(tmp_path, CSV_SINGLE)

        person = Person.all_objects.get(external_ids__campminder_id="CM001")
        assert person.first_name == "Alice"
        assert person.last_name == "Smith"
        assert person.email == "alice@example.com"
        assert Person.all_objects.filter(organization=org).count() == 1

    def test_preserves_other_external_ids(self, tmp_path, program):
        org = program.organization
        Person.objects.create(
            organization=org,
            first_name="Alice",
            last_name="Smith",
            email="alice@example.com",
            external_ids={"campminder_id": "CM001", "other_system": "XYZ"},
        )

        _run(tmp_path, CSV_SINGLE)

        person = Person.all_objects.get(external_ids__campminder_id="CM001")
        assert person.external_ids["other_system"] == "XYZ"


@pytest.mark.django_db
class TestIdempotency:
    def test_no_duplicates_on_rerun(self, tmp_path, program):
        _run(tmp_path, CSV_TWO)
        _run(tmp_path, CSV_TWO)

        assert Person.all_objects.filter(organization=program.organization).count() == 2
        assert Membership.all_objects.filter(program=program).count() == 2

    def test_unchanged_person_not_written(self, tmp_path, program):
        out = _run(tmp_path, CSV_SINGLE)
        assert "Created: 1" in out.getvalue()

        out2 = _run(tmp_path, CSV_SINGLE)
        assert "Updated: 0" in out2.getvalue()
        assert "Unchanged: 1" in out2.getvalue()


@pytest.mark.django_db
class TestDryRun:
    def test_dry_run_writes_nothing(self, tmp_path, program):
        _run(tmp_path, CSV_SINGLE, dry_run=True)
        assert Person.all_objects.count() == 0
        assert Membership.all_objects.count() == 0

    def test_dry_run_prints_rows(self, tmp_path, program):
        out = _run(tmp_path, CSV_SINGLE, dry_run=True)
        assert "[dry-run]" in out.getvalue()
        assert "CM001" in out.getvalue()


@pytest.mark.django_db
class TestValidation:
    def test_unknown_role_skipped(self, tmp_path, program):
        csv = """
            campminder_id,first_name,last_name,email,role,language_preference,tags
            CM001,Alice,Smith,alice@example.com,INVALID_ROLE,,
        """
        out = _run(tmp_path, csv)
        assert Person.all_objects.count() == 0
        assert "unknown role" in out.getvalue()

    def test_missing_campminder_id_skipped(self, tmp_path, program):
        csv = """
            campminder_id,first_name,last_name,email,role,language_preference,tags
            ,Alice,Smith,alice@example.com,counselor,,
        """
        out = _run(tmp_path, csv)
        assert Person.all_objects.count() == 0
        assert "missing campminder_id" in out.getvalue()

    def test_missing_org_raises(self, tmp_path, program):
        with pytest.raises(CommandError, match="Organization not found"):
            _run(tmp_path, CSV_SINGLE, org_slug="does-not-exist")

    def test_missing_program_raises(self, tmp_path, program):
        with pytest.raises(CommandError, match="Program not found"):
            _run(tmp_path, CSV_SINGLE, program_slug="no-such-program")

    def test_missing_csv_file_raises(self, tmp_path, program):
        out = StringIO()
        with pytest.raises(CommandError, match="CSV file not found"):
            call_command(
                "import_campminder_staff",
                csv_path="/nonexistent/path.csv",
                org_slug="test-camp",
                program_slug="summer-2026",
                stdout=out,
            )


@pytest.mark.django_db
class TestTagNormalization:
    def test_tags_lowercased_and_deduplicated(self, tmp_path, program):
        csv = """
            campminder_id,first_name,last_name,email,role,language_preference,tags
            CM001,Alice,Smith,alice@example.com,counselor,,"Nature, ARTS, arts"
        """
        _run(tmp_path, csv)
        membership = Membership.all_objects.get(program=program, role="counselor")
        assert membership.tags == ["arts", "nature"]

    def test_empty_tags_stored_as_empty_list(self, tmp_path, program):
        csv = """
            campminder_id,first_name,last_name,email,role,language_preference,tags
            CM001,Alice,Smith,alice@example.com,counselor,,
        """
        _run(tmp_path, csv)
        membership = Membership.all_objects.get(program=program, role="counselor")
        assert membership.tags == []
