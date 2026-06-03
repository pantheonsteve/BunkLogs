"""Tests for the assignment-centric Reflections Dashboard (overhaul).

Covers the selector visibility scoping (admin = all, supervising LT = their
role, non-supervisor = none, admin grant widens) and the per-assignment
dashboard data (completion roster, summary, empty-period edge).
"""

from __future__ import annotations

from datetime import date

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework.test import APIRequestFactory

from bunk_logs.api.dashboards.group_template_cards import build_group_template_cards
from bunk_logs.core.context import organization_context
from bunk_logs.core.models import AssignmentDashboardGrant
from bunk_logs.core.models import AssignmentGroup
from bunk_logs.core.models import AssignmentGroupMembership
from bunk_logs.core.models import Membership
from bunk_logs.core.models import Organization
from bunk_logs.core.models import Person
from bunk_logs.core.models import Program
from bunk_logs.core.models import Reflection
from bunk_logs.core.models import ReflectionTemplate
from bunk_logs.core.models import Supervision
from bunk_logs.core.models import TemplateAssignment

User = get_user_model()

DAY = date(2026, 6, 1)
PAST = date(2020, 1, 1)


@pytest.fixture
def org(db):
    return Organization.objects.create(
        name="Reflections Camp", slug="reflections-camp",
        settings={"rollover_hour": 0, "timezone": "UTC"},
    )


@pytest.fixture
def program(org):
    return Program.all_objects.create(
        organization=org, name="Reflections Camp Summer 2026", slug="summer-2026",
        program_type="summer_camp",
        start_date=date(2026, 6, 1), end_date=date(2026, 8, 31),
    )


def _person(org, first, role, program, *, with_user=True):
    user = (
        User.objects.create_user(email=f"{first.lower()}@refl.test", password="pw")
        if with_user else None
    )
    person = Person.all_objects.create(
        organization=org, first_name=first, last_name="X", user=user,
    )
    membership = Membership.all_objects.create(
        program=program, person=person, role=role, is_active=True,
    )
    return user, person, membership


@pytest.fixture
def kitchen_template(org):
    return ReflectionTemplate.all_objects.create(
        organization=org, name="Kitchen Daily", slug="kitchen-daily",
        cadence="daily", role="kitchen_staff",
        schema={"fields": [{"key": "note", "type": "textarea", "prompts": {"en": "Notes?"}}]},
        languages=["en"], subject_mode="self", author_role_filter=["kitchen_staff"],
        status=ReflectionTemplate.Status.PUBLISHED, is_active=True, version=1,
    )


@pytest.fixture
def counselor_template(org):
    return ReflectionTemplate.all_objects.create(
        organization=org, name="Counselor Daily", slug="counselor-daily",
        cadence="daily", role="counselor",
        schema={"fields": [{"key": "note", "type": "textarea", "prompts": {"en": "Notes?"}}]},
        languages=["en"], subject_mode="self", author_role_filter=["counselor"],
        status=ReflectionTemplate.Status.PUBLISHED, is_active=True, version=1,
    )


@pytest.fixture
def bunk_log_template(org):
    return ReflectionTemplate.all_objects.create(
        organization=org, name="Bunk Pulse", slug="bunk-pulse",
        cadence="daily", role="counselor",
        schema={"fields": [{"key": "note", "type": "textarea", "prompts": {"en": "Notes?"}}]},
        languages=["en"], subject_mode="single_subject",
        assignment_scope="per_subject_in_group",
        assignment_group_types=["bunk"], author_role_filter=["counselor"],
        subject_role_filter=["camper"],
        status=ReflectionTemplate.Status.PUBLISHED, is_active=True, version=1,
    )


@pytest.fixture
def kitchen_assignment(org, program, kitchen_template):
    return TemplateAssignment.all_objects.create(
        organization=org, program=program, template=kitchen_template,
        target_type=TemplateAssignment.TargetType.ROLE,
        target_payload={"role": "kitchen_staff"},
        start_date=PAST, status=TemplateAssignment.Status.ACTIVE,
    )


