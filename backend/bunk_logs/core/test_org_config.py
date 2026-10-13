"""Defaults for org roles and group types, plus settings validation.

Crane Lake and Temple Beth-El ship with no ``roles`` or ``group_types``
setting. The computed defaults are the snapshot of today's behavior.
"""
from __future__ import annotations

from datetime import date

import pytest

from bunk_logs.core.models import Membership
from bunk_logs.core.models import Organization
from bunk_logs.core.models import Person
from bunk_logs.core.models import Program
from bunk_logs.core.org_config import DEFAULT_GROUP_TYPE_CONFIG
from bunk_logs.core.org_config import enabled_roles
from bunk_logs.core.org_config import group_type_config
from bunk_logs.core.org_config import validate_group_types
from bunk_logs.core.org_config import validate_roles_update

pytestmark = pytest.mark.django_db


def _program(org, slug):
    return Program.all_objects.create(
        organization=org,
        name=f"{org.name} Season",
        slug=slug,
        program_type="summer_camp",
        start_date=date(2026, 6, 1),
        end_date=date(2026, 8, 15),
    )


def _person(org, role, program):
    person = Person.all_objects.create(
        organization=org, first_name=role, last_name="Person",
    )
    Membership.all_objects.create(
        program=program, person=person, role=role, is_active=True,
    )
    return person


def test_default_group_config_matches_current_placement():
    org = Organization.objects.create(name="Plain Org", slug="plain-org")
    config = group_type_config(org)
    assert config == DEFAULT_GROUP_TYPE_CONFIG

    bunk_authors = [
        member["role"] for member in config["bunk"]["members"]
        if member["placed_as"] == "author"
    ]
    assert bunk_authors == ["counselor", "junior_counselor", "general_counselor"]
    assert config["bunk"]["members"][-1] == {
        "role": "camper", "placed_as": "subject", "supervises_group": False,
    }

    classroom = config["classroom"]["members"]
    assert classroom == [
        {"role": "madrich", "placed_as": "author", "supervises_group": False},
        {"role": "madrich", "placed_as": "subject", "supervises_group": False},
        {"role": "faculty", "placed_as": "author", "supervises_group": False},
        {"role": "student", "placed_as": "subject", "supervises_group": False},
    ]
    assert config["unit"]["members"] == [{
        "role": "unit_head", "placed_as": "author", "supervises_group": True,
    }]
    assert config["division"]["members"] == config["unit"]["members"]
    assert "camper_care" not in {m["role"] for m in config["unit"]["members"]}


def test_enabled_roles_follow_memberships_when_unset():
    """CLC-shaped and TBE-shaped orgs, with no settings written."""
    clc = Organization.objects.create(name="Crane Shape", slug="crane-shape")
    clc_program = _program(clc, "crane-season")
    for role in ("camper", "counselor", "unit_head", "camper_care"):
        _person(clc, role, clc_program)
    assert enabled_roles(clc) == ["camper", "counselor", "unit_head", "camper_care", "admin"]

    tbe = Organization.objects.create(name="Temple Shape", slug="temple-shape")
    tbe_program = _program(tbe, "temple-season")
    for role in ("student", "madrich", "faculty"):
        _person(tbe, role, tbe_program)
    # An inactive membership still counts: the role has been used here.
    retired = Person.all_objects.create(
        organization=tbe, first_name="Old", last_name="Counselor",
    )
    Membership.all_objects.create(
        program=tbe_program, person=retired, role="counselor", is_active=False,
    )
    assert enabled_roles(tbe) == ["student", "counselor", "madrich", "faculty", "admin"]


def test_explicit_roles_replace_the_computed_list():
    org = Organization.objects.create(
        name="Saved Org", slug="saved-org", settings={"roles": ["faculty", "student", "nope"]},
    )
    assert enabled_roles(org) == ["student", "faculty"]


def test_cannot_disable_a_role_that_still_has_people():
    org = Organization.objects.create(name="Busy Org", slug="busy-org")
    program = _program(org, "busy-season")
    _person(org, "counselor", program)
    _person(org, "counselor", program)

    message = validate_roles_update(org, ["admin"])
    assert message is not None
    assert "Counselor still has 2 active people" in message

    assert validate_roles_update(org, ["admin", "counselor"]) is None


def test_participant_cannot_be_marked_as_supervising():
    org = Organization.objects.create(name="Rule Org", slug="rule-org")
    message = validate_group_types(org, {
        "bunk": {
            "enabled": True,
            "members": [{
                "role": "counselor",
                "placed_as": "author",
                "supervises_group": True,
            }],
        },
    })
    assert message is not None
    assert "can't supervise" in message


def test_a_role_may_be_author_and_subject_when_listed_twice():
    org = Organization.objects.create(name="Twice Org", slug="twice-org")
    assert validate_group_types(org, {
        "classroom": {
            "enabled": True,
            "members": [
                {"role": "madrich", "placed_as": "author", "supervises_group": False},
                {"role": "madrich", "placed_as": "subject", "supervises_group": False},
            ],
        },
    }) is None
    duplicate = validate_group_types(org, {
        "classroom": {
            "enabled": True,
            "members": [
                {"role": "madrich", "placed_as": "author", "supervises_group": False},
                {"role": "madrich", "placed_as": "author", "supervises_group": False},
            ],
        },
    })
    assert duplicate is not None
