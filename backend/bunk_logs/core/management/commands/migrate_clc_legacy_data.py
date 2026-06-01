"""Migrate legacy CLC Summer 2025 data to the multi-tenant models.

Defaults to dry-run. Pass --apply to actually write. Safe to re-run: every phase
is idempotent (Person via external_ids, Membership/AGM via unique_together,
Reflection via deterministic client_submission_id UUID).

Prerequisite: run `setup_clc_summer_2025` first so Programs, AssignmentGroups,
and legacy templates exist.

Usage
-----
    # Default: dry-run, report only, no DB writes
    python manage.py migrate_clc_legacy_data

    # Actually apply changes:
    python manage.py migrate_clc_legacy_data --apply

    # Apply only a subset (for testing):
    python manage.py migrate_clc_legacy_data --apply --limit 100

    # Skip reflection migration (do persons/memberships/AGMs only):
    python manage.py migrate_clc_legacy_data --apply --skip-reflections

Phases (each idempotent, each in its own transaction)
-----------------------------------------------------
  1. Build lookup tables from existing AssignmentGroups / Programs / templates
  2. Migrate Camper rows -> Person rows
  3. Migrate User (staff) rows -> Person rows (linked to User via Person.user)
  4. Migrate CamperBunkAssignment -> Membership(role=camper) + AGM(role=subject)
  5. Migrate CounselorBunkAssignment -> Membership(role=counselor) + AGM(role=author)
  6. Migrate UnitStaffAssignment -> Membership(role=unit_head|camper_care)
  7. Backfill TemplateAssignment(target_type=assignment_group) per bunk AG so the
     legacy counselor template appears on the group dashboard for in-session dates
  8. Migrate BunkLog -> Reflection (legacy counselor template)
  9. Migrate StaffLog -> Reflection (legacy staff log template)
 10. Verification report
"""
from __future__ import annotations

import time
import uuid
from typing import TYPE_CHECKING
from typing import Any

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.core.management.base import CommandError
from django.db import transaction
from django.db.models import Q

from bunk_logs.bunklogs.models import BunkLog
from bunk_logs.bunklogs.models import StaffLog
from bunk_logs.bunks.models import CounselorBunkAssignment
from bunk_logs.bunks.models import Session
from bunk_logs.bunks.models import UnitStaffAssignment
from bunk_logs.campers.models import Camper
from bunk_logs.campers.models import CamperBunkAssignment
from bunk_logs.core.models import AssignmentGroup
from bunk_logs.core.models import AssignmentGroupMembership
from bunk_logs.core.models import Membership
from bunk_logs.core.models import Organization
from bunk_logs.core.models import Person
from bunk_logs.core.models import Program
from bunk_logs.core.models import Reflection
from bunk_logs.core.models import ReflectionTemplate
from bunk_logs.core.models import TemplateAssignment

if TYPE_CHECKING:
    from datetime import date

User = get_user_model()

ORG_SLUG = "clc"

# Legacy Session.name -> new Program.slug. Resolved at runtime to the
# actual Session ids via _get_programs() so tests and replayed DBs work
# regardless of insertion order.
SESSION_NAME_TO_PROGRAM_SLUG: dict[str, str] = {
    "Session 1 - 2025": "summer-2025-session-1",
    "Session 2 - 2025": "summer-2025-session-2",
}

LEGACY_COUNSELOR_TEMPLATE_SLUG = "clc-legacy-counselor-daily"
LEGACY_STAFF_LOG_TEMPLATE_SLUG = "clc-legacy-staff-log-daily"

# Fixed UUID namespace for deterministic Reflection.client_submission_id values.
# Generated once; do not change. If it changes, idempotency breaks.
LEGACY_UUID_NAMESPACE = uuid.UUID("8c6a2f10-b0c0-4000-a000-000000000001")

# Map old User.role (free-text) to new Membership role code.
# Anything not in this map gets logged as a warning and skipped for membership creation.
USER_ROLE_TO_MEMBERSHIP_ROLE: dict[str, str] = {
    "Counselor": "counselor",
    "Unit Head": "unit_head",
    "Camper Care": "camper_care",
    "Leadership": "leadership_team",
    "Kitchen Staff": "kitchen_staff",
    "Admin": "admin",
}

BATCH_SIZE = 500


def deterministic_uuid(kind: str, legacy_id: int) -> uuid.UUID:
    """Stable UUID for idempotent Reflection imports."""
    return uuid.uuid5(LEGACY_UUID_NAMESPACE, f"{kind}:{legacy_id}")


def bool_to_yn(value: bool | None) -> str:
    return "yes" if value else "no"


