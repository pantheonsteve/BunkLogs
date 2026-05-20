"""Tests for seed_role_template management command."""
from __future__ import annotations

import json
from io import StringIO
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pathlib import Path
from django.core.management import call_command
from django.core.management.base import CommandError

from bunk_logs.core.models import Organization
from bunk_logs.core.models import ReflectionTemplate


def _minimal_template_payload() -> dict:
    return {
        "name": "Test weekly",
        "slug": "test-weekly-seed",
        "version": 1,
        "cadence": "weekly",
        "program_type": "summer_camp",
        "description": "",
        "languages": ["en"],
        "schema": {
            "fields": [
                {
                    "key": "note",
                    "type": "textarea",
                    "prompts": {"en": "Notes?"},
                },
            ],
        },
    }


@pytest.mark.django_db
class TestSeedRoleTemplateCommand:
    def test_creates_template_from_valid_json(self, tmp_path: Path):
        org = Organization.objects.create(name="Test Org", slug="test-org-seed")
        path = tmp_path / "t.json"
        path.write_text(json.dumps(_minimal_template_payload()), encoding="utf-8")
        out = StringIO()
        call_command(
            "seed_role_template",
            org_slug="test-org-seed",
            role="counselor",
            template_file=str(path),
            stdout=out,
        )
        t = ReflectionTemplate.all_objects.get(organization=org, slug="test-weekly-seed", version=1)
        assert t.role == "counselor"
        assert t.name == "Test weekly"
        assert "Created" in out.getvalue()

    def test_dry_run_does_not_write(self, tmp_path: Path):
        Organization.objects.create(name="Test Org", slug="test-org-dry")
        path = tmp_path / "t.json"
        path.write_text(json.dumps(_minimal_template_payload()), encoding="utf-8")
        before = ReflectionTemplate.all_objects.count()
        call_command(
            "seed_role_template",
            org_slug="test-org-dry",
            role="counselor",
            template_file=str(path),
            dry_run=True,
            stdout=StringIO(),
        )
        assert ReflectionTemplate.all_objects.count() == before

    def test_invalid_schema_clear_error(self, tmp_path: Path):
        Organization.objects.create(name="Test Org", slug="test-org-bad")
        path = tmp_path / "bad.json"
        bad = {**_minimal_template_payload(), "schema": {"fields": []}}
        path.write_text(json.dumps(bad), encoding="utf-8")
        with pytest.raises(CommandError) as exc:
            call_command(
                "seed_role_template",
                org_slug="test-org-bad",
                role="counselor",
                template_file=str(path),
                stdout=StringIO(),
            )
        assert "fields" in str(exc.value).lower()

    def test_idempotent_rerun(self, tmp_path: Path):
        org = Organization.objects.create(name="Test Org", slug="test-org-idem")
        path = tmp_path / "t.json"
        path.write_text(json.dumps(_minimal_template_payload()), encoding="utf-8")
        call_command(
            "seed_role_template",
            org_slug="test-org-idem",
            role="counselor",
            template_file=str(path),
            stdout=StringIO(),
        )
        first_pk = ReflectionTemplate.all_objects.get(organization=org).pk
        assert ReflectionTemplate.all_objects.count() == 1
        out2 = StringIO()
        call_command(
            "seed_role_template",
            org_slug="test-org-idem",
            role="counselor",
            template_file=str(path),
            stdout=out2,
        )
        assert ReflectionTemplate.all_objects.count() == 1
        second_pk = ReflectionTemplate.all_objects.get(organization=org).pk
        assert first_pk == second_pk
        assert "Updated" in out2.getvalue()

    def test_invalid_role_rejected(self, tmp_path: Path):
        Organization.objects.create(name="Test Org", slug="test-org-role")
        path = tmp_path / "t.json"
        path.write_text(json.dumps(_minimal_template_payload()), encoding="utf-8")
        with pytest.raises(CommandError) as exc:
            call_command(
                "seed_role_template",
                org_slug="test-org-role",
                role="not_a_real_role",
                template_file=str(path),
                stdout=StringIO(),
            )
        assert "Invalid role" in str(exc.value)

    def test_relative_path_resolves_from_repo_root(self, tmp_path: Path, settings, monkeypatch):
        """Paths like templates/... live at repo root; manage.py is often run with cwd=backend/."""
        repo = tmp_path / "repo"
        backend = repo / "backend"
        backend.mkdir(parents=True)
        rel = "templates/reflection_templates/seed.json"
        full = repo / rel
        full.parent.mkdir(parents=True)
        full.write_text(json.dumps(_minimal_template_payload()), encoding="utf-8")

        settings.BASE_DIR = backend
        monkeypatch.chdir(backend)
        Organization.objects.create(name="Test Org", slug="test-org-repo-root")

        call_command(
            "seed_role_template",
            org_slug="test-org-repo-root",
            role="counselor",
            template_file=rel,
            stdout=StringIO(),
        )
        assert ReflectionTemplate.all_objects.filter(slug="test-weekly-seed").exists()
