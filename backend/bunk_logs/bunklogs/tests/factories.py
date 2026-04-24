"""Factories for BunkLog, StaffLog, and its proxy models."""

from datetime import date

import factory
from factory.django import DjangoModelFactory

from bunk_logs.bunklogs.models import CounselorLog
from bunk_logs.bunklogs.models import KitchenStaffLog
from bunk_logs.bunklogs.models import LeadershipLog
from bunk_logs.bunklogs.models import StaffLog
from bunk_logs.users.tests.factories import UserFactory


class StaffLogFactory(DjangoModelFactory):
    """Factory for the concrete StaffLog model."""

    staff_member = factory.SubFactory(UserFactory)
    date = factory.LazyFunction(date.today)
    day_quality_score = factory.Faker("random_int", min=3, max=5)
    support_level_score = factory.Faker("random_int", min=3, max=5)
    elaboration = factory.Faker("paragraph")
    values_reflection = factory.Faker("paragraph")
    day_off = False
    staff_care_support_needed = False

    class Meta:
        model = StaffLog


class CounselorLogFactory(StaffLogFactory):
    """Factory for CounselorLog proxy (staff_member has role=Counselor)."""

    staff_member = factory.SubFactory(UserFactory, counselor=True)

    class Meta:
        model = CounselorLog


class LeadershipLogFactory(StaffLogFactory):
    """Factory for LeadershipLog proxy (staff_member has role=Leadership)."""

    staff_member = factory.SubFactory(UserFactory, leadership=True)

    class Meta:
        model = LeadershipLog


class KitchenStaffLogFactory(StaffLogFactory):
    """Factory for KitchenStaffLog proxy (staff_member has role=Kitchen Staff)."""

    staff_member = factory.SubFactory(UserFactory, kitchen=True)

    class Meta:
        model = KitchenStaffLog
