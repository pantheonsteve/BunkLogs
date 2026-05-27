"""Seed a focused integration-test scenario from the existing user pool.

Sets up a single unit with all active-session bunks, wires camper care / unit
head RBAC to that unit, assigns exactly two counselors per bunk, and writes
five days of BunkLogs for every camper currently assigned to those bunks.

Designed to run on top of an already-populated DB (e.g. after seed_dev_data)
without duplicating users or campers. All new rows are flagged is_test_data=True
so cleanup_test_data removes them cleanly.

Usage (inside the django container):

    python manage.py seed_test_scenario
    python manage.py seed_test_scenario --reset   # wipe test rows first
    python manage.py seed_test_scenario --days 5  # default is already 5
"""
from __future__ import annotations

import datetime as dt
import random
from typing import Any

from django.conf import settings
from django.core.management.base import BaseCommand
from django.core.management.base import CommandError
from django.db import transaction
from django.utils import timezone

from bunk_logs.bunklogs.models import BunkLog
from bunk_logs.bunks.models import Bunk
from bunk_logs.bunks.models import CounselorBunkAssignment
from bunk_logs.bunks.models import Session
from bunk_logs.bunks.models import Unit
from bunk_logs.bunks.models import UnitStaffAssignment
from bunk_logs.campers.models import CamperBunkAssignment
from bunk_logs.users.models import User

LOCAL_DB_HOST_ALLOWLIST = {"localhost", "127.0.0.1", "postgres", "::1", ""}

UNIT_NAME = "Integration Test Unit"


