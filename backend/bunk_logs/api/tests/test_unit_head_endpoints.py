"""Tests for ``/api/v1/unit-head/*`` (Step 7_7, Stories 10-17).

Covers supervision-driven bunk resolution, attention badges, score
grid, bunk-concerns surfacing, camper-dashboard ranges + visibility,
self-reflection write + history, and the supervision permission gate
on every endpoint.

Visibility specifics (sensitive note exclusion, edit-window 403s,
template fall-back) live in their own focused module tests; here we
focus on the UH-specific composition.
"""

from __future__ import annotations

from datetime import date
from datetime import datetime
from datetime import timedelta
from uuid import uuid4

import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.utils import timezone
from rest_framework.test import APIClient

from bunk_logs.core.context import organization_context
from bunk_logs.core.models import AssignmentGroup
from bunk_logs.core.models import AssignmentGroupMembership
from bunk_logs.core.models import CamperDayState
from bunk_logs.core.models import MaintenanceTicket
from bunk_logs.core.models import Membership
from bunk_logs.core.models import Note
from bunk_logs.core.models import Order
from bunk_logs.core.models import Organization
from bunk_logs.core.models import Person
from bunk_logs.core.models import Program
from bunk_logs.core.models import Reflection
from bunk_logs.core.models import ReflectionTemplate
from bunk_logs.core.models import Supervision
from bunk_logs.core.state_machine import OrderStateMachine

User = get_user_model()


CAMPER_REFLECTION_SCHEMA = {
    "fields": [
        {
            "key": "overall",
            "type": "single_rating",
            "required": False,
            "scale": [1, 5],
            "scale_labels": {"en": ["1", "2", "3", "4", "5"]},
            "dashboard_role": "primary_rating",
        },
        {
            "key": "camper_scores",
            "type": "rating_group",
            "required": False,
            "scale": [1, 5],
            "scale_labels": {"en": ["1", "2", "3", "4", "5"]},
            "dashboard_role": "category_ratings",
            "categories": [
                {"key": "behavior", "labels": {"en": "Behavior"}},
                {"key": "participation", "labels": {"en": "Participation"}},
            ],
        },
        {
            "key": "request_unit_head_help",
            "type": "yes_no",
            "required": False,
            "prompts": {"en": "Help requested?"},
        },
        {
            "key": "notes",
            "type": "textarea",
            "required": False,
            "prompts": {"en": "Notes"},
        },
    ],
}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _clear_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def org(db):
    return Organization.objects.create(name="UH Camp", slug="uh-camp", settings={"rollover_hour": 0, "timezone": "UTC"})


@pytest.fixture
def program(org):
    return Program.all_objects.create(
        organization=org,
        name="UH Camp Summer 2026",
        slug="uh-summer-2026",
        program_type="summer_camp",
        start_date=date(2026, 6, 1),
        end_date=date(2026, 8, 31),
    )


@pytest.fixture
def uh_user():
    return User.objects.create_user(email="uh@uh.test", password="pw")


@pytest.fixture
def uh_person(org, uh_user):
    return Person.all_objects.create(
        organization=org,
        first_name="Avery",
        last_name="Reeves",
        user=uh_user,
    )


@pytest.fixture
def uh_membership(program, uh_person):
    return Membership.all_objects.create(
        program=program, person=uh_person, role="unit_head", is_active=True,
    )


@pytest.fixture
def counselor_user():
    return User.objects.create_user(email="counselor@uh.test", password="pw")


@pytest.fixture
def counselor_person(org, counselor_user):
    return Person.all_objects.create(
        organization=org,
        first_name="Mira",
        last_name="Sandberg",
        user=counselor_user,
    )


@pytest.fixture
def counselor_membership(program, counselor_person):
    return Membership.all_objects.create(
        program=program, person=counselor_person, role="counselor", is_active=True,
    )


@pytest.fixture
def bunk(org, program):
    return AssignmentGroup.objects.create(
        organization=org,
        program=program,
        name="Bunk Birch",
        slug="bunk-birch",
        group_type="bunk",
        is_active=True,
    )


@pytest.fixture
def other_bunk(org, program):
    return AssignmentGroup.objects.create(
        organization=org,
        program=program,
        name="Bunk Pine",
        slug="bunk-pine",
        group_type="bunk",
        is_active=True,
    )


@pytest.fixture
def counselor_authors_bunk(bunk, counselor_person):
    return AssignmentGroupMembership.objects.create(
        group=bunk, person=counselor_person, role_in_group="author", is_active=True,
    )


