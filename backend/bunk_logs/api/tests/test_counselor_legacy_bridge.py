"""Step 7_6g: backfill + dual-write tests for legacy ``StaffLog`` rows.

Covers:

* :func:`sync_staff_log_to_reflection` idempotency, skip semantics, and
  field mapping.
* ``backfill_counselor_logs`` management command in dry-run and apply
  modes, including the deterministic ``client_submission_id``.
* The ``post_save`` signal that dual-writes new StaffLog rows into
  Reflection on commit, including the kill-switch setting.

These tests treat the seeded ``counselor-self-reflection`` template
(migration 0029) as the resolution target. The seed is a global
``organization IS NULL`` row so any org we create in fixtures resolves
to it without further setup.
"""
from __future__ import annotations

from datetime import date
from datetime import timedelta
from io import StringIO

import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.management import call_command
from django.db import transaction
from django.test.utils import override_settings
from django.utils import timezone


def _today() -> date:
    """Real "today" — must match what ``StaffLog.clean()`` checks against.

    Hard-coding a future date breaks the legacy validator (no future
    dates), so we anchor all test rows around the actual system date.
    """
    return timezone.localtime().date()

from bunk_logs.api.counselor.legacy_mapping import client_submission_id_for_staff_log
from bunk_logs.api.counselor.legacy_mapping import sync_staff_log_to_reflection
from bunk_logs.bunklogs.models import StaffLog
from bunk_logs.core.models import AuditEvent
from bunk_logs.core.models import Membership
from bunk_logs.core.models import Organization
from bunk_logs.core.models import Person
from bunk_logs.core.models import Program
from bunk_logs.core.models import Reflection

User = get_user_model()

# The seeded ``counselor-self-reflection`` template is restored before
# every test by the autouse fixture in ``api/tests/conftest.py``; see
# that file for the rationale (TransactionTestCase flush would wipe it).


@pytest.fixture(autouse=True)
def _clear_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def org(db):
    return Organization.objects.create(name="Bridge Camp", slug="bridge-camp")


@pytest.fixture
def program(org):
    return Program.all_objects.create(
        organization=org,
        name="Bridge Camp Summer 2026",
        slug="bridge-summer-2026",
        program_type="summer_camp",
        start_date=date(2026, 6, 1),
        end_date=date(2026, 8, 31),
    )


@pytest.fixture
def counselor_user():
    return User.objects.create_user(email="bridge-counselor@bridge.test", password="pw")


@pytest.fixture
def counselor_person(org, counselor_user):
    return Person.all_objects.create(
        organization=org,
        first_name="Lee",
        last_name="Bridge",
        user=counselor_user,
    )


@pytest.fixture
def counselor_membership(program, counselor_person):
    return Membership.all_objects.create(
        program=program,
        person=counselor_person,
        role="counselor",
        is_active=True,
    )


def _staff_log(user, **overrides):
    # Default to "yesterday" so we sit safely inside the legacy
    # validator's allowed window (no future, no older than 30 days).
    defaults = {
        "staff_member": user,
        "date": _today() - timedelta(days=1),
        "day_quality_score": 4,
        "support_level_score": 5,
        "elaboration": "Good day; bunk hike went great.",
        "day_off": False,
        "staff_care_support_needed": False,
        "values_reflection": "Modeled curiosity and kindness today.",
    }
    defaults.update(overrides)
    return StaffLog.objects.create(**defaults)


# ---------------------------------------------------------------------------
# sync_staff_log_to_reflection — direct mapper tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_sync_maps_fields_onto_seeded_schema_keys(
    org, counselor_user, counselor_person, counselor_membership,
):
    log = _staff_log(counselor_user)

    result = sync_staff_log_to_reflection(log)
    assert result.action == "created", result.reason

    reflection = Reflection.all_objects.get(id=result.reflection_id)
    assert reflection.author == counselor_person
    assert reflection.subject == counselor_person
    assert reflection.period_start == log.date
    assert reflection.period_end == log.date
    assert reflection.is_complete is True
    assert reflection.team_visibility == Reflection.TeamVisibility.TEAM

    answers = reflection.answers
    # Schema-mapped keys
    assert answers["day_off"] is False
    assert answers["overall_day"] == 4
    assert answers["concern"] == "Good day; bunk hike went great."
    assert answers["wins"] == []
    assert answers["improvements"] == []
    # Provenance + lossless legacy fields
    assert answers["_legacy_staff_log_id"] == log.id
    assert answers["support_level_score"] == 5
    assert answers["values_reflection"] == "Modeled curiosity and kindness today."
    assert answers["staff_care_support_needed"] is False