@pytest.fixture
def counselor_assignment(org, program, counselor_template):
    return TemplateAssignment.all_objects.create(
        organization=org, program=program, template=counselor_template,
        target_type=TemplateAssignment.TargetType.ROLE,
        target_payload={"role": "counselor"},
        start_date=PAST, status=TemplateAssignment.Status.ACTIVE,
    )


def _client(user, org):
    c = APIClient()
    c.force_authenticate(user=user)
    c.credentials(HTTP_X_ORGANIZATION_SLUG=org.slug)
    return c


def _kitchen_setup(org, program):
    """Two kitchen staff; k1 submits today, k2 does not."""
    _, k1, _m1 = _person(org, "Kone", "kitchen_staff", program, with_user=False)
    _, k2, _m2 = _person(org, "Ktwo", "kitchen_staff", program, with_user=False)
    return k1, k2


# ---------------------------------------------------------------------------
# Selector visibility
# ---------------------------------------------------------------------------


def _selector(client, org, **params):
    with organization_context(org):
        return client.get("/api/v1/dashboards/assignment-templates/", params)


def _template_ids(resp):
    return {t["template_id"] for t in resp.json()["templates"]}


@pytest.mark.django_db
def test_admin_reflections_scope_lists_self_templates(
    org, program, kitchen_assignment, counselor_assignment,
):
    admin_user, _, _ = _person(org, "Admin", "admin", program)
    c = _client(admin_user, org)
    resp = _selector(c, org, status="active", scope="reflections")
    assert resp.status_code == 200, resp.data
    ids = _template_ids(resp)
    assert kitchen_assignment.template_id in ids
    assert counselor_assignment.template_id in ids


@pytest.mark.django_db
def test_logs_scope_lists_group_assignments_only(
    org, program, kitchen_assignment, bunk_log_template, counselor_template,
):
    admin_user, _, _ = _person(org, "Admin", "admin", program)
    bunk = AssignmentGroup.all_objects.create(
        organization=org, program=program, name="Bunk A", slug="bunk-a", group_type="bunk",
    )
    TemplateAssignment.all_objects.create(
        organization=org, program=program, template=bunk_log_template,
        target_type=TemplateAssignment.TargetType.ASSIGNMENT_GROUP,
        assignment_group=bunk, start_date=PAST,
        status=TemplateAssignment.Status.ACTIVE,
    )
    TemplateAssignment.all_objects.create(
        organization=org, program=program, template=counselor_template,
        target_type=TemplateAssignment.TargetType.ASSIGNMENT_GROUP,
        assignment_group=bunk, start_date=PAST,
        status=TemplateAssignment.Status.ACTIVE,
    )
    c = _client(admin_user, org)
    resp = _selector(c, org, status="active", scope="logs")
    assert resp.status_code == 200, resp.data
    ids = _template_ids(resp)
    assert bunk_log_template.id in ids
    assert counselor_template.id not in ids
    assert kitchen_assignment.template_id not in ids


@pytest.mark.django_db
def test_logs_scope_excludes_self_template_on_bunk_reflections_includes_it(
    org, program, counselor_template,
):
    admin_user, _, _ = _person(org, "Admin", "admin", program)
    bunk = AssignmentGroup.all_objects.create(
        organization=org, program=program, name="Bunk A", slug="bunk-a", group_type="bunk",
    )
    TemplateAssignment.all_objects.create(
        organization=org, program=program, template=counselor_template,
        target_type=TemplateAssignment.TargetType.ASSIGNMENT_GROUP,
        assignment_group=bunk, start_date=PAST,
        status=TemplateAssignment.Status.ACTIVE,
    )
    c = _client(admin_user, org)
    logs = _selector(c, org, status="active", scope="logs")
    refl = _selector(c, org, status="active", scope="reflections")
    assert counselor_template.id not in _template_ids(logs)
    assert counselor_template.id in _template_ids(refl)


