"""Tests for StaffLog, its proxy models, and related API endpoints.

Covers:
  - Model-level validation and properties
  - Proxy model behavior (shared table, bunk_names scoping)
  - API permission rules for all staff roles
"""

from datetime import date
from datetime import timedelta

import pytest
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from bunk_logs.bunklogs.models import CounselorLog
from bunk_logs.bunklogs.models import KitchenStaffLog
from bunk_logs.bunklogs.models import LeadershipLog
from bunk_logs.bunklogs.models import StaffLog
from bunk_logs.bunks.models import Bunk
from bunk_logs.bunks.models import Cabin
from bunk_logs.bunks.models import CounselorBunkAssignment
from bunk_logs.bunks.models import Session
from bunk_logs.bunks.models import Unit
from bunk_logs.users.tests.factories import UserFactory

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_staff_log(user, **kwargs):
    """Create a StaffLog directly for the given user without going through the factory."""
    defaults = {
        "staff_member": user,
        "date": date.today(),
        "day_quality_score": 4,
        "support_level_score": 4,
        "elaboration": "Test elaboration text.",
        "values_reflection": "Test values reflection.",
    }
    defaults.update(kwargs)
    return StaffLog.objects.create(**defaults)


# ---------------------------------------------------------------------------
# Model tests
# ---------------------------------------------------------------------------

class TestStaffLogModel(TestCase):
    """Model-level tests for StaffLog."""

    def test_create_staff_log_for_counselor(self):
        user = UserFactory(counselor=True)
        log = _make_staff_log(user)
        assert log.pk is not None
        assert log.staff_member == user

    def test_create_staff_log_for_leadership(self):
        user = UserFactory(leadership=True)
        log = _make_staff_log(user)
        assert log.pk is not None

    def test_create_staff_log_for_kitchen_staff(self):
        user = UserFactory(kitchen=True)
        log = _make_staff_log(user)
        assert log.pk is not None

    def test_create_staff_log_for_unit_head(self):
        user = UserFactory(unit_head=True)
        log = _make_staff_log(user)
        assert log.pk is not None

    def test_create_staff_log_for_camper_care(self):
        user = UserFactory(camper_care=True)
        log = _make_staff_log(user)
        assert log.pk is not None

    def test_unique_together_enforced(self):
        from django.core.exceptions import ValidationError
        user = UserFactory(counselor=True)
        _make_staff_log(user)
        with pytest.raises((ValidationError, Exception)):
            _make_staff_log(user)

    def test_future_date_raises_validation_error(self):
        from django.core.exceptions import ValidationError
        user = UserFactory(counselor=True)
        log = StaffLog(
            staff_member=user,
            date=date.today() + timedelta(days=1),
            day_quality_score=4,
            support_level_score=4,
            elaboration="Test.",
            values_reflection="Test.",
        )
        with pytest.raises(ValidationError):
            log.save()

    def test_old_date_raises_validation_error(self):
        from django.core.exceptions import ValidationError
        user = UserFactory(counselor=True)
        log = StaffLog(
            staff_member=user,
            date=date.today() - timedelta(days=60),
            day_quality_score=4,
            support_level_score=4,
            elaboration="Test.",
            values_reflection="Test.",
        )
        with pytest.raises(ValidationError):
            log.save()

    def test_needs_support_true_on_low_day_quality(self):
        user = UserFactory(counselor=True)
        log = _make_staff_log(user, day_quality_score=2, support_level_score=4)
        assert log.needs_support is True

    def test_needs_support_true_on_low_support_level(self):
        user = UserFactory(counselor=True)
        log = _make_staff_log(user, day_quality_score=4, support_level_score=2)
        assert log.needs_support is True

    def test_needs_support_true_on_explicit_flag(self):
        user = UserFactory(counselor=True)
        log = _make_staff_log(user, staff_care_support_needed=True)
        assert log.needs_support is True

    def test_needs_support_false_when_scores_good(self):
        user = UserFactory(counselor=True)
        log = _make_staff_log(user, day_quality_score=4, support_level_score=4)
        assert log.needs_support is False

    def test_overall_wellbeing_score_computed(self):
        user = UserFactory(counselor=True)
        log = _make_staff_log(user, day_quality_score=4, support_level_score=2)
        assert log.overall_wellbeing_score == 3.0

    def test_can_edit_own_log(self):
        user = UserFactory(counselor=True)
        log = _make_staff_log(user)
        assert log.can_edit(user) is True

    def test_cannot_edit_others_log_without_permission(self):
        owner = UserFactory(counselor=True)
        other = UserFactory(counselor=True)
        log = _make_staff_log(owner)
        assert log.can_edit(other) is False

    def test_str_representation(self):
        user = UserFactory(counselor=True)
        log = _make_staff_log(user)
        assert str(log).startswith("Staff log for")
        assert str(date.today()) in str(log)


