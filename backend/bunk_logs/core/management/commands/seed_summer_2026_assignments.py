"""Seed TemplateAssignment rows for the CLC Summer 2026 program (Step 7_22).

Idempotent: keyed on ``(program, template, target_type='role', target_payload['role'])``.
Existing scheduled/active rows get title/is_required reconciled in-place; ended or
cancelled rows are left alone (a fresh scheduled row is added alongside with a
warning, per acceptance criterion 8 — never resurrect).

Usage
-----
    python manage.py seed_summer_2026_assignments \
        --org-slug clc --program-slug summer-2026 \
        [--dry-run] [--actor-username <email>]
"""
from __future__ import annotations

from typing import Any

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.core.management.base import CommandError
from django.db import transaction

from bunk_logs.core.models import Membership
from bunk_logs.core.models import Organization
from bunk_logs.core.models import Program
from bunk_logs.core.models import ReflectionTemplate
from bunk_logs.core.models import TemplateAssignment

User = get_user_model()

ASSIGNMENT_MANIFEST: list[dict[str, str]] = [
    {"role": "counselor",          "slug": "clc-2026-counselor-daily",            "title": "Counselor daily bunk log"},
    {"role": "junior_counselor",   "slug": "clc-2026-junior-counselor-daily",     "title": "Junior counselor daily reflection"},
    {"role": "general_counselor",  "slug": "clc-2026-general-counselor-daily",    "title": "General counselor daily reflection"},
    {"role": "specialist",         "slug": "clc-2026-specialist-daily",           "title": "Specialist daily reflection"},
    {"role": "unit_head",          "slug": "clc-2026-unit-head-daily",            "title": "Unit head daily reflection"},
    {"role": "leadership_team",    "slug": "clc-2026-leadership-biweekly",        "title": "Leadership team check-in (biweekly)"},
    {"role": "kitchen_staff",      "slug": "clc-2026-kitchen-daily",              "title": "Kitchen staff daily reflection"},
    {"role": "maintenance",        "slug": "clc-2026-maintenance-daily",          "title": "Maintenance daily reflection"},
    {"role": "housekeeping",       "slug": "clc-2026-housekeeping-daily",         "title": "Housekeeping daily reflection"},
    {"role": "camper_care",        "slug": "clc-2026-camper-care-daily",          "title": "Camper care daily reflection"},
    {"role": "health_center",      "slug": "clc-2026-health-center-daily",        "title": "Health center daily reflection"},
    {"role": "special_diets",      "slug": "clc-2026-special-diets-daily",        "title": "Special diets daily reflection"},
]

ACTOR_ROLES = ("admin", "leadership_team")


