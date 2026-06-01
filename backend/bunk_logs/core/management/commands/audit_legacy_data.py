"""Read-only inventory of legacy (old-model) data ahead of multi-tenant migration.

Safe to run against production. Performs zero writes. Produces a human-readable
report on stdout and, optionally, a JSON file for downstream tooling.

Usage
-----
    python manage.py audit_legacy_data
    python manage.py audit_legacy_data --year 2025
    python manage.py audit_legacy_data --year 2025 --json-out /tmp/audit-2025.json

The --year filter restricts Session-scoped counts (Bunks, CamperBunkAssignments,
CounselorBunkAssignments, BunkLogs) to Sessions whose start_date or end_date
fall in the given calendar year. Global tallies (Cabins, Units, Campers,
StaffLogs, Users) are reported unfiltered for context.
"""
from __future__ import annotations

import json
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db.models import Count
from django.db.models import Max
from django.db.models import Min
from django.db.models import Q

from bunk_logs.bunklogs.models import BunkLog
from bunk_logs.bunklogs.models import StaffLog
from bunk_logs.bunks.models import Bunk
from bunk_logs.bunks.models import Cabin
from bunk_logs.bunks.models import CounselorBunkAssignment
from bunk_logs.bunks.models import Session
from bunk_logs.bunks.models import Unit
from bunk_logs.bunks.models import UnitStaffAssignment
from bunk_logs.campers.models import Camper
from bunk_logs.campers.models import CamperBunkAssignment

User = get_user_model()


def _session_filter(year: int | None) -> Q:
    """Sessions touching ``year`` (start or end falls in that calendar year)."""
    if year is None:
        return Q()
    return Q(start_date__year=year) | Q(end_date__year=year)


def _date_range(qs, field: str = "date") -> tuple[str | None, str | None]:
    agg = qs.aggregate(min_d=Min(field), max_d=Max(field))
    return (
        agg["min_d"].isoformat() if agg["min_d"] else None,
        agg["max_d"].isoformat() if agg["max_d"] else None,
    )


