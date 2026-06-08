"""Merge duplicate Person records (loser into winner).

Dry-run by default. Re-points Memberships, group memberships, Reflections,
Observations, and related FKs before deleting the loser.

Usage
-----
    python manage.py merge_persons --org-slug clc --winner 42 --loser 99
    python manage.py merge_persons --org-slug clc --winner 42 --loser 99 --apply
    python manage.py merge_persons --org-slug clc --winner 42 --loser 99 --apply --force-user
"""
from __future__ import annotations

from typing import Any

from django.core.management.base import BaseCommand
from django.core.management.base import CommandError

from bunk_logs.core.models import Organization
from bunk_logs.core.models import Person
from bunk_logs.core.person_merge import merge_persons
from bunk_logs.core.person_merge import plan_person_merge


class Command(BaseCommand):
    help = "Merge duplicate Person records by re-pointing FKs from loser to winner."

    def add_arguments(self, parser) -> None:
        parser.add_argument("--org-slug", default="clc", help="Organization slug.")
        parser.add_argument("--winner", type=int, required=True, help="Canonical Person pk to keep.")
        parser.add_argument("--loser", type=int, required=True, help="Duplicate Person pk to merge away.")
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Perform the merge. Default is dry-run plan only.",
        )
        parser.add_argument(
            "--force-user",
            action="store_true",
            help="When both Persons link to different Users, keep winner's User and unlink loser's.",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        org_slug: str = options["org_slug"]
        winner_id: int = options["winner"]
        loser_id: int = options["loser"]
        apply: bool = options["apply"]
        force_user: bool = options["force_user"]

        try:
            org = Organization.objects.get(slug=org_slug)
        except Organization.DoesNotExist as exc:
            msg = f"Organization not found: {org_slug!r}"
            raise CommandError(msg) from exc

        try:
            winner = Person.all_objects.get(pk=winner_id, organization=org)
            loser = Person.all_objects.get(pk=loser_id, organization=org)
        except Person.DoesNotExist as exc:
            msg = f"Person not found in org {org_slug!r}: {exc}"
            raise CommandError(msg) from exc

        plan = plan_person_merge(winner=winner, loser=loser)
        user_blocker = (
            winner.user_id
            and loser.user_id
            and winner.user_id != loser.user_id
            and not force_user
        )

        self.stdout.write(
            f"Merge plan: keep Person #{winner.id} ({winner.full_name}), "
            f"remove Person #{loser.id} ({loser.full_name})",
        )
        if plan.blockers:
            for blocker in plan.blockers:
                self.stdout.write(self.style.ERROR(f"  BLOCKER: {blocker}"))
        for action in plan.actions:
            suffix = f" (x{action.count})" if action.count > 1 else ""
            self.stdout.write(f"  [{action.model}] {action.description}{suffix}")

        if user_blocker:
            msg = "Merge blocked: both Persons link to different Users. Use --force-user."
            raise CommandError(msg)

        if plan.blockers:
            msg = "Merge blocked; resolve blockers before applying."
            raise CommandError(msg)

        if not apply:
            self.stdout.write(self.style.WARNING("Dry-run only — pass --apply to execute."))
            return

        try:
            merge_persons(winner=winner, loser=loser, force_user=force_user)
        except ValueError as exc:
            raise CommandError(str(exc)) from exc

        self.stdout.write(self.style.SUCCESS(f"Merged Person #{loser_id} into #{winner_id}."))
