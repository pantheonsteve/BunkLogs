"""Shared pytest fixtures for the ``bunk_logs.api`` test package.

Why this lives here
-------------------

The counselor-flow tests in step 7_6 depend on the seeded
``counselor-self-reflection`` ReflectionTemplate that migration
``core/0029`` adds to the DB. That works fine for ordinary
``@pytest.mark.django_db`` tests because pytest-django wraps each one
in a transaction that's rolled back at teardown — the seeded row
survives.

But the dual-write signal tests in step 7_6g need
``@pytest.mark.django_db(transaction=True)`` so that
``transaction.on_commit`` callbacks actually fire. ``transaction=True``
uses ``TransactionTestCase`` semantics, which **flushes every table**
between tests to reset state. That flush removes the seeded
ReflectionTemplate, and any subsequent ordinary test that expected to
find it 403s out (Story 5 endpoints) or hits a NOT-NULL violation when
constructing a Reflection without a template FK.

Re-seeding the template at the start of every test fixes both:

- transactional tests get a fresh seed after the flush;
- ordinary tests still see a seeded template even if a transactional
  test ran earlier in the same session.

Keeping the fixture as ``autouse=True`` here (rather than in each test
file) means new test modules pick up the protection automatically.

Step 7_21: TemplateAssignment auto-seeding
------------------------------------------

After Step 7_21 the per-role dashboards resolve templates by looking
for an active ``TemplateAssignment``. Existing tests built up a
``Program`` and expected the seeded role template to "just work";
under the new resolver they would all hit ``no_template`` instead.

The :func:`_autobind_role_assignments_to_new_programs` autouse fixture
connects a ``post_save`` handler on ``Program`` that creates a
role-targeted assignment for every seeded role template the moment a
test creates its program. Tests that want to verify the no-template
empty-state should either skip that fixture explicitly or delete the
auto-created rows.
"""
from __future__ import annotations

from datetime import date
from datetime import timedelta

import pytest
from django.db.models.signals import post_save

from bunk_logs.core.models import Program
from bunk_logs.core.models import ReflectionTemplate
from bunk_logs.core.models import TemplateAssignment

_COUNSELOR_SELF_REFLECTION_SCHEMA = {
    "fields": [
        {"key": "day_off", "type": "yes_no", "required": False},
        {"key": "overall_day", "type": "single_rating", "required": False, "scale": [1, 5]},
        {"key": "wins", "type": "text_list", "required": False},
        {"key": "improvements", "type": "text_list", "required": False},
        {"key": "concern", "type": "textarea", "required": False},
        # Bunk-concerns surface (UH2 / Step 7_7). Counselors can flag
        # specific bunks via this multi-select; the UH bunk dashboard
        # consumes those references.
        {
            "key": "bunk_concerns_bunks",
            "type": "multiple_choice",
            "required": False,
            "option_source": "supervised_bunks",
        },
    ],
}

_UNIT_HEAD_SELF_REFLECTION_SCHEMA = {
    "fields": [
        {"key": "day_off", "type": "yes_no", "required": False},
        {"key": "overall_day", "type": "single_rating", "required": False, "scale": [1, 5]},
        {"key": "wins", "type": "text_list", "required": False},
        {"key": "improvements", "type": "text_list", "required": False},
        {"key": "concern", "type": "textarea", "required": False},
        {
            "key": "bunk_concerns_bunks",
            "type": "multiple_choice",
            "required": False,
            "option_source": "supervised_bunks",
        },
        {"key": "bunk_concerns_note", "type": "textarea", "required": False},
    ],
}

_KITCHEN_STAFF_SELF_REFLECTION_SCHEMA = {
    "fields": [
        {"key": "day_off", "type": "yes_no", "required": False},
        {
            "key": "service_summary",
            "type": "textarea",
            "required": False,
            "prompts": {"en": "Summarize today's service.", "es": "Resume el servicio de hoy."},
        },
        {
            "key": "highlight",
            "type": "textarea",
            "required": False,
            "prompts": {"en": "What went well?", "es": "¿Qué salió bien?"},
        },
    ],
}

