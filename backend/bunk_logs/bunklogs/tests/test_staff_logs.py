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


# ---------------------------------------------------------------------------
# API permission tests
# ---------------------------------------------------------------------------

class TestStaffLogAPI(TestCase):
    """API permission tests for /api/v1/counselorlogs/."""

    def setUp(self):
        self.client = APIClient()
        self.list_url = reverse("api:counselorlog-list")

        self.admin = UserFactory(admin=True, is_staff=True)
        self.counselor1 = UserFactory(counselor=True)
        self.counselor2 = UserFactory(counselor=True)
        self.leader = UserFactory(leadership=True)
        self.kitchen = UserFactory(kitchen=True)
        self.unit_head = UserFactory(unit_head=True)
        self.camper_care = UserFactory(camper_care=True)

        # Pre-existing log for counselor1
        self.counselor1_log = _make_staff_log(self.counselor1)
        # Pre-existing log for leader
        self.leader_log = _make_staff_log(self.leader)
        # Pre-existing log for kitchen staff
        self.kitchen_log = _make_staff_log(self.kitchen)

    def _post_payload(self, override_date=None):
        """Return a valid POST payload for today (or an explicit date)."""
        return {
            "date": str(override_date or date.today()),
            "day_quality_score": 4,
            "support_level_score": 4,
            "elaboration": "Had a great day.",
            "values_reflection": "Team showed great teamwork.",
            "day_off": False,
            "staff_care_support_needed": False,
        }

    # --- Create (POST) ---

    def test_counselor_can_create_own_log(self):
        new_counselor = UserFactory(counselor=True)
        self.client.force_authenticate(user=new_counselor)
        response = self.client.post(self.list_url, self._post_payload(), format="json")
        assert response.status_code == status.HTTP_201_CREATED
        assert StaffLog.objects.filter(staff_member=new_counselor).exists()

    def test_leadership_can_create_own_log(self):
        new_leader = UserFactory(leadership=True)
        self.client.force_authenticate(user=new_leader)
        response = self.client.post(self.list_url, self._post_payload(), format="json")
        assert response.status_code == status.HTTP_201_CREATED
        assert StaffLog.objects.filter(staff_member=new_leader).exists()

    def test_kitchen_staff_can_create_own_log(self):
        new_kitchen = UserFactory(kitchen=True)
        self.client.force_authenticate(user=new_kitchen)
        response = self.client.post(self.list_url, self._post_payload(), format="json")
        assert response.status_code == status.HTTP_201_CREATED
        assert StaffLog.objects.filter(staff_member=new_kitchen).exists()

    def test_duplicate_log_on_same_date_rejected(self):
        """Second log for the same staff member on the same date must be rejected."""
        self.client.force_authenticate(user=self.counselor1)
        response = self.client.post(self.list_url, self._post_payload(), format="json")
        # counselor1 already has a log for today from setUp
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_unauthenticated_cannot_create(self):
        response = self.client.post(self.list_url, self._post_payload(), format="json")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    # --- List (GET) ---

    def test_admin_can_list_all_logs(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.get(self.list_url)
        assert response.status_code == status.HTTP_200_OK
        ids_returned = {r["id"] for r in response.data["results"]}
        assert self.counselor1_log.pk in ids_returned
        assert self.leader_log.pk in ids_returned
        assert self.kitchen_log.pk in ids_returned

    def test_counselor_sees_only_own_logs(self):
        self.client.force_authenticate(user=self.counselor1)
        response = self.client.get(self.list_url)
        assert response.status_code == status.HTTP_200_OK
        ids_returned = {r["id"] for r in response.data["results"]}
        assert self.counselor1_log.pk in ids_returned
        # Should NOT see the leader's or kitchen's logs
        assert self.leader_log.pk not in ids_returned
        assert self.kitchen_log.pk not in ids_returned

    def test_leadership_sees_only_own_logs(self):
        self.client.force_authenticate(user=self.leader)
        response = self.client.get(self.list_url)
        assert response.status_code == status.HTTP_200_OK
        ids_returned = {r["id"] for r in response.data["results"]}
        assert self.leader_log.pk in ids_returned
        assert self.counselor1_log.pk not in ids_returned
        assert self.kitchen_log.pk not in ids_returned

    def test_kitchen_staff_sees_only_own_logs(self):
        self.client.force_authenticate(user=self.kitchen)
        response = self.client.get(self.list_url)
        assert response.status_code == status.HTTP_200_OK
        ids_returned = {r["id"] for r in response.data["results"]}
        assert self.kitchen_log.pk in ids_returned
        assert self.counselor1_log.pk not in ids_returned
        assert self.leader_log.pk not in ids_returned

    # --- Retrieve (GET detail) ---

    def test_counselor_can_retrieve_own_log(self):
        self.client.force_authenticate(user=self.counselor1)
        url = reverse("api:counselorlog-detail", kwargs={"pk": self.counselor1_log.pk})
        response = self.client.get(url)
        assert response.status_code == status.HTTP_200_OK

    # --- Update (PATCH) ---

    def test_counselor_can_update_own_log_same_day(self):
        self.client.force_authenticate(user=self.counselor1)
        url = reverse("api:counselorlog-detail", kwargs={"pk": self.counselor1_log.pk})
        response = self.client.patch(url, {"elaboration": "Updated text."}, format="json")
        assert response.status_code == status.HTTP_200_OK

    def test_leadership_can_update_own_log_same_day(self):
        self.client.force_authenticate(user=self.leader)
        url = reverse("api:counselorlog-detail", kwargs={"pk": self.leader_log.pk})
        response = self.client.patch(url, {"elaboration": "Updated leadership text."}, format="json")
        assert response.status_code == status.HTTP_200_OK

    def test_kitchen_staff_can_update_own_log_same_day(self):
        self.client.force_authenticate(user=self.kitchen)
        url = reverse("api:counselorlog-detail", kwargs={"pk": self.kitchen_log.pk})
        response = self.client.patch(url, {"elaboration": "Updated kitchen text."}, format="json")
        assert response.status_code == status.HTTP_200_OK

    def test_counselor_cannot_update_log_next_day(self):
        # Backdate created_at so the log appears to have been made yesterday
        from django.utils import timezone
        StaffLog.objects.filter(pk=self.counselor1_log.pk).update(
            created_at=timezone.now() - timedelta(days=1),
        )
        self.client.force_authenticate(user=self.counselor1)
        url = reverse("api:counselorlog-detail", kwargs={"pk": self.counselor1_log.pk})
        response = self.client.patch(url, {"elaboration": "Too late."}, format="json")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_admin_can_update_any_log(self):
        self.client.force_authenticate(user=self.admin)
        url = reverse("api:counselorlog-detail", kwargs={"pk": self.counselor1_log.pk})
        response = self.client.patch(url, {"elaboration": "Admin update."}, format="json")
        assert response.status_code == status.HTTP_200_OK

    def test_counselor_cannot_update_another_counselors_log(self):
        self.client.force_authenticate(user=self.counselor2)
        url = reverse("api:counselorlog-detail", kwargs={"pk": self.counselor1_log.pk})
        response = self.client.patch(url, {"elaboration": "Sneaky edit."}, format="json")
        # counselor2 cannot see counselor1's log so should get 404
        assert response.status_code in (status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND)

    def test_unit_head_cannot_edit_staff_log(self):
        self.client.force_authenticate(user=self.unit_head)
        url = reverse("api:counselorlog-detail", kwargs={"pk": self.counselor1_log.pk})
        response = self.client.patch(url, {"elaboration": "Unit head edit attempt."}, format="json")
        assert response.status_code in (status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND)

    # --- Serializer field checks ---

    def test_response_includes_staff_member_fields(self):
        self.client.force_authenticate(user=self.counselor1)
        url = reverse("api:counselorlog-detail", kwargs={"pk": self.counselor1_log.pk})
        response = self.client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert "staff_member" in response.data
        assert "staff_member_role" in response.data
        assert "staff_member_first_name" in response.data

    def test_response_includes_legacy_counselor_fields(self):
        """Backward-compat: frontend still expects counselor_* fields."""
        self.client.force_authenticate(user=self.counselor1)
        url = reverse("api:counselorlog-detail", kwargs={"pk": self.counselor1_log.pk})
        response = self.client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert "counselor" in response.data
        assert "counselor_first_name" in response.data
        assert "counselor_last_name" in response.data
        assert "counselor_email" in response.data

    def test_date_filter_query_param(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.get(self.list_url, {"date": str(date.today())})
        assert response.status_code == status.HTTP_200_OK
        # All setUp logs were created for today
        assert len(response.data["results"]) >= 3

    def test_invalid_date_filter_does_not_crash(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.get(self.list_url, {"date": "not-a-date"})
        assert response.status_code == status.HTTP_200_OK


# ---------------------------------------------------------------------------
# Performance regression tests
# ---------------------------------------------------------------------------

class TestStaffLogQueryCount(TestCase):
    """Guard against the N+1 in StaffLogSerializer that caused 502 timeouts.

    Before the fix, ``get_bunk_assignments`` and ``get_unit_assignment_name``
    each issued a fresh DB query per StaffLog row when the list endpoint
    returned more than a handful of rows. With ~30+ logs that exceeded
    Render's upstream timeout. These tests pin the query count so that
    regressions are caught immediately.
    """

    def setUp(self):
        from datetime import timedelta

        self.client = APIClient()
        self.list_url = reverse("api:counselorlog-list")
        self.admin = UserFactory(admin=True, is_staff=True)
        self.counselor = UserFactory(counselor=True)

        # Set up a bunk assignment for the counselor so get_bunk_assignments
        # has data to traverse on every row (worst case for the old N+1).
        self.session = Session.objects.create(
            name="Perf Session",
            start_date=date.today() - timedelta(days=60),
            end_date=date.today() + timedelta(days=60),
        )
        self.cabin = Cabin.objects.create(name="Perf Cabin", capacity=10)
        self.unit = Unit.objects.create(name="Perf Unit")
        self.bunk = Bunk.objects.create(
            cabin=self.cabin, session=self.session, unit=self.unit, is_active=True,
        )
        CounselorBunkAssignment.objects.create(
            counselor=self.counselor,
            bunk=self.bunk,
            start_date=date.today() - timedelta(days=30),
            is_primary=True,
        )

        # Create 20 logs across different dates so a fresh per-row query
        # would multiply visibly.
        self.log_count = 20
        for i in range(self.log_count):
            _make_staff_log(self.counselor, date=date.today() - timedelta(days=i))

    def test_staff_member_filter_query_count_is_bounded(self):
        """Listing logs for a single staff member must not be O(N)."""
        self.client.force_authenticate(user=self.admin)
        with CaptureQueriesContext(connection) as ctx:
            response = self.client.get(self.list_url, {"staff_member": self.counselor.id})

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == self.log_count
        # Pre-fix this hovered around (2 * log_count + auth overhead) queries.
        # With prefetches in place it should stay well under 20 regardless of
        # log_count. Generous ceiling so unrelated middleware additions don't
        # trip the test, but still tight enough to catch a regression.
        assert len(ctx.captured_queries) < 20, (
            f"Expected <20 queries, got {len(ctx.captured_queries)} "
            f"for {self.log_count} logs. The serializer is likely issuing "
            f"per-row queries again."
        )

    def test_admin_full_list_query_count_is_bounded(self):
        """Listing all logs (no filter) must also be bounded, not O(N)."""
        self.client.force_authenticate(user=self.admin)
        with CaptureQueriesContext(connection) as ctx:
            response = self.client.get(self.list_url)

        assert response.status_code == status.HTTP_200_OK
        assert len(ctx.captured_queries) < 20, (
            f"Expected <20 queries, got {len(ctx.captured_queries)} "
            f"for full list. Serializer is issuing per-row queries."
        )


class TestStaffLogResultLimit(TestCase):
    """Multi-day list responses must be capped, with metadata for the client."""

    def setUp(self):
        from datetime import timedelta

        self.client = APIClient()
        self.list_url = reverse("api:counselorlog-list")
        self.admin = UserFactory(admin=True, is_staff=True)
        self.counselor = UserFactory(counselor=True)

        # Need > STAFF_LOG_DEFAULT_LIMIT (200) rows to test truncation.
        # Use bulk_create to bypass StaffLog.clean()'s 30-day-old guard
        # (we need historical dates beyond that window for this test).
        self.total = 220
        StaffLog.objects.bulk_create([
            StaffLog(
                staff_member=self.counselor,
                date=date.today() - timedelta(days=i),
                day_quality_score=4,
                support_level_score=4,
                elaboration="Test elaboration text.",
                values_reflection="Test values reflection.",
            )
            for i in range(self.total)
        ])

    def test_default_limit_truncates_large_result_set(self):
        """Without a date filter, response is capped to STAFF_LOG_DEFAULT_LIMIT."""
        self.client.force_authenticate(user=self.admin)
        response = self.client.get(self.list_url, {"staff_member": self.counselor.id})

        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == self.total
        assert response.data["returned"] == 200
        assert response.data["limit"] == 200
        assert response.data["truncated"] is True
        assert len(response.data["results"]) == 200

    def test_explicit_limit_param_is_honored(self):
        """Caller can request a smaller page via ?limit=N."""
        self.client.force_authenticate(user=self.admin)
        response = self.client.get(
            self.list_url, {"staff_member": self.counselor.id, "limit": 25},
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == self.total
        assert response.data["returned"] == 25
        assert response.data["limit"] == 25
        assert response.data["truncated"] is True
        assert len(response.data["results"]) == 25

    def test_limit_is_clamped_to_max(self):
        """?limit values above STAFF_LOG_MAX_LIMIT are clamped, not honored."""
        self.client.force_authenticate(user=self.admin)
        response = self.client.get(
            self.list_url, {"staff_member": self.counselor.id, "limit": 99999},
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data["limit"] == 500

    def test_garbage_limit_falls_back_to_default(self):
        """Non-integer ?limit values fall back to default rather than 500ing."""
        self.client.force_authenticate(user=self.admin)
        response = self.client.get(
            self.list_url, {"staff_member": self.counselor.id, "limit": "lots"},
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data["limit"] == 200

    def test_date_filter_is_exempt_from_truncation(self):
        """Single-day filters are inherently bounded; do not apply the cap."""
        self.client.force_authenticate(user=self.admin)
        target = (date.today()).isoformat()
        response = self.client.get(self.list_url, {"date": target})

        assert response.status_code == status.HTTP_200_OK
        assert response.data["truncated"] is False
        assert response.data["limit"] is None

    def test_results_are_newest_first(self):
        """Truncation slices the most recent N rows."""
        self.client.force_authenticate(user=self.admin)
        response = self.client.get(self.list_url, {"staff_member": self.counselor.id})

        dates = [r["date"] for r in response.data["results"]]
        assert dates == sorted(dates, reverse=True)
        assert dates[0] == date.today().isoformat()
