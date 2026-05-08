"""Tests for the onboard_clc_summer_2026 management command."""
from __future__ import annotations

import csv
import io
import tempfile
from pathlib import Path

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from bunk_logs.core.models import Membership
from bunk_logs.core.models import Organization
from bunk_logs.core.models import Person
from bunk_logs.core.models import Program
from bunk_logs.core.models import ReflectionTemplate


def _run(*args, **kwargs):
    out = io.StringIO()
    err = io.StringIO()
    call_command("onboard_clc_summer_2026", *args, stdout=out, stderr=err, **kwargs)
    return out.getvalue(), err.getvalue()


def _write_csv(rows: list[dict], path: Path) -> None:
    if not rows:
        path.write_text("campminder_id,first_name,last_name,email,role\n")
        return
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)


# ---------------------------------------------------------------------------
# Argument validation
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_requires_csv_or_skip():
    with pytest.raises((CommandError, SystemExit)):
        call_command("onboard_clc_summer_2026", stdout=io.StringIO(), stderr=io.StringIO())


@pytest.mark.django_db
def test_skip_import_no_csv_required():
    out, _ = _run(skip_import=True)
    assert "ready" in out.lower() or "passed" in out.lower()


# ---------------------------------------------------------------------------
# Org + program seeded
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_org_and_program_created():
    _run(skip_import=True)
    org = Organization.objects.get(slug="clc")
    assert org.name == "URJ Crane Lake Camp"
    program = Program.all_objects.get(organization=org, slug="summer-2026")
    assert program.program_type == "summer_camp"


@pytest.mark.django_db
def test_idempotent_run_twice():
    _run(skip_import=True)
    _run(skip_import=True)
    assert Organization.objects.filter(slug="clc").count() == 1


# ---------------------------------------------------------------------------
# Templates seeded
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_all_templates_created():
    _run(skip_import=True)
    org = Organization.objects.get(slug="clc")
    n = ReflectionTemplate.all_objects.filter(organization=org, is_active=True).count()
    assert n == 11


@pytest.mark.django_db
def test_template_roles_present():
    _run(skip_import=True)
    org = Organization.objects.get(slug="clc")
    roles = set(
        ReflectionTemplate.all_objects.filter(organization=org, is_active=True)
        .values_list("role", flat=True),
    )
    expected = {
        "counselor", "junior_counselor", "specialist", "general_counselor",
        "leadership_team", "kitchen_staff", "maintenance", "housekeeping",
        "camper_care", "health_center", "special_diets",
    }
    assert expected <= roles


# ---------------------------------------------------------------------------
# Staff CSV import
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_csv_import_creates_persons():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        tmp = Path(f.name)
    rows = [
        {"campminder_id": "CM001", "first_name": "Alice", "last_name": "Smith",
         "email": "alice@clc.test", "role": "counselor"},
        {"campminder_id": "CM002", "first_name": "Bob", "last_name": "Jones",
         "email": "bob@clc.test", "role": "kitchen_staff"},
    ]
    _write_csv(rows, tmp)
    try:
        _run(csv_path=str(tmp))
        org = Organization.objects.get(slug="clc")
        assert Person.all_objects.filter(organization=org).count() == 2
        program = Program.all_objects.get(organization=org, slug="summer-2026")
        assert Membership.all_objects.filter(program=program).count() == 2
    finally:
        tmp.unlink(missing_ok=True)


@pytest.mark.django_db
def test_csv_import_is_idempotent():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        tmp = Path(f.name)
    rows = [
        {"campminder_id": "CM010", "first_name": "Carol", "last_name": "C",
         "email": "carol@clc.test", "role": "counselor"},
    ]
    _write_csv(rows, tmp)
    try:
        _run(csv_path=str(tmp))
        _run(csv_path=str(tmp))
        org = Organization.objects.get(slug="clc")
        assert Person.all_objects.filter(organization=org).count() == 1
    finally:
        tmp.unlink(missing_ok=True)


@pytest.mark.django_db
def test_dry_run_does_not_write():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        tmp = Path(f.name)
    rows = [
        {"campminder_id": "CM099", "first_name": "Ghost", "last_name": "User",
         "email": "ghost@clc.test", "role": "counselor"},
    ]
    _write_csv(rows, tmp)
    try:
        out, _ = _run(csv_path=str(tmp), dry_run=True)
        assert "dry-run" in out.lower()
        assert Organization.objects.filter(slug="clc").count() == 0
    finally:
        tmp.unlink(missing_ok=True)


@pytest.mark.django_db
def test_missing_csv_raises():
    with pytest.raises((CommandError, SystemExit)):
        call_command(
            "onboard_clc_summer_2026",
            csv_path="/does/not/exist.csv",
            stdout=io.StringIO(),
            stderr=io.StringIO(),
        )
