"""
Tests for BunkLog and CounselorLog date synchronization.

These tests verify that the date field always matches the local date
when the log was created, preventing timezone-related issues.
"""

from django.test import TestCase
from django.utils import timezone
from django.contrib.auth import get_user_model
from unittest.mock import patch
from datetime import datetime, date, timedelta

from bunk_logs.bunklogs.models import BunkLog, CounselorLog
from bunk_logs.campers.models import Camper, CamperBunkAssignment
from bunk_logs.bunks.models import Unit, Bunk, Session, Cabin
from bunk_logs.bunks.models import Bunk, Unit


User = get_user_model()


class BunkLogDateSyncTestCase(TestCase):
    """Test BunkLog date synchronization with created_at timestamp."""

    def setUp(self):
        """Set up test data."""
        # Create test user (counselor)
        self.counselor = User.objects.create_user(
            email='testcounselor@example.com',
            first_name='Test',
            last_name='Counselor',
            role='Counselor'
        )
        
        # Create test data first
        self.session = Session.objects.create(
            name="Test Session",
            start_date=timezone.now().date(),
            end_date=timezone.now().date() + timezone.timedelta(days=30),
            is_active=True
        )
        
        self.cabin = Cabin.objects.create(
            name="Test Cabin",
            capacity=20
        )
        
        # Create test unit
        self.unit = Unit.objects.create(
            name='Test Unit'
        )
        
        # Create test bunk
        self.bunk = Bunk.objects.create(
            cabin=self.cabin,
            session=self.session,
            unit=self.unit,
            is_active=True
        )
        
        # Create test camper
        self.camper = Camper.objects.create(
            first_name='Test',
            last_name='Camper',
            date_of_birth=date(2010, 1, 1)
        )
        
        # Create bunk assignment
        self.assignment = CamperBunkAssignment.objects.create(
            camper=self.camper,
            bunk=self.bunk,
            start_date=date.today() - timedelta(days=7),
            is_active=True
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
            description="Test log created during normal hours"
        )
        
        # Verify date matches created_at date in local timezone
        created_date = timezone.localtime(log.created_at).date()
        self.assertEqual(log.date, created_date)
        self.assertEqual(log.date, timezone.localtime().date())

    @patch('django.utils.timezone.localtime')
    def test_bunklog_date_sync_just_before_midnight(self, mock_localtime):
        """Test BunkLog created at 11:59 PM gets correct date."""
        # Mock time to be 11:59 PM on July 14, 2025
        mock_date = datetime(2025, 7, 14, 23, 59, 0)
        mock_localtime.return_value = mock_date
        
        # Create BunkLog
        log = BunkLog.objects.create(
            bunk_assignment=self.assignment,
            counselor=self.counselor,
            social_score=4,
            behavior_score=4,
            participation_score=4,
            description="Test log created at 11:59 PM"
        )
        
        # Should have July 14 as the date, not July 15
        self.assertEqual(log.date, date(2025, 7, 14))

    @patch('django.utils.timezone.localtime')
    def test_bunklog_date_sync_just_after_midnight(self, mock_localtime):
        """Test BunkLog created at 12:01 AM gets correct date."""
        # Mock time to be 12:01 AM on July 15, 2025
        mock_date = datetime(2025, 7, 15, 0, 1, 0)
        mock_localtime.return_value = mock_date
        
        # Create BunkLog
        log = BunkLog.objects.create(
            bunk_assignment=self.assignment,
            counselor=self.counselor,
            social_score=3,
            behavior_score=3,
            participation_score=3,
            description="Test log created at 12:01 AM"
        )
        
        # Should have July 15 as the date
        self.assertEqual(log.date, date(2025, 7, 15))

    def test_bunklog_with_explicit_date_gets_overridden(self):
        """Test that explicitly setting a date gets overridden by save method."""
        # Try to create a BunkLog with an explicit wrong date
        wrong_date = date(2020, 1, 1)
        log = BunkLog(
            bunk_assignment=self.assignment,
            counselor=self.counselor,
            date=wrong_date,  # This should be overridden
            social_score=2,
            behavior_score=2,
            participation_score=2,
            description="Test log with wrong explicit date"
        )
        log.save()
        
        # Date should be today, not the wrong date we set
        expected_date = timezone.localtime().date()
        self.assertEqual(log.date, expected_date)
        self.assertNotEqual(log.date, wrong_date)

    def test_bunklog_update_preserves_correct_date(self):
        """Test that updating a BunkLog preserves the correct date."""
        # Create initial log
        log = BunkLog.objects.create(
            bunk_assignment=self.assignment,
            counselor=self.counselor,
            social_score=5,
            behavior_score=5,
            participation_score=5,
            description="Initial description"
        )
        
        original_date = log.date
        
        # Update the log
        log.description = "Updated description"
        log.save()
        
        # Date should remain the same
        self.assertEqual(log.date, original_date)

    def test_bunklog_date_matches_created_at_after_save(self):
        """Test that date field always matches created_at date after save."""
        log = BunkLog.objects.create(
            bunk_assignment=self.assignment,
            counselor=self.counselor,
            social_score=1,
            behavior_score=1,
            participation_score=1,
            description="Test date matching"
        )
        
        # Force a mismatch scenario and call save again
        BunkLog.objects.filter(pk=log.pk).update(date=date(2020, 1, 1))
        log.refresh_from_db()
        
        # Now call save - it should fix the mismatch
        log.save()
        
        # Date should now match created_at
        expected_date = timezone.localtime(log.created_at).date()
        self.assertEqual(log.date, expected_date)


