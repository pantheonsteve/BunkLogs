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