@pytest.fixture
def uh_supervises_counselor(uh_membership, counselor_membership):
    return Supervision.all_objects.create(
        supervisor_membership=uh_membership,
        target_type="membership",
        target_membership=counselor_membership,
        start_date=date(2026, 1, 1),
    )


@pytest.fixture
def campers(org, bunk):
    persons = []
    for first, last in [("Sarah", "Levin"), ("Maya", "Cohen"), ("Eli", "Roth")]:
        p = Person.all_objects.create(organization=org, first_name=first, last_name=last)
        AssignmentGroupMembership.objects.create(
            group=bunk, person=p, role_in_group="subject", is_active=True,
        )
        persons.append(p)
    return persons


@pytest.fixture
def camper_template(org, program):
    from bunk_logs.api.tests.conftest import make_active_assignment

    t = ReflectionTemplate.all_objects.create(
        organization=org,
        name="Bunk Log",
        slug="bunk-log-uh",
        cadence="daily",
        subject_mode="single_subject",
        assignment_group_types=["bunk"],
        schema=CAMPER_REFLECTION_SCHEMA,
        languages=["en"],
        is_active=True,
        program_type="summer_camp",
        author_role_filter=["counselor"],
    )
    make_active_assignment(template=t, program=program, target_role="counselor")
    return t


def _client(user, org):
    c = APIClient()
    c.force_authenticate(user=user)
    c.credentials(HTTP_X_ORGANIZATION_SLUG=org.slug)
    return c


def _today_in_org(org):
    """Test helper that mirrors the server's ``get_today`` result."""
    from bunk_logs.core.time_utils import get_today
    return get_today(org)


# ---------------------------------------------------------------------------
# Dashboard (Story 10)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_dashboard_requires_auth():
    c = APIClient()
    resp = c.get("/api/v1/unit-head/dashboard/")
    assert resp.status_code in {401, 403}


@pytest.mark.django_db
def test_dashboard_requires_uh_membership(org, counselor_user, counselor_person, counselor_membership):
    # Counselor has org + person but no UH membership — should 403.
    c = _client(counselor_user, org)
    with organization_context(org):
        resp = c.get("/api/v1/unit-head/dashboard/?nocache=1")
    assert resp.status_code == 403


@pytest.mark.django_db
def test_dashboard_lists_supervised_bunks_only(
    org, program, uh_user, uh_membership, bunk, other_bunk,
    counselor_person, counselor_membership, counselor_authors_bunk,
    uh_supervises_counselor,
):
    """Story 10 criterion 5: only bunks where a supervised counselor authors."""
    c = _client(uh_user, org)
    with organization_context(org):
        resp = c.get("/api/v1/unit-head/dashboard/?nocache=1")
    assert resp.status_code == 200
    body = resp.json()
    names = [b["name"] for b in body["bunks"]]
    assert names == [bunk.name]  # other_bunk has no supervised counselor


@pytest.mark.django_db
def test_dashboard_completion_excludes_off_camp(
    org, program, uh_user, uh_membership, bunk,
    counselor_person, counselor_membership, counselor_authors_bunk,
    uh_supervises_counselor, campers, camper_template,
):
    """Off-camp campers are excluded from the 'expected' denominator."""
    today = _today_in_org(org)
    # Mark one camper off-camp
    CamperDayState.objects.create(
        organization=org, program=program, camper=campers[0],
        date=today, is_off_camp=True,
    )
    # Submit a reflection for one of the on-camp campers
    Reflection.all_objects.create(
        organization=org, program=program,
        template=camper_template, assignment_group=bunk,
        subject=campers[1], author=counselor_person,
        period_start=today, period_end=today,
        answers={"overall": 5}, language="en", is_complete=True,
    )
    c = _client(uh_user, org)
    with organization_context(org):
        resp = c.get("/api/v1/unit-head/dashboard/?nocache=1")
    body = resp.json()
    completion = body["bunks"][0]["completion"]
    assert completion == {"submitted": 1, "expected": 2, "off_camp": 1}