@pytest.mark.django_db
def test_sync_preserves_day_off_flag(
    org, counselor_user, counselor_person, counselor_membership,
):
    # ``day_off=True`` short-circuits the elaboration/values *clean()*
    # requirement in ``StaffLog`` but the field-level ``blank=False`` on
    # CharField still applies, so we keep non-empty placeholder text.
    # The mapper must preserve the day_off bool regardless.
    log = _staff_log(
        counselor_user, day_off=True,
        elaboration="(day off)", values_reflection="(day off)",
        day_quality_score=3, support_level_score=3,
    )
    result = sync_staff_log_to_reflection(log)
    assert result.action == "created"
    assert Reflection.all_objects.get(id=result.reflection_id).answers["day_off"] is True


@pytest.mark.django_db
def test_sync_is_idempotent_on_re_run(
    org, counselor_user, counselor_person, counselor_membership,
):
    log = _staff_log(counselor_user)
    first = sync_staff_log_to_reflection(log)
    assert first.action == "created"

    second = sync_staff_log_to_reflection(log)
    assert second.action == "unchanged"
    assert second.reflection_id == first.reflection_id
    assert Reflection.all_objects.filter(
        client_submission_id=client_submission_id_for_staff_log(log.id),
    ).count() == 1


@pytest.mark.django_db
def test_sync_updates_when_staff_log_changes(
    org, counselor_user, counselor_person, counselor_membership,
):
    log = _staff_log(counselor_user, elaboration="initial")
    first = sync_staff_log_to_reflection(log)
    assert first.action == "created"

    log.elaboration = "edited later"
    log.day_quality_score = 5
    log.save()
    second = sync_staff_log_to_reflection(log)
    assert second.action == "updated"
    assert second.reflection_id == first.reflection_id

    refreshed = Reflection.all_objects.get(id=first.reflection_id)
    assert refreshed.answers["concern"] == "edited later"
    assert refreshed.answers["overall_day"] == 5


@pytest.mark.django_db
def test_sync_emits_audit_event_on_create(
    org, counselor_user, counselor_person, counselor_membership,
):
    log = _staff_log(counselor_user)
    sync_staff_log_to_reflection(log)
    assert AuditEvent.all_objects.filter(
        event_type=AuditEvent.EventType.CREATED,
        content_type="reflection",
    ).exists()


@pytest.mark.django_db
def test_sync_skips_when_no_person_for_user(db, counselor_user):
    """A User with no Person row is silently skipped (unmigrated staff)."""
    log = _staff_log(counselor_user)
    result = sync_staff_log_to_reflection(log)
    assert result.action == "skipped"
    assert result.reason == "no_person_for_user"
    assert Reflection.all_objects.count() == 0


@pytest.mark.django_db
def test_sync_skips_when_no_counselor_membership(
    org, counselor_user, counselor_person,
):
    """A Person without a counselor Membership is skipped (e.g. kitchen)."""
    log = _staff_log(counselor_user)
    result = sync_staff_log_to_reflection(log)
    assert result.action == "skipped"
    assert result.reason == "no_active_counselor_membership"


@pytest.mark.django_db
def test_sync_picks_junior_counselor_role_too(
    org, program, counselor_user, counselor_person,
):
    """``junior_counselor`` is treated as a counselor for the bridge."""
    Membership.all_objects.create(
        program=program, person=counselor_person,
        role="junior_counselor", is_active=True,
    )
    log = _staff_log(counselor_user)
    result = sync_staff_log_to_reflection(log)
    assert result.action == "created", result.reason


# ---------------------------------------------------------------------------
# Management command tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_backfill_command_dry_run_makes_no_writes(
    org, counselor_user, counselor_person, counselor_membership,
):
    _staff_log(counselor_user)
    _staff_log(counselor_user, date=_today() - timedelta(days=2))
    assert Reflection.all_objects.count() == 0

    out = StringIO()
    call_command("backfill_counselor_logs", stdout=out)
    text = out.getvalue()
    assert "Dry run only" in text
    assert "created: 2" in text
    # Nothing actually persisted.
    assert Reflection.all_objects.count() == 0


@pytest.mark.django_db
def test_backfill_command_apply_persists_writes(
    org, counselor_user, counselor_person, counselor_membership,
):
    log1 = _staff_log(counselor_user)
    log2 = _staff_log(counselor_user, date=_today() - timedelta(days=2))

    out = StringIO()
    call_command("backfill_counselor_logs", "--apply", stdout=out)
    assert "created: 2" in out.getvalue()

    csids = {
        client_submission_id_for_staff_log(log1.id),
        client_submission_id_for_staff_log(log2.id),
    }
    assert (
        set(Reflection.all_objects.values_list("client_submission_id", flat=True))
        == csids
    )