@pytest.mark.django_db
def test_selector_groups_assignments_under_one_template(
    org, program, bunk_log_template,
):
    """Two bunk assignments of one template collapse to a single selector row
    with two groups underneath."""
    admin_user, _, _ = _person(org, "Admin", "admin", program)
    bunk_a = AssignmentGroup.all_objects.create(
        organization=org, program=program, name="Bunk A", slug="bunk-a", group_type="bunk",
    )
    bunk_b = AssignmentGroup.all_objects.create(
        organization=org, program=program, name="Bunk B", slug="bunk-b", group_type="bunk",
    )
    for grp in (bunk_a, bunk_b):
        TemplateAssignment.all_objects.create(
            organization=org, program=program, template=bunk_log_template,
            target_type=TemplateAssignment.TargetType.ASSIGNMENT_GROUP,
            assignment_group=grp, start_date=PAST,
            status=TemplateAssignment.Status.ACTIVE,
        )
    c = _client(admin_user, org)
    resp = _selector(c, org, status="active", scope="logs")
    assert resp.status_code == 200, resp.data
    row = next(t for t in resp.json()["templates"] if t["template_id"] == bunk_log_template.id)
    assert row["group_count"] == 2
    labels = {g["label"] for g in row["groups"]}
    assert labels == {"Bunk A", "Bunk B"}
    # Each group carries its program for the Program filter.
    assert all(g["program_label"] == program.name for g in row["groups"])


@pytest.mark.django_db
def test_lt_selector_scoped_to_supervised_role(
    org, program, kitchen_assignment, counselor_assignment,
):
    lt_user, _lt_person, lt_mb = _person(org, "Lead", "leadership_team", program)
    Supervision.all_objects.create(
        supervisor_membership=lt_mb,
        target_type=Supervision.TargetType.ROLE_IN_PROGRAM,
        target_role="kitchen_staff",
        target_program=program,
        start_date=PAST,
    )
    c = _client(lt_user, org)
    resp = _selector(c, org, status="active", scope="reflections")
    assert resp.status_code == 200, resp.data
    ids = _template_ids(resp)
    assert kitchen_assignment.template_id in ids
    assert counselor_assignment.template_id not in ids


@pytest.mark.django_db
def test_non_supervisor_logs_scope_empty(org, program, kitchen_assignment):
    plain_user, _, _ = _person(org, "Plain", "counselor", program)
    c = _client(plain_user, org)
    resp = _selector(c, org, status="active", scope="logs")
    assert resp.status_code == 200
    assert resp.json()["templates"] == []


@pytest.mark.django_db
def test_counselor_sees_own_reflections_scope(
    org, program, counselor_assignment,
):
    plain_user, _, _ = _person(org, "Plain", "counselor", program)
    c = _client(plain_user, org)
    resp = _selector(c, org, status="active", scope="reflections")
    assert resp.status_code == 200
    assert counselor_assignment.template_id in _template_ids(resp)


@pytest.mark.django_db
def test_grant_widens_selector(org, program, counselor_assignment):
    plain_user, _plain_person, plain_mb = _person(org, "Granted", "kitchen_staff", program)
    AssignmentDashboardGrant.objects.create(
        organization=org, assignment=counselor_assignment, membership=plain_mb,
    )
    c = _client(plain_user, org)
    resp = _selector(c, org, status="active", scope="reflections")
    assert resp.status_code == 200
    assert counselor_assignment.template_id in _template_ids(resp)


@pytest.mark.django_db
def test_group_template_cards_exclude_self_reflection_templates(
    org, program, bunk_log_template, counselor_template,
):
    admin_user, _, _ = _person(org, "Admin", "admin", program)
    bunk = AssignmentGroup.all_objects.create(
        organization=org, program=program, name="Bunk A", slug="bunk-a", group_type="bunk",
    )
    for tpl in (bunk_log_template, counselor_template):
        TemplateAssignment.all_objects.create(
            organization=org, program=program, template=tpl,
            target_type=TemplateAssignment.TargetType.ASSIGNMENT_GROUP,
            assignment_group=bunk, start_date=PAST,
            status=TemplateAssignment.Status.ACTIVE,
        )
    req = APIRequestFactory().get("/")
    req.user = admin_user
    with organization_context(org):
        cards = build_group_template_cards(
            request=req, group=bunk, target_date=DAY, organization=org,
        )
    ids = {c["template"]["id"] for c in cards}
    assert bunk_log_template.id in ids
    assert counselor_template.id not in ids