@pytest.mark.django_db
def test_dashboard_attention_badges_and_sort(
    org, program, uh_user, uh_membership, bunk, other_bunk,
    counselor_person, counselor_membership, counselor_authors_bunk,
    uh_supervises_counselor, campers, camper_template,
):
    """Help requested + off-camp + bunk-concerns badges; badged bunks sort first."""
    today = _today_in_org(org)

    # Mark a camper off-camp on Birch — triggers `off_camp` badge.
    CamperDayState.objects.create(
        organization=org, program=program, camper=campers[0],
        date=today, is_off_camp=True,
    )
    # Help requested by another camper.
    Reflection.all_objects.create(
        organization=org, program=program,
        template=camper_template, assignment_group=bunk,
        subject=campers[1], author=counselor_person,
        period_start=today, period_end=today,
        answers={"request_unit_head_help": True}, is_complete=True,
    )
    # Pine has a supervised counselor too so it makes the list.
    pine_counselor = Person.all_objects.create(
        organization=org, first_name="Lior", last_name="Yarden",
    )
    pine_membership = Membership.all_objects.create(
        program=program, person=pine_counselor, role="counselor", is_active=True,
    )
    AssignmentGroupMembership.objects.create(
        group=other_bunk, person=pine_counselor, role_in_group="author", is_active=True,
    )
    Supervision.all_objects.create(
        supervisor_membership=uh_membership,
        target_type="membership",
        target_membership=pine_membership,
        start_date=date(2026, 1, 1),
    )

    c = _client(uh_user, org)
    with organization_context(org):
        resp = c.get("/api/v1/unit-head/dashboard/?nocache=1")
    body = resp.json()
    # Birch must sort first because it has badges; Pine has none.
    names = [b["name"] for b in body["bunks"]]
    assert names[0] == "Bunk Birch"
    assert names[1] == "Bunk Pine"
    birch_badges = body["bunks"][0]["badges"]
    assert "help_requested" in birch_badges
    assert "off_camp" in birch_badges
    # help_requested must precede off_camp per ATTENTION_BADGE_ORDER.
    assert birch_badges.index("help_requested") < birch_badges.index("off_camp")


@pytest.mark.django_db
def test_dashboard_includes_my_reflection_state(
    org, program, uh_user, uh_membership, bunk,
    counselor_person, counselor_membership, counselor_authors_bunk,
    uh_supervises_counselor, campers, uh_person,
):
    """Story 10 criterion 10 + Story 16: My reflection section state."""
    c = _client(uh_user, org)
    with organization_context(org):
        # Missing state initially
        resp = c.get("/api/v1/unit-head/dashboard/?nocache=1")
    assert resp.json()["self_reflection"]["state"] == "missing"

    # Create one + re-fetch
    today = _today_in_org(org)
    template = ReflectionTemplate.all_objects.get(slug="unit-head-self-reflection")
    Reflection.all_objects.create(
        organization=org, program=program,
        template=template, subject=uh_person, author=uh_person,
        period_start=today, period_end=today,
        answers={"day_off": True}, is_complete=True,
    )
    with organization_context(org):
        resp = c.get("/api/v1/unit-head/dashboard/?nocache=1")
    body = resp.json()["self_reflection"]
    assert body["state"] == "day_off"
    assert body["editable"] is True


# ---------------------------------------------------------------------------
# Bunk Dashboard (Story 11) + Score Grid (Story 12)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_bunk_dashboard_requires_supervision(
    org, program, uh_user, uh_membership, bunk, other_bunk,
):
    """Forbidden if the UH doesn't supervise the bunk."""
    c = _client(uh_user, org)
    with organization_context(org):
        resp = c.get(f"/api/v1/unit-head/bunks/{other_bunk.id}/")
    assert resp.status_code == 403