@pytest.mark.django_db
def test_backfill_command_replay_marks_rows_unchanged(
    org, counselor_user, counselor_person, counselor_membership,
):
    _staff_log(counselor_user)
    call_command("backfill_counselor_logs", "--apply", stdout=StringIO())
    assert Reflection.all_objects.count() == 1

    out = StringIO()
    call_command("backfill_counselor_logs", "--apply", stdout=out)
    text = out.getvalue()
    assert "unchanged: 1" in text
    assert "created: 0" in text
    # No duplicates introduced.
    assert Reflection.all_objects.count() == 1


@pytest.mark.django_db
def test_backfill_command_date_range_filter(
    org, counselor_user, counselor_person, counselor_membership,
):
    today = _today()
    _staff_log(counselor_user, date=today - timedelta(days=10))
    _staff_log(counselor_user, date=today - timedelta(days=5))
    _staff_log(counselor_user, date=today - timedelta(days=1))

    target = today - timedelta(days=5)
    out = StringIO()
    call_command(
        "backfill_counselor_logs", "--apply",
        "--since", (target - timedelta(days=1)).isoformat(),
        "--until", (target + timedelta(days=1)).isoformat(),
        stdout=out,
    )
    assert "created: 1" in out.getvalue()
    assert Reflection.all_objects.count() == 1


@pytest.mark.django_db
def test_backfill_command_reports_skip_reasons(
    db, counselor_user,
):
    """A run with mostly orphan StaffLog rows surfaces skip reasons in the summary."""
    _staff_log(counselor_user)
    out = StringIO()
    call_command("backfill_counselor_logs", "--apply", stdout=out)
    text = out.getvalue()
    assert "skipped: 1" in text
    assert "no_person_for_user: 1" in text


# ---------------------------------------------------------------------------
# Dual-write signal tests
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Dual-write signal tests
# ---------------------------------------------------------------------------
#
# The signal uses ``transaction.on_commit`` so the mirror only fires after
# the outer transaction wrapping the StaffLog save commits. Pytest's
# ``@django_db(transaction=True)`` mode runs in autocommit BUT fixture
# setup still runs inside an implicit transaction — so the callback
# never fires before the test body exits. We work around that by
# explicitly wrapping the saves in our own ``transaction.atomic()``
# block so we control the commit boundary precisely.


@pytest.mark.django_db(transaction=True)
def test_dual_write_signal_mirrors_on_commit(
    org, counselor_user, counselor_person, counselor_membership,
):
    """Saving a StaffLog through the ORM triggers a Reflection mirror."""
    assert Reflection.all_objects.count() == 0
    with transaction.atomic():
        log = _staff_log(counselor_user)
    # post_save → on_commit fires on transaction exit.
    reflections = Reflection.all_objects.filter(
        client_submission_id=client_submission_id_for_staff_log(log.id),
    )
    assert reflections.count() == 1, list(reflections.values())
    mirrored = reflections.get()
    assert mirrored.answers["_legacy_staff_log_id"] == log.id
    assert mirrored.answers["overall_day"] == log.day_quality_score


@pytest.mark.django_db(transaction=True)
def test_dual_write_signal_updates_on_subsequent_save(
    org, counselor_user, counselor_person, counselor_membership,
):
    with transaction.atomic():
        log = _staff_log(counselor_user)
    assert Reflection.all_objects.count() == 1

    with transaction.atomic():
        log.elaboration = "now updated"
        log.day_quality_score = 5
        log.save()

    reflection = Reflection.all_objects.get(
        client_submission_id=client_submission_id_for_staff_log(log.id),
    )
    assert reflection.answers["concern"] == "now updated"
    assert reflection.answers["overall_day"] == 5
    assert Reflection.all_objects.count() == 1


@pytest.mark.django_db(transaction=True)
@override_settings(BUNKLOGS_DUAL_WRITE_REFLECTION=False)
def test_dual_write_signal_respects_kill_switch(
    org, counselor_user, counselor_person, counselor_membership,
):
    """``BUNKLOGS_DUAL_WRITE_REFLECTION=False`` disables the mirror entirely."""
    with transaction.atomic():
        _staff_log(counselor_user)
    assert Reflection.all_objects.count() == 0


@pytest.mark.django_db(transaction=True)
def test_dual_write_signal_swallows_mapper_errors(
    db, counselor_user,
):
    """A StaffLog without prerequisites does NOT block legacy persistence."""
    # No Person, no Membership — the mapper will skip cleanly. Verify
    # that the StaffLog row still persisted (i.e. the signal didn't
    # break the implicit transaction commit).
    with transaction.atomic():
        log = _staff_log(counselor_user)
    assert StaffLog.objects.filter(id=log.id).exists()
    assert Reflection.all_objects.count() == 0