class Command(BaseCommand):
    help = "Migrate legacy CLC Summer 2025 data (Campers, assignments, BunkLogs, StaffLogs) to multi-tenant models."

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Actually write changes. Without this, runs in dry-run mode.",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=None,
            help="Limit each phase to N rows (for testing). No effect when omitted.",
        )
        parser.add_argument(
            "--skip-reflections",
            action="store_true",
            help="Migrate persons / memberships / AGMs only; skip BunkLog and StaffLog rows.",
        )
        parser.add_argument(
            "--skip-bunk-logs",
            action="store_true",
            help="Migrate everything except BunkLogs.",
        )
        parser.add_argument(
            "--skip-staff-logs",
            action="store_true",
            help="Migrate everything except StaffLogs.",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        self.apply: bool = options["apply"]
        self.limit: int | None = options["limit"]
        self.skip_reflections: bool = options["skip_reflections"]
        self.skip_bunk_logs: bool = options["skip_bunk_logs"] or self.skip_reflections
        self.skip_staff_logs: bool = options["skip_staff_logs"] or self.skip_reflections

        self._banner()
        if not self.apply:
            self.stdout.write(
                self.style.WARNING(
                    "DRY-RUN mode. No database writes will occur. Pass --apply to write.\n",
                ),
            )

        # ── Setup: prerequisites and lookups ───────────────────────────────
        self._step("1/10  Loading prerequisites + building lookups")
        org = self._get_org()
        programs = self._get_programs(org)  # legacy_session_id -> Program
        sessions = self._get_sessions(programs.keys())  # legacy_session_id -> Session
        bunk_ag_by_legacy_id = self._get_bunk_ag_map(org, programs)
        counselor_template, staff_template = self._get_legacy_templates(org)
        self._summarize_prereqs(programs, bunk_ag_by_legacy_id, counselor_template, staff_template)

        # ── Phase 2: Campers -> Persons ────────────────────────────────────
        self._step("2/10  Migrating Campers -> Persons")
        person_by_legacy_camper: dict[int, Person] = self._migrate_campers(org)

        # ── Phase 3: Users (staff) -> Persons ──────────────────────────────
        self._step("3/10  Migrating Users (staff) -> Persons")
        person_by_legacy_user: dict[int, Person] = self._migrate_staff_users(
            org, programs,
        )

        # ── Phase 4: Camper memberships + AGMs ─────────────────────────────
        self._step("4/10  Migrating CamperBunkAssignment -> Membership + AGM")
        self._migrate_camper_assignments(
            programs, bunk_ag_by_legacy_id, person_by_legacy_camper,
        )

        # ── Phase 5: Counselor memberships + AGMs ──────────────────────────
        self._step("5/10  Migrating CounselorBunkAssignment -> Membership + AGM")
        self._migrate_counselor_assignments(
            programs, bunk_ag_by_legacy_id, person_by_legacy_user,
        )

        # ── Phase 6: UH/CC memberships ─────────────────────────────────────
        self._step("6/10  Migrating UnitStaffAssignment -> Membership")
        self._migrate_unit_staff_assignments(programs, sessions, person_by_legacy_user)

        # ── Phase 7: Backfill TemplateAssignments ──────────────────────────
        self._step("7/10  Backfilling TemplateAssignments (counselor template -> bunk AGs)")
        self._backfill_template_assignments(
            org, programs, bunk_ag_by_legacy_id, counselor_template,
        )

        # ── Phase 8: BunkLogs -> Reflections ───────────────────────────────
        if self.skip_bunk_logs:
            self._step("8/10  BunkLogs -> Reflections   SKIPPED")
        else:
            self._step("8/10  Migrating BunkLogs -> Reflections")
            self._migrate_bunk_logs(
                org, programs, bunk_ag_by_legacy_id,
                person_by_legacy_camper, person_by_legacy_user,
                counselor_template,
            )

        # ── Phase 9: StaffLogs -> Reflections ──────────────────────────────
        if self.skip_staff_logs:
            self._step("9/10  StaffLogs -> Reflections   SKIPPED")
        else:
            self._step("9/10  Migrating StaffLogs -> Reflections")
            self._migrate_staff_logs(
                org, programs, sessions, person_by_legacy_user, staff_template,
            )

        # ── Phase 10: Verification ─────────────────────────────────────────
        self._step("10/10  Verification report")
        self._verify(org, programs)

        self.stdout.write("")
        if self.apply:
            self.stdout.write(self.style.SUCCESS("Migration complete."))
        else:
            self.stdout.write(
                self.style.WARNING("Dry-run complete. Re-run with --apply to write."),
            )

    # ── Prerequisites ─────────────────────────────────────────────────────

    def _get_org(self) -> Organization:
        try:
            return Organization.objects.get(slug=ORG_SLUG)
        except Organization.DoesNotExist as exc:
            msg = "Run `setup_clc_summer_2025` first."
            raise CommandError(msg) from exc

    def _get_programs(self, org: Organization) -> dict[int, Program]:
        """Resolve legacy Session ids -> Programs via name lookup."""
        out: dict[int, Program] = {}
        for legacy_name, slug in SESSION_NAME_TO_PROGRAM_SLUG.items():
            sess = Session.objects.filter(name=legacy_name).first()
            if sess is None:
                msg = (
                    f"Legacy Session {legacy_name!r} not found. "
                    "Run `setup_clc_summer_2025` first."
                )
                raise CommandError(msg)
            try:
                program = Program.all_objects.get(organization=org, slug=slug)
            except Program.DoesNotExist as exc:
                msg = (
                    f"Program {slug!r} not found. Run `setup_clc_summer_2025` first."
                )
                raise CommandError(msg) from exc
            out[sess.id] = program
        return out

    def _get_sessions(self, legacy_ids) -> dict[int, Session]:
        out: dict[int, Session] = {}
        for sid in legacy_ids:
            try:
                out[sid] = Session.objects.get(pk=sid)
            except Session.DoesNotExist as exc:
                msg = f"Legacy Session #{sid} not found in production data."
                raise CommandError(msg) from exc
        return out

    def _get_bunk_ag_map(
        self,
        org: Organization,
        programs: dict[int, Program],
    ) -> dict[int, AssignmentGroup]:
        """legacy Bunk.id -> AssignmentGroup (built from metadata['legacy_bunk_id']).

        Scoped to the 2025 Programs only so 2026 bunk AGs (created by
        setup_crane_lake / seed_summer_2026_assignments) don't bleed in.
        """
        out: dict[int, AssignmentGroup] = {}
        ags = AssignmentGroup.all_objects.filter(
            organization=org,
            program__in=programs.values(),
            group_type="bunk",
        ).select_related("program")
        for ag in ags:
            legacy_id = (ag.metadata or {}).get("legacy_bunk_id")
            if legacy_id is not None:
                out[int(legacy_id)] = ag
        if not out:
            msg = (
                "No Bunk AssignmentGroups with legacy_bunk_id metadata found "
                "for the 2025 Programs. Run `setup_clc_summer_2025` first."
            )
            raise CommandError(msg)
        return out

    def _get_legacy_templates(
        self,
        org: Organization,
    ) -> tuple[ReflectionTemplate, ReflectionTemplate]:
        try:
            counselor_tpl = ReflectionTemplate.all_objects.get(
                organization=org, slug=LEGACY_COUNSELOR_TEMPLATE_SLUG,
            )
            staff_tpl = ReflectionTemplate.all_objects.get(
                organization=org, slug=LEGACY_STAFF_LOG_TEMPLATE_SLUG,
            )
        except ReflectionTemplate.DoesNotExist as exc:
            msg = (
                "Legacy ReflectionTemplates not found. "
                "Run `setup_clc_summer_2025` first."
            )
            raise CommandError(msg) from exc
        return counselor_tpl, staff_tpl

    def _summarize_prereqs(
        self,
        programs: dict[int, Program],
        bunk_ag_by_legacy_id: dict[int, AssignmentGroup],
        counselor_tpl: ReflectionTemplate,
        staff_tpl: ReflectionTemplate,
    ) -> None:
        self.stdout.write(f"  ✓ {len(programs)} Programs loaded")
        self.stdout.write(f"  ✓ {len(bunk_ag_by_legacy_id)} Bunk AssignmentGroups indexed")
        self.stdout.write(f"  ✓ Legacy counselor template: {counselor_tpl.slug} (pk={counselor_tpl.pk})")
        self.stdout.write(f"  ✓ Legacy staff log template: {staff_tpl.slug} (pk={staff_tpl.pk})")

    # ── Phase 2: Campers -> Persons ───────────────────────────────────────

    def _migrate_campers(self, org: Organization) -> dict[int, Person]:
        """Returns legacy_camper_id -> Person."""
        qs = Camper.objects.all().order_by("id")
        if self.limit:
            qs = qs[: self.limit]

        out: dict[int, Person] = {}
        created = updated = unchanged = 0
        t0 = time.time()

        for camper in qs.iterator(chunk_size=BATCH_SIZE):
            existing = Person.all_objects.filter(
                organization=org,
                external_ids__legacy_camper_id=camper.id,
            ).first()

            if existing is not None:
                # Already migrated; just update name/dob if drift.
                changed = self._maybe_update_person_fields(existing, camper)
                if changed and self.apply:
                    existing.save()
                    updated += 1
                else:
                    unchanged += 1
                out[camper.id] = existing
            else:
                if self.apply:
                    person = Person.all_objects.create(
                        organization=org,
                        first_name=camper.first_name or "",
                        last_name=camper.last_name or "",
                        date_of_birth=camper.date_of_birth,
                        external_ids={"legacy_camper_id": camper.id},
                        notes=(camper.camper_notes or "")[:65000],
                    )
                    out[camper.id] = person
                created += 1

        self._phase_report("campers", created, updated, unchanged, t0)
        return out

    def _maybe_update_person_fields(self, person: Person, camper: Camper) -> bool:
        changed = False
        if (camper.first_name or "") and person.first_name != (camper.first_name or ""):
            person.first_name = camper.first_name
            changed = True
        if (camper.last_name or "") and person.last_name != (camper.last_name or ""):
            person.last_name = camper.last_name
            changed = True
        if camper.date_of_birth and person.date_of_birth != camper.date_of_birth:
            person.date_of_birth = camper.date_of_birth
            changed = True
        return changed

    # ── Phase 3: Users (staff) -> Persons ─────────────────────────────────

    def _migrate_staff_users(
        self,
        org: Organization,
        programs: dict[int, Program],
    ) -> dict[int, Person]:
        """Returns legacy_user_id -> Person, linking Person.user FK to existing User."""
        legacy_session_ids = list(programs.keys())
        # Only migrate Users who appear in 2025 staff data
        user_ids = set()
        user_ids.update(
            CounselorBunkAssignment.objects
            .filter(bunk__session_id__in=legacy_session_ids)
            .values_list("counselor_id", flat=True),
        )
        user_ids.update(
            UnitStaffAssignment.objects.values_list("staff_member_id", flat=True),
        )
        user_ids.update(
            BunkLog.objects
            .filter(bunk_assignment__bunk__session_id__in=legacy_session_ids)
            .values_list("counselor_id", flat=True),
        )
        user_ids.update(
            StaffLog.objects.filter(date__year=2025).values_list("staff_member_id", flat=True),
        )

        qs = User.objects.filter(id__in=user_ids).order_by("id")
        if self.limit:
            qs = qs[: self.limit]

        out: dict[int, Person] = {}
        created = updated = unchanged = 0
        t0 = time.time()

        for user in qs.iterator(chunk_size=BATCH_SIZE):
            # Prefer matching by Person.user FK (one-to-one).
            existing = Person.all_objects.filter(
                organization=org, user=user,
            ).first()

            # Fallback: external_ids match (handles re-runs before user FK was linked)
            if existing is None:
                existing = Person.all_objects.filter(
                    organization=org,
                    external_ids__legacy_user_id=user.id,
                ).first()

            if existing is not None:
                changed = self._maybe_update_staff_person_fields(existing, user)
                if changed and self.apply:
                    existing.save()
                    updated += 1
                else:
                    unchanged += 1
                out[user.id] = existing
            else:
                if self.apply:
                    person = Person.all_objects.create(
                        organization=org,
                        first_name=(user.first_name or "")[:100],
                        last_name=(user.last_name or "")[:100],
                        email=user.email or "",
                        user=user,
                        external_ids={"legacy_user_id": user.id},
                    )
                    out[user.id] = person
                created += 1

        self._phase_report("staff users", created, updated, unchanged, t0)
        return out

    def _maybe_update_staff_person_fields(self, person: Person, user) -> bool:
        changed = False
        if person.user_id != user.id:
            person.user = user
            changed = True
        ext = dict(person.external_ids or {})
        if ext.get("legacy_user_id") != user.id:
            ext["legacy_user_id"] = user.id
            person.external_ids = ext
            changed = True
        if user.email and person.email != user.email:
            person.email = user.email
            changed = True
        return changed

    # ── Phase 4: Camper assignments ───────────────────────────────────────

    def _migrate_camper_assignments(
        self,
        programs: dict[int, Program],
        bunk_ag_by_legacy_id: dict[int, AssignmentGroup],
        person_by_legacy_camper: dict[int, Person],
    ) -> None:
        qs = (
            CamperBunkAssignment.objects
            .filter(bunk__session_id__in=programs.keys())
            .select_related("bunk", "bunk__session", "camper")
            .order_by("id")
        )
        if self.limit:
            qs = qs[: self.limit]

        ms_created = ms_skipped = 0
        agm_created = agm_skipped = 0
        warnings = 0
        t0 = time.time()

        for cba in qs.iterator(chunk_size=BATCH_SIZE):
            person = person_by_legacy_camper.get(cba.camper_id)
            program = programs.get(cba.bunk.session_id)
            bunk_ag = bunk_ag_by_legacy_id.get(cba.bunk_id)

            if person is None or program is None or bunk_ag is None:
                warnings += 1
                continue

            # Create Membership (role=camper)
            if self.apply:
                _, created = Membership.all_objects.get_or_create(
                    program=program,
                    person=person,
                    role="camper",
                    defaults={
                        "start_date": cba.start_date,
                        "end_date": cba.end_date,
                        "is_active": cba.is_active,
                        "metadata": {"legacy_camper_bunk_assignment_id": cba.id},
                    },
                )
                if created:
                    ms_created += 1
                else:
                    ms_skipped += 1
            else:
                ms_created += 1

            # Create AssignmentGroupMembership (role=subject in the bunk)
            if self.apply:
                _, created = AssignmentGroupMembership.all_objects.get_or_create(
                    group=bunk_ag,
                    person=person,
                    role_in_group="subject",
                    defaults={
                        "start_date": cba.start_date,
                        "end_date": cba.end_date,
                        "is_active": cba.is_active,
                        "metadata": {"legacy_camper_bunk_assignment_id": cba.id},
                    },
                )
                if created:
                    agm_created += 1
                else:
                    agm_skipped += 1
            else:
                agm_created += 1

        self._phase_report(
            "camper assignments",
            ms_created, ms_skipped, 0, t0,
            extra=f"AGMs: {agm_created} created, {agm_skipped} existing; "
                  f"{warnings} skipped (missing lookup)",
        )

    # ── Phase 5: Counselor assignments ────────────────────────────────────

    def _migrate_counselor_assignments(
        self,
        programs: dict[int, Program],
        bunk_ag_by_legacy_id: dict[int, AssignmentGroup],
        person_by_legacy_user: dict[int, Person],
    ) -> None:
        qs = (
            CounselorBunkAssignment.objects
            .filter(bunk__session_id__in=programs.keys())
            .select_related("bunk", "bunk__session", "counselor")
            .order_by("id")
        )
        if self.limit:
            qs = qs[: self.limit]

        ms_created = ms_skipped = 0
        agm_created = agm_skipped = 0
        warnings = 0
        t0 = time.time()

        for ccba in qs.iterator(chunk_size=BATCH_SIZE):
            person = person_by_legacy_user.get(ccba.counselor_id)
            program = programs.get(ccba.bunk.session_id)
            bunk_ag = bunk_ag_by_legacy_id.get(ccba.bunk_id)

            if person is None or program is None or bunk_ag is None:
                warnings += 1
                continue

            if self.apply:
                _, created = Membership.all_objects.get_or_create(
                    program=program,
                    person=person,
                    role="counselor",
                    defaults={
                        "start_date": ccba.start_date,
                        "end_date": ccba.end_date,
                        "is_active": True,
                        "metadata": {"legacy_counselor_bunk_assignment_id": ccba.id},
                    },
                )
                if created:
                    ms_created += 1
                else:
                    ms_skipped += 1
            else:
                ms_created += 1

            if self.apply:
                _, created = AssignmentGroupMembership.all_objects.get_or_create(
                    group=bunk_ag,
                    person=person,
                    role_in_group="author",
                    defaults={
                        "start_date": ccba.start_date,
                        "end_date": ccba.end_date,
                        "is_active": True,
                        "metadata": {
                            "legacy_counselor_bunk_assignment_id": ccba.id,
                            "is_lead_counselor": bool(ccba.is_primary),
                        },
                    },
                )
                if created:
                    agm_created += 1
                else:
                    agm_skipped += 1
            else:
                agm_created += 1

        self._phase_report(
            "counselor assignments",
            ms_created, ms_skipped, 0, t0,
            extra=f"AGMs: {agm_created} created, {agm_skipped} existing; "
                  f"{warnings} skipped (missing lookup)",
        )

    # ── Phase 6: UH/CC assignments ────────────────────────────────────────

    def _migrate_unit_staff_assignments(
        self,
        programs: dict[int, Program],
        sessions: dict[int, Session],
        person_by_legacy_user: dict[int, Person],
    ) -> None:
        qs = UnitStaffAssignment.objects.select_related("staff_member").order_by("id")
        if self.limit:
            qs = qs[: self.limit]

        ms_created = ms_skipped = warnings = 0
        t0 = time.time()

        for usa in qs.iterator(chunk_size=BATCH_SIZE):
            person = person_by_legacy_user.get(usa.staff_member_id)
            if person is None:
                warnings += 1
                continue

            # Match to every session whose date window overlaps the USA's window.
            for legacy_session_id, program in programs.items():
                sess = sessions[legacy_session_id]
                if not self._date_ranges_overlap(
                    usa.start_date, usa.end_date,
                    sess.start_date, sess.end_date,
                ):
                    continue

                role_code = usa.role  # already "unit_head" or "camper_care"
                if self.apply:
                    _, created = Membership.all_objects.get_or_create(
                        program=program,
                        person=person,
                        role=role_code,
                        defaults={
                            "start_date": max(usa.start_date, sess.start_date) if usa.start_date else sess.start_date,
                            "end_date": (
                                min(usa.end_date, sess.end_date) if usa.end_date else sess.end_date
                            ),
                            "is_active": True,
                            "metadata": {
                                "legacy_unit_staff_assignment_id": usa.id,
                                "legacy_unit_id": usa.unit_id,
                                "is_primary": bool(usa.is_primary),
                            },
                        },
                    )
                    if created:
                        ms_created += 1
                    else:
                        ms_skipped += 1
                else:
                    ms_created += 1

        self._phase_report(
            "UH/CC assignments",
            ms_created, ms_skipped, 0, t0,
            extra=f"{warnings} skipped (missing User->Person lookup)",
        )

    @staticmethod
    def _date_ranges_overlap(
        a_start: date | None, a_end: date | None,
        b_start: date, b_end: date,
    ) -> bool:
        if a_start is None:
            return True
        if a_end is None:
            return a_start <= b_end
        return a_start <= b_end and a_end >= b_start

    # ── Phase 7: Backfill TemplateAssignments ─────────────────────────────

    def _backfill_template_assignments(
        self,
        org: Organization,
        programs: dict[int, Program],
        bunk_ag_by_legacy_id: dict[int, AssignmentGroup],
        counselor_template: ReflectionTemplate,
    ) -> None:
        """Create one assignment_group TemplateAssignment per bunk AG.

        The group dashboard surfaces templates via TemplateAssignment rows
        (target_type='assignment_group'). Legacy data has Reflections but no
        such assignments, so the legacy counselor template would never appear
        on a 2025 group page. We backfill one assignment per bunk AG spanning
        the whole program (session) window so any in-session date shows the
        card — even days with zero reflections. Status='ended' since the
        programs are historical; the dashboard includes ended assignments.

        Idempotent: skips a bunk AG that already has an assignment_group
        assignment for this template.
        """
        created = skipped = warnings = 0
        t0 = time.time()

        for bunk_ag in bunk_ag_by_legacy_id.values():
            program = bunk_ag.program
            if program is None or program.start_date is None:
                warnings += 1
                continue

            exists = TemplateAssignment.all_objects.filter(
                template=counselor_template,
                assignment_group=bunk_ag,
                target_type=TemplateAssignment.TargetType.ASSIGNMENT_GROUP,
            ).exists()
            if exists:
                skipped += 1
                continue

            if self.apply:
                TemplateAssignment.all_objects.create(
                    organization=org,
                    program=program,
                    template=counselor_template,
                    target_type=TemplateAssignment.TargetType.ASSIGNMENT_GROUP,
                    target_payload={"legacy_backfill": True},
                    assignment_group=bunk_ag,
                    start_date=program.start_date,
                    end_date=program.end_date,
                    status=TemplateAssignment.Status.ENDED,
                    is_required=True,
                )
            created += 1

        self._phase_report(
            "template assignments", created, skipped, 0, t0,
            extra=f"{warnings} skipped (bunk AG missing program/dates)",
        )

    # ── Phase 8: BunkLogs -> Reflections ──────────────────────────────────

    def _migrate_bunk_logs(
        self,
        org: Organization,
        programs: dict[int, Program],
        bunk_ag_by_legacy_id: dict[int, AssignmentGroup],
        person_by_legacy_camper: dict[int, Person],
        person_by_legacy_user: dict[int, Person],
        template: ReflectionTemplate,
    ) -> None:
        qs = (
            BunkLog.objects
            .filter(bunk_assignment__bunk__session_id__in=programs.keys())
            .select_related("bunk_assignment", "bunk_assignment__bunk", "bunk_assignment__camper")
            .order_by("id")
        )
        total = qs.count()
        if self.limit:
            qs = qs[: self.limit]
            total = min(total, self.limit)

        created = skipped = warnings = 0
        t0 = time.time()

        for i, bl in enumerate(qs.iterator(chunk_size=BATCH_SIZE), start=1):
            cba = bl.bunk_assignment
            bunk = cba.bunk

            subject = person_by_legacy_camper.get(cba.camper_id)
            author = person_by_legacy_user.get(bl.counselor_id)
            program = programs.get(bunk.session_id)
            bunk_ag = bunk_ag_by_legacy_id.get(bunk.id)

            if not all((subject, author, program, bunk_ag)):
                warnings += 1
                continue

            answers = self._build_bunk_log_answers(bl)
            csid = deterministic_uuid("bunklog", bl.id)

            if self.apply:
                try:
                    with transaction.atomic():
                        existing = Reflection.all_objects.filter(
                            program=program, client_submission_id=csid,
                        ).first()
                        if existing is not None:
                            skipped += 1
                        else:
                            Reflection.all_objects.create(
                                organization=org,
                                program=program,
                                subject=subject,
                                author=author,
                                assignment_group=bunk_ag,
                                template=template,
                                submitted_by=bl.counselor,
                                period_start=bl.date,
                                period_end=bl.date,
                                answers=answers,
                                language="en",
                                is_complete=True,
                                client_submission_id=csid,
                            )
                            created += 1
                except Exception as exc:
                    warnings += 1
                    self.stderr.write(
                        self.style.WARNING(
                            f"    BunkLog #{bl.id} failed: {exc}",
                        ),
                    )
            else:
                created += 1

            if i % 1000 == 0:
                elapsed = time.time() - t0
                rate = i / elapsed if elapsed else 0
                self.stdout.write(
                    f"    ... {i:>6,} / {total:,} processed "
                    f"({rate:.0f}/s, {elapsed:.0f}s elapsed)",
                )

        self._phase_report(
            "bunk logs", created, skipped, 0, t0,
            extra=f"{warnings} warnings/skipped",
        )

    def _build_bunk_log_answers(self, bl: BunkLog) -> dict[str, Any]:
        answers: dict[str, Any] = {
            "not_on_camp": bool_to_yn(bl.not_on_camp),
            "request_unit_head_help": bool_to_yn(bl.request_unit_head_help),
            "request_camper_care_help": bool_to_yn(bl.request_camper_care_help),
        }
        scores = {}
        if bl.behavior_score is not None:
            scores["behavior"] = bl.behavior_score
        if bl.participation_score is not None:
            scores["participation"] = bl.participation_score
        if bl.social_score is not None:
            scores["social"] = bl.social_score
        if scores:
            answers["camper_scores"] = scores
        if (bl.description or "").strip():
            answers["daily_report"] = bl.description
        return answers

    # ── Phase 8: StaffLogs -> Reflections ─────────────────────────────────

    def _migrate_staff_logs(
        self,
        org: Organization,
        programs: dict[int, Program],
        sessions: dict[int, Session],
        person_by_legacy_user: dict[int, Person],
        template: ReflectionTemplate,
    ) -> None:
        # Filter: must be in 2025, AND date must fall in a known session window.
        session_window = Q()
        for sess in sessions.values():
            session_window |= Q(date__gte=sess.start_date, date__lte=sess.end_date)

        qs = (
            StaffLog.objects
            .filter(date__year=2025)
            .filter(session_window)
            .select_related("staff_member")
            .order_by("id")
        )
        total = qs.count()
        if self.limit:
            qs = qs[: self.limit]
            total = min(total, self.limit)

        created = skipped = warnings = 0
        t0 = time.time()

        for i, sl in enumerate(qs.iterator(chunk_size=BATCH_SIZE), start=1):
            person = person_by_legacy_user.get(sl.staff_member_id)
            program = self._pick_program_for_date(sl.date, sessions, programs)

            if not all((person, program)):
                warnings += 1
                continue

            answers = self._build_staff_log_answers(sl)
            csid = deterministic_uuid("stafflog", sl.id)

            if self.apply:
                try:
                    with transaction.atomic():
                        existing = Reflection.all_objects.filter(
                            program=program, client_submission_id=csid,
                        ).first()
                        if existing is not None:
                            skipped += 1
                        else:
                            Reflection.all_objects.create(
                                organization=org,
                                program=program,
                                subject=person,
                                author=person,
                                assignment_group=None,
                                template=template,
                                submitted_by=sl.staff_member,
                                period_start=sl.date,
                                period_end=sl.date,
                                answers=answers,
                                language="en",
                                is_complete=True,
                                client_submission_id=csid,
                            )
                            created += 1
                except Exception as exc:
                    warnings += 1
                    self.stderr.write(
                        self.style.WARNING(
                            f"    StaffLog #{sl.id} failed: {exc}",
                        ),
                    )
            else:
                created += 1

            if i % 500 == 0:
                elapsed = time.time() - t0
                rate = i / elapsed if elapsed else 0
                self.stdout.write(
                    f"    ... {i:>6,} / {total:,} processed "
                    f"({rate:.0f}/s, {elapsed:.0f}s elapsed)",
                )

        self._phase_report(
            "staff logs", created, skipped, 0, t0,
            extra=f"{warnings} warnings/skipped",
        )

    def _build_staff_log_answers(self, sl: StaffLog) -> dict[str, Any]:
        return {
            "day_off": bool_to_yn(sl.day_off),
            "day_quality_score": sl.day_quality_score,
            "support_level_score": sl.support_level_score,
            "elaboration": sl.elaboration or "",
            "staff_care_support_needed": bool_to_yn(sl.staff_care_support_needed),
            "values_reflection": sl.values_reflection or "",
        }

    @staticmethod
    def _pick_program_for_date(
        d: date,
        sessions: dict[int, Session],
        programs: dict[int, Program],
    ) -> Program | None:
        """Pick the program whose session window contains `d`.

        Session 1 and Session 2 share the boundary day 2025-07-26. Tie-breaker:
        Session 2 wins (the later session) since staff typically transition that
        morning. Adjust here if reporting wants the other convention.
        """
        # Iterate in reverse-start-date order so the later session wins ties.
        ordered = sorted(
            sessions.items(),
            key=lambda kv: kv[1].start_date,
            reverse=True,
        )
        for sid, sess in ordered:
            if sess.start_date <= d <= sess.end_date:
                return programs.get(sid)
        return None

    # ── Phase 9: Verification ─────────────────────────────────────────────

    def _verify(
        self,
        org: Organization,
        programs: dict[int, Program],
    ) -> None:
        n_persons = Person.all_objects.filter(organization=org).count()
        n_legacy_campers = Person.all_objects.filter(
            organization=org,
            external_ids__has_key="legacy_camper_id",
        ).count()
        n_legacy_users = Person.all_objects.filter(
            organization=org,
            external_ids__has_key="legacy_user_id",
        ).count()
        n_memberships = Membership.all_objects.filter(
            program__in=programs.values(),
        ).count()
        n_agms = AssignmentGroupMembership.all_objects.filter(
            group__program__in=programs.values(),
        ).count()
        n_legacy_reflections = Reflection.all_objects.filter(
            program__in=programs.values(),
            template__slug__in=[
                LEGACY_COUNSELOR_TEMPLATE_SLUG, LEGACY_STAFF_LOG_TEMPLATE_SLUG,
            ],
        ).count()
        n_bunk_log_refs = Reflection.all_objects.filter(
            program__in=programs.values(),
            template__slug=LEGACY_COUNSELOR_TEMPLATE_SLUG,
        ).count()
        n_staff_log_refs = Reflection.all_objects.filter(
            program__in=programs.values(),
            template__slug=LEGACY_STAFF_LOG_TEMPLATE_SLUG,
        ).count()
        n_template_assignments = TemplateAssignment.all_objects.filter(
            program__in=programs.values(),
            target_type=TemplateAssignment.TargetType.ASSIGNMENT_GROUP,
            template__slug=LEGACY_COUNSELOR_TEMPLATE_SLUG,
        ).count()

        # Source-of-truth counts
        n_campers_src = Camper.objects.count()
        n_cba_src = CamperBunkAssignment.objects.filter(
            bunk__session_id__in=programs.keys(),
        ).count()
        n_ccba_src = CounselorBunkAssignment.objects.filter(
            bunk__session_id__in=programs.keys(),
        ).count()
        n_bunklog_src = BunkLog.objects.filter(
            bunk_assignment__bunk__session_id__in=programs.keys(),
        ).count()

        self.stdout.write(f"  Persons total:                       {n_persons}")
        self.stdout.write(f"    with legacy_camper_id:             {n_legacy_campers} / {n_campers_src} source")
        self.stdout.write(f"    with legacy_user_id:               {n_legacy_users}")
        self.stdout.write(f"  Memberships (2025 programs):         {n_memberships}")
        self.stdout.write(f"    (sources: {n_cba_src} CBA + {n_ccba_src} CCBA + UH/CC USAs)")
        self.stdout.write(f"  AssignmentGroupMemberships:          {n_agms}")
        self.stdout.write(f"  Reflections (legacy):                {n_legacy_reflections}")
        self.stdout.write(f"    from BunkLogs:                     {n_bunk_log_refs} / {n_bunklog_src} source")
        self.stdout.write(f"    from StaffLogs:                    {n_staff_log_refs}")
        self.stdout.write(f"  TemplateAssignments (bunk AGs):      {n_template_assignments}")

    # ── helpers ───────────────────────────────────────────────────────────

    def _phase_report(
        self,
        label: str,
        created: int,
        existing: int,
        unchanged: int,
        t0: float,
        *,
        extra: str = "",
    ) -> None:
        elapsed = time.time() - t0
        verb = "Would create" if not self.apply else "Created"
        msg = (
            f"  → {verb} {created} {label}; {existing} already existed; "
            f"{unchanged} unchanged.  ({elapsed:.1f}s)"
        )
        if extra:
            msg += f"\n    {extra}"
        self.stdout.write(self.style.SUCCESS(msg))

    def _banner(self) -> None:
        text = "CLC Legacy Data Migration (Summer 2025)"
        bar = "═" * (len(text) + 4)
        self.stdout.write("")
        self.stdout.write(bar)
        self.stdout.write(f"  {text}")
        self.stdout.write(bar)

    def _step(self, text: str) -> None:
        self.stdout.write("")
        self.stdout.write(self.style.MIGRATE_HEADING(f"▶  {text}"))
