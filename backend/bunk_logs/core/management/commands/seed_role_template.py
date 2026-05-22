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
        msg = f"Template file not found: {resolved}"
        raise CommandError(msg)

    # /repo is the full monorepo mount used in the local Docker/Podman setup.
    _REPO_MOUNT = Path("/repo")
    base_dirs: list[Path] = []
    for raw in (
        Path.cwd(),
        Path(settings.BASE_DIR).resolve().parent,
        Path(settings.BASE_DIR).resolve(),
        _REPO_MOUNT if _REPO_MOUNT.is_dir() else None,
    ):
        if raw is None:
            continue
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

    tried_lines = "\n  ".join(str(t) for t in tried)
    msg = f"Template file not found: {arg!r}. Tried:\n  {tried_lines}"
    raise CommandError(msg)


def _coerce_positive_int(value: Any, field: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        msg = f'"{field}" must be a positive integer.'
        raise CommandError(msg)
    if value < 1:
        msg = f'"{field}" must be >= 1.'
        raise CommandError(msg)
    return value


def parse_template_file(raw: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(raw, dict):
        msg = "Template file must contain a JSON object."
        raise CommandError(msg)
    missing = {"name", "slug", "cadence", "schema"} - raw.keys()
    if missing:
        msg = f"Template JSON missing required keys: {', '.join(sorted(missing))}."
        raise CommandError(msg)
    version = raw.get("version", 1)
    version = _coerce_positive_int(version, "version")
    slug = raw["slug"]
    if not isinstance(slug, str) or not slug.strip():
        msg = '"slug" must be a non-empty string.'
        raise CommandError(msg)
    name = raw["name"]
    if not isinstance(name, str) or not name.strip():
        msg = '"name" must be a non-empty string.'
        raise CommandError(msg)
    cadence = raw["cadence"]
    if cadence not in CADENCE_CODES:
        msg = f'Invalid cadence {cadence!r}; allowed: {", ".join(sorted(CADENCE_CODES))}.'
        raise CommandError(msg)
    schema = raw["schema"]
    validate_reflection_template_schema(schema)

    program_type = raw.get("program_type")
    if program_type is not None and program_type != "":
        if program_type not in PROGRAM_TYPE_CODES:
            allowed = ", ".join(sorted(PROGRAM_TYPE_CODES))
            msg = f"Invalid program_type {program_type!r}; allowed: {allowed} or omit/null."
            raise CommandError(msg)
    else:
        program_type = None

    description = raw.get("description", "")
    if description is None:
        description = ""
    if not isinstance(description, str):
        msg = '"description" must be a string.'
        raise CommandError(msg)

    languages = raw.get("languages", [])
    if languages is None:
        languages = []
    if not isinstance(languages, list) or not all(isinstance(x, str) for x in languages):
        msg = '"languages" must be a list of strings.'
        raise CommandError(msg)

    is_active = raw.get("is_active", True)
    if not isinstance(is_active, bool):
        msg = '"is_active" must be a boolean.'
        raise CommandError(msg)

    # status defaults to published when is_active=True so old seed JSON
    # without an explicit field remains backwards-compatible. Explicit
    # status wins. Both columns are kept in sync for rollback safety.
    raw_status = raw.get("status")
    if raw_status is None:
        derived_status = (
            ReflectionTemplate.Status.PUBLISHED
            if is_active
            else ReflectionTemplate.Status.ARCHIVED
        )
    elif raw_status in {s.value for s in ReflectionTemplate.Status}:
        derived_status = raw_status
    else:
        choices = ", ".join(s.value for s in ReflectionTemplate.Status)
        msg = f"Invalid status {raw_status!r}; allowed: {choices}."
        raise CommandError(msg)

    return {
        "name": name.strip(),
        "slug": slug.strip(),
        "version": version,
        "cadence": cadence,
        "program_type": program_type,
        "description": description,
        "languages": languages,
        "is_active": is_active,
        "status": derived_status,
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
            roles_list = ", ".join(sorted(MEMBERSHIP_ROLE_CODES))
            msg = f"Invalid role {role!r}; must be one of: {roles_list}."
            raise CommandError(msg)

        try:
            org = Organization.objects.get(slug=org_slug)
        except Organization.DoesNotExist as exc:
            msg = f"Organization with slug {org_slug!r} does not exist."
            raise CommandError(msg) from exc

        try:
            with template_path.open(encoding="utf-8") as fh:
                raw = json.load(fh)
        except json.JSONDecodeError as exc:
            msg = f"Invalid JSON in template file: {exc}"
            raise CommandError(msg) from exc

        try:
            parsed = parse_template_file(raw)
        except ValidationError as exc:
            msg = self._format_validation_error(exc)
            raise CommandError(msg) from exc

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
            status=parsed["status"],
            version=parsed["version"],
        )
        try:
            candidate.full_clean()
        except ValidationError as exc:
            msg = self._format_validation_error(exc)
            raise CommandError(msg) from exc

        key = f"{org.slug}/{parsed['slug']} v{parsed['version']} (role={role})"
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
                "status": parsed["status"],
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