_CAMPER_CARE_SELF_REFLECTION_SCHEMA = {
    "fields": [
        {"key": "day_off", "type": "yes_no", "required": False},
        {"key": "overall_day", "type": "single_rating", "required": False, "scale": [1, 5]},
        {"key": "wins", "type": "text_list", "required": False},
        {"key": "improvements", "type": "text_list", "required": False},
        {"key": "concern", "type": "textarea", "required": False},
        {
            "key": "bunk_concerns_bunks",
            "type": "multiple_choice",
            "required": False,
            "option_source": "caseload_bunks",
        },
        {"key": "bunk_concerns_note", "type": "textarea", "required": False},
    ],
}


@pytest.fixture(autouse=True)
def _ensure_counselor_self_reflection_template(db):
    """Re-seed the counselor self-reflection template before every test.

    Mirrors the production seed (migration ``core/0029``) but is
    explicit about it so a single failing test surfaces immediately
    rather than cascading into 'no template configured' 403s in
    seemingly unrelated tests.
    """
    ReflectionTemplate.all_objects.update_or_create(
        organization=None,
        slug="counselor-self-reflection",
        version=1,
        defaults={
            "name": "Counselor Self-Reflection",
            "description": "Auto-seeded for tests via api/tests/conftest.py.",
            "cadence": "daily",
            "schema": _COUNSELOR_SELF_REFLECTION_SCHEMA,
            "languages": ["en", "es"],
            "is_active": True,
            "subject_mode": "self",
            "assignment_scope": "none",
            "assignment_group_types": [],
            "author_role_filter": ["counselor", "junior_counselor"],
            "subject_role_filter": [],
            "required_per_subject_per_period": 1,
            "subject_visible": False,
            "supports_privacy": False,
            "role": "counselor",
            "program_type": None,
        },
    )


@pytest.fixture(autouse=True)
def _ensure_unit_head_self_reflection_template(db):
    """Re-seed the UH self-reflection template before every test (Step 7_7).

    Same rationale as the counselor seed; ``transaction=True`` tests
    flush the seeded migration row otherwise. Keeping the schema list
    aligned with the production migration ``core/0030`` is the test
    author's responsibility — anything materially different should
    land in BOTH places at once.
    """
    ReflectionTemplate.all_objects.update_or_create(
        organization=None,
        slug="unit-head-self-reflection",
        version=1,
        defaults={
            "name": "Unit Head Self-Reflection",
            "description": "Auto-seeded for tests via api/tests/conftest.py.",
            "cadence": "daily",
            "schema": _UNIT_HEAD_SELF_REFLECTION_SCHEMA,
            "languages": ["en", "es"],
            "is_active": True,
            "subject_mode": "self",
            "assignment_scope": "none",
            "assignment_group_types": [],
            "author_role_filter": ["unit_head"],
            "subject_role_filter": [],
            "required_per_subject_per_period": 1,
            "subject_visible": False,
            "supports_privacy": False,
            "role": "unit_head",
            "program_type": None,
        },
    )


@pytest.fixture(autouse=True)
def _ensure_camper_care_self_reflection_template(db):
    """Re-seed the CC self-reflection template before every test (Step 7_8d).

    Same rationale as counselor and UH seeds — ``transaction=True`` tests
    flush the migration-seeded row, breaking CC self-reflection tests that
    run later in the session. Aligned with production migration ``core/0032``.
    """
    ReflectionTemplate.all_objects.update_or_create(
        organization=None,
        slug="camper-care-self-reflection",
        version=1,
        defaults={
            "name": "Camper Care Self-Reflection",
            "description": "Auto-seeded for tests via api/tests/conftest.py.",
            "cadence": "daily",
            "schema": _CAMPER_CARE_SELF_REFLECTION_SCHEMA,
            "languages": ["en", "es"],
            "is_active": True,
            "subject_mode": "self",
            "assignment_scope": "none",
            "assignment_group_types": [],
            "author_role_filter": ["camper_care"],
            "subject_role_filter": [],
            "required_per_subject_per_period": 1,
            "subject_visible": False,
            "supports_privacy": False,
            "role": "camper_care",
            "program_type": None,
        },
    )