@pytest.mark.django_db
def test_bunk_dashboard_payload_shape(
    org, program, uh_user, uh_membership, bunk,
    counselor_person, counselor_membership, counselor_authors_bunk,
    uh_supervises_counselor, campers, camper_template,
):
    """Every spec section is present in the response."""
    today = _today_in_org(org)
    Reflection.all_objects.create(
        organization=org, program=program,
        template=camper_template, assignment_group=bunk,
        subject=campers[0], author=counselor_person,
        period_start=today, period_end=today,
        answers={
            "overall": 4,
            "camper_scores": {"behavior": 5, "participation": 3},
            "notes": "Great day at the lake.",
        },
        is_complete=True,
    )
    c = _client(uh_user, org)
    with organization_context(org):
        resp = c.get(f"/api/v1/unit-head/bunks/{bunk.id}/?date={today.isoformat()}")
    assert resp.status_code == 200
    body = resp.json()
    expected_sections = {
        "header", "help_requested", "camper_care_help_requested", "off_camp",
        "bunk_concerns", "score_grid", "orders", "specialist_reports",
    }
    assert expected_sections.issubset(body.keys())
    # Score grid: ratings + yes/no + textarea columns, 3 rows.
    cols = [c["label"] for c in body["score_grid"]["columns"]]
    assert cols == [
        "overall",
        "camper_scores__behavior",
        "camper_scores__participation",
        "request_unit_head_help",
        "notes",
    ]
    headers = [c["header"] for c in body["score_grid"]["columns"]]
    assert headers == [
        "overall",
        "Behavior",
        "Participation",
        "Help requested?",
        "Notes",
    ]
    rows = body["score_grid"]["rows"]
    assert len(rows) == 3
    # Submitted camper has cell values; the others have None.
    sarah_row = next(r for r in rows if r["camper"]["first_name"] == "Sarah")
    assert sarah_row["cells"] == {
        "overall": 4.0,
        "camper_scores__behavior": 5.0,
        "camper_scores__participation": 3.0,
        "request_unit_head_help": None,
        "notes": "Great day at the lake.",
    }
    maya_row = next(r for r in rows if r["camper"]["first_name"] == "Maya")
    assert maya_row["cells"] == {
        "overall": None,
        "camper_scores__behavior": None,
        "camper_scores__participation": None,
        "request_unit_head_help": None,
        "notes": None,
    }


@pytest.mark.django_db
def test_bunk_dashboard_surfaces_camper_care_help(
    org, program, uh_user, uh_membership, bunk,
    counselor_person, counselor_membership, counselor_authors_bunk,
    uh_supervises_counselor, campers, camper_template,
):
    """A camper reflection flagging `request_camper_care_help` surfaces in the card list."""
    today = _today_in_org(org)
    Reflection.all_objects.create(
        organization=org, program=program,
        template=camper_template, assignment_group=bunk,
        subject=campers[0], author=counselor_person,
        period_start=today, period_end=today,
        answers={"request_camper_care_help": "yes"},
        is_complete=True,
    )
    c = _client(uh_user, org)
    with organization_context(org):
        resp = c.get(f"/api/v1/unit-head/bunks/{bunk.id}/?date={today.isoformat()}")
    assert resp.status_code == 200
    cc = resp.json()["camper_care_help_requested"]
    assert [p["id"] for p in cc] == [campers[0].id]


@pytest.mark.django_db
def test_bunk_dashboard_future_date_rejected(
    org, uh_user, uh_membership, bunk,
    counselor_person, counselor_membership, counselor_authors_bunk,
    uh_supervises_counselor,
):
    """Story 11 criterion 3 — future dates not selectable."""
    c = _client(uh_user, org)
    future = (_today_in_org(org) + timedelta(days=1)).isoformat()
    with organization_context(org):
        resp = c.get(f"/api/v1/unit-head/bunks/{bunk.id}/?date={future}")
    assert resp.status_code == 400


@pytest.mark.django_db
def test_bunk_dashboard_surfaces_bunk_concerns(
    org, program, uh_user, uh_membership, bunk,
    counselor_user, counselor_person, counselor_membership, counselor_authors_bunk,
    uh_supervises_counselor,
):
    """Counselor self-reflection referencing this bunk shows up in `bunk_concerns`."""
    today = _today_in_org(org)
    counselor_template = ReflectionTemplate.all_objects.get(
        slug="counselor-self-reflection",
    )
    Reflection.all_objects.create(
        organization=org, program=program,
        template=counselor_template,
        subject=counselor_person, author=counselor_person,
        period_start=today, period_end=today,
        answers={
            "bunk_concerns_bunks": [bunk.id],
            "concern": "Group dynamics tense today.",
        },
        is_complete=True,
        team_visibility=Reflection.TeamVisibility.SUPERVISORS_ONLY,
    )

    c = _client(uh_user, org)
    with organization_context(org):
        resp = c.get(f"/api/v1/unit-head/bunks/{bunk.id}/?date={today.isoformat()}")
    body = resp.json()
    assert len(body["bunk_concerns"]) == 1
    assert body["bunk_concerns"][0]["open_concern"].startswith("Group dynamics")