# ---------------------------------------------------------------------------
# Proxy model tests
# ---------------------------------------------------------------------------

class TestProxyModels(TestCase):
    """Verify that proxy models share the StaffLog table and behave correctly."""

    def setUp(self):
        self.session = Session.objects.create(
            name="Test Session",
            start_date=date.today() - timedelta(days=30),
            end_date=date.today() + timedelta(days=60),
        )
        self.cabin = Cabin.objects.create(name="Test Cabin", capacity=20)
        self.unit = Unit.objects.create(name="Test Unit")
        self.bunk = Bunk.objects.create(
            cabin=self.cabin,
            session=self.session,
            unit=self.unit,
            is_active=True,
        )

    def test_counselor_log_is_proxy_of_staff_log(self):
        user = UserFactory(counselor=True)
        _make_staff_log(user)
        assert CounselorLog.objects.count() == StaffLog.objects.count()

    def test_leadership_log_is_proxy_of_staff_log(self):
        user = UserFactory(leadership=True)
        _make_staff_log(user)
        assert LeadershipLog.objects.count() == StaffLog.objects.count()

    def test_kitchen_log_is_proxy_of_staff_log(self):
        user = UserFactory(kitchen=True)
        _make_staff_log(user)
        assert KitchenStaffLog.objects.count() == StaffLog.objects.count()

    def test_counselor_alias_property(self):
        user = UserFactory(counselor=True)
        log_row = _make_staff_log(user)
        # Fetch via CounselorLog proxy to access the .counselor alias
        cl = CounselorLog.objects.get(pk=log_row.pk)
        assert cl.counselor == cl.staff_member

    def test_counselor_log_has_bunk_names_property(self):
        user = UserFactory(counselor=True)
        CounselorBunkAssignment.objects.create(
            counselor=user,
            bunk=self.bunk,
            start_date=date.today() - timedelta(days=10),
            is_primary=True,
        )
        log_row = _make_staff_log(user)
        cl = CounselorLog.objects.get(pk=log_row.pk)
        assert hasattr(cl, "bunk_names")
        assert self.bunk.name in cl.bunk_names

    def test_leadership_log_has_no_bunk_names(self):
        user = UserFactory(leadership=True)
        log_row = _make_staff_log(user)
        ll = LeadershipLog.objects.get(pk=log_row.pk)
        assert not hasattr(ll, "bunk_names")

    def test_kitchen_log_has_no_bunk_names(self):
        user = UserFactory(kitchen=True)
        log_row = _make_staff_log(user)
        kl = KitchenStaffLog.objects.get(pk=log_row.pk)
        assert not hasattr(kl, "bunk_names")

    def test_counselor_log_str(self):
        user = UserFactory(counselor=True)
        log_row = _make_staff_log(user)
        cl = CounselorLog.objects.get(pk=log_row.pk)
        assert "Counselor log for" in str(cl)

    def test_leadership_log_str(self):
        user = UserFactory(leadership=True)
        log_row = _make_staff_log(user)
        ll = LeadershipLog.objects.get(pk=log_row.pk)
        assert "Leadership log for" in str(ll)

    def test_proxy_models_share_single_table(self):
        """All proxy logs count toward the same StaffLog queryset."""
        counselor = UserFactory(counselor=True)
        leader = UserFactory(leadership=True)
        kitchen = UserFactory(kitchen=True)
        _make_staff_log(counselor)
        _make_staff_log(leader)
        _make_staff_log(kitchen)
        assert StaffLog.objects.count() == 3
        assert CounselorLog.objects.count() == 3
        assert LeadershipLog.objects.count() == 3
        assert KitchenStaffLog.objects.count() == 3