class Command(BaseCommand):
    help = "Read-only inventory of legacy data ahead of multi-tenant migration."

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--year",
            type=int,
            default=None,
            help="Optional calendar year filter for Session-scoped counts (e.g. 2025).",
        )
        parser.add_argument(
            "--json-out",
            default=None,
            help="Optional path; if set, also writes a machine-readable JSON report.",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        year: int | None = options["year"]
        json_out: str | None = options["json_out"]

        self._banner(year)

        report: dict[str, Any] = {
            "generated_at": date.today().isoformat(),
            "year_filter": year,
        }

        # ── Sessions ───────────────────────────────────────────────────────
        sessions_qs = Session.objects.filter(_session_filter(year)).order_by("start_date")
        sessions = list(sessions_qs.values("id", "name", "start_date", "end_date", "is_active"))
        report["sessions"] = [
            {
                "id": s["id"],
                "name": s["name"],
                "start_date": s["start_date"].isoformat() if s["start_date"] else None,
                "end_date": s["end_date"].isoformat() if s["end_date"] else None,
                "is_active": s["is_active"],
            }
            for s in sessions
        ]
        self._section("Sessions" + (f" (year={year})" if year else ""))
        if not sessions:
            self.stdout.write(self.style.WARNING("  No sessions found."))
        else:
            for s in sessions:
                self.stdout.write(
                    f"  #{s['id']:>3}  {s['name']:<40} "
                    f"{s['start_date']} → {s['end_date']}  "
                    f"{'(active)' if s['is_active'] else ''}",
                )

        session_ids = [s["id"] for s in sessions]

        # ── Cabins (unfiltered) ────────────────────────────────────────────
        cabins = list(Cabin.objects.order_by("name").values("id", "name", "capacity"))
        report["cabins"] = {
            "total": len(cabins),
            "names": [c["name"] for c in cabins],
            "total_capacity": sum(c["capacity"] or 0 for c in cabins),
        }
        self._section("Cabins (unfiltered)")
        self.stdout.write(f"  Total: {len(cabins)} cabins")
        if cabins:
            self.stdout.write(
                f"  Total capacity: {report['cabins']['total_capacity']}",
            )

        # ── Units (unfiltered) ─────────────────────────────────────────────
        units = list(Unit.objects.order_by("name").values("id", "name"))
        report["units"] = {
            "total": len(units),
            "names": [u["name"] for u in units],
        }
        self._section("Units (unfiltered)")
        self.stdout.write(f"  Total: {len(units)} units")
        for u in units:
            self.stdout.write(f"    #{u['id']:>3}  {u['name']}")

        # ── Bunks (filtered to sessions) ───────────────────────────────────
        bunks_qs = Bunk.objects.all()
        if session_ids:
            bunks_qs = bunks_qs.filter(session_id__in=session_ids)
        bunks_by_session = (
            bunks_qs
            .values("session__id", "session__name")
            .annotate(n=Count("id"))
            .order_by("session__start_date")
        )
        bunks_with_unit = bunks_qs.filter(unit__isnull=False).count()
        bunks_without_unit = bunks_qs.filter(unit__isnull=True).count()
        bunks_by_unit = list(
            bunks_qs
            .filter(unit__isnull=False)
            .values("unit__id", "unit__name", "session__id", "session__name")
            .annotate(n=Count("id"))
            .order_by("unit__name", "session__start_date"),
        )
        report["bunks"] = {
            "total": bunks_qs.count(),
            "by_session": list(bunks_by_session),
            "with_unit": bunks_with_unit,
            "without_unit": bunks_without_unit,
            "by_unit_and_session": [
                {
                    "unit_id": b["unit__id"],
                    "unit_name": b["unit__name"],
                    "session_id": b["session__id"],
                    "session_name": b["session__name"],
                    "bunks": b["n"],
                }
                for b in bunks_by_unit
            ],
        }
        self._section("Bunks" + (f" (year={year})" if year else ""))
        self.stdout.write(f"  Total: {bunks_qs.count()} bunks")
        self.stdout.write(
            f"  With unit assignment: {bunks_with_unit}  |  "
            f"Without unit: {bunks_without_unit}",
        )
        for row in bunks_by_session:
            self.stdout.write(
                f"    Session #{row['session__id']} {row['session__name']!r}: "
                f"{row['n']} bunks",
            )
        if bunks_without_unit:
            self.stdout.write(
                self.style.WARNING(
                    f"  ⚠ {bunks_without_unit} bunks have no unit FK — "
                    "migration will need a fallback (or these need backfill first).",
                ),
            )

        # ── Campers (unfiltered) ───────────────────────────────────────────
        campers_total = Camper.objects.count()
        campers_with_dob = Camper.objects.filter(date_of_birth__isnull=False).count()
        report["campers"] = {
            "total": campers_total,
            "with_dob": campers_with_dob,
            "without_dob": campers_total - campers_with_dob,
        }
        self._section("Campers (unfiltered)")
        self.stdout.write(f"  Total: {campers_total} campers")
        self.stdout.write(
            f"  With DOB: {campers_with_dob}  |  "
            f"Without DOB: {campers_total - campers_with_dob}",
        )

        # ── CamperBunkAssignments ──────────────────────────────────────────
        cba_qs = CamperBunkAssignment.objects.all()
        if session_ids:
            cba_qs = cba_qs.filter(bunk__session_id__in=session_ids)
        cba_active = cba_qs.filter(is_active=True).count()
        cba_by_session = list(
            cba_qs
            .values("bunk__session__id", "bunk__session__name")
            .annotate(n=Count("id"), n_active=Count("id", filter=Q(is_active=True)))
            .order_by("bunk__session__start_date"),
        )
        unique_campers_in_scope = (
            cba_qs.values("camper_id").distinct().count()
        )
        report["camper_bunk_assignments"] = {
            "total": cba_qs.count(),
            "active": cba_active,
            "unique_campers_in_scope": unique_campers_in_scope,
            "by_session": [
                {
                    "session_id": r["bunk__session__id"],
                    "session_name": r["bunk__session__name"],
                    "total": r["n"],
                    "active": r["n_active"],
                }
                for r in cba_by_session
            ],
        }
        self._section(
            "CamperBunkAssignments" + (f" (year={year})" if year else ""),
        )
        self.stdout.write(f"  Total: {cba_qs.count()} assignments")
        self.stdout.write(f"  Active: {cba_active}")
        self.stdout.write(
            f"  Unique campers in scope: {unique_campers_in_scope}",
        )
        for row in cba_by_session:
            self.stdout.write(
                f"    {row['bunk__session__name']!r}: "
                f"{row['n']} total, {row['n_active']} active",
            )

        # ── CounselorBunkAssignments ───────────────────────────────────────
        ccba_qs = CounselorBunkAssignment.objects.all()
        if session_ids:
            ccba_qs = ccba_qs.filter(bunk__session_id__in=session_ids)
        ccba_primary = ccba_qs.filter(is_primary=True).count()
        unique_counselors_in_scope = (
            ccba_qs.values("counselor_id").distinct().count()
        )
        report["counselor_bunk_assignments"] = {
            "total": ccba_qs.count(),
            "primary": ccba_primary,
            "unique_counselors_in_scope": unique_counselors_in_scope,
        }
        self._section(
            "CounselorBunkAssignments" + (f" (year={year})" if year else ""),
        )
        self.stdout.write(f"  Total: {ccba_qs.count()} assignments")
        self.stdout.write(f"  Primary: {ccba_primary}")
        self.stdout.write(
            f"  Unique counselors in scope: {unique_counselors_in_scope}",
        )

        # ── UnitStaffAssignments (unfiltered: not session-scoped) ──────────
        usa_qs = UnitStaffAssignment.objects.all()
        usa_by_role = Counter(usa_qs.values_list("role", flat=True))
        usa_open_ended = usa_qs.filter(end_date__isnull=True).count()
        report["unit_staff_assignments"] = {
            "total": usa_qs.count(),
            "by_role": dict(usa_by_role),
            "open_ended": usa_open_ended,
        }
        self._section("UnitStaffAssignments (unfiltered)")
        self.stdout.write(f"  Total: {usa_qs.count()} assignments")
        for role, n in sorted(usa_by_role.items()):
            self.stdout.write(f"    {role}: {n}")
        self.stdout.write(f"  Open-ended (no end_date): {usa_open_ended}")

        # ── BunkLogs ───────────────────────────────────────────────────────
        bl_qs = BunkLog.objects.all()
        if session_ids:
            bl_qs = bl_qs.filter(bunk_assignment__bunk__session_id__in=session_ids)
        bl_total = bl_qs.count()
        bl_not_on_camp = bl_qs.filter(not_on_camp=True).count()
        bl_with_uh_help = bl_qs.filter(request_unit_head_help=True).count()
        bl_with_cc_help = bl_qs.filter(request_camper_care_help=True).count()
        bl_min, bl_max = _date_range(bl_qs)
        unique_counselors_logged = (
            bl_qs.values("counselor_id").distinct().count()
        )
        report["bunk_logs"] = {
            "total": bl_total,
            "not_on_camp": bl_not_on_camp,
            "request_unit_head_help": bl_with_uh_help,
            "request_camper_care_help": bl_with_cc_help,
            "date_min": bl_min,
            "date_max": bl_max,
            "unique_counselors_logged": unique_counselors_logged,
        }
        self._section("BunkLogs" + (f" (year={year})" if year else ""))
        self.stdout.write(f"  Total: {bl_total} bunk logs")
        self.stdout.write(f"  Date range: {bl_min} → {bl_max}")
        self.stdout.write(f"  Not on camp: {bl_not_on_camp}")
        self.stdout.write(
            f"  UH help requested: {bl_with_uh_help}  |  "
            f"CC help requested: {bl_with_cc_help}",
        )
        self.stdout.write(
            f"  Unique counselors who logged: {unique_counselors_logged}",
        )

        # ── StaffLogs (unfiltered: not session-scoped on the model) ────────
        sl_qs = StaffLog.objects.all()
        sl_total = sl_qs.count()
        sl_day_off = sl_qs.filter(day_off=True).count()
        sl_support_needed = sl_qs.filter(staff_care_support_needed=True).count()
        sl_min, sl_max = _date_range(sl_qs)
        sl_by_year: dict[int, int] = {}
        if year is not None:
            yr_total = sl_qs.filter(date__year=year).count()
            sl_by_year[year] = yr_total
        else:
            agg = sl_qs.dates("date", "year")
            for d in agg:
                sl_by_year[d.year] = sl_qs.filter(date__year=d.year).count()
        unique_staff_logged = sl_qs.values("staff_member_id").distinct().count()
        report["staff_logs"] = {
            "total": sl_total,
            "day_off": sl_day_off,
            "staff_care_support_needed": sl_support_needed,
            "date_min": sl_min,
            "date_max": sl_max,
            "by_year": sl_by_year,
            "unique_staff_logged": unique_staff_logged,
        }
        self._section("StaffLogs (unfiltered)")
        self.stdout.write(f"  Total: {sl_total} staff logs")
        self.stdout.write(f"  Date range: {sl_min} → {sl_max}")
        self.stdout.write(f"  Day off: {sl_day_off}")
        self.stdout.write(f"  Care support requested: {sl_support_needed}")
        self.stdout.write(f"  Unique staff who logged: {unique_staff_logged}")
        for yr, n in sorted(sl_by_year.items()):
            self.stdout.write(f"    {yr}: {n} logs")

        # ── Users ──────────────────────────────────────────────────────────
        users_total = User.objects.count()
        users_active = User.objects.filter(is_active=True).count()
        users_with_role = (
            User.objects.exclude(role="").exclude(role__isnull=True).count()
            if hasattr(User, "role")
            else None
        )
        users_by_role: dict[str, int] = {}
        if hasattr(User, "role"):
            for row in (
                User.objects
                .values("role")
                .annotate(n=Count("id"))
                .order_by("-n")
            ):
                role_key = row["role"] or "(blank)"
                users_by_role[role_key] = row["n"]
        report["users"] = {
            "total": users_total,
            "active": users_active,
            "with_role": users_with_role,
            "by_role": users_by_role,
        }
        self._section("Users (auth.User, unfiltered)")
        self.stdout.write(f"  Total: {users_total}  |  Active: {users_active}")
        if users_with_role is not None:
            self.stdout.write(f"  With role set: {users_with_role}")
            for role_key, n in sorted(users_by_role.items(), key=lambda x: -x[1]):
                self.stdout.write(f"    {role_key}: {n}")

        # ── Migration volume summary ───────────────────────────────────────
        self._section("Estimated migration volume")
        self.stdout.write(
            f"  Programs to create:                {len(sessions)}",
        )
        self.stdout.write(
            f"  Unit AssignmentGroups to create:   "
            f"{len(units) * len(sessions)} ({len(units)} units x {len(sessions)} sessions)",
        )
        self.stdout.write(
            f"  Bunk AssignmentGroups to create:   {bunks_qs.count()}",
        )
        self.stdout.write(
            f"  Person records to create/link:     "
            f"{campers_total + unique_counselors_in_scope} "
            f"({campers_total} campers + {unique_counselors_in_scope} counselors)",
        )
        self.stdout.write(
            f"  Membership rows (camper):          {cba_qs.count()}",
        )
        self.stdout.write(
            f"  Membership rows (counselor):       {ccba_qs.count()}",
        )
        self.stdout.write(
            f"  Membership rows (UH/CC from USA):  {usa_qs.count()}",
        )
        self.stdout.write(
            f"  Reflection rows (BunkLog):         {bl_total}",
        )
        self.stdout.write(
            f"  Reflection rows (StaffLog):        {sl_total}",
        )
        total_writes = (
            len(sessions)
            + len(units) * len(sessions)
            + bunks_qs.count()
            + campers_total
            + unique_counselors_in_scope
            + cba_qs.count() * 2  # Membership + AssignmentGroupMembership
            + ccba_qs.count() * 2
            + usa_qs.count()
            + bl_total
            + sl_total
        )
        self.stdout.write("")
        self.stdout.write(
            self.style.NOTICE(
                f"  Approximate total INSERT rows: {total_writes:,}",
            ),
        )

        # ── Write JSON report if requested ─────────────────────────────────
        if json_out:
            path = Path(json_out).expanduser().resolve()
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("w") as fh:
                json.dump(report, fh, indent=2, default=str)
            self.stdout.write("")
            self.stdout.write(
                self.style.SUCCESS(f"Wrote JSON report to {path}"),
            )

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS("Audit complete. No writes were performed."),
        )

    # ── helpers ───────────────────────────────────────────────────────────

    def _banner(self, year: int | None) -> None:
        text = "Legacy data audit (READ-ONLY)"
        if year is not None:
            text += f" — filter year={year}"
        bar = "═" * (len(text) + 4)
        self.stdout.write("")
        self.stdout.write(bar)
        self.stdout.write(f"  {text}")
        self.stdout.write(bar)

    def _section(self, title: str) -> None:
        self.stdout.write("")
        self.stdout.write(self.style.MIGRATE_HEADING(f"── {title} ──"))
