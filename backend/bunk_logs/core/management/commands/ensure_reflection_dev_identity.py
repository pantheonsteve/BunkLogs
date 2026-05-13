"""Link a Django user to Person + Membership so reflection APIs work locally.

The SPA calls ``admin``/``localhost`` as API host, so ``OrganizationMiddleware`` does
not infer tenant from subdomain. With ``DEBUG=True``, ``X-Organization-Slug`` (sent by
the Vite dev client when ``VITE_DEV_ORGANIZATION_SLUG`` is set) resolves ``clc``, but
``ReflectionPermission`` and ``template-for-me`` still need a ``Person`` and active
``Membership`` on a program.

Run (inside the django container):

    python manage.py setup_crane_lake
    python manage.py ensure_reflection_dev_identity

Then seed at least one template (see docs/clc-2026-templates.md) for the chosen role.
"""
from __future__ import annotations

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.core.management.base import CommandError
from django.db import transaction

from bunk_logs.core.models import Membership
from bunk_logs.core.models import Organization
from bunk_logs.core.models import Person
from bunk_logs.core.models import Program

User = get_user_model()
_MEMBERSHIP_ROLE_CODES = {code for code, _ in Membership.ROLES}


class Command(BaseCommand):
    help = (
        "DEBUG only: ensure a User has Person + Membership on CLC Summer 2026 for reflection testing."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--email",
            default="dev-admin@example.test",
            help="Django user email (default: dev-admin@example.test from seed_dev_data).",
        )
        parser.add_argument(
            "--org-slug",
            default="clc",
            help="Organization slug (default: clc).",
        )
        parser.add_argument(
            "--program-slug",
            default="summer-2026",
            help="Program slug within the org (default: summer-2026).",
        )
        parser.add_argument(
            "--role",
            default="counselor",
            help=f"Membership role code (default: counselor). Allowed: {', '.join(sorted(_MEMBERSHIP_ROLE_CODES))}.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        if not settings.DEBUG:
            msg = (
                "This command is only allowed when DEBUG=True (local settings). "
                "It is blocked in production-like settings."
            )
            raise CommandError(msg)

        email = (options["email"] or "").strip().lower()
        org_slug = (options["org_slug"] or "").strip()
        program_slug = (options["program_slug"] or "").strip()
        role = (options["role"] or "").strip()

        if role not in _MEMBERSHIP_ROLE_CODES:
            allowed = ", ".join(sorted(_MEMBERSHIP_ROLE_CODES))
            msg = f"Invalid role {role!r}. Use one of: {allowed}."
            raise CommandError(msg)

        try:
            org = Organization.objects.get(slug=org_slug, is_active=True)
        except Organization.DoesNotExist as e:
            msg = f'Organization slug={org_slug!r} not found or inactive. Run "setup_crane_lake" first.'
            raise CommandError(msg) from e

        try:
            program = Program.all_objects.get(organization=org, slug=program_slug, is_active=True)
        except Program.DoesNotExist as e:
            msg = (
                f'Program org={org_slug!r} slug={program_slug!r} not found or inactive. '
                f'Run "setup_crane_lake" first.'
            )
            raise CommandError(msg) from e

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist as e:
            msg = (
                f'User with email={email!r} not found. '
                f'Create the account or run "seed_dev_data --reset" (creates dev-admin@example.test).'
            )
            raise CommandError(msg) from e

        existing = Person.all_objects.filter(user=user).first()
        if existing is not None and existing.organization_id != org.id:
            msg = (
                f"User {email!r} is already linked to Person pk={existing.pk} in another organization. "
                "Unlink or use a different user."
            )
            raise CommandError(msg)

        if existing is None:
            person = Person.all_objects.create(
                organization=org,
                first_name=(user.first_name or "").strip() or "Dev",
                last_name=(user.last_name or "").strip() or "Tester",
                email=user.email or "",
                user=user,
            )
            self.stdout.write(self.style.SUCCESS(f"Created Person pk={person.pk} for {email} in org {org_slug}."))
        else:
            person = existing
            self.stdout.write(f"Using existing Person pk={person.pk} for {email}.")

        m, created = Membership.all_objects.get_or_create(
            program=program,
            person=person,
            role=role,
            defaults={"is_active": True},
        )
        if not created and not m.is_active:
            m.is_active = True
            m.save(update_fields=["is_active"])
            self.stdout.write(self.style.NOTICE(f"Reactivated Membership pk={m.pk} ({role} on {program_slug})."))
        elif created:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Created Membership pk={m.pk}: role={role!r} program={program_slug!r}.",
                ),
            )
        else:
            self.stdout.write(f"Membership already present pk={m.pk} ({role} on {program_slug}).")

        self.stdout.write("")
        self.stdout.write(
            "Next: set VITE_DEV_ORGANIZATION_SLUG=clc in frontend/.env (see .env.example), "
            "run `npm run dev`, sign in as this user, open /reflect.",
        )
        self.stdout.write(
            f"Seed a template for role {role!r} if you have not yet (docs/clc-2026-templates.md).",
        )
