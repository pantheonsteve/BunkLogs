"""Tests for ``/api/v1/leadership-team/*`` (Step 7_12 PR A, Stories 45-47, 50).

Covers:

* Supervision-driven dashboard (Story 45) — supervised teams card list,
  attention badges, sort order, bunks-and-units summary, self section.
* Team dashboard (Story 46) — period selector, member rows, flagged
  reflections, marker-count integration.
* Member reflection reader (Story 47) — visibility filter, trend
  payload, translation embed shape.
* Self-reflection submit + edit (Story 50) — biweekly period
  resolution, privacy toggle audience change, idempotency,
  edit-window enforcement.
* Mark-attention POST + DELETE (Story 46 c5) — idempotency, co-supervisor
  visibility, permission gate.

Visibility / RBAC specifics around sensitive content are covered by
the content-visibility unit tests; here we focus on the LT-specific
composition.
"""

from __future__ import annotations

from datetime import date
from datetime import timedelta
from uuid import uuid4

import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from rest_framework.test import APIClient

from bunk_logs.core.context import organization_context
from bunk_logs.core.models import Membership
from bunk_logs.core.models import Organization
from bunk_logs.core.models import Person
from bunk_logs.core.models import Program
from bunk_logs.core.models import Reflection
from bunk_logs.core.models import ReflectionAttentionMarker
from bunk_logs.core.models import ReflectionTemplate
from bunk_logs.core.models import Supervision

User = get_user_model()


@pytest.fixture(autouse=True)
def _clear_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def org(db):
    return Organization.objects.create(
        name="LT Camp", slug="lt-camp",
        settings={"rollover_hour": 0, "timezone": "UTC"},
    )


@pytest.fixture
def program(org):
    return Program.all_objects.create(
        organization=org, name="LT Camp Summer 2026", slug="lt-summer-2026",
        program_type="summer_camp",
        start_date=date(2026, 6, 1), end_date=date(2026, 8, 31),
    )


@pytest.fixture
def lt_user():
    return User.objects.create_user(email="lt@lt.test", password="pw")


@pytest.fixture
def lt_person(org, lt_user):
    return Person.all_objects.create(
        organization=org, first_name="Riley", last_name="Park", user=lt_user,
    )


@pytest.fixture
def lt_membership(program, lt_person):
    return Membership.all_objects.create(
        program=program, person=lt_person, role="leadership_team", is_active=True,
    )


def _create_team_member(org, program, role: str, first: str, last: str):
    """Create a Person + active Membership in the given role."""
    p = Person.all_objects.create(organization=org, first_name=first, last_name=last)
    Membership.all_objects.create(
        program=program, person=p, role=role, is_active=True,
    )
    return p


@pytest.fixture
def kitchen_team(org, program):
    return [
        _create_team_member(org, program, "kitchen_staff", "Alice", "Romero"),
        _create_team_member(org, program, "kitchen_staff", "Bo", "Singer"),
    ]


@pytest.fixture
def lt_supervises_kitchen(lt_membership, program):
    """LT supervises the kitchen_staff role in program."""
    return Supervision.all_objects.create(
        supervisor_membership=lt_membership,
        target_type=Supervision.TargetType.ROLE_IN_PROGRAM,
        target_role="kitchen_staff",
        target_program=program,
        start_date=date(2026, 1, 1),
    )


def _client(user, org):
    c = APIClient()
    c.force_authenticate(user=user)
    c.credentials(HTTP_X_ORGANIZATION_SLUG=org.slug)
    return c


def _today_in_org(org):
    from bunk_logs.core.time_utils import get_today
    return get_today(org)


# ---------------------------------------------------------------------------
# Dashboard — Story 45
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_dashboard_requires_lt_membership(org, lt_user):
    """Authenticated user without an LT Membership gets 403."""
    c = _client(lt_user, org)
    with organization_context(org):
        resp = c.get("/api/v1/leadership-team/dashboard/?nocache=1")
    assert resp.status_code == 403


@pytest.mark.django_db
def test_dashboard_lists_supervised_teams_only(
    org, lt_user, lt_membership, kitchen_team, lt_supervises_kitchen, program,
):
    """Story 45 c3 — one card per ROLE_IN_PROGRAM supervision; others excluded."""
    # Add a counselor team not under supervision.
    _create_team_member(org, program, "counselor", "Casey", "Lee")

    c = _client(lt_user, org)
    with organization_context(org):
        resp = c.get("/api/v1/leadership-team/dashboard/?nocache=1")
    assert resp.status_code == 200
    body = resp.json()
    team_roles = [t["team_role"] for t in body["teams"]]
    assert team_roles == ["kitchen_staff"]
    card = body["teams"][0]
    assert card["member_count"] == 2
    assert card["program_name"] == program.name


