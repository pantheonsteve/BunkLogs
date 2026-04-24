"""
Tests for BunkLog and CounselorLog date synchronization.

These tests verify that the date field always matches the local date
when the log was created, preventing timezone-related issues.
"""

from datetime import date
from datetime import datetime
from datetime import timedelta
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from bunk_logs.bunklogs.models import BunkLog
from bunk_logs.bunklogs.models import CounselorLog
from bunk_logs.bunks.models import Bunk
from bunk_logs.bunks.models import Cabin
from bunk_logs.bunks.models import Session
from bunk_logs.bunks.models import Unit
from bunk_logs.campers.models import Camper
from bunk_logs.campers.models import CamperBunkAssignment

User = get_user_model()


class BunkLogDateSyncTestCase(TestCase):
    """Test BunkLog date synchronization with created_at timestamp."""

    def setUp(self):
        """Set up test data."""
        # Create test user (counselor)
        self.counselor = User.objects.create_user(
            email="testcounselor@example.com",
            first_name="Test",
            last_name="Counselor",
            role="Counselor",
        )

        # Create test data first
        self.session = Session.objects.create(
            name="Test Session",
            start_date=timezone.now().date(),
            end_date=timezone.now().date() + timezone.timedelta(days=30),
            is_active=True,
        )

        self.cabin = Cabin.objects.create(
            name="Test Cabin",
            capacity=20,
        )

        # Create test unit
        self.unit = Unit.objects.create(
            name="Test Unit",
        )

        # Create test bunk
        self.bunk = Bunk.objects.create(
            cabin=self.cabin,
            session=self.session,
            unit=self.unit,
            is_active=True,
        )

        # Create test camper
        self.camper = Camper.objects.create(
            first_name="Test",
            last_name="Camper",
            date_of_birth=date(2010, 1, 1),
        )

        # Create bunk assignment
        self.assignment = CamperBunkAssignment.objects.create(
            camper=self.camper,
            bunk=self.bunk,
            start_date=date.today() - timedelta(days=7),
            is_active=True,
        )

    def test_bunklog_date_sync_normal_time(self):
        """Test BunkLog date sync during normal daytime hours."""
        # Create a BunkLog without specifying date
        log = BunkLog.objects.create(
            bunk_assignment=self.assignment,
            counselor=self.counselor,
            social_score=5,
            behavior_score=5,
            participation_score=5,
            description="Test log created during normal hours",
        )

        # Verify date matches created_at date in local timezone
        created_date = timezone.localtime(log.created_at).date()
        assert log.date == created_date
        assert log.date == timezone.localtime().date()

    @patch("django.utils.timezone.localtime")
    def test_bunklog_date_sync_just_before_midnight(self, mock_localtime):
        """Test BunkLog created at 11:59 PM gets correct date."""
        # Mock time to be 11:59 PM yesterday (recent enough to pass validation)
        yesterday = date.today() - timedelta(days=1)
        mock_date = datetime(yesterday.year, yesterday.month, yesterday.day, 23, 59, 0)
        mock_localtime.return_value = mock_date

        # Create BunkLog
        log = BunkLog.objects.create(
            bunk_assignment=self.assignment,
            counselor=self.counselor,
            social_score=4,
            behavior_score=4,
            participation_score=4,
            description="Test log created at 11:59 PM",
        )

        # Should have yesterday's date, not today's
        assert log.date == yesterday

    @patch("django.utils.timezone.localtime")
    def test_bunklog_date_sync_just_after_midnight(self, mock_localtime):
        """Test BunkLog created at 12:01 AM gets correct date."""
        # Mock time to be 12:01 AM today (recent enough to pass validation)
        today = date.today()
        mock_date = datetime(today.year, today.month, today.day, 0, 1, 0)
        mock_localtime.return_value = mock_date

        # Create BunkLog
        log = BunkLog.objects.create(
            bunk_assignment=self.assignment,
            counselor=self.counselor,
            social_score=3,
            behavior_score=3,
            participation_score=3,
            description="Test log created at 12:01 AM",
        )

        # Should have today's date
        assert log.date == today

    def test_bunklog_with_old_explicit_date_raises_validation_error(self):
        """Test that saving a BunkLog with a date older than 30 days raises ValidationError."""
        from django.core.exceptions import ValidationError

        old_date = date.today() - timedelta(days=60)
        log = BunkLog(
            bunk_assignment=self.assignment,
            counselor=self.counselor,
            date=old_date,
            social_score=2,
            behavior_score=2,
            participation_score=2,
            description="Test log with old explicit date",
        )
        with pytest.raises(ValidationError):
            log.save()

    def test_bunklog_update_preserves_correct_date(self):
        """Test that updating a BunkLog preserves the correct date."""
        # Create initial log
        log = BunkLog.objects.create(
            bunk_assignment=self.assignment,
            counselor=self.counselor,
            social_score=5,
            behavior_score=5,
            participation_score=5,
            description="Initial description",
        )

        original_date = log.date

        # Update the log
        log.description = "Updated description"
        log.save()

        # Date should remain the same
        assert log.date == original_date

    def test_bunklog_date_matches_created_at_after_create(self):
        """Test that date field matches the local date when the log is created."""
        log = BunkLog.objects.create(
            bunk_assignment=self.assignment,
            counselor=self.counselor,
            social_score=1,
            behavior_score=1,
            participation_score=1,
            description="Test date matching",
        )

        # Date should match the local date of created_at
        expected_date = timezone.localtime(log.created_at).date()
        assert log.date == expected_date
        assert log.date == date.today()


