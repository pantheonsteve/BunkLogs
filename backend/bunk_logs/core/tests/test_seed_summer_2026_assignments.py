"""Tests for the ``seed_summer_2026_assignments`` management command (Step 7_22).

Covers the 8 acceptance scenarios in
``migration_prompts/7_22_seed_summer_2026_assignments.md`` §7.
"""
from __future__ import annotations

import io
from datetime import date

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError

from bunk_logs.core.management.commands.seed_summer_2026_assignments import ASSIGNMENT_MANIFEST
from bunk_logs.core.models import Membership
from bunk_logs.core.models import Organization
from bunk_logs.core.models import Person
from bunk_logs.core.models import Program
from bunk_logs.core.models import ReflectionTemplate
from bunk_logs.core.models import TemplateAssignment

User = get_user_model()
pytestmark = pytest.mark.django_db

SCHEMA = {
    "fields": [
        {"key": "note", "type": "textarea", "required": False, "prompts": {"en": "Notes"}},
    ],
}


def _run(**kwargs) -> tuple[str, str]:
    out = io.StringIO()
    err = io.StringIO()
    call_command("seed_summer_2026_assignments", stdout=out, stderr=err, **kwargs)
    return out.getvalue(), err.getvalue()


# ── fixtures ─────────────────────────────────────────────────────────────


@pytest.fixture
def org():
    return Organization.objects.create(name="URJ Crane Lake Camp", slug="clc")


@pytest.fixture
def program(org):
    return Program.all_objects.create(
        organization=org,
        name=f"{org.name} - Summer 2026",
        slug="summer-2026",
        program_type="summer_camp",
        start_date=date(2026, 6, 28),
        end_date=date(2026, 8, 16),
    )


def _make_template(org, *, role: str, slug: str, cadence: str = "daily"):
    return ReflectionTemplate.all_objects.create(
        organization=org,
        name=f"{slug} v1",
        slug=slug,
        cadence=cadence,
        role=role,
        schema=SCHEMA,
        languages=["en"],
        subject_mode="self",
        author_role_filter=[role],
        status=ReflectionTemplate.Status.PUBLISHED,
        is_active=True,
        version=1,
    )


@pytest.fixture
def all_templates(org):
    created = {}
    for entry in ASSIGNMENT_MANIFEST:
        cadence = "biweekly" if entry["role"] == "leadership_team" else "daily"
        created[entry["role"]] = _make_template(
            org, role=entry["role"], slug=entry["slug"], cadence=cadence,
        )
    return created


# ── 1. happy path ───────────────────────────────────────────────────────


def test_happy_path_creates_twelve_assignments(org, program, all_templates):
    out, _ = _run(org_slug="clc", program_slug="summer-2026")
    assert TemplateAssignment.all_objects.filter(program=program).count() == 12
    rows = TemplateAssignment.all_objects.filter(program=program)
    roles_seen = {row.target_payload["role"] for row in rows}
    expected_roles = {entry["role"] for entry in ASSIGNMENT_MANIFEST}
    assert roles_seen == expected_roles
    for row in rows:
        assert row.target_type == TemplateAssignment.TargetType.ROLE
        assert row.is_required is True
        assert row.status == TemplateAssignment.Status.SCHEDULED
        assert row.start_date == program.start_date
        assert row.end_date == program.end_date
        assert row.cadence_override is None
        assert row.organization_id == org.pk
    assert "Seeded 12 assignments" in out


# ── 2. idempotency ──────────────────────────────────────────────────────


def test_idempotent_when_run_twice(org, program, all_templates):
    _run(org_slug="clc", program_slug="summer-2026")
    _run(org_slug="clc", program_slug="summer-2026")
    assert TemplateAssignment.all_objects.filter(program=program).count() == 12


# ── 3. dry run ──────────────────────────────────────────────────────────


def test_dry_run_writes_nothing(org, program, all_templates):
    out, _ = _run(org_slug="clc", program_slug="summer-2026", dry_run=True)
    assert TemplateAssignment.all_objects.filter(program=program).count() == 0
    assert "DRY-RUN" in out
    assert "12 planned actions" in out


# ── 4. missing template fails ───────────────────────────────────────────


def test_missing_template_raises(org, program, all_templates):
    missing = all_templates["counselor"]
    missing.delete()
    with pytest.raises(CommandError) as excinfo:
        _run(org_slug="clc", program_slug="summer-2026")
    assert "clc-2026-counselor-daily" in str(excinfo.value)
    assert TemplateAssignment.all_objects.filter(program=program).count() == 0


# ── 5. title update is reconciled in-place ──────────────────────────────


def test_existing_assignment_with_wrong_title_is_corrected(
    org, program, all_templates,
):
    template = all_templates["counselor"]
    stale = TemplateAssignment.all_objects.create(
        organization=org,
        program=program,
        template=template,
        target_type=TemplateAssignment.TargetType.ROLE,
        target_payload={"role": "counselor"},
        start_date=program.start_date,
        end_date=program.end_date,
        is_required=False,
        title="Old wrong title",
        status=TemplateAssignment.Status.SCHEDULED,
    )
    _run(org_slug="clc", program_slug="summer-2026")
    stale.refresh_from_db()
    assert stale.title == "Counselor daily bunk log"
    assert stale.is_required is True
    assert TemplateAssignment.all_objects.filter(program=program).count() == 12