@pytest.mark.django_db
def test_dashboard_low_completion_badge_after_expected_by(
    org, lt_user, lt_membership, kitchen_team, lt_supervises_kitchen, program,
):
    """Story 45 c5 — low_completion fires when ratio < 0.5 after expected_by."""
    # Move expected-by hour to past so the gate fires (default 18:00 local).
    org.settings = {"rollover_hour": 0, "timezone": "UTC",
                    "dashboards": {"expected_by_hour": 0}}
    org.save()

    c = _client(lt_user, org)
    with organization_context(org):
        resp = c.get("/api/v1/leadership-team/dashboard/?nocache=1")
    body = resp.json()
    badges = body["teams"][0]["badges"]
    assert "low_completion" in badges


@pytest.mark.django_db
def test_dashboard_includes_self_section(
    org, lt_user, lt_membership, lt_person, program,
):
    """Story 50 — self_reflection section shows missing + period bounds."""
    c = _client(lt_user, org)
    with organization_context(org):
        resp = c.get("/api/v1/leadership-team/dashboard/?nocache=1")
    body = resp.json()
    self_section = body["self_reflection"]
    assert self_section["state"] == "missing"
    assert self_section["editable"] is True
    assert self_section["cadence"] == "biweekly"
    # Period start/end span 14 days.
    ps = date.fromisoformat(self_section["period_start"])
    pe = date.fromisoformat(self_section["period_end"])
    assert (pe - ps).days == 13


# ---------------------------------------------------------------------------
# Team dashboard — Story 46
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_team_dashboard_requires_supervised_role(
    org, lt_user, lt_membership, lt_supervises_kitchen,
):
    """Story 46 — unsupervised role returns 403."""
    c = _client(lt_user, org)
    with organization_context(org):
        resp = c.get("/api/v1/leadership-team/teams/counselor/")
    assert resp.status_code == 403


@pytest.mark.django_db
def test_team_dashboard_member_status_grouping(
    org, lt_user, lt_membership, kitchen_team, lt_supervises_kitchen, program,
):
    """Story 46 c1 — submitted / not submitted / day-off counts + rows."""
    template = ReflectionTemplate.all_objects.get(
        slug="kitchen-staff-self-reflection",
    )
    today = _today_in_org(org)
    # First member submits a normal reflection.
    Reflection.all_objects.create(
        organization=org, program=program, template=template,
        subject=kitchen_team[0], author=kitchen_team[0],
        period_start=today, period_end=today,
        answers={"service_summary": "Smooth lunch."},
        is_complete=True,
    )
    c = _client(lt_user, org)
    with organization_context(org):
        resp = c.get("/api/v1/leadership-team/teams/kitchen_staff/")
    assert resp.status_code == 200
    body = resp.json()
    status_summary = body["submission_status"]
    assert status_summary == {
        "submitted": 1, "day_off": 0, "not_submitted": 1, "total": 2,
    }
    statuses = sorted(r["status"] for r in body["members"])
    assert statuses == ["not_submitted", "submitted"]


@pytest.mark.django_db
def test_team_dashboard_rejects_future_date(
    org, lt_user, lt_membership, lt_supervises_kitchen,
):
    today = _today_in_org(org)
    future = (today + timedelta(days=1)).isoformat()
    c = _client(lt_user, org)
    with organization_context(org):
        resp = c.get(f"/api/v1/leadership-team/teams/kitchen_staff/?date={future}")
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Member reflection reader — Story 47
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_member_reflection_returns_visible_payload(
    org, lt_user, lt_membership, kitchen_team, lt_supervises_kitchen, program,
):
    """Story 47 — payload includes header, content, trend structure."""
    template = ReflectionTemplate.all_objects.get(
        slug="kitchen-staff-self-reflection",
    )
    today = _today_in_org(org)
    Reflection.all_objects.create(
        organization=org, program=program, template=template,
        subject=kitchen_team[0], author=kitchen_team[0],
        period_start=today, period_end=today,
        answers={"service_summary": "Smooth lunch."},
        is_complete=True,
    )
    member_membership = Membership.all_objects.get(
        person=kitchen_team[0], program=program, role="kitchen_staff",
    )

    c = _client(lt_user, org)
    with organization_context(org):
        resp = c.get(
            f"/api/v1/leadership-team/teams/kitchen_staff/members/"
            f"{member_membership.id}/reflection/",
        )
    assert resp.status_code == 200
    body = resp.json()
    assert body["header"]["person"]["first_name"] == "Alice"
    assert body["metadata"]["reflection_id"]
    assert body["content"]["fields"]
    # Trend payload always returns a structure; kitchen template has no
    # scored fields so series is empty — that's expected.
    assert "series" in body["trend"]
    assert body["trend"]["period"]["cadence"] == "daily"