@pytest.mark.django_db
def test_bunk_dashboard_orders_filter_to_bunk_counselors_only(
    org, program, uh_user, uh_membership, bunk, other_bunk,
    counselor_user, counselor_person, counselor_membership,
    counselor_authors_bunk, uh_supervises_counselor, campers,
):
    """Story 14: only orders from THIS bunk's counselors appear."""
    today = _today_in_org(org)
    # Another counselor on a different bunk.
    other_counselor = Person.all_objects.create(
        organization=org, first_name="Tal", last_name="Stein",
    )
    other_membership = Membership.all_objects.create(
        program=program, person=other_counselor, role="counselor", is_active=True,
    )
    AssignmentGroupMembership.objects.create(
        group=other_bunk, person=other_counselor,
        role_in_group="author", is_active=True,
    )

    # Order from THE bunk's counselor — should appear.
    Order.all_objects.create(
        organization=org, program=program,
        submitted_by=counselor_membership,
        subject=campers[0],
        item="Toothpaste", status=OrderStateMachine.NEW,
    )
    # Order from a different bunk's counselor — must NOT appear.
    Order.all_objects.create(
        organization=org, program=program,
        submitted_by=other_membership,
        item="Soap", status=OrderStateMachine.NEW,
    )
    # Maintenance ticket from the bunk's counselor — should appear.
    MaintenanceTicket.all_objects.create(
        organization=org, program=program,
        submitted_by=counselor_membership,
        location="Bunk Birch", category=MaintenanceTicket.Category.LEAK,
        status=OrderStateMachine.NEW,
    )

    c = _client(uh_user, org)
    with organization_context(org):
        resp = c.get(f"/api/v1/unit-head/bunks/{bunk.id}/?date={today.isoformat()}")
    body = resp.json()
    today_items = body["orders"]["today"]
    items = [(i["kind"], i.get("item") or i.get("location")) for i in today_items]
    assert ("camper_care", "Toothpaste") in items
    assert ("maintenance", "Bunk Birch") in items
    assert all(i.get("item") != "Soap" for i in today_items)
    assert body["orders"]["counts"] == {"open": 2, "in_progress": 0, "resolved": 0}


@pytest.mark.django_db
def test_bunk_dashboard_orders_carries_over_open(
    org, program, uh_user, uh_membership, bunk,
    counselor_membership, counselor_authors_bunk,
    uh_supervises_counselor, campers,
):
    """Story 14 criterion 6 — carry over older still-open orders."""
    today = _today_in_org(org)
    old = today - timedelta(days=3)
    order = Order.all_objects.create(
        organization=org, program=program,
        submitted_by=counselor_membership, subject=campers[0],
        item="Bandages", status=OrderStateMachine.IN_PROGRESS,
    )
    # Manually backdate (auto_now_add doesn't allow constructor override).
    backdate = timezone.make_aware(datetime.combine(old, datetime.min.time()))
    Order.all_objects.filter(id=order.id).update(created_at=backdate)

    c = _client(uh_user, org)
    with organization_context(org):
        resp = c.get(f"/api/v1/unit-head/bunks/{bunk.id}/?date={today.isoformat()}")
    body = resp.json()
    assert len(body["orders"]["today"]) == 0
    assert len(body["orders"]["carried_over"]) == 1
    assert body["orders"]["carried_over"][0]["item"] == "Bandages"


@pytest.mark.django_db
def test_bunk_dashboard_specialist_reports_excludes_sensitive(
    org, program, uh_user, uh_membership, bunk,
    counselor_person, counselor_membership, counselor_authors_bunk,
    uh_supervises_counselor, campers,
):
    """Story 15 criterion 4 — sensitive notes excluded; placeholder count emitted."""
    today = _today_in_org(org)
    specialist = Person.all_objects.create(
        organization=org, first_name="Dr.", last_name="Avi",
    )
    Membership.all_objects.create(
        program=program, person=specialist, role="specialist", is_active=True,
    )
    # Non-sensitive note: visible to UH.
    Note.all_objects.create(
        organization=org, program=program, subject=campers[0], author=specialist,
        note_type=Note.NoteType.SPECIALIST,
        body="Routine specialist observation about Sarah.",
    )
    # Sensitive note: NOT visible to UH (UH not in audience for SPECIALIST_NOTE sensitive variant).
    Note.all_objects.create(
        organization=org, program=program, subject=campers[1], author=specialist,
        note_type=Note.NoteType.SPECIALIST,
        body="Sensitive medical information.",
        is_sensitive=True,
    )

    c = _client(uh_user, org)
    with organization_context(org):
        resp = c.get(f"/api/v1/unit-head/bunks/{bunk.id}/?date={today.isoformat()}")
    body = resp.json()
    visible_bodies = [
        n["body"] for n in (body["specialist_reports"]["today"]
                            + body["specialist_reports"]["recent"])
    ]
    assert "Routine specialist observation about Sarah." in visible_bodies
    assert all("Sensitive" not in b for b in visible_bodies)
    counts = body["specialist_reports"]["sensitive_counts_by_camper"]
    assert counts.get(str(campers[1].id)) == 1 or counts.get(campers[1].id) == 1


