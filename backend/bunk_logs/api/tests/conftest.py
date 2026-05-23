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
"""
from __future__ import annotations

import pytest

from bunk_logs.core.models import ReflectionTemplate

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
                {"key": "reliability_punctuality", "label": {"en": "Reliability & Punctuality"}},
                {"key": "initiative", "label": {"en": "Initiative"}},
                {"key": "communication", "label": {"en": "Communication"}},
                {"key": "problem_solving", "label": {"en": "Problem Solving"}},
                {"key": "interpersonal", "label": {"en": "Interpersonal"}},
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
