"""Seed or update a ReflectionTemplate from a JSON file (role-specific)."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand
from django.core.management.base import CommandError

from bunk_logs.core.models import Membership
from bunk_logs.core.models import Organization
from bunk_logs.core.models import Program
from bunk_logs.core.models import ReflectionTemplate
from bunk_logs.core.models import validate_reflection_template_schema

MEMBERSHIP_ROLE_CODES = {code for code, _ in Membership.ROLES}
CADENCE_CODES = {code for code, _ in ReflectionTemplate.CADENCES}
PROGRAM_TYPE_CODES = {code for code, _ in Program.PROGRAM_TYPES}


def resolve_template_file_path(arg: str) -> Path:
    """Resolve JSON path: absolute as-is; relative tries cwd, repo root, then Django BASE_DIR."""
    p = Path(arg).expanduser()
    if p.is_absolute():
        resolved = p.resolve()
        if resolved.is_file():
            return resolved
        raise CommandError(f"Template file not found: {resolved}")

    base_dirs: list[Path] = []
    for raw in (
        Path.cwd(),
        Path(settings.BASE_DIR).resolve().parent,
        Path(settings.BASE_DIR).resolve(),
    ):
        try:
            resolved_base = raw.resolve()
        except OSError:
            continue
        if resolved_base not in base_dirs:
            base_dirs.append(resolved_base)

    tried: list[Path] = []
    for base in base_dirs:
        candidate = (base / p).resolve()
        tried.append(candidate)
        if candidate.is_file():
            return candidate

    raise CommandError(
        "Template file not found: {!r}. Tried:\n  {}".format(arg, "\n  ".join(str(t) for t in tried)),
    )


def _coerce_positive_int(value: Any, field: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise CommandError(f'"{field}" must be a positive integer.')
    if value < 1:
        raise CommandError(f'"{field}" must be >= 1.')
    return value


def parse_template_file(raw: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise CommandError("Template file must contain a JSON object.")
    missing = {"name", "slug", "cadence", "schema"} - raw.keys()
    if missing:
        raise CommandError(f"Template JSON missing required keys: {', '.join(sorted(missing))}.")
    version = raw.get("version", 1)
    version = _coerce_positive_int(version, "version")
    slug = raw["slug"]
    if not isinstance(slug, str) or not slug.strip():
        raise CommandError('"slug" must be a non-empty string.')
    name = raw["name"]
    if not isinstance(name, str) or not name.strip():
        raise CommandError('"name" must be a non-empty string.')
    cadence = raw["cadence"]
    if cadence not in CADENCE_CODES:
        raise CommandError(
            f'Invalid cadence {cadence!r}; allowed: {", ".join(sorted(CADENCE_CODES))}.',
        )
    schema = raw["schema"]
    validate_reflection_template_schema(schema)

    program_type = raw.get("program_type")
    if program_type is not None and program_type != "":
        if program_type not in PROGRAM_TYPE_CODES:
            raise CommandError(
                f'Invalid program_type {program_type!r}; '
                f'allowed: {", ".join(sorted(PROGRAM_TYPE_CODES))} or omit/null.',
            )
    else:
        program_type = None

    description = raw.get("description", "")
    if description is None:
        description = ""
    if not isinstance(description, str):
        raise CommandError('"description" must be a string.')

    languages = raw.get("languages", [])
    if languages is None:
        languages = []
    if not isinstance(languages, list) or not all(isinstance(x, str) for x in languages):
        raise CommandError('"languages" must be a list of strings.')

    is_active = raw.get("is_active", True)
    if not isinstance(is_active, bool):
        raise CommandError('"is_active" must be a boolean.')

    return {
        "name": name.strip(),
        "slug": slug.strip(),
        "version": version,
        "cadence": cadence,
        "program_type": program_type,
        "description": description,
        "languages": languages,
        "is_active": is_active,
        "schema": schema,
    }


class Command(BaseCommand):
    help = "Create or update a ReflectionTemplate from a JSON definition (idempotent by org + slug + version)."

    def add_arguments(self, parser):
        parser.add_argument("--org-slug", required=True, help="Organization slug (e.g. clc).")
        parser.add_argument(
            "--role",
            required=True,
            help="Membership role code (e.g. counselor, kitchen_staff).",
        )
        parser.add_argument(
            "--template-file",
            required=True,
            help="Path to JSON template definition.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Validate only; do not write to the database.",
        )

    def handle(self, *args, **options):
        org_slug: str = options["org_slug"]
        role: str = options["role"]
        template_path = resolve_template_file_path(options["template_file"])
        dry_run: bool = options["dry_run"]

        if role not in MEMBERSHIP_ROLE_CODES:
            raise CommandError(
                f'Invalid role {role!r}; must be one of: {", ".join(sorted(MEMBERSHIP_ROLE_CODES))}.',
            )

        try:
            org = Organization.objects.get(slug=org_slug)
        except Organization.DoesNotExist as exc:
            raise CommandError(f'Organization with slug {org_slug!r} does not exist.') from exc

        try:
            with template_path.open(encoding="utf-8") as fh:
                raw = json.load(fh)
        except json.JSONDecodeError as exc:
            raise CommandError(f"Invalid JSON in template file: {exc}") from exc

        try:
            parsed = parse_template_file(raw)
        except ValidationError as exc:
            raise CommandError(self._format_validation_error(exc)) from exc

        candidate = ReflectionTemplate(
            organization=org,
            role=role,
            name=parsed["name"],
            slug=parsed["slug"],
            description=parsed["description"],
            cadence=parsed["cadence"],
            program_type=parsed["program_type"],
            schema=parsed["schema"],
            languages=parsed["languages"],
            is_active=parsed["is_active"],
            version=parsed["version"],
        )
        try:
            candidate.full_clean()
        except ValidationError as exc:
            raise CommandError(self._format_validation_error(exc)) from exc

        key = f'{org.slug}/{parsed["slug"]} v{parsed["version"]} (role={role})'
        if dry_run:
            existing = ReflectionTemplate.all_objects.filter(
                organization=org,
                slug=parsed["slug"],
                version=parsed["version"],
            ).first()
            if existing:
                self.stdout.write(
                    self.style.WARNING(f"[dry-run] Would update existing template {key}"),
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f"[dry-run] Would create template {key}"),
                )
            self.stdout.write(f"[dry-run] Loaded and validated {template_path}")
            return

        existing = ReflectionTemplate.all_objects.filter(
            organization=org,
            slug=parsed["slug"],
            version=parsed["version"],
        ).first()

        obj, created = ReflectionTemplate.all_objects.update_or_create(
            organization=org,
            slug=parsed["slug"],
            version=parsed["version"],
            defaults={
                "role": role,
                "name": parsed["name"],
                "description": parsed["description"],
                "cadence": parsed["cadence"],
                "program_type": parsed["program_type"],
                "schema": parsed["schema"],
                "languages": parsed["languages"],
                "is_active": parsed["is_active"],
            },
        )

        action = "Created" if created else "Updated"
        self.stdout.write(
            self.style.SUCCESS(f"{action} reflection template {key} (pk={obj.pk})"),
        )

    @staticmethod
    def _format_validation_error(exc: ValidationError) -> str:
        if hasattr(exc, "error_dict"):
            parts = []
            for field, errs in exc.error_dict.items():
                for e in errs:
                    parts.append(f"{field}: {e.message}")
            return "; ".join(parts) if parts else str(exc)
        if exc.messages:
            return "; ".join(str(m) for m in exc.messages)
        return str(exc)