# ---------------------------------------------------------------------------
# Camper Dashboard (Story 13)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_camper_dashboard_requires_supervision(
    org, program, uh_user, uh_membership, other_bunk, campers,
):
    """403 if the camper isn't rostered under any supervised bunk."""
    # campers fixture rosters into `bunk`, not other_bunk; this UH supervises nothing.
    c = _client(uh_user, org)
    with organization_context(org):
        resp = c.get(f"/api/v1/unit-head/campers/{campers[0].id}/")
    assert resp.status_code == 403


@pytest.mark.django_db
def test_camper_dashboard_trend_gaps_as_null(
    org, program, uh_user, uh_membership, bunk,
    counselor_person, counselor_membership, counselor_authors_bunk,
    uh_supervises_counselor, campers, camper_template,
):
    """Story 13 criterion 4 — missing days are gaps, not zeros."""
    today = _today_in_org(org)
    # Submit only for 2 days out of 7.
    for d in (today - timedelta(days=6), today - timedelta(days=2)):
        Reflection.all_objects.create(
            organization=org, program=program,
            template=camper_template, assignment_group=bunk,
            subject=campers[0], author=counselor_person,
            period_start=d, period_end=d,
            answers={"overall": 4}, is_complete=True,
        )

    c = _client(uh_user, org)
    with organization_context(org):
        resp = c.get(
            f"/api/v1/unit-head/campers/{campers[0].id}/?range=this_week",
        )
    body = resp.json()
    overall_series = next(s for s in body["trend"]["series"] if s["label"] == "overall")
    values = [p["value"] for p in overall_series["points"]]
    # 7 days; 2 numeric, 5 None.
    assert values.count(4.0) == 2
    assert values.count(None) == 5


@pytest.mark.django_db
def test_camper_dashboard_today_section_and_flags(
    org, program, uh_user, uh_membership, bunk,
    counselor_person, counselor_membership, counselor_authors_bunk,
    uh_supervises_counselor, campers, camper_template,
):
    """Story 13 criterion 1: full reflection + scores + flags returned."""
    today = _today_in_org(org)
    Reflection.all_objects.create(
        organization=org, program=program,
        template=camper_template, assignment_group=bunk,
        subject=campers[0], author=counselor_person,
        period_start=today, period_end=today,
        answers={
            "overall": 2,
            "camper_scores": {"behavior": 3, "participation": 4},
            "request_unit_head_help": True,
            "notes": "Talked to Sarah after lunch.",
        },
        is_complete=True,
    )

    c = _client(uh_user, org)
    with organization_context(org):
        resp = c.get(f"/api/v1/unit-head/campers/{campers[0].id}/")
    body = resp.json()
    assert body["today_reflection"] is not None
    assert body["today_reflection"]["fields"]
    # Help-requested flag must surface as a Today flag.
    flag_keys = {f["key"] for f in body["today_flags"]}
    assert "request_unit_head_help" in flag_keys
    score_labels = {s["label"] for s in body["today_scores"]}
    assert "overall" in score_labels
    assert "camper_scores__behavior" in score_labels


# ---------------------------------------------------------------------------
# Self-reflection (Stories 16, 17)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_self_reflection_day_off_post(
    org, uh_user, uh_membership, uh_person,
):
    c = _client(uh_user, org)
    with organization_context(org):
        resp = c.post(
            "/api/v1/unit-head/self-reflection/",
            data={
                "day_off": True,
                "language": "en",
                "client_submission_id": str(uuid4()),
            },
            format="json",
        )
    assert resp.status_code == 201
    body = resp.json()
    assert body["answers"] == {"day_off": True}


