"""Read-only audit of duplicate Person/User identity issues within an org.

Safe to run against production. Performs zero writes.

Usage
-----
    python manage.py audit_duplicate_identities --org-slug clc
    python manage.py audit_duplicate_identities --org-slug clc --json-out /tmp/dup-audit.json
"""
from __future__ import annotations

import json
from collections import defaultdict
from typing import Any

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.core.management.base import CommandError
from django.db.models import Count
from django.db.models.functions import Lower

from bunk_logs.core.models import Organization
from bunk_logs.core.models import Person

User = get_user_model()


def _person_campminder_id(person: Person) -> str:
    return str(person.external_ids.get("campminder_id") or "").strip()


class Command(BaseCommand):
    help = "Read-only audit of duplicate Person/User identity issues."

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--org-slug",
            default="clc",
            help="Organization slug to scope Person checks (default: clc).",
        )
        parser.add_argument(
            "--json-out",
            default=None,
            help="Optional path for machine-readable JSON output.",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        org_slug: str = options["org_slug"]
        json_out: str | None = options["json_out"]

        try:
            org = Organization.objects.get(slug=org_slug)
        except Organization.DoesNotExist as exc:
            msg = f"Organization not found: {org_slug!r}"
            raise CommandError(msg) from exc

        report: dict[str, Any] = {"org_slug": org_slug, "org_id": org.id}

        self.stdout.write(self.style.MIGRATE_HEADING(f"Duplicate identity audit — org {org_slug!r}"))

        # ── 1A. Duplicate Person emails (case-insensitive) ─────────────────
        email_groups: dict[str, list[dict]] = defaultdict(list)
        for person in Person.all_objects.filter(organization=org).exclude(email=""):
            key = person.email.strip().lower()
            email_groups[key].append({
                "id": person.id,
                "email": person.email,
                "name": person.full_name,
                "campminder_id": _person_campminder_id(person),
                "user_id": person.user_id,
                "legacy_user_id": person.external_ids.get("legacy_user_id"),
            })
        dup_emails = {email: rows for email, rows in email_groups.items() if len(rows) > 1}
        report["duplicate_person_emails"] = dup_emails
        self._section(f"Duplicate Person emails ({len(dup_emails)} groups)")
        for email, rows in sorted(dup_emails.items()):
            ids = ", ".join(f"#{r['id']}" for r in rows)
            self.stdout.write(f"  {email}: {ids}")

        # ── Legacy staff without Campminder ID ─────────────────────────────
        legacy_qs = Person.all_objects.filter(
            organization=org,
            external_ids__campminder_id__isnull=True,
        ).exclude(user__isnull=True)
        legacy_without_cm = [
            {
                "id": p.id,
                "name": p.full_name,
                "email": p.email,
                "user_id": p.user_id,
                "legacy_user_id": p.external_ids.get("legacy_user_id"),
            }
            for p in legacy_qs.order_by("last_name", "first_name")
        ]
        report["legacy_staff_without_campminder_id"] = legacy_without_cm
        self._section(f"Legacy staff linked to User but missing Campminder ID ({len(legacy_without_cm)})")
        for row in legacy_without_cm[:20]:
            self.stdout.write(f"  Person #{row['id']} {row['name']} user={row['user_id']}")
        if len(legacy_without_cm) > 20:
            self.stdout.write(f"  … and {len(legacy_without_cm) - 20} more")

        # ── Persons with email but no login User ───────────────────────────
        no_user = list(
            Person.all_objects.filter(organization=org, user__isnull=True)
            .exclude(email="")
            .order_by("last_name", "first_name")
            .values("id", "email", "first_name", "last_name"),
        )
        report["persons_with_email_no_user"] = no_user
        self._section(f"Persons with email but no linked User ({len(no_user)})")

        # ── Duplicate campminder_id on multiple Persons ────────────────────
        cm_dupes: dict[str, list[int]] = defaultdict(list)
        for person in Person.all_objects.filter(organization=org):
            cm_id = _person_campminder_id(person)
            if cm_id:
                cm_dupes[cm_id].append(person.id)
        cm_dupes = {k: v for k, v in cm_dupes.items() if len(v) > 1}
        report["duplicate_campminder_ids"] = cm_dupes
        self._section(f"Duplicate campminder_id values ({len(cm_dupes)} groups)")
        for cm_id, ids in sorted(cm_dupes.items()):
            self.stdout.write(f"  {cm_id}: Person ids {ids}")

        # ── 1C. User linked to multiple Persons in org ─────────────────────
        user_multi = list(
            Person.all_objects.filter(organization=org, user__isnull=False)
            .values("user_id")
            .annotate(n=Count("id"))
            .filter(n__gt=1),
        )
        user_multi_detail = []
        for row in user_multi:
            persons = list(
                Person.all_objects.filter(organization=org, user_id=row["user_id"]).values(
                    "id", "email", "first_name", "last_name",
                ),
            )
            user_multi_detail.append({"user_id": row["user_id"], "persons": persons})
        report["users_linked_to_multiple_persons"] = user_multi_detail
        self._section(f"Users linked to multiple Persons in org ({len(user_multi_detail)})")
        for item in user_multi_detail:
            ids = ", ".join(f"#{p['id']}" for p in item["persons"])
            self.stdout.write(f"  User {item['user_id']}: {ids}")

        # ── Ambiguous name matches (multiple Persons, no campminder_id) ────
        name_groups: dict[tuple[str, str], list[int]] = defaultdict(list)
        for person in Person.all_objects.filter(organization=org):
            if _person_campminder_id(person):
                continue
            key = (person.first_name.strip().lower(), person.last_name.strip().lower())
            name_groups[key].append(person.id)
        ambiguous_names = {
            f"{first} {last}": ids
            for (first, last), ids in name_groups.items()
            if len(ids) > 1
        }
        report["ambiguous_names_without_campminder_id"] = ambiguous_names
        self._section(f"Ambiguous names without Campminder ID ({len(ambiguous_names)} groups)")

        # ── 1B. Duplicate auth Users (case-insensitive email) ──────────────
        user_email_dupes = list(
            User.objects.values(lower=Lower("email"))
            .annotate(n=Count("id"))
            .filter(n__gt=1),
        )
        user_dup_detail = []
        for row in user_email_dupes:
            users = list(
                User.objects.annotate(email_lower=Lower("email"))
                .filter(email_lower=row["lower"])
                .values("id", "email", "is_active"),
            )
            user_dup_detail.append({"email_lower": row["lower"], "users": users})
        report["duplicate_auth_users"] = user_dup_detail
        self._section(f"Duplicate auth Users by email (case-insensitive) ({len(user_dup_detail)})")
        for item in user_dup_detail:
            ids = ", ".join(f"#{u['id']} ({u['email']})" for u in item["users"])
            self.stdout.write(f"  {item['email_lower']}: {ids}")

        # ── Summary ──────────────────────────────────────────────────────
        summary = {
            "duplicate_person_email_groups": len(dup_emails),
            "legacy_staff_without_campminder_id": len(legacy_without_cm),
            "persons_with_email_no_user": len(no_user),
            "duplicate_campminder_id_groups": len(cm_dupes),
            "users_linked_to_multiple_persons": len(user_multi_detail),
            "ambiguous_name_groups": len(ambiguous_names),
            "duplicate_auth_user_groups": len(user_dup_detail),
        }
        report["summary"] = summary
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("Summary"))
        for key, value in summary.items():
            self.stdout.write(f"  {key}: {value}")

        if json_out:
            path = json_out
            with open(path, "w", encoding="utf-8") as handle:
                json.dump(report, handle, indent=2, default=str)
            self.stdout.write(self.style.NOTICE(f"Wrote JSON report to {path}"))

    def _section(self, title: str) -> None:
        self.stdout.write("")
        self.stdout.write(self.style.MIGRATE_LABEL(title))
