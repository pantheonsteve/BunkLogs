"""Seed the local database with realistic synthetic data.

Designed to populate the UI well enough to develop against:
- 2 sessions (one in progress, one recently ended)
- 4 units, 8 cabins, 16 bunks (8 per session)
- ~120 campers (60 per session)
- 32 counselors (one primary + one floater per bunk in current session)
- 4 unit heads, 2 camper-care, 2 leadership, 2 kitchen staff, 1 superuser
- 21 days of BunkLogs and StaffLogs for the current session
- A handful of orders across both order types

Everything is created with ``is_test_data=True`` so the existing
``cleanup_test_data`` command can wipe it cleanly.

Run inside the django container:

    podman-compose -f docker-compose.local.yml exec django \
        python manage.py seed_dev_data --reset
"""
from __future__ import annotations

import datetime as dt
import random
from dataclasses import dataclass
from typing import Any

from django.conf import settings
from django.core.management.base import BaseCommand
from django.core.management.base import CommandError
from django.db import transaction
from django.utils import timezone
from faker import Faker

from bunk_logs.bunklogs.models import BunkLog
from bunk_logs.bunklogs.models import CounselorLog
from bunk_logs.bunklogs.models import StaffLog
from bunk_logs.bunks.models import Bunk
from bunk_logs.bunks.models import Cabin
from bunk_logs.bunks.models import CounselorBunkAssignment
from bunk_logs.bunks.models import Session
from bunk_logs.bunks.models import Unit
from bunk_logs.bunks.models import UnitStaffAssignment
from bunk_logs.campers.models import Camper
from bunk_logs.campers.models import CamperBunkAssignment
from bunk_logs.orders.models import Item
from bunk_logs.orders.models import ItemCategory
from bunk_logs.orders.models import Order
from bunk_logs.orders.models import OrderItem
from bunk_logs.orders.models import OrderType
from bunk_logs.users.models import User

LOCAL_DB_HOST_ALLOWLIST = {"localhost", "127.0.0.1", "postgres", "::1", ""}

DEV_PASSWORD = "devpass123"

UNITS = ["Pioneers", "Mariners", "Voyagers", "Trailblazers"]
CABIN_NAMES = [
    "Maple", "Birch", "Pine", "Oak",
    "Cedar", "Spruce", "Aspen", "Willow",
]


@dataclass
class SessionPlan:
    name: str
    start_date: dt.date
    end_date: dt.date
    is_active: bool