@pytest.fixture(autouse=True)
def _ensure_kitchen_staff_self_reflection_template(db):
    """Re-seed the kitchen_staff self-reflection template before every test (Step 7_11)."""
    ReflectionTemplate.all_objects.update_or_create(
        organization=None,
        slug="kitchen-staff-self-reflection",
        version=1,
        defaults={
            "name": "Kitchen Staff Self-Reflection",
            "description": "Auto-seeded for tests via api/tests/conftest.py.",
            "cadence": "daily",
            "schema": _KITCHEN_STAFF_SELF_REFLECTION_SCHEMA,
            "languages": ["en", "es"],
            "is_active": True,
            "subject_mode": "self",
            "assignment_scope": "none",
            "assignment_group_types": [],
            "author_role_filter": ["kitchen_staff"],
            "subject_role_filter": [],
            "required_per_subject_per_period": 1,
            "subject_visible": False,
            "supports_privacy": False,
            "role": "kitchen_staff",
            "program_type": None,
        },
    )


_LEADERSHIP_TEAM_SELF_REFLECTION_SCHEMA = {
    "fields": [
        {
            "key": "overall_period",
            "type": "single_rating",
            "required": False,
            "scale": [1, 5],
            "prompts": {"en": "How did the period feel overall?"},
            "dashboard_role": "primary_rating",
        },
        {
            "key": "wins",
            "type": "text_list",
            "required": False,
            "prompts": {"en": "What went well?"},
            "dashboard_role": "wins",
        },
        {
            "key": "improvements",
            "type": "text_list",
            "required": False,
            "prompts": {"en": "What needs more attention?"},
            "dashboard_role": "improvements",
        },
        {
            "key": "concern",
            "type": "textarea",
            "required": False,
            "prompts": {"en": "Anything to flag?"},
            "dashboard_role": "open_concern",
        },
    ],
}


_MADRICH_3_2_1_WEEKLY_SCHEMA = {
    "fields": [
        {
            "key": "wins",
            "type": "text_list",
            "required": True,
            "min_items": 3,
            "max_items": 3,
            "prompts": {"en": "Three wins from this week"},
        },
        {
            "key": "improvements",
            "type": "text_list",
            "required": True,
            "min_items": 2,
            "max_items": 2,
            "prompts": {"en": "Two things to improve next week"},
        },
        {
            "key": "question_or_concern",
            "type": "text",
            "required": True,
            "prompts": {"en": "One question or concern for your Director"},
        },
        {
            "key": "ratings",
            "type": "rating_group",
            "required": True,
            "scale": [1, 4],
            "categories": [
                {"key": "reliability_punctuality", "labels": {"en": "Reliability & Punctuality"}},
                {"key": "initiative", "labels": {"en": "Initiative"}},
                {"key": "communication", "labels": {"en": "Communication"}},
                {"key": "problem_solving", "labels": {"en": "Problem Solving"}},
                {"key": "interpersonal", "labels": {"en": "Interpersonal"}},
            ],
        },
    ],
}


@pytest.fixture(autouse=True)
def _ensure_madrich_weekly_template(db):
    """Re-seed the TBE Madrich weekly 3-2-1 template before every test (Step 7_14)."""
    ReflectionTemplate.all_objects.update_or_create(
        organization=None,
        slug="tbe-madrich-3-2-1-weekly",
        version=1,
        defaults={
            "name": "TBE Madrich Weekly 3-2-1",
            "description": "Auto-seeded for tests via api/tests/conftest.py.",
            "cadence": "weekly",
            "schema": _MADRICH_3_2_1_WEEKLY_SCHEMA,
            "languages": ["en"],
            "is_active": True,
            "subject_mode": "self",
            "assignment_scope": "none",
            "assignment_group_types": [],
            "author_role_filter": ["madrich"],
            "subject_role_filter": [],
            "required_per_subject_per_period": 1,
            "subject_visible": False,
            "supports_privacy": False,
            "role": "madrich",
            "program_type": "religious_school",
        },
    )


@pytest.fixture(autouse=True)
def _ensure_leadership_team_self_reflection_template(db):
    """Re-seed the LT self-reflection template before every test (Step 7_12)."""
    ReflectionTemplate.all_objects.update_or_create(
        organization=None,
        slug="leadership-team-self-reflection",
        version=1,
        defaults={
            "name": "Leadership Team Self-Reflection",
            "description": "Auto-seeded for tests via api/tests/conftest.py.",
            "cadence": "biweekly",
            "schema": _LEADERSHIP_TEAM_SELF_REFLECTION_SCHEMA,
            "languages": ["en", "es"],
            "is_active": True,
            "subject_mode": "self",
            "assignment_scope": "none",
            "assignment_group_types": [],
            "author_role_filter": ["leadership_team"],
            "subject_role_filter": [],
            "required_per_subject_per_period": 1,
            "subject_visible": False,
            "supports_privacy": True,
            "role": "leadership_team",
            "program_type": None,
        },
    )