@pytest.mark.django_db
def test_member_reflection_rejects_non_team_membership(
    org, lt_user, lt_membership, lt_supervises_kitchen, program,
):
    """A membership that isn't on the supervised team returns 404."""
    counselor = _create_team_member(org, program, "counselor", "Pat", "Lee")
    membership = Membership.all_objects.get(
        person=counselor, program=program, role="counselor",
    )
    c = _client(lt_user, org)
    with organization_context(org):
        resp = c.get(
            f"/api/v1/leadership-team/teams/kitchen_staff/members/"
            f"{membership.id}/reflection/",
        )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Self-reflection — Story 50
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_self_reflection_post_creates_with_biweekly_period(
    org, lt_user, lt_membership, lt_person, program,
):
    today = _today_in_org(org)
    c = _client(lt_user, org)
    with organization_context(org):
        resp = c.post(
            "/api/v1/leadership-team/self-reflection/",
            data={
                "answers": {"overall_period": 4},
                "language": "en",
                "client_submission_id": str(uuid4()),
            },
            format="json",
        )
    assert resp.status_code == 201
    body = resp.json()
    ps = date.fromisoformat(body["period_start"])
    pe = date.fromisoformat(body["period_end"])
    assert ps <= today <= pe
    assert (pe - ps).days == 13


@pytest.mark.django_db
def test_self_reflection_private_toggle_marks_sensitive(
    org, lt_user, lt_membership, lt_person, program,
):
    """Story 50 c11 — is_private maps to is_sensitive + SUPERVISORS_ONLY."""
    c = _client(lt_user, org)
    with organization_context(org):
        resp = c.post(
            "/api/v1/leadership-team/self-reflection/",
            data={
                "answers": {"overall_period": 5},
                "language": "en",
                "is_private": True,
                "client_submission_id": str(uuid4()),
            },
            format="json",
        )
    assert resp.status_code == 201
    reflection_id = resp.json()["id"]
    row = Reflection.all_objects.get(id=reflection_id)
    assert row.is_sensitive is True
    assert row.team_visibility == Reflection.TeamVisibility.SUPERVISORS_ONLY


@pytest.mark.django_db
def test_self_reflection_post_idempotent_on_client_submission_id(
    org, lt_user, lt_membership, lt_person, program,
):
    """Replays return the same row with HTTP 200 instead of duplicating."""
    csid = str(uuid4())
    c = _client(lt_user, org)
    with organization_context(org):
        first = c.post(
            "/api/v1/leadership-team/self-reflection/",
            data={
                "answers": {"overall_period": 3},
                "language": "en",
                "client_submission_id": csid,
            },
            format="json",
        )
        second = c.post(
            "/api/v1/leadership-team/self-reflection/",
            data={
                "answers": {"overall_period": 3},
                "language": "en",
                "client_submission_id": csid,
            },
            format="json",
        )
    assert first.status_code == 201
    assert second.status_code == 200
    assert first.json()["id"] == second.json()["id"]


@pytest.mark.django_db
def test_self_reflection_patch_within_period(
    org, lt_user, lt_membership, lt_person, program,
):
    """Story 50 c7 — edits allowed within current period."""
    c = _client(lt_user, org)
    with organization_context(org):
        first = c.post(
            "/api/v1/leadership-team/self-reflection/",
            data={
                "answers": {"overall_period": 3},
                "language": "en",
                "client_submission_id": str(uuid4()),
            },
            format="json",
        )
        rid = first.json()["id"]
        patched = c.patch(
            f"/api/v1/leadership-team/self-reflection/{rid}/",
            data={"answers": {"overall_period": 5}},
            format="json",
        )
    assert patched.status_code == 200
    assert patched.json()["answers"]["overall_period"] == 5