@pytest.mark.django_db
def test_audience_type_for_role_template(org, program, kitchen_assignment):
    admin_user, _, _ = _person(org, "Admin", "admin", program)
    c = _client(admin_user, org)
    resp = _selector(c, org, status="active", scope="reflections")
    row = next(t for t in resp.json()["templates"] if t["template_id"] == kitchen_assignment.template_id)
    assert "team" in row["audience_types"]
    assert any(g["label"] == "Kitchen Staff" for g in row["groups"])


# ---------------------------------------------------------------------------
# Per-template dashboard (aggregated across groups)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_template_dashboard_completion_roster(
    org, program, kitchen_template, kitchen_assignment,
):
    admin_user, _, _ = _person(org, "Admin", "admin", program)
    k1, k2 = _kitchen_setup(org, program)
    Reflection.all_objects.create(
        organization=org, program=program, template=kitchen_template,
        subject=k1, author=k1, period_start=DAY, period_end=DAY,
        answers={"note": "did things"}, is_complete=True,
    )
    c = _client(admin_user, org)
    with organization_context(org):
        resp = c.get(
            f"/api/v1/dashboards/assignment-template/{kitchen_template.id}/",
            {"date": DAY.isoformat()},
        )
    assert resp.status_code == 200, resp.data
    body = resp.json()
    assert body["summary"]["expected_count"] == 2
    assert body["summary"]["submitted_count"] == 1
    assert body["summary"]["completion_rate"] == 0.5
    assert body["summary"]["response_count"] == 1
    roster = {r["person_id"]: r["status"] for r in body["roster"]}
    assert roster[k1.id] == "submitted"
    assert roster[k2.id] == "outstanding"


@pytest.mark.django_db
def test_template_dashboard_returns_responses_block(
    org, program, kitchen_template, kitchen_assignment,
):
    """The dashboard ships a per-reflection responses block (FormResponsesCard
    shape) so the UI can render every column, including scores."""
    admin_user, _, _ = _person(org, "Admin", "admin", program)
    k1, _k2 = _kitchen_setup(org, program)
    Reflection.all_objects.create(
        organization=org, program=program, template=kitchen_template,
        subject=k1, author=k1, period_start=DAY, period_end=DAY,
        answers={"note": "did things"}, is_complete=True,
    )
    c = _client(admin_user, org)
    with organization_context(org):
        resp = c.get(
            f"/api/v1/dashboards/assignment-template/{kitchen_template.id}/",
            {"date": DAY.isoformat()},
        )
    assert resp.status_code == 200, resp.data
    block = resp.json()["responses"]
    assert block["schema_fields"] == kitchen_template.schema["fields"]
    assert len(block["columns"]) >= 1
    assert len(block["reflections"]) == 1
    row = block["reflections"][0]
    assert row["answers"] == {"note": "did things"}
    assert row["subject"]["name"] == "Kone X"
    assert row["date"] == DAY.isoformat()


