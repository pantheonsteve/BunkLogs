"""resolve_role_in_group follows a single configured seat."""

from __future__ import annotations

import pytest

from bunk_logs.core.group_roster_import import resolve_role_in_group
from bunk_logs.core.models import AssignmentGroup
from bunk_logs.core.models import Organization
from bunk_logs.core.models import Program
from bunk_logs.testing import SEASON_END
from bunk_logs.testing import SEASON_START

pytestmark = pytest.mark.django_db


@pytest.fixture
def classroom():
    org = Organization.objects.create(name="Roster School", slug="roster-school")
    org.settings = {
        "group_types": {
            "classroom": {
                "enabled": True,
                "members": [
                    {"role": "student", "placed_as": "author", "supervises_group": False},
                    {"role": "madrich", "placed_as": "author", "supervises_group": False},
                    {"role": "madrich", "placed_as": "subject", "supervises_group": False},
                ],
            },
        },
    }
    org.save(update_fields=["settings"])
    program = Program.all_objects.create(
        organization=org,
        name="Roster School Year",
        slug="roster-year",
        program_type="religious_school",
        start_date=SEASON_START,
        end_date=SEASON_END,
    )
    return AssignmentGroup.all_objects.create(
        organization=org,
        program=program,
        name="Grade 3",
        slug="grade-3",
        group_type="classroom",
    )


def test_column_wins_over_the_configured_seat(classroom):
    assert resolve_role_in_group(
        {"role_in_group": "subject"},
        "student",
        group=classroom,
    ) == "subject"


def test_one_configured_seat_is_used(classroom):
    assert resolve_role_in_group({}, "student", group=classroom) == "author"


def test_two_seats_still_ask(classroom):
    assert resolve_role_in_group(
        {},
        "madrich",
        bulk_role_in_group="subject",
        group=classroom,
    ) == "subject"
    assert resolve_role_in_group({}, "madrich", group=classroom) == "author"


def test_without_a_group_the_role_still_decides():
    assert resolve_role_in_group({}, "student") == "subject"
    assert resolve_role_in_group({}, "faculty") == "author"