# ---------------------------------------------------------------------------
# Step 7_21 — TemplateAssignment auto-seeding for the seeded role templates
# ---------------------------------------------------------------------------


_AUTOSEED_ROLE_SLUGS: tuple[tuple[str, str], ...] = (
    ("counselor", "counselor-self-reflection"),
    ("junior_counselor", "counselor-self-reflection"),
    ("unit_head", "unit-head-self-reflection"),
    ("camper_care", "camper-care-self-reflection"),
    ("kitchen_staff", "kitchen-staff-self-reflection"),
    ("leadership_team", "leadership-team-self-reflection"),
    ("madrich", "tbe-madrich-3-2-1-weekly"),
)


def _seed_role_assignments_for_program(program: Program) -> None:
    """Create one role-targeted assignment per seeded role template.

    Idempotent: ``get_or_create`` keyed on (program, template, role) so
    repeat invocations (e.g. fixtures that ``save()`` the same Program
    twice) don't blow up. Start_date is anchored far enough in the past
    to be safe for any test — programs in the future, in the past, or
    aligned with "today" should all see the assignment as active.
    """
    if program.organization_id is None:
        return
    anchor = program.start_date or date.today()
    start = min(anchor, date.today()) - timedelta(days=365)
    for role, slug in _AUTOSEED_ROLE_SLUGS:
        template = ReflectionTemplate.all_objects.filter(
            slug=slug, organization__isnull=True,
        ).first()
        if template is None:
            continue
        TemplateAssignment.all_objects.get_or_create(
            organization=program.organization,
            program=program,
            template=template,
            target_type=TemplateAssignment.TargetType.ROLE,
            target_payload={"role": role},
            defaults={
                "start_date": start,
                "status": TemplateAssignment.Status.ACTIVE,
                "is_required": True,
            },
        )


def _on_program_saved(sender, instance, created, **kwargs):
    del sender, kwargs
    if not created:
        return
    _seed_role_assignments_for_program(instance)


@pytest.fixture(autouse=True)
def _autobind_role_assignments_to_new_programs(db):
    """Auto-bind seeded role templates to any ``Program`` created in a test.

    Step 7_21 made the per-role helpers route through
    ``TemplateAssignment``; tests that previously relied on the seeded
    template alone now need an active assignment binding it to the
    program. Hooking ``post_save`` keeps existing fixtures unchanged.
    Tests that need the "no assignment" empty-state should delete the
    auto-created rows.
    """
    post_save.connect(_on_program_saved, sender=Program)
    yield
    post_save.disconnect(_on_program_saved, sender=Program)


# ---------------------------------------------------------------------------
# Helper for tests that build their own (non-seeded) ReflectionTemplate
# ---------------------------------------------------------------------------


def make_active_assignment(
    *,
    template,
    program,
    target_role: str | None = None,
    assignment_group=None,
    is_required: bool = True,
):
    """Create a Step 7_21-style TemplateAssignment row for a test template.

    Tests that mint their own ``ReflectionTemplate`` (typically the
    counselor camper-reflection template, which is org-scoped and not
    seeded by the autouse fixtures above) call this to make the
    template visible to the per-role dashboards' resolvers.

    The window is anchored a year before "today" / the program's
    start_date so the assignment is always live regardless of the
    program's date span.
    """
    anchor = program.start_date or date.today()
    start = min(anchor, date.today()) - timedelta(days=365)
    if assignment_group is not None:
        return TemplateAssignment.all_objects.create(
            organization=program.organization,
            program=program,
            template=template,
            target_type=TemplateAssignment.TargetType.ASSIGNMENT_GROUP,
            target_payload={},
            assignment_group=assignment_group,
            start_date=start,
            status=TemplateAssignment.Status.ACTIVE,
            is_required=is_required,
        )
    role = target_role or (
        (template.author_role_filter or [None])[0]
        or template.role
        or "counselor"
    )
    return TemplateAssignment.all_objects.create(
        organization=program.organization,
        program=program,
        template=template,
        target_type=TemplateAssignment.TargetType.ROLE,
        target_payload={"role": role},
        start_date=start,
        status=TemplateAssignment.Status.ACTIVE,
        is_required=is_required,
    )
