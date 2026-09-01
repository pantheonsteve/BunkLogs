"""Downloadable CSV templates for the admin bulk-people importer, per source.

Each source's importer reads its own column names, so the template an admin
downloads has to match the source they picked -- a Campminder ``PersonID``
header means nothing to ``import_tbe_roster``, which keys on names.

Campminder's variants stay in ``campminder_csv``; this module only registers
them alongside TBE's and the generic spreadsheet source so the API can serve
any of them.

Invariant: headers here must track the columns the matching management
command actually reads, or admins get a file the importer silently skips.
"""
from __future__ import annotations

import csv
import io

from bunk_logs.core.campminder_csv import IMPORT_TEMPLATE_VARIANTS
from bunk_logs.core.models import Membership

# Columns read by ``import_tbe_roster``. Rows are matched to an existing
# Person on (organization, first_name, last_name) -- ShulCloud exports carry
# no stable external id -- so names are the de-duplication key, not decoration.
TBE_IMPORT_TEMPLATE_VARIANTS: dict[str, dict] = {
    "roster": {
        "label": "Roster",
        "filename": "tbe-roster-import-template.csv",
        "headers": [
            "first_name",
            "last_name",
            "role",
            "classroom_name",
            "grade_level",
            "email",
        ],
        "required_headers": ["first_name", "last_name", "role", "classroom_name"],
        "optional_headers": ["grade_level", "email"],
        "example_rows": [
            ["Maya", "Rosen", "madrich", "Grade 9", "10", "maya.rosen@example.org"],
            ["Daniel", "Katz", "madrich", "Grade 9", "11", ""],
            ["Sarah", "Levine", "faculty", "Grade 9", "", "sarah.levine@example.org"],
        ],
        "notes": (
            "One row per person. Classrooms are created on first use, so spell "
            "classroom_name identically across rows. A madrich becomes a subject "
            "of the classroom (faculty observe them) and an author of their own "
            "self-reflections; faculty become authors of the classroom. "
            "grade_level must be a whole number and applies to madrichim. "
            "Rows missing first_name, last_name, role, or classroom_name are "
            "skipped with a warning."
        ),
    },
}

# Columns read by ``import_people_roster``, the source for orgs that only have
# a spreadsheet. Only the two name columns are required; role defaults to
# student so a plain list of names uploads as a student roster.
SPREADSHEET_IMPORT_TEMPLATE_VARIANTS: dict[str, dict] = {
    "students": {
        "label": "Students",
        "filename": "student-import-template.csv",
        "headers": [
            "first_name",
            "last_name",
            "preferred_name",
            "email",
            "role",
            "grade_level",
            "group_name",
            "group_type",
        ],
        "required_headers": ["first_name", "last_name"],
        "optional_headers": [
            "preferred_name",
            "email",
            "role",
            "grade_level",
            "group_name",
            "group_type",
        ],
        "example_rows": [
            ["Maya", "Rosen", "", "", "", "7", "Grade 7A", ""],
            ["Daniel", "Katz", "Danny", "", "student", "7", "Grade 7A", ""],
            ["Sarah", "Levine", "", "sarah.levine@example.org", "faculty", "", "Grade 7A", ""],
        ],
        "notes": (
            "One row per person. Role defaults to student when blank; students "
            "and campers are subjects of reflections, so they never get a login "
            "and cannot be invited. group_name is optional -- when set, groups "
            "are created on first use, so spell the name identically across "
            "rows, and group_type defaults from the program type (classroom for "
            "religious school, bunk for summer camp). Rows are matched to an "
            "existing person by email, then by first and last name. Rows "
            "missing first_name or last_name are skipped with a warning."
        ),
    },
}

TEMPLATE_VARIANTS_BY_SOURCE: dict[str, dict[str, dict]] = {
    "campminder": IMPORT_TEMPLATE_VARIANTS,
    "tbe": TBE_IMPORT_TEMPLATE_VARIANTS,
    "spreadsheet": SPREADSHEET_IMPORT_TEMPLATE_VARIANTS,
}


def variants_for_source(source: str) -> dict[str, dict]:
    """Template specs for ``source``, or an empty mapping when unknown."""
    return TEMPLATE_VARIANTS_BY_SOURCE.get(source, {})


def list_template_variants(source: str) -> list[dict]:
    """Metadata for every template ``source`` offers, for the download picker."""
    roles = [{"slug": slug, "label": label} for slug, label in Membership.ROLES]
    return [
        {
            "variant": key,
            "label": spec["label"],
            "filename": spec["filename"],
            "headers": spec["headers"],
            "required_headers": spec["required_headers"],
            "optional_headers": spec["optional_headers"],
            "notes": spec["notes"],
            "valid_roles": roles,
        }
        for key, spec in variants_for_source(source).items()
    ]


def build_template_csv(source: str, variant: str) -> tuple[str, str]:
    """Return ``(filename, csv_text)`` for one source's template variant."""
    spec = variants_for_source(source)[variant]
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(spec["headers"])
    writer.writerows(spec["example_rows"])
    return spec["filename"], buffer.getvalue()