class Command(BaseCommand):
    help = "Seed the local DB with realistic synthetic data (test data flagged)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Delete all is_test_data=True rows before seeding.",
        )
        parser.add_argument(
            "--seed",
            type=int,
            default=42,
            help="Seed for Faker / random for reproducible data.",
        )
        parser.add_argument(
            "--days",
            type=int,
            default=21,
            help="How many days of logs to generate for the active session (max 30).",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        self._enforce_local_only()

        days = min(max(options["days"], 1), 30)
        Faker.seed(options["seed"])
        random.seed(options["seed"])
        fake = Faker()

        with transaction.atomic():
            if options["reset"]:
                self._reset_test_data()

            superuser = self._ensure_superuser()
            unit_heads = self._create_users(fake, count=4, role=User.UNIT_HEAD, label="unit-head")
            camper_care = self._create_users(fake, count=2, role=User.CAMPER_CARE, label="camper-care")
            counselors = self._create_users(fake, count=32, role=User.COUNSELOR, label="counselor")
            leadership = self._create_users(fake, count=2, role=User.LEADERSHIP, label="leadership")
            kitchen_staff = self._create_users(fake, count=2, role=User.KITCHEN_STAFF, label="kitchen-staff")

            sessions = self._create_sessions()
            units = self._create_units(unit_heads, camper_care)
            cabins = self._create_cabins()
            bunks_by_session = self._create_bunks(cabins, sessions, units)

            current_session = next(s for s in sessions if s.is_active)

            self._assign_counselors(counselors, bunks_by_session, current_session)

            campers = self._create_campers(fake, count=120)
            assignments = self._assign_campers_to_bunks(campers, bunks_by_session)

            current_assignments = [
                a for a in assignments if a.bunk.session_id == current_session.id
            ]
            current_counselor_assignments = CounselorBunkAssignment.objects.filter(
                bunk__session=current_session,
            ).select_related("bunk", "counselor")

            log_count = self._create_bunk_logs(current_assignments, current_counselor_assignments, days)
            counselor_log_count = self._create_counselor_logs(
                fake, current_counselor_assignments, days,
            )
            leadership_log_count = self._create_staff_logs(fake, leadership, days)
            kitchen_staff_log_count = self._create_staff_logs(fake, kitchen_staff, days)

            order_setup = self._ensure_order_catalog()
            order_count = self._create_orders(
                counselors=counselors,
                bunks=bunks_by_session[current_session.id],
                **order_setup,
            )

        self._report({
            "superuser": 1 if superuser else 0,
            "unit_heads": len(unit_heads),
            "camper_care": len(camper_care),
            "counselors": len(counselors),
            "leadership": len(leadership),
            "kitchen_staff": len(kitchen_staff),
            "sessions": len(sessions),
            "units": len(units),
            "cabins": len(cabins),
            "bunks": sum(len(v) for v in bunks_by_session.values()),
            "campers": len(campers),
            "camper_bunk_assignments": len(assignments),
            "bunk_logs": log_count,
            "counselor_logs": counselor_log_count,
            "leadership_logs": leadership_log_count,
            "kitchen_staff_logs": kitchen_staff_log_count,
            "orders": order_count,
        })

    # ------------------------------------------------------------- safety

    def _enforce_local_only(self) -> None:
        if not settings.DEBUG:
            msg = "Refusing to seed: settings.DEBUG is False."
            raise CommandError(msg)
        host = (settings.DATABASES.get("default", {}).get("HOST") or "").strip().lower()
        if host not in LOCAL_DB_HOST_ALLOWLIST:
            msg = f"Refusing to seed: database host '{host}' is not in the local allowlist."
            raise CommandError(msg)

    # ------------------------------------------------------------- reset

    def _reset_test_data(self) -> None:
        self.stdout.write(self.style.WARNING("--reset: deleting existing is_test_data=True rows..."))
        # Order matters: delete leaf rows first.
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
        # UnitStaffAssignment is the one model without TestDataMixin.
        if not hasattr(model, "get_test_data_queryset"):
            # delete UnitStaffAssignment whose staff_member is test data
            if model is UnitStaffAssignment:
                return UnitStaffAssignment.objects.filter(staff_member__is_test_data=True)
            return None
        # never wipe non-test superusers
        if model is User:
            return model.get_test_data_queryset().filter(is_superuser=False)
        return model.get_test_data_queryset()

    # ------------------------------------------------------------- users

    def _ensure_superuser(self) -> User | None:
        email = "dev-admin@example.test"
        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                "first_name": "Dev",
                "last_name": "Admin",
                "is_staff": True,
                "is_superuser": True,
                "role": User.ADMIN,
                "is_test_data": True,
            },
        )
        if created:
            user.set_password(DEV_PASSWORD)
            user.save(update_fields=["password"])
        return user

    def _create_users(self, fake: Faker, *, count: int, role: str, label: str) -> list[User]:
        users: list[User] = []
        for i in range(1, count + 1):
            email = f"{label}-{i}@example.test"
            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    "first_name": fake.first_name(),
                    "last_name": fake.last_name(),
                    "role": role,
                    "is_test_data": True,
                    "is_active": True,
                },
            )
            if created:
                user.set_password(DEV_PASSWORD)
                user.save(update_fields=["password"])
            users.append(user)
        return users

    # ----------------------------------------------------------- sessions

    def _create_sessions(self) -> list[Session]:
        today = timezone.localdate()
        plans = [
            SessionPlan(
                name="Spring Session",
                start_date=today - dt.timedelta(days=90),
                end_date=today - dt.timedelta(days=30),
                is_active=False,
            ),
            SessionPlan(
                name="Summer Session",
                start_date=today - dt.timedelta(days=15),
                end_date=today + dt.timedelta(days=45),
                is_active=True,
            ),
        ]
        sessions: list[Session] = []
        for plan in plans:
            session, _ = Session.objects.get_or_create(
                name=plan.name,
                defaults={
                    "start_date": plan.start_date,
                    "end_date": plan.end_date,
                    "is_active": plan.is_active,
                    "is_test_data": True,
                },
            )
            sessions.append(session)
        return sessions

    # -------------------------------------------------------------- units

    def _create_units(self, unit_heads: list[User], camper_care: list[User]) -> list[Unit]:
        units: list[Unit] = []
        for i, name in enumerate(UNITS):
            unit, _ = Unit.objects.get_or_create(name=name, defaults={"is_test_data": True})
            units.append(unit)
            head = unit_heads[i % len(unit_heads)]
            UnitStaffAssignment.objects.get_or_create(
                unit=unit,
                staff_member=head,
                role="unit_head",
                defaults={"is_primary": True, "start_date": timezone.localdate()},
            )
            care = camper_care[i % len(camper_care)]
            UnitStaffAssignment.objects.get_or_create(
                unit=unit,
                staff_member=care,
                role="camper_care",
                defaults={"is_primary": True, "start_date": timezone.localdate()},
            )
        return units

    # ------------------------------------------------------------- cabins

    def _create_cabins(self) -> list[Cabin]:
        cabins: list[Cabin] = []
        for name in CABIN_NAMES:
            cabin, _ = Cabin.objects.get_or_create(
                name=name,
                defaults={"capacity": 10, "location": "Lakeside", "is_test_data": True},
            )
            cabins.append(cabin)
        return cabins

    # -------------------------------------------------------------- bunks

    def _create_bunks(
        self, cabins: list[Cabin], sessions: list[Session], units: list[Unit],
    ) -> dict[int, list[Bunk]]:
        bunks_by_session: dict[int, list[Bunk]] = {s.id: [] for s in sessions}
        for session in sessions:
            for i, cabin in enumerate(cabins):
                unit = units[i % len(units)]
                bunk, _ = Bunk.objects.get_or_create(
                    cabin=cabin,
                    session=session,
                    defaults={"unit": unit, "is_active": True, "is_test_data": True},
                )
                bunks_by_session[session.id].append(bunk)
        return bunks_by_session

    # --------------------------------------------------- counselor assigns

    def _assign_counselors(
        self,
        counselors: list[User],
        bunks_by_session: dict[int, list[Bunk]],
        current_session: Session,
    ) -> None:
        # Two counselors per bunk in the current session: one primary, one floater.
        # Idempotency: skip a bunk entirely if it already has any counselor
        # assignments (e.g. from a prior seed run that scrub_pii has since
        # mangled emails on). Use --reset for a fresh start.
        current_bunks = bunks_by_session[current_session.id]
        for i, bunk in enumerate(current_bunks):
            if bunk.counselor_assignments.exists():
                continue
            primary = counselors[(i * 2) % len(counselors)]
            floater = counselors[(i * 2 + 1) % len(counselors)]
            CounselorBunkAssignment.objects.create(
                counselor=primary,
                bunk=bunk,
                start_date=current_session.start_date,
                end_date=current_session.end_date,
                is_primary=True,
                is_test_data=True,
            )
            CounselorBunkAssignment.objects.create(
                counselor=floater,
                bunk=bunk,
                start_date=current_session.start_date,
                end_date=current_session.end_date,
                is_primary=False,
                is_test_data=True,
            )

    # ----------------------------------------------------------- campers

    def _create_campers(self, fake: Faker, *, count: int) -> list[Camper]:
        existing = Camper.objects.filter(is_test_data=True).count()
        needed = max(count - existing, 0)
        new_campers: list[Camper] = []
        today = timezone.localdate()
        for _ in range(needed):
            age = random.randint(8, 16)  # noqa: S311
            dob = today.replace(year=today.year - age) - dt.timedelta(
                days=random.randint(0, 364),  # noqa: S311
            )
            new_campers.append(Camper(
                first_name=fake.first_name(),
                last_name=fake.last_name(),
                date_of_birth=dob,
                emergency_contact_name=fake.name(),
                emergency_contact_phone=fake.numerify("###-###-####"),
                camper_notes="",
                parent_notes="",
                is_test_data=True,
            ))
        if new_campers:
            Camper.objects.bulk_create(new_campers)
        return list(Camper.objects.filter(is_test_data=True).order_by("id")[:count])

    def _assign_campers_to_bunks(
        self, campers: list[Camper], bunks_by_session: dict[int, list[Bunk]],
    ) -> list[CamperBunkAssignment]:
        # Half to spring (ended), half to summer (active).
        sessions = list(bunks_by_session.keys())
        per_session = len(campers) // len(sessions)
        assignments: list[CamperBunkAssignment] = []

        for session_idx, session_id in enumerate(sessions):
            chunk = campers[session_idx * per_session : (session_idx + 1) * per_session]
            bunks = bunks_by_session[session_id]
            for i, camper in enumerate(chunk):
                bunk = bunks[i % len(bunks)]
                # Skip if camper already has any assignment (idempotency)
                if camper.bunk_assignments.exists():
                    existing = camper.bunk_assignments.first()
                    if existing:
                        assignments.append(existing)
                    continue
                # CamperBunkAssignment.save() auto-fills start/end from session
                # and runs validation. Use the model's save path directly.
                a = CamperBunkAssignment(
                    camper=camper,
                    bunk=bunk,
                    is_active=True,
                    is_test_data=True,
                )
                try:
                    a.save()
                except Exception as exc:
                    self.stderr.write(
                        f"  skipped camper assignment ({camper}, {bunk}): {exc}",
                    )
                    continue
                assignments.append(a)
        return assignments

    # --------------------------------------------------------- bunk logs

    def _create_bunk_logs(
        self,
        camper_assignments: list[CamperBunkAssignment],
        counselor_assignments,
        days: int,
    ) -> int:
        # Index counselors by bunk so we can pick a plausible author per log.
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
                # Respect assignment date window
                if assignment.start_date and log_date < assignment.start_date:
                    continue
                if assignment.end_date and log_date > assignment.end_date:
                    continue
                if BunkLog.objects.filter(
                    bunk_assignment=assignment, date=log_date,
                ).exists():
                    continue
                counselor = random.choice(counselors)  # noqa: S311
                not_on_camp = random.random() < 0.05  # noqa: S311 - ~5% absence
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
                except Exception as exc:
                    self.stderr.write(
                        f"  skipped bunk log ({assignment.id}, {log_date}): {exc}",
                    )
                    continue
        return created

    # ---------------------------------------------------- counselor logs

    def _create_counselor_logs(
        self, fake: Faker, counselor_assignments, days: int,
    ) -> int:
        today = timezone.localdate()
        created = 0
        seen: set[tuple[int, dt.date]] = set()
        for ca in counselor_assignments:
            for d in range(1, days + 1):
                log_date = today - dt.timedelta(days=d)
                key = (ca.counselor_id, log_date)
                if key in seen:
                    continue
                seen.add(key)
                if CounselorLog.objects.filter(
                    staff_member=ca.counselor, date=log_date,
                ).exists():
                    continue
                day_off = random.random() < 0.1  # noqa: S311
                try:
                    CounselorLog.objects.create(
                        staff_member=ca.counselor,
                        date=log_date,
                        day_quality_score=random.randint(2, 5),  # noqa: S311
                        support_level_score=random.randint(2, 5),  # noqa: S311
                        elaboration=fake.sentence(nb_words=12),
                        values_reflection=fake.sentence(nb_words=12),
                        day_off=day_off,
                        is_test_data=True,
                    )
                    created += 1
                except Exception as exc:
                    self.stderr.write(
                        f"  skipped counselor log ({ca.counselor_id}, {log_date}): {exc}",
                    )
                    continue
        return created

    def _create_staff_logs(self, fake: Faker, users: list[User], days: int) -> int:
        """Generate StaffLog rows for non-counselor staff (Leadership, Kitchen Staff)."""
        today = timezone.localdate()
        created = 0
        for user in users:
            for d in range(1, days + 1):
                log_date = today - dt.timedelta(days=d)
                if StaffLog.objects.filter(staff_member=user, date=log_date).exists():
                    continue
                day_off = random.random() < 0.1  # noqa: S311
                try:
                    StaffLog.objects.create(
                        staff_member=user,
                        date=log_date,
                        day_quality_score=random.randint(2, 5),  # noqa: S311
                        support_level_score=random.randint(2, 5),  # noqa: S311
                        elaboration=fake.sentence(nb_words=12),
                        values_reflection=fake.sentence(nb_words=12),
                        day_off=day_off,
                        is_test_data=True,
                    )
                    created += 1
                except Exception as exc:
                    self.stderr.write(
                        f"  skipped staff log ({user.id}, {log_date}): {exc}",
                    )
                    continue
        return created

    # ------------------------------------------------------------ orders

    def _ensure_order_catalog(self) -> dict[str, Any]:
        """Make sure OrderType / ItemCategory / Item rows exist for orders."""
        maintenance, _ = OrderType.objects.get_or_create(
            type_name="Maintenance Request",
            defaults={
                "type_description": "Repairs and facility issues.",
                "is_test_data": True,
            },
        )
        camper_care, _ = OrderType.objects.get_or_create(
            type_name="Camper Care",
            defaults={
                "type_description": "Items requested for camper wellbeing.",
                "is_test_data": True,
            },
        )
        cat_supplies, _ = ItemCategory.objects.get_or_create(
            category_name="Supplies",
            defaults={
                "category_description": "General supplies",
                "is_test_data": True,
            },
        )
        cat_repairs, _ = ItemCategory.objects.get_or_create(
            category_name="Repairs",
            defaults={
                "category_description": "Maintenance items",
                "is_test_data": True,
            },
        )
        items: list[Item] = []
        for name, cat in [
            ("Bandages", cat_supplies),
            ("Sunscreen", cat_supplies),
            ("Light bulb", cat_repairs),
            ("Mop head", cat_repairs),
        ]:
            item, _ = Item.objects.get_or_create(
                item_name=name,
                defaults={
                    "item_description": f"{name} (dev)",
                    "available": True,
                    "item_category": cat,
                    "is_test_data": True,
                },
            )
            items.append(item)
        return {
            "order_types": [maintenance, camper_care],
            "items": items,
        }

    def _create_orders(
        self,
        *,
        counselors: list[User],
        bunks: list[Bunk],
        order_types: list[OrderType],
        items: list[Item],
    ) -> int:
        # 8 orders, mixed types and statuses
        statuses = ["submitted", "pending", "completed", "cancelled"]
        created = 0
        for i in range(8):
            order = Order.objects.create(
                user=counselors[i % len(counselors)],
                order_status=statuses[i % len(statuses)],
                order_bunk=bunks[i % len(bunks)],
                order_type=order_types[i % len(order_types)],
                additional_notes=f"Dev seed order #{i + 1}",
                is_test_data=True,
            )
            n_items = random.randint(1, 3)  # noqa: S311
            for item in random.sample(items, n_items):
                OrderItem.objects.create(
                    order=order,
                    item=item,
                    item_quantity=random.randint(1, 5),  # noqa: S311
                    is_test_data=True,
                )
            created += 1
        return created

    # ----------------------------------------------------------- output

    def _report(self, counts: dict[str, int]) -> None:
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("seed_dev_data complete:"))
        for label, n in counts.items():
            self.stdout.write(f"  - {label:30s} {n}")
        self.stdout.write("")
        self.stdout.write(self.style.WARNING(
            f"All seeded users have password '{DEV_PASSWORD}'.",
        ))
        self.stdout.write("Superuser: dev-admin@example.test")
