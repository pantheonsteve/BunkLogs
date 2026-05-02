"""Tests for seed_role_template management command."""
from __future__ import annotations

import json
from io import StringIO
from pathlib import Path

import pytest
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
        assert ReflectionTemplate.all_objects.count() == 0
        call_command(
            "seed_role_template",
            org_slug="test-org-dry",
            role="counselor",
            template_file=str(path),
            dry_run=True,
            stdout=StringIO(),
        )
        assert ReflectionTemplate.all_objects.count() == 0

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
        first_pk = ReflectionTemplate.all_objects.get(
            organization=org,
            slug="test-weekly-seed",
        ).pk
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
        second_pk = ReflectionTemplate.all_objects.get(
            organization=org,
            slug="test-weekly-seed",
        ).pk
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