class Command(BaseCommand):
    help = (
        "Build a single-unit test scenario: all bunks → one unit, "
        "2 counselors/bunk, camper-care + unit-head RBAC wired, "
        "5 days of BunkLogs for every camper."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Delete all is_test_data=True rows before seeding.",
        )
        parser.add_argument(
            "--days",
            type=int,
            default=5,
            help="How many days of BunkLogs to create (default 5, max 30).",
        )
        parser.add_argument(
            "--seed",
            type=int,
            default=99,
            help="RNG seed for reproducible log scores.",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        self._enforce_local_only()

        days = min(max(options["days"], 1), 30)
        random.seed(options["seed"])

        with transaction.atomic():
            if options["reset"]:
                self._reset_test_data()

            session = self._active_session()
            if session is None:
                raise CommandError(
                    "No active Session found. Run seed_dev_data first, "
                    "or create a Session with is_active=True."
                )

            unit = self._ensure_unit()

            counselors = self._users_by_role(User.COUNSELOR)
            unit_heads = self._users_by_role(User.UNIT_HEAD)
            camper_care = self._users_by_role(User.CAMPER_CARE)

            if not counselors:
                raise CommandError(
                    "No users with role='Counselor' found. "
                    "Run seed_dev_data first."
                )

            bunks = self._assign_bunks_to_unit(session, unit)
            if not bunks:
                raise CommandError(
                    f"No bunks found for the active session '{session}'. "
                    "Run seed_dev_data first."
                )

            uh_count = self._assign_unit_heads(unit, unit_heads)
            cc_count = self._assign_camper_care(unit, camper_care)
            counselor_assignment_count = self._assign_counselors(
                bunks, session, counselors
            )

            camper_assignments = list(
                CamperBunkAssignment.objects.filter(
                    bunk__in=bunks,
                    is_active=True,
                ).select_related("bunk")
            )

            counselor_assignments = list(
                CounselorBunkAssignment.objects.filter(
                    bunk__in=bunks
                ).select_related("bunk", "counselor")
            )

            log_count = self._create_bunk_logs(
                camper_assignments, counselor_assignments, days
            )

        self._report(
            session=str(session),
            unit=str(unit),
            bunks=len(bunks),
            unit_heads_assigned=uh_count,
            camper_care_assigned=cc_count,
            counselor_assignments_created=counselor_assignment_count,
            camper_assignments_covered=len(camper_assignments),
            bunk_logs_created=log_count,
            days=days,
        )

    # ---------------------------------------------------------------- safety

    def _enforce_local_only(self) -> None:
        if not settings.DEBUG:
            raise CommandError("Refusing to seed: settings.DEBUG is False.")
        host = (settings.DATABASES.get("default", {}).get("HOST") or "").strip().lower()
        if host not in LOCAL_DB_HOST_ALLOWLIST:
            raise CommandError(
                f"Refusing to seed: database host '{host}' is not in the local allowlist."
            )

    # ---------------------------------------------------------------- reset

    def _reset_test_data(self) -> None:
        self.stdout.write(self.style.WARNING(
            "--reset: deleting is_test_data=True rows..."
        ))
        # BunkLogs first (PROTECT FK prevents assignment deletion otherwise)
        orphaned = BunkLog.objects.filter(bunk_assignment__bunk__is_test_data=True)
        n = orphaned.count()
        if n:
            orphaned.delete()
            self.stdout.write(f"  deleted {n} BunkLog")

        from bunk_logs.bunklogs.models import StaffLog
        from bunk_logs.bunks.models import Cabin
        from bunk_logs.campers.models import Camper
        from bunk_logs.orders.models import Item, ItemCategory, Order, OrderItem, OrderType

        for model in (
            BunkLog, StaffLog,
            OrderItem, Order,
            CamperBunkAssignment, CounselorBunkAssignment,
            Camper,
            Bunk,
            UnitStaffAssignment,
            Unit, Session, Cabin,
            Item, ItemCategory, OrderType,
            User,
        ):
            qs = self._test_qs(model)
            if qs is None:
                continue
            n = qs.count()
            if n:
                qs.delete()
                self.stdout.write(f"  deleted {n} {model.__name__}")

    @staticmethod
    def _test_qs(model):
        if model is UnitStaffAssignment:
            return UnitStaffAssignment.objects.filter(staff_member__is_test_data=True)
        if not hasattr(model, "get_test_data_queryset"):
            return None
        if model is User:
            return model.get_test_data_queryset().filter(is_superuser=False)
        return model.get_test_data_queryset()

    # ---------------------------------------------------------------- helpers

    def _active_session(self) -> Session | None:
        return Session.objects.filter(is_active=True).order_by("-start_date").first()

    def _users_by_role(self, role: str) -> list[User]:
        return list(User.objects.filter(role=role, is_active=True).order_by("id"))

    def _ensure_unit(self) -> Unit:
        unit, created = Unit.objects.get_or_create(
            name=UNIT_NAME,
            defaults={"is_test_data": True},
        )
        if created:
            self.stdout.write(f"  created unit: {unit.name}")
        else:
            self.stdout.write(f"  using existing unit: {unit.name}")
        return unit

    def _assign_bunks_to_unit(self, session: Session, unit: Unit) -> list[Bunk]:
        """Move every bunk in the active session into `unit`."""
        bunks = list(Bunk.objects.filter(session=session).order_by("id"))
        Bunk.objects.filter(session=session).update(unit=unit)
        return bunks

    def _assign_unit_heads(self, unit: Unit, unit_heads: list[User]) -> int:
        today = timezone.localdate()
        count = 0
        for uh in unit_heads:
            _, created = UnitStaffAssignment.objects.get_or_create(
                unit=unit,
                staff_member=uh,
                role="unit_head",
                defaults={"is_primary": True, "start_date": today},
            )
            if created:
                count += 1
        return count

    def _assign_camper_care(self, unit: Unit, camper_care: list[User]) -> int:
        today = timezone.localdate()
        count = 0
        for cc in camper_care:
            _, created = UnitStaffAssignment.objects.get_or_create(
                unit=unit,
                staff_member=cc,
                role="camper_care",
                defaults={"is_primary": True, "start_date": today},
            )
            if created:
                count += 1
        return count

    def _assign_counselors(
        self,
        bunks: list[Bunk],
        session: Session,
        counselors: list[User],
    ) -> int:
        """Ensure every bunk has at least two counselor assignments (one primary, one floater).

        Idempotent: skips any slot already covered by an existing assignment.
        """
        count = 0
        for i, bunk in enumerate(bunks):
            existing = list(bunk.counselor_assignments.all())
            existing_counselor_ids = {a.counselor_id for a in existing}
            has_primary = any(a.is_primary for a in existing)
            non_primary_count = sum(1 for a in existing if not a.is_primary)

            # Pick two counselors round-robin, avoiding same person
            primary = counselors[(i * 2) % len(counselors)]
            floater = counselors[(i * 2 + 1) % len(counselors)]
            if primary.id == floater.id and len(counselors) > 1:
                floater = counselors[(i * 2 + 2) % len(counselors)]

            if not has_primary and primary.id not in existing_counselor_ids:
                try:
                    CounselorBunkAssignment.objects.create(
                        counselor=primary,
                        bunk=bunk,
                        start_date=session.start_date,
                        end_date=session.end_date,
                        is_primary=True,
                        is_test_data=True,
                    )
                    count += 1
                except Exception as exc:  # noqa: BLE001
                    self.stderr.write(
                        f"  skipped primary counselor ({primary}, {bunk}): {exc}"
                    )

            if non_primary_count == 0 and floater.id not in existing_counselor_ids:
                try:
                    CounselorBunkAssignment.objects.create(
                        counselor=floater,
                        bunk=bunk,
                        start_date=session.start_date,
                        end_date=session.end_date,
                        is_primary=False,
                        is_test_data=True,
                    )
                    count += 1
                except Exception as exc:  # noqa: BLE001
                    self.stderr.write(
                        f"  skipped floater counselor ({floater}, {bunk}): {exc}"
                    )

        return count

    # --------------------------------------------------------------- logs

    def _create_bunk_logs(
        self,
        camper_assignments: list[CamperBunkAssignment],
        counselor_assignments: list,
        days: int,
    ) -> int:
        counselors_by_bunk: dict[int, list[User]] = {}
        for ca in counselor_assignments:
            counselors_by_bunk.setdefault(ca.bunk_id, []).append(ca.counselor)

        today = timezone.localdate()
        created = 0
        for assignment in camper_assignments:
            counselors = counselors_by_bunk.get(assignment.bunk_id)
            if not counselors:
                continue

            for d in range(1, days + 1):
                log_date = today - dt.timedelta(days=d)

                if assignment.start_date and log_date < assignment.start_date:
                    continue
                if assignment.end_date and log_date > assignment.end_date:
                    continue

                if BunkLog.objects.filter(
                    bunk_assignment=assignment, date=log_date
                ).exists():
                    continue

                counselor = random.choice(counselors)  # noqa: S311
                not_on_camp = random.random() < 0.05  # noqa: S311

                kwargs: dict[str, Any] = {
                    "bunk_assignment": assignment,
                    "counselor": counselor,
                    "date": log_date,
                    "not_on_camp": not_on_camp,
                    "is_test_data": True,
                }
                if not not_on_camp:
                    kwargs.update({
                        "social_score": random.randint(2, 5),  # noqa: S311
                        "behavior_score": random.randint(2, 5),  # noqa: S311
                        "participation_score": random.randint(2, 5),  # noqa: S311
                        "description": "",
                    })

                try:
                    BunkLog.objects.create(**kwargs)
                    created += 1
                except Exception as exc:  # noqa: BLE001
                    self.stderr.write(
                        f"  skipped log ({assignment.id}, {log_date}): {exc}"
                    )

        return created

    # --------------------------------------------------------------- output

    def _report(self, **kwargs: Any) -> None:
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("seed_test_scenario complete:"))
        for k, v in kwargs.items():
            self.stdout.write(f"  {k:<40s} {v}")
        self.stdout.write("")