# ── 6. cross-program isolation ──────────────────────────────────────────


def test_other_program_assignments_are_untouched(org, program, all_templates):
    _run(org_slug="clc", program_slug="summer-2026")
    pks_2026_before = set(
        TemplateAssignment.all_objects.filter(program=program).values_list(
            "pk", flat=True,
        ),
    )
    summer_2027 = Program.all_objects.create(
        organization=org,
        name=f"{org.name} - Summer 2027",
        slug="summer-2027",
        program_type="summer_camp",
        start_date=date(2027, 6, 27),
        end_date=date(2027, 8, 15),
    )
    # Templates are org-scoped, so re-running against a different program in
    # the same org succeeds. The 2026 rows must stay intact.
    _run(org_slug="clc", program_slug="summer-2027")
    pks_2026_after = set(
        TemplateAssignment.all_objects.filter(program=program).values_list(
            "pk", flat=True,
        ),
    )
    assert pks_2026_after == pks_2026_before
    assert TemplateAssignment.all_objects.filter(program=program).count() == 12
    assert TemplateAssignment.all_objects.filter(program=summer_2027).count() == 12


# ── 7. cross-org isolation ──────────────────────────────────────────────


def test_other_org_run_does_not_affect_clc(org, program, all_templates):
    _run(org_slug="clc", program_slug="summer-2026")
    other = Organization.objects.create(name="Other Camp", slug="other")
    Program.all_objects.create(
        organization=other,
        name=f"{other.name} - Summer 2026",
        slug="summer-2026",
        program_type="summer_camp",
        start_date=date(2026, 6, 28),
        end_date=date(2026, 8, 16),
    )
    with pytest.raises(CommandError):
        _run(org_slug="other", program_slug="summer-2026")
    assert TemplateAssignment.all_objects.filter(program=program).count() == 12


# ── 8. ended/cancelled row → warn + create alongside (no resurrect) ────


def test_existing_ended_row_does_not_block_new_creation(
    org, program, all_templates,
):
    template = all_templates["counselor"]
    ended = TemplateAssignment.all_objects.create(
        organization=org,
        program=program,
        template=template,
        target_type=TemplateAssignment.TargetType.ROLE,
        target_payload={"role": "counselor"},
        start_date=date(2025, 6, 1),
        end_date=date(2025, 8, 31),
        is_required=True,
        title="Last year's counselor log",
        status=TemplateAssignment.Status.ENDED,
    )
    out, _ = _run(org_slug="clc", program_slug="summer-2026")
    ended.refresh_from_db()
    assert ended.status == TemplateAssignment.Status.ENDED
    assert ended.title == "Last year's counselor log"
    counselor_rows = TemplateAssignment.all_objects.filter(
        program=program,
        template=template,
        target_type=TemplateAssignment.TargetType.ROLE,
        target_payload__role="counselor",
    )
    assert counselor_rows.count() == 2
    assert counselor_rows.filter(
        status=TemplateAssignment.Status.SCHEDULED,
    ).count() == 1
    assert "warn" in out.lower()


# ── actor resolution ────────────────────────────────────────────────────


def test_actor_username_attaches_created_by(org, program, all_templates):
    user = User.objects.create_user(email="alyson@clc.test", password="pw")
    person = Person.all_objects.create(
        organization=org, first_name="Aly", last_name="Son", user=user,
    )
    lt_membership = Membership.all_objects.create(
        program=program, person=person, role="leadership_team", is_active=True,
    )
    _run(
        org_slug="clc",
        program_slug="summer-2026",
        actor_username="alyson@clc.test",
    )
    rows = TemplateAssignment.all_objects.filter(program=program)
    assert rows.count() == 12
    for row in rows:
        assert row.created_by_id == lt_membership.pk


def test_actor_username_unknown_user_raises(org, program, all_templates):
    with pytest.raises(CommandError):
        _run(
            org_slug="clc",
            program_slug="summer-2026",
            actor_username="nope@clc.test",
        )
    assert TemplateAssignment.all_objects.filter(program=program).count() == 0


def test_actor_username_without_admin_or_lt_role_raises(
    org, program, all_templates,
):
    user = User.objects.create_user(email="counselor@clc.test", password="pw")
    person = Person.all_objects.create(
        organization=org, first_name="C", last_name="Counselor", user=user,
    )
    Membership.all_objects.create(
        program=program, person=person, role="counselor", is_active=True,
    )
    with pytest.raises(CommandError):
        _run(
            org_slug="clc",
            program_slug="summer-2026",
            actor_username="counselor@clc.test",
        )
    assert TemplateAssignment.all_objects.filter(program=program).count() == 0


# ── pre-flight ──────────────────────────────────────────────────────────


def test_missing_org_raises():
    with pytest.raises(CommandError):
        _run(org_slug="missing", program_slug="summer-2026")


def test_missing_program_raises(org):
    with pytest.raises(CommandError):
        _run(org_slug="clc", program_slug="not-here")