@pytest.mark.django_db
def test_template_dashboard_completed_tab_shows_historical_responses(
    org, program, counselor_template,
):
    """Completed tab lists ended assignments; the date picker scopes responses."""
    admin_user, _, _ = _person(org, "Admin", "admin", program)

    historical = date(2025, 7, 17)
    bunk = AssignmentGroup.all_objects.create(
        organization=org, program=program, name="Bunk A", slug="bunk-a", group_type="bunk",
    )
    _, author, _ = _person(org, "Counselor", "counselor", program, with_user=False)
    AssignmentGroupMembership.all_objects.create(
        group=bunk, person=author, role_in_group="author", is_active=True,
    )
    TemplateAssignment.all_objects.create(
        organization=org, program=program, template=counselor_template,
        target_type=TemplateAssignment.TargetType.ASSIGNMENT_GROUP,
        assignment_group=bunk,
        start_date=date(2025, 6, 28),
        end_date=date(2025, 7, 26),
        status=TemplateAssignment.Status.ENDED,
    )
    Reflection.all_objects.create(
        organization=org, program=program, template=counselor_template,
        subject=author, author=author, assignment_group=bunk,
        period_start=historical, period_end=historical,
        answers={"note": "during session"}, is_complete=True,
    )
    c = _client(admin_user, org)
    with organization_context(org):
        resp = c.get(
            f"/api/v1/dashboards/assignment-template/{counselor_template.id}/",
            {"date": historical.isoformat(), "status": "completed"},
        )
    assert resp.status_code == 200, resp.data
    assert resp.json()["summary"]["response_count"] == 1
    assert len(resp.json()["responses"]["reflections"]) == 1


@pytest.mark.django_db
def test_template_dashboard_historical_date_active_tab(
    org, program, counselor_template,
):
    """Active tab + a past date resolves assignments in effect then, even if
    their lifecycle status is now ``ended``."""
    admin_user, _, _ = _person(org, "Admin", "admin", program)

    historical = date(2025, 7, 17)
    bunk = AssignmentGroup.all_objects.create(
        organization=org, program=program, name="Bunk A", slug="bunk-a", group_type="bunk",
    )
    _, author, _ = _person(org, "Counselor", "counselor", program, with_user=False)
    AssignmentGroupMembership.all_objects.create(
        group=bunk, person=author, role_in_group="author", is_active=True,
    )
    TemplateAssignment.all_objects.create(
        organization=org, program=program, template=counselor_template,
        target_type=TemplateAssignment.TargetType.ASSIGNMENT_GROUP,
        assignment_group=bunk,
        start_date=date(2025, 6, 28),
        end_date=date(2025, 7, 26),
        status=TemplateAssignment.Status.ENDED,
    )
    Reflection.all_objects.create(
        organization=org, program=program, template=counselor_template,
        subject=author, author=author, assignment_group=bunk,
        period_start=historical, period_end=historical,
        answers={"note": "legacy row"}, is_complete=True,
    )
    c = _client(admin_user, org)
    with organization_context(org):
        resp = c.get(
            f"/api/v1/dashboards/assignment-template/{counselor_template.id}/",
            {"date": historical.isoformat(), "status": "active"},
        )
    assert resp.status_code == 200, resp.data
    body = resp.json()
    assert body["summary"]["response_count"] == 1
    assert len(body["responses"]["reflections"]) == 1
    assert body["responses"]["reflections"][0]["answers"]["note"] == "legacy row"