class CounselorLogDateSyncTestCase(TestCase):
    """Test CounselorLog date synchronization with created_at timestamp."""

    def setUp(self):
        """Set up test data."""
        self.counselor = User.objects.create_user(
            email="testcounselor2@example.com",
            first_name="Test",
            last_name="Counselor2",
            role="Counselor",
        )

    def test_counselorlog_date_sync_normal_time(self):
        """Test CounselorLog date sync during normal hours."""
        log = CounselorLog.objects.create(
            staff_member=self.counselor,
            day_quality_score=5,
            support_level_score=5,
            elaboration="Great day!",
            values_reflection="Kids showed great teamwork.",
        )

        # Verify date matches created_at date in local timezone
        created_date = timezone.localtime(log.created_at).date()
        assert log.date == created_date
        assert log.date == timezone.localtime().date()

    @patch("django.utils.timezone.localtime")
    def test_counselorlog_date_sync_midnight_edge_case(self, mock_localtime):
        """Test CounselorLog created at midnight gets correct date."""
        # Mock time to be 11:58 PM on July 14, 2025
        mock_date = datetime(2025, 7, 14, 23, 58, 0)
        mock_localtime.return_value = mock_date

        log = CounselorLog.objects.create(
            staff_member=self.counselor,
            day_quality_score=3,
            support_level_score=4,
            elaboration="Long day, but good.",
            values_reflection="Kids were tired but respectful.",
        )

        # Should have July 14 as the date
        assert log.date == date(2025, 7, 14)

    def test_counselorlog_with_old_explicit_date_raises_validation_error(self):
        """Test that saving a CounselorLog with a date older than 30 days raises ValidationError."""
        from django.core.exceptions import ValidationError

        old_date = date.today() - timedelta(days=60)
        log = CounselorLog(
            staff_member=self.counselor,
            date=old_date,
            day_quality_score=4,
            support_level_score=3,
            elaboration="Test with old date",
            values_reflection="Testing old date raises error",
        )
        with pytest.raises(ValidationError):
            log.save()


class DateSyncIntegrationTestCase(TestCase):
    """Integration tests for date synchronization across the application."""

    def setUp(self):
        """Set up test data."""
        self.counselor = User.objects.create_user(
            email="integration@example.com",
            first_name="Integration",
            last_name="Test",
            role="Counselor",
        )

        # Create test data first
        self.session = Session.objects.create(
            name="Integration Session",
            start_date=timezone.now().date(),
            end_date=timezone.now().date() + timezone.timedelta(days=30),
            is_active=True,
        )

        self.cabin = Cabin.objects.create(
            name="Integration Cabin",
            capacity=20,
        )

        self.unit = Unit.objects.create(name="Integration Unit")
        self.bunk = Bunk.objects.create(
            cabin=self.cabin,
            session=self.session,
            unit=self.unit,
            is_active=True,
        )
        self.camper = Camper.objects.create(
            first_name="Integration",
            last_name="Camper",
            date_of_birth=date(2012, 6, 15),
        )
        self.assignment = CamperBunkAssignment.objects.create(
            camper=self.camper,
            bunk=self.bunk,
            start_date=date.today() - timedelta(days=5),
            is_active=True,
        )

    def test_multiple_logs_same_day_different_times(self):
        """Test multiple logs created on same day at different times."""
        # Create a second camper and assignment for the second log to avoid unique constraint
        camper2 = Camper.objects.create(
            first_name="Second",
            last_name="Camper",
            date_of_birth=date(2012, 8, 20),
        )
        assignment2 = CamperBunkAssignment.objects.create(
            camper=camper2,
            bunk=self.bunk,
            start_date=date.today() - timedelta(days=5),
            is_active=True,
        )

        # Create logs at different times (simulated) for different campers
        log1 = BunkLog.objects.create(
            bunk_assignment=self.assignment,
            counselor=self.counselor,
            social_score=5,
            description="Morning log",
        )

        log2 = BunkLog.objects.create(
            bunk_assignment=assignment2,
            counselor=self.counselor,
            social_score=4,
            description="Evening log",
        )

        # Both should have same date (today)
        expected_date = timezone.localtime().date()
        assert log1.date == expected_date
        assert log2.date == expected_date
        assert log1.date == log2.date

    def test_logs_maintain_date_consistency_after_multiple_saves(self):
        """Test that logs maintain date consistency after multiple saves."""
        log = BunkLog.objects.create(
            bunk_assignment=self.assignment,
            counselor=self.counselor,
            social_score=3,
            description="Initial",
        )

        original_date = log.date

        # Multiple saves shouldn't change the date
        for i in range(5):
            log.description = f"Updated {i}"
            log.save()
            assert log.date == original_date

    @patch("django.utils.timezone.localtime")
    def test_timezone_consistency_across_log_types(self, mock_localtime):
        """Test that both BunkLog and CounselorLog handle timezones consistently."""
        # Mock a specific time today (recent enough to pass validation)
        today = date.today()
        mock_date = datetime(today.year, today.month, today.day, 14, 30, 0)
        mock_localtime.return_value = mock_date

        # Create both types of logs
        bunk_log = BunkLog.objects.create(
            bunk_assignment=self.assignment,
            counselor=self.counselor,
            social_score=4,
            description="Bunk log test",
        )

        counselor_log = CounselorLog.objects.create(
            staff_member=self.counselor,
            day_quality_score=4,
            support_level_score=4,
            elaboration="Counselor log test",
            values_reflection="Both logs should have same date",
        )

        # Both should have the same date (today, from the mock)
        expected_date = today
        assert bunk_log.date == expected_date
        assert counselor_log.date == expected_date
        assert bunk_log.date == counselor_log.date