class CounselorLogDateSyncTestCase(TestCase):
    """Test CounselorLog date synchronization with created_at timestamp."""

    def setUp(self):
        """Set up test data."""
        self.counselor = User.objects.create_user(
            email='testcounselor2@example.com',
            first_name='Test',
            last_name='Counselor2',
            role='Counselor'
        )

    def test_counselorlog_date_sync_normal_time(self):
        """Test CounselorLog date sync during normal hours."""
        log = CounselorLog.objects.create(
            counselor=self.counselor,
            day_quality_score=5,
            support_level_score=5,
            elaboration="Great day!",
            values_reflection="Kids showed great teamwork."
        )
        
        # Verify date matches created_at date in local timezone
        created_date = timezone.localtime(log.created_at).date()
        self.assertEqual(log.date, created_date)
        self.assertEqual(log.date, timezone.localtime().date())

    @patch('django.utils.timezone.localtime')
    def test_counselorlog_date_sync_midnight_edge_case(self, mock_localtime):
        """Test CounselorLog created at midnight gets correct date."""
        # Mock time to be 11:58 PM on July 14, 2025
        mock_date = datetime(2025, 7, 14, 23, 58, 0)
        mock_localtime.return_value = mock_date
        
        log = CounselorLog.objects.create(
            counselor=self.counselor,
            day_quality_score=3,
            support_level_score=4,
            elaboration="Long day, but good.",
            values_reflection="Kids were tired but respectful."
        )
        
        # Should have July 14 as the date
        self.assertEqual(log.date, date(2025, 7, 14))

    def test_counselorlog_with_explicit_date_gets_overridden(self):
        """Test that explicitly setting a date gets overridden."""
        wrong_date = date(2019, 12, 25)
        log = CounselorLog(
            counselor=self.counselor,
            date=wrong_date,  # This should be overridden
            day_quality_score=4,
            support_level_score=3,
            elaboration="Test with wrong date",
            values_reflection="Testing date override"
        )
        log.save()
        
        # Date should be today, not the wrong date
        expected_date = timezone.localtime().date()
        self.assertEqual(log.date, expected_date)
        self.assertNotEqual(log.date, wrong_date)


class DateSyncIntegrationTestCase(TestCase):
    """Integration tests for date synchronization across the application."""

    def setUp(self):
        """Set up test data."""
        self.counselor = User.objects.create_user(
            email='integration@example.com',
            first_name='Integration',
            last_name='Test',
            role='Counselor'
        )
        
        # Create test data first
        self.session = Session.objects.create(
            name="Integration Session",
            start_date=timezone.now().date(),
            end_date=timezone.now().date() + timezone.timedelta(days=30),
            is_active=True
        )
        
        self.cabin = Cabin.objects.create(
            name="Integration Cabin",
            capacity=20
        )
        
        self.unit = Unit.objects.create(name='Integration Unit')
        self.bunk = Bunk.objects.create(
            cabin=self.cabin,
            session=self.session,
            unit=self.unit,
            is_active=True
        )
        self.camper = Camper.objects.create(
            first_name='Integration',
            last_name='Camper',
            date_of_birth=date(2012, 6, 15)
        )
        self.assignment = CamperBunkAssignment.objects.create(
            camper=self.camper,
            bunk=self.bunk,
            start_date=date.today() - timedelta(days=5),
            is_active=True
        )

    def test_multiple_logs_same_day_different_times(self):
        """Test multiple logs created on same day at different times."""
        # Create a second camper and assignment for the second log to avoid unique constraint
        camper2 = Camper.objects.create(
            first_name='Second',
            last_name='Camper',
            date_of_birth=date(2012, 8, 20)
        )
        assignment2 = CamperBunkAssignment.objects.create(
            camper=camper2,
            bunk=self.bunk,
            start_date=date.today() - timedelta(days=5),
            is_active=True
        )
        
        # Create logs at different times (simulated) for different campers
        log1 = BunkLog.objects.create(
            bunk_assignment=self.assignment,
            counselor=self.counselor,
            social_score=5,
            description="Morning log"
        )
        
        log2 = BunkLog.objects.create(
            bunk_assignment=assignment2,
            counselor=self.counselor,
            social_score=4,
            description="Evening log"
        )
        
        # Both should have same date (today)
        expected_date = timezone.localtime().date()
        self.assertEqual(log1.date, expected_date)
        self.assertEqual(log2.date, expected_date)
        self.assertEqual(log1.date, log2.date)

    def test_logs_maintain_date_consistency_after_multiple_saves(self):
        """Test that logs maintain date consistency after multiple saves."""
        log = BunkLog.objects.create(
            bunk_assignment=self.assignment,
            counselor=self.counselor,
            social_score=3,
            description="Initial"
        )
        
        original_date = log.date
        
        # Multiple saves shouldn't change the date
        for i in range(5):
            log.description = f"Updated {i}"
            log.save()
            self.assertEqual(log.date, original_date)

    @patch('django.utils.timezone.localtime')
    def test_timezone_consistency_across_log_types(self, mock_localtime):
        """Test that both BunkLog and CounselorLog handle timezones consistently."""
        # Mock a specific time
        mock_date = datetime(2025, 7, 20, 14, 30, 0)
        mock_localtime.return_value = mock_date
        
        # Create both types of logs
        bunk_log = BunkLog.objects.create(
            bunk_assignment=self.assignment,
            counselor=self.counselor,
            social_score=4,
            description="Bunk log test"
        )
        
        counselor_log = CounselorLog.objects.create(
            counselor=self.counselor,
            day_quality_score=4,
            support_level_score=4,
            elaboration="Counselor log test",
            values_reflection="Both logs should have same date"
        )
        
        # Both should have the same date
        expected_date = date(2025, 7, 20)
        self.assertEqual(bunk_log.date, expected_date)
        self.assertEqual(counselor_log.date, expected_date)
        self.assertEqual(bunk_log.date, counselor_log.date)