@pytest.mark.django_db
def test_template_dashboard_aggregates_groups_then_drills_down(
    org, program, counselor_template,
):
    """Default view aggregates both bunks; ?group= narrows to one bunk."""
    admin_user, _, _ = _person(org, "Admin", "admin", program)

    def _bunk_with_author(name, slug, author_first):
        bunk = AssignmentGroup.all_objects.create(
            organization=org, program=program, name=name, slug=slug, group_type="bunk",
        )
        _, person, _ = _person(org, author_first, "counselor", program, with_user=False)
        AssignmentGroupMembership.all_objects.create(
            group=bunk, person=person, role_in_group="author", is_active=True,
        )
        assignment = TemplateAssignment.all_objects.create(
            organization=org, program=program, template=counselor_template,
            target_type=TemplateAssignment.TargetType.ASSIGNMENT_GROUP,
            assignment_group=bunk, start_date=PAST,
            status=TemplateAssignment.Status.ACTIVE,
        )
        Reflection.all_objects.create(
            organization=org, program=program, template=counselor_template,
            subject=person, author=person, assignment_group=bunk,
            period_start=DAY, period_end=DAY, answers={"note": "x"}, is_complete=True,
        )
        return bunk, person, assignment

    _, p_east, a_east = _bunk_with_author("Mountainview East", "mv-east", "East")
    _, p_west, _ = _bunk_with_author("Mountainview West", "mv-west", "West")

    c = _client(admin_user, org)
    with organization_context(org):
        agg = c.get(
            f"/api/v1/dashboards/assignment-template/{counselor_template.id}/",
            {"date": DAY.isoformat()},
        )
        drill = c.get(
            f"/api/v1/dashboards/assignment-template/{counselor_template.id}/",
            {"date": DAY.isoformat(), "group": a_east.id},
        )
    assert agg.status_code == 200, agg.data
    assert agg.json()["summary"]["response_count"] == 2
    assert agg.json()["selection"]["group_count"] == 2

    assert drill.status_code == 200, drill.data
    assert drill.json()["summary"]["response_count"] == 1
    drill_people = {r["person_id"] for r in drill.json()["roster"]}
    assert p_east.id in drill_people
    assert p_west.id not in drill_people


@pytest.mark.django_db
def test_template_dashboard_program_scope(org, program, counselor_template):
    """A template assigned across two programs scopes to one via ?program=."""
    admin_user, _, _ = _person(org, "Admin", "admin", program)

    program2 = Program.all_objects.create(
        organization=org, name="Reflections Camp Winter", slug="winter-2026",
        program_type="summer_camp",
        start_date=date(2026, 1, 1), end_date=date(2026, 3, 31),
    )

    def _bunk_with_response(prog, name, slug, author_first):
        bunk = AssignmentGroup.all_objects.create(
            organization=org, program=prog, name=name, slug=slug, group_type="bunk",
        )
        _, person, _ = _person(org, author_first, "counselor", prog, with_user=False)
        AssignmentGroupMembership.all_objects.create(
            group=bunk, person=person, role_in_group="author", is_active=True,
        )
        TemplateAssignment.all_objects.create(
            organization=org, program=prog, template=counselor_template,
            target_type=TemplateAssignment.TargetType.ASSIGNMENT_GROUP,
            assignment_group=bunk, start_date=PAST,
            status=TemplateAssignment.Status.ACTIVE,
        )
        Reflection.all_objects.create(
            organization=org, program=prog, template=counselor_template,
            subject=person, author=person, assignment_group=bunk,
            period_start=DAY, period_end=DAY, answers={"note": "x"}, is_complete=True,
        )

    _bunk_with_response(program, "Summer Bunk", "summer-bunk", "Sue")
    _bunk_with_response(program2, "Winter Bunk", "winter-bunk", "Win")

    c = _client(admin_user, org)
    with organization_context(org):
        agg = c.get(
            f"/api/v1/dashboards/assignment-template/{counselor_template.id}/",
            {"date": DAY.isoformat()},
        )
        scoped = c.get(
            f"/api/v1/dashboards/assignment-template/{counselor_template.id}/",
            {"date": DAY.isoformat(), "program": program.id},
        )
    assert agg.status_code == 200, agg.data
    assert agg.json()["selection"]["program_count"] == 2
    assert agg.json()["summary"]["response_count"] == 2

    assert scoped.status_code == 200, scoped.data
    assert scoped.json()["selection"]["selected_program"] == program.id
    assert scoped.json()["summary"]["response_count"] == 1
    assert all(g["program_id"] == program.id for g in scoped.json()["groups"])


@pytest.mark.django_db
def test_template_dashboard_denies_unscoped_viewer(
    org, program, counselor_assignment,
):
    plain_user, _, _ = _person(org, "Plain", "kitchen_staff", program)
    c = _client(plain_user, org)
    with organization_context(org):
        resp = c.get(
            f"/api/v1/dashboards/assignment-template/{counselor_assignment.template_id}/",
            {"date": DAY.isoformat()},
        )
    assert resp.status_code == 403