class Command(BaseCommand):
    help = "Seed TemplateAssignment rows for the CLC Summer 2026 program (idempotent)."

    def add_arguments(self, parser) -> None:
        parser.add_argument("--org-slug", required=True, help="Organization slug (e.g. clc).")
        parser.add_argument("--program-slug", required=True, help="Program slug (e.g. summer-2026).")
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Print what would be created/updated; make no DB writes.",
        )
        parser.add_argument(
            "--actor-username",
            default=None,
            help=(
                "Optional email of an admin or LT user in the target org. Their "
                "Membership becomes ``created_by`` on each new row."
            ),
        )

    def handle(self, *args: Any, **opts: Any) -> None:
        org = self._get_org(opts["org_slug"])
        program = self._get_program(org, opts["program_slug"])
        actor = self._resolve_actor(org, opts.get("actor_username"))
        plan = self._build_plan(org, program)

        if opts["dry_run"]:
            self._print_plan(plan)
            return

        created = updated = unchanged = resurrected_warnings = 0
        with transaction.atomic():
            for entry in plan:
                outcome = self._upsert_assignment(entry, actor=actor)
                if outcome == "created":
                    created += 1
                elif outcome == "updated":
                    updated += 1
                elif outcome == "unchanged":
                    unchanged += 1
                if outcome == "created-after-ended":
                    resurrected_warnings += 1
                    created += 1

        summary = (
            f"Seeded {len(plan)} assignments — "
            f"{created} created, {updated} updated, {unchanged} unchanged."
        )
        if resurrected_warnings:
            summary += (
                f" ({resurrected_warnings} created alongside pre-existing "
                f"ended/cancelled rows.)"
            )
        self.stdout.write(self.style.SUCCESS(summary))

    # ── plan construction ────────────────────────────────────────────────

    def _get_org(self, slug: str) -> Organization:
        try:
            return Organization.objects.get(slug=slug)
        except Organization.DoesNotExist as exc:
            msg = f"Organization with slug {slug!r} does not exist."
            raise CommandError(msg) from exc

    def _get_program(self, org: Organization, slug: str) -> Program:
        try:
            return Program.all_objects.get(organization=org, slug=slug)
        except Program.DoesNotExist as exc:
            msg = (
                f"Program with slug {slug!r} does not exist in org "
                f"{org.slug!r}."
            )
            raise CommandError(msg) from exc

    def _resolve_actor(
        self,
        org: Organization,
        username: str | None,
    ) -> Membership | None:
        if not username:
            return None
        try:
            user = User.objects.get(email=username)
        except User.DoesNotExist as exc:
            msg = f"No user with email {username!r}."
            raise CommandError(msg) from exc

        membership = (
            Membership.all_objects.filter(
                person__user=user,
                program__organization=org,
                role__in=ACTOR_ROLES,
                is_active=True,
            )
            .order_by("-created_at")
            .first()
        )
        if not membership:
            roles = ", ".join(ACTOR_ROLES)
            msg = (
                f"User {username!r} has no active {roles} membership in org "
                f"{org.slug!r}."
            )
            raise CommandError(msg)
        return membership

    def _build_plan(self, org: Organization, program: Program) -> list[dict[str, Any]]:
        plan: list[dict[str, Any]] = []
        missing: list[str] = []
        for entry in ASSIGNMENT_MANIFEST:
            template = (
                ReflectionTemplate.all_objects.filter(
                    organization=org,
                    slug=entry["slug"],
                )
                .order_by("-version")
                .first()
            )
            if template is None:
                missing.append(entry["slug"])
                continue
            plan.append({
                "organization": org,
                "program": program,
                "template": template,
                "role": entry["role"],
                "title": entry["title"],
                "start_date": program.start_date,
                "end_date": program.end_date,
            })
        if missing:
            slugs = ", ".join(sorted(missing))
            msg = (
                f"Template(s) not found for org={org.slug}: {slugs}. "
                f"Run onboard_clc_summer_2026 first."
            )
            raise CommandError(msg)
        return plan

    # ── per-entry write ──────────────────────────────────────────────────

    def _upsert_assignment(
        self,
        entry: dict[str, Any],
        *,
        actor: Membership | None,
    ) -> str:
        existing = TemplateAssignment.all_objects.filter(
            program=entry["program"],
            template=entry["template"],
            target_type=TemplateAssignment.TargetType.ROLE,
            target_payload__role=entry["role"],
            status__in=[
                TemplateAssignment.Status.SCHEDULED,
                TemplateAssignment.Status.ACTIVE,
            ],
        ).first()

        if existing:
            changes: list[str] = []
            if existing.title != entry["title"]:
                existing.title = entry["title"]
                changes.append("title")
            if not existing.is_required:
                existing.is_required = True
                changes.append("is_required")
            if changes:
                existing.save(update_fields=[*changes, "updated_at"])
                self.stdout.write(
                    f"updated  role={entry['role']:<18} "
                    f"({', '.join(changes)})  #{existing.pk}",
                )
                return "updated"
            self.stdout.write(
                f"unchanged role={entry['role']:<18} "
                f"#{existing.pk}",
            )
            return "unchanged"

        # No active/scheduled row. Warn (don't fail) if a stale ended or
        # cancelled row exists for the same key — we add a fresh row
        # alongside rather than resurrecting it.
        stale_count = TemplateAssignment.all_objects.filter(
            program=entry["program"],
            template=entry["template"],
            target_type=TemplateAssignment.TargetType.ROLE,
            target_payload__role=entry["role"],
            status__in=[
                TemplateAssignment.Status.ENDED,
                TemplateAssignment.Status.CANCELLED,
            ],
        ).count()
        if stale_count:
            self.stdout.write(
                self.style.WARNING(
                    f"warn     role={entry['role']:<18} "
                    f"({stale_count} ended/cancelled row(s) exist — "
                    f"creating a fresh scheduled row alongside)",
                ),
            )

        new_assignment = TemplateAssignment.all_objects.create(
            organization=entry["organization"],
            program=entry["program"],
            template=entry["template"],
            target_type=TemplateAssignment.TargetType.ROLE,
            target_payload={"role": entry["role"]},
            start_date=entry["start_date"],
            end_date=entry["end_date"],
            cadence_override=None,
            is_required=True,
            title=entry["title"],
            status=TemplateAssignment.Status.SCHEDULED,
            created_by=actor,
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"created  role={entry['role']:<18} "
                f"#{new_assignment.pk}",
            ),
        )
        return "created-after-ended" if stale_count else "created"

    # ── dry-run reporting ────────────────────────────────────────────────

    def _print_plan(self, plan: list[dict[str, Any]]) -> None:
        self.stdout.write(self.style.WARNING("DRY-RUN: no database writes will occur.\n"))
        for entry in plan:
            existing = TemplateAssignment.all_objects.filter(
                program=entry["program"],
                template=entry["template"],
                target_type=TemplateAssignment.TargetType.ROLE,
                target_payload__role=entry["role"],
                status__in=[
                    TemplateAssignment.Status.SCHEDULED,
                    TemplateAssignment.Status.ACTIVE,
                ],
            ).first()
            if existing is None:
                action = "create"
            elif (
                existing.title != entry["title"]
                or not existing.is_required
            ):
                action = "update"
            else:
                action = "noop  "
            self.stdout.write(
                f"  {action}  role={entry['role']:<18} "
                f"template={entry['template'].slug:<40} "
                f"window={entry['start_date']}→{entry['end_date']}",
            )
        self.stdout.write(self.style.WARNING(f"\nTotal: {len(plan)} planned actions."))