@pytest.mark.django_db
def test_self_reflection_bunk_concerns_rejects_non_supervised_bunk(
    org, program, uh_user, uh_membership, uh_person,
    other_bunk,
):
    """UH cannot flag bunks they don't supervise (UH2)."""
    c = _client(uh_user, org)
    with organization_context(org):
        resp = c.post(
            "/api/v1/unit-head/self-reflection/",
            data={
                "day_off": False,
                "answers": {
                    "overall_day": 4,
                    "bunk_concerns_bunks": [other_bunk.id],
                },
                "language": "en",
                "client_submission_id": str(uuid4()),
            },
            format="json",
        )
    assert resp.status_code == 403


@pytest.mark.django_db
def test_self_reflection_bunk_concerns_accepts_supervised_bunk(
    org, program, uh_user, uh_membership, uh_person,
    bunk, counselor_person, counselor_membership, counselor_authors_bunk,
    uh_supervises_counselor,
):
    c = _client(uh_user, org)
    with organization_context(org):
        resp = c.post(
            "/api/v1/unit-head/self-reflection/",
            data={
                "day_off": False,
                "answers": {
                    "overall_day": 4,
                    "bunk_concerns_bunks": [bunk.id],
                    "bunk_concerns_note": "Sleep schedule rough.",
                },
                "language": "en",
                "client_submission_id": str(uuid4()),
            },
            format="json",
        )
    assert resp.status_code == 201
    refl = Reflection.all_objects.get(author=uh_person, subject=uh_person)
    assert refl.answers["bunk_concerns_bunks"] == [bunk.id]


@pytest.mark.django_db
def test_self_reflection_idempotent_replay(
    org, uh_user, uh_membership, uh_person,
):
    """Same client_submission_id replays the same row with HTTP 200."""
    cid = str(uuid4())
    c = _client(uh_user, org)
    with organization_context(org):
        first = c.post(
            "/api/v1/unit-head/self-reflection/",
            data={"day_off": True, "client_submission_id": cid},
            format="json",
        )
        assert first.status_code == 201
        replay = c.post(
            "/api/v1/unit-head/self-reflection/",
            data={"day_off": True, "client_submission_id": cid},
            format="json",
        )
    assert replay.status_code == 200
    assert replay.json()["id"] == first.json()["id"]


@pytest.mark.django_db
def test_self_reflection_patch_within_today(
    org, program, uh_user, uh_membership, uh_person,
):
    today = _today_in_org(org)
    template = ReflectionTemplate.all_objects.get(slug="unit-head-self-reflection")
    refl = Reflection.all_objects.create(
        organization=org, program=program, template=template,
        subject=uh_person, author=uh_person,
        period_start=today, period_end=today,
        answers={"overall_day": 3}, is_complete=True,
    )
    c = _client(uh_user, org)
    with organization_context(org):
        resp = c.patch(
            f"/api/v1/unit-head/self-reflection/{refl.id}/",
            data={"answers": {"overall_day": 5}},
            format="json",
        )
    assert resp.status_code == 200
    refl.refresh_from_db()
    assert refl.answers["overall_day"] == 5


@pytest.mark.django_db
def test_self_reflection_patch_outside_window_403(
    org, program, uh_user, uh_membership, uh_person,
):
    """Story 17 criterion 2: editable until rollover; locked after."""
    today = _today_in_org(org)
    template = ReflectionTemplate.all_objects.get(slug="unit-head-self-reflection")
    # Backdate by one day so today's window doesn't include it.
    refl = Reflection.all_objects.create(
        organization=org, program=program, template=template,
        subject=uh_person, author=uh_person,
        period_start=today - timedelta(days=1),
        period_end=today - timedelta(days=1),
        answers={"overall_day": 3}, is_complete=True,
    )
    c = _client(uh_user, org)
    with organization_context(org):
        resp = c.patch(
            f"/api/v1/unit-head/self-reflection/{refl.id}/",
            data={"answers": {"overall_day": 5}},
            format="json",
        )
    assert resp.status_code == 403


