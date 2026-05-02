"""CLC 2026 reflection template JSON files validate against ReflectionTemplate schema."""
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from django.conf import settings

from bunk_logs.core.management.commands.seed_role_template import parse_template_file


def _repo_root() -> Path:
    env = os.environ.get("BUNKLOGS_REPO_ROOT")
    if env:
        return Path(env).resolve()
    return Path(settings.BASE_DIR).resolve().parent


CLC_TEMPLATE_DIR = _repo_root() / "templates" / "reflection_templates" / "clc_2026"

ROLE_FILES = [
    ("counselor", "counselor.json"),
    ("junior_counselor", "junior_counselor.json"),
    ("specialist", "specialist.json"),
    ("general_counselor", "general_counselor.json"),
    ("leadership_team", "leadership_team.json"),
    ("kitchen_staff", "kitchen_staff.json"),
    ("maintenance", "maintenance.json"),
    ("housekeeping", "housekeeping.json"),
    ("camper_care", "camper_care.json"),
    ("health_center", "health_center.json"),
    ("special_diets", "special_diets.json"),
]


@pytest.mark.parametrize(("role", "filename"), ROLE_FILES)
def test_clc_2026_template_json_validates(role: str, filename: str):
    path = CLC_TEMPLATE_DIR / filename
    assert path.is_file(), f"Missing template file: {path}"
    raw = json.loads(path.read_text(encoding="utf-8"))
    parsed = parse_template_file(raw)
    assert parsed["schema"]
    assert parsed["cadence"]
