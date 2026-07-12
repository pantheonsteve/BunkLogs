"""Read-only freeze for deprecated legacy models (strangler-fig step 6_1).

Verifies that when ``BUNKLOGS_LEGACY_READ_ONLY`` is enabled (production default),
instance writes raise, reads still work, and bulk ``QuerySet`` operations bypass
the guard so operational tooling (e.g. scrub_pii) keeps working.
"""

from datetime import date

import pytest
from django.test import override_settings

from bunk_logs.bunks.models import Session
from bunk_logs.utils.legacy import LegacyModelReadOnlyError

from .factories import StaffLogFactory


def _make_session():
    return Session(name="S1", start_date=date(2026, 6, 1), end_date=date(2026, 8, 1))


@pytest.mark.django_db
@override_settings(BUNKLOGS_LEGACY_READ_ONLY=True)
def test_save_blocked_when_read_only():
    with pytest.raises(LegacyModelReadOnlyError):
        _make_session().save()


@pytest.mark.django_db
@override_settings(BUNKLOGS_LEGACY_READ_ONLY=True)
def test_custom_save_model_blocked_when_read_only():
    # StaffLog defines its own save(); the guard must fire before validation.
    with pytest.raises(LegacyModelReadOnlyError):
        StaffLogFactory.build().save()


@pytest.mark.django_db
def test_writes_allowed_by_default():
    # Test/dev settings leave the flag unset, so fixtures and seeding still work.
    session = _make_session()
    session.save()
    assert Session.objects.filter(pk=session.pk).exists()


@pytest.mark.django_db
def test_reads_and_bulk_ops_work_under_read_only():
    session = _make_session()
    session.save()  # created while writable

    with override_settings(BUNKLOGS_LEGACY_READ_ONLY=True):
        # Reads still work.
        assert Session.objects.get(pk=session.pk).name == "S1"
        # Bulk QuerySet ops intentionally bypass the per-instance guard.
        Session.objects.filter(pk=session.pk).update(name="S1-renamed")

    session.refresh_from_db()
    assert session.name == "S1-renamed"