@pytest.mark.django_db
def test_self_reflection_history_shows_gaps_and_day_off(
    org, program, uh_user, uh_membership, uh_person,
):
    """Story 17 criterion 5: gaps + day-off indicators in history rows."""
    today = _today_in_org(org)
    template = ReflectionTemplate.all_objects.get(slug="unit-head-self-reflection")
    # Submit on day -1 (day off) and day -3 (full).
    Reflection.all_objects.create(
        organization=org, program=program, template=template,
        subject=uh_person, author=uh_person,
        period_start=today - timedelta(days=1),
        period_end=today - timedelta(days=1),
        answers={"day_off": True}, is_complete=True,
    )
    Reflection.all_objects.create(
        organization=org, program=program, template=template,
        subject=uh_person, author=uh_person,
        period_start=today - timedelta(days=3),
        period_end=today - timedelta(days=3),
        answers={"overall_day": 4, "concern": "Long week."}, is_complete=True,
    )

    c = _client(uh_user, org)
    with organization_context(org):
        resp = c.get("/api/v1/unit-head/self-reflection/history/")
    body = resp.json()
    rows = {r["date"]: r for r in body["results"]}
    yesterday_row = rows[(today - timedelta(days=1)).isoformat()]
    today_row = rows[today.isoformat()]
    day_minus_3 = rows[(today - timedelta(days=3)).isoformat()]
    day_minus_2 = rows[(today - timedelta(days=2)).isoformat()]
    assert yesterday_row["is_day_off"] is True
    assert yesterday_row["submitted"] is True
    assert today_row["submitted"] is False  # gap on today
    assert day_minus_3["submitted"] is True
    assert day_minus_3["preview"]  # non-empty
    assert day_minus_2["submitted"] is False  # gap row


@pytest.mark.django_db
def test_self_reflection_history_does_not_show_other_uh_rows(
    org, program, uh_user, uh_membership, uh_person,
):
    """UH6: another UH's reflections aren't visible."""
    today = _today_in_org(org)
    template = ReflectionTemplate.all_objects.get(slug="unit-head-self-reflection")

    other_uh_user = User.objects.create_user(email="other@uh.test", password="pw")
    other_uh_person = Person.all_objects.create(
        organization=org, first_name="Sam", last_name="Cole", user=other_uh_user,
    )
    Membership.all_objects.create(
        program=program, person=other_uh_person, role="unit_head", is_active=True,
    )
    Reflection.all_objects.create(
        organization=org, program=program, template=template,
        subject=other_uh_person, author=other_uh_person,
        period_start=today, period_end=today,
        answers={"overall_day": 5}, is_complete=True,
    )

    c = _client(uh_user, org)
    with organization_context(org):
        resp = c.get("/api/v1/unit-head/self-reflection/history/")
    rows = {r["date"]: r for r in resp.json()["results"]}
    today_row = rows[today.isoformat()]
    assert today_row["submitted"] is False
    assert today_row["reflection_id"] is None


@pytest.mark.django_db
def test_self_reflection_supports_non_daily_cadence(
    org, program, uh_user, uh_membership, uh_person,
):
    """A biweekly UH template resolves, submits, and reports state per period."""
    from bunk_logs.core.time_utils import get_current_period

    template = ReflectionTemplate.all_objects.get(slug="unit-head-self-reflection")
    template.cadence = "biweekly"
    template.save(update_fields=["cadence"])

    today = _today_in_org(org)
    p_start, p_end = get_current_period("biweekly", org, program=program, anchor=today)
    assert p_start != p_end  # a real multi-day window, not today-only

    c = _client(uh_user, org)

    # Dashboard resolves the template despite the non-daily cadence.
    with organization_context(org):
        resp = c.get("/api/v1/unit-head/dashboard/?nocache=1")
    body = resp.json()["self_reflection"]
    assert body["template_id"] == template.id
    assert body["state"] == "missing"
    assert body["cadence"] == "biweekly"
    assert body["period_start"] == p_start.isoformat()
    assert body["period_end"] == p_end.isoformat()

    # Submitting stores the reflection across the whole period window.
    with organization_context(org):
        post = c.post(
            "/api/v1/unit-head/self-reflection/",
            data={"day_off": True, "client_submission_id": str(uuid4())},
            format="json",
        )
    assert post.status_code == 201, post.content
    refl = Reflection.all_objects.get(author=uh_person, template=template)
    assert (refl.period_start, refl.period_end) == (p_start, p_end)

    # Dashboard now reports complete for the current period + history shows it.
    with organization_context(org):
        resp2 = c.get("/api/v1/unit-head/dashboard/?nocache=1")
        hist = c.get("/api/v1/unit-head/self-reflection/history/")
    body2 = resp2.json()["self_reflection"]
    assert body2["state"] == "day_off"
    assert body2["reflection_id"] == refl.id
    assert body2["editable"] is True

    rows = {r["date"]: r for r in hist.json()["results"]}
    period_row = rows[p_start.isoformat()]
    assert period_row["submitted"] is True
    assert period_row["editable"] is True
    assert period_row["period_end"] == p_end.isoformat()