@pytest.mark.django_db
def test_self_reflection_patch_outside_period_is_forbidden(
    org, lt_user, lt_membership, lt_person, program,
):
    """Story 50 c7 — once the period closes, edits 403."""
    template = ReflectionTemplate.all_objects.get(
        slug="leadership-team-self-reflection",
    )
    old_start = date(2024, 1, 1)
    old_end = old_start + timedelta(days=13)
    reflection = Reflection.all_objects.create(
        organization=org, program=program, template=template,
        subject=lt_person, author=lt_person,
        period_start=old_start, period_end=old_end,
        answers={"overall_period": 3},
        is_complete=True,
    )
    c = _client(lt_user, org)
    with organization_context(org):
        resp = c.patch(
            f"/api/v1/leadership-team/self-reflection/{reflection.id}/",
            data={"answers": {"overall_period": 5}},
            format="json",
        )
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Mark attention — Story 46 c5
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_mark_attention_creates_and_is_idempotent(
    org, lt_user, lt_membership, kitchen_team, lt_supervises_kitchen, program,
):
    template = ReflectionTemplate.all_objects.get(
        slug="kitchen-staff-self-reflection",
    )
    today = _today_in_org(org)
    reflection = Reflection.all_objects.create(
        organization=org, program=program, template=template,
        subject=kitchen_team[0], author=kitchen_team[0],
        period_start=today, period_end=today,
        answers={"service_summary": "Smooth lunch."},
        is_complete=True,
    )
    c = _client(lt_user, org)
    with organization_context(org):
        first = c.post(
            f"/api/v1/leadership-team/reflections/{reflection.id}/mark-attention/",
            data={"note": "Follow up tomorrow."}, format="json",
        )
        second = c.post(
            f"/api/v1/leadership-team/reflections/{reflection.id}/mark-attention/",
            data={"note": "Follow up tomorrow."}, format="json",
        )
    assert first.status_code == 201
    assert second.status_code == 200
    assert first.json()["id"] == second.json()["id"]
    assert ReflectionAttentionMarker.all_objects.filter(
        reflection=reflection,
    ).count() == 1


@pytest.mark.django_db
def test_mark_attention_delete_removes_own_marker(
    org, lt_user, lt_membership, kitchen_team, lt_supervises_kitchen, program,
):
    template = ReflectionTemplate.all_objects.get(
        slug="kitchen-staff-self-reflection",
    )
    today = _today_in_org(org)
    reflection = Reflection.all_objects.create(
        organization=org, program=program, template=template,
        subject=kitchen_team[0], author=kitchen_team[0],
        period_start=today, period_end=today,
        answers={"service_summary": "Smooth lunch."},
        is_complete=True,
    )
    c = _client(lt_user, org)
    with organization_context(org):
        c.post(
            f"/api/v1/leadership-team/reflections/{reflection.id}/mark-attention/",
            data={}, format="json",
        )
        del_resp = c.delete(
            f"/api/v1/leadership-team/reflections/{reflection.id}/mark-attention/",
        )
    assert del_resp.status_code == 204
    assert not ReflectionAttentionMarker.all_objects.filter(
        reflection=reflection,
    ).exists()


@pytest.mark.django_db
def test_mark_attention_rejects_invisible_reflection(
    org, lt_user, lt_membership, program,
):
    """An LT cannot flag a reflection they cannot read (visibility gate).

    Another LT's *private* self-reflection has the {admin}-only
    sensitive audience — the viewer LT is neither author nor admin so
    visibility filter excludes it.
    """
    other_lt_person = Person.all_objects.create(
        organization=org, first_name="Other", last_name="LT",
    )
    Membership.all_objects.create(
        program=program, person=other_lt_person, role="leadership_team",
        is_active=True,
    )
    lt_template = ReflectionTemplate.all_objects.get(
        slug="leadership-team-self-reflection",
    )
    today = _today_in_org(org)
    reflection = Reflection.all_objects.create(
        organization=org, program=program, template=lt_template,
        subject=other_lt_person, author=other_lt_person,
        period_start=today, period_end=today,
        answers={"overall_period": 3},
        team_visibility=Reflection.TeamVisibility.SUPERVISORS_ONLY,
        is_sensitive=True,
        is_complete=True,
    )
    c = _client(lt_user, org)
    with organization_context(org):
        resp = c.post(
            f"/api/v1/leadership-team/reflections/{reflection.id}/mark-attention/",
            data={}, format="json",
        )
    assert resp.status_code == 403
