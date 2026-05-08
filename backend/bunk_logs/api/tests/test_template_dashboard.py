from __future__ import annotations

import csv
import io
from datetime import date

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from bunk_logs.core.models import Membership
from bunk_logs.core.models import Organization
from bunk_logs.core.models import Person
from bunk_logs.core.models import Program
from bunk_logs.core.models import Reflection
from bunk_logs.core.models import ReflectionTemplate

User = get_user_model()


def _hdr(org_slug: str) -> dict:
    return {"HTTP_X_ORGANIZATION_SLUG": org_slug}


# ── Shared schema fixtures ─────────────────────────────────────────────────────


def _full_schema() -> dict:
    return {
        "fields": [
            {
                "key": "overall",
                "type": "single_rating",
                "dashboard_role": "primary_rating",
                "scale": [1, 5],
                "scale_labels": {"en": ["1", "2", "3", "4", "5"]},
                "required": True,
            },
            {
                "key": "pulse",
                "type": "rating_group",
                "dashboard_role": "category_ratings",
                "scale": [1, 4],
                "scale_labels": {"en": ["1", "2", "3", "4"]},
                "categories": [
                    {"key": "morale", "labels": {"en": "Morale"}},
                    {"key": "energy", "labels": {"en": "Energy"}},
                ],
                "required": True,
            },
            {
                "key": "win_items",
                "type": "text_list",
                "dashboard_role": "wins",
                "prompts": {"en": "What went well?"},
                "min_items": 1,
                "max_items": 3,
            },
            {
                "key": "growth_items",
                "type": "text_list",
                "dashboard_role": "improvements",
                "prompts": {"en": "What to improve?"},
                "min_items": 1,
                "max_items": 3,
            },
            {
                "key": "concerns",
                "type": "textarea",
                "dashboard_role": "open_concern",
                "prompts": {"en": "Any concerns?"},
                "max_length": 1000,
            },
            {
                "key": "yn_question",
                "type": "yes_no",
                "prompts": {"en": "All good?"},
            },
            {
                "key": "notes",
                "type": "text",
                "prompts": {"en": "Extra notes"},
                "max_length": 500,
            },
            {
                "key": "header_section",
                "type": "section_header",
                "prompts": {"en": "Section"},
            },
        ],
    }


def _wellness_schema() -> dict:
    return {
        "fields": [
            {
                "key": "pulse",
                "type": "rating_group",
                "dashboard_role": "category_ratings",
                "scale": [1, 4],
                "scale_labels": {"en": ["1", "2", "3", "4"]},
                "categories": [
                    {"key": "workload", "labels": {"en": "Workload"}},
                ],
            },
            {
                "key": "concern_text",
                "type": "textarea",
                "dashboard_role": "open_concern",
                "prompts": {"en": "Concerns?"},
                "max_length": 1000,
            },
        ],
    }


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def org(db):
    return Organization.objects.create(name="TDash Org", slug="tdash-org")


@pytest.fixture
def program(org):
    return Program.all_objects.create(
        organization=org,
        name="TDash Org Summer",
        slug="tdash-org-summer",
        program_type="summer_camp",
        start_date=date(2026, 6, 1),
        end_date=date(2026, 8, 31),
    )


@pytest.fixture
def lt_template(org):
    return ReflectionTemplate.all_objects.create(
        organization=org,
        name="LT Weekly",
        slug="lt-weekly",
        cadence="weekly",
        role="leadership_team",
        program_type="summer_camp",
        schema=_full_schema(),
        languages=["en"],
    )


@pytest.fixture
def wellness_template(org):
    return ReflectionTemplate.all_objects.create(
        organization=org,
        name="Wellness Daily",
        slug="wellness-daily",
        cadence="daily",
        role="camper_care",
        program_type="summer_camp",
        schema=_wellness_schema(),
        languages=["en"],
    )


def _make_person(org, program, role: str, unit_slug: str | None = None, email_suffix: str = ""):
    u = User.objects.create_user(email=f"td-{role}-{email_suffix}@example.com", password="pw")
    p = Person.all_objects.create(organization=org, first_name="F", last_name="L", user=u)
    meta = {"unit_slug": unit_slug} if unit_slug else {}
    Membership.all_objects.create(
        program=program,
        person=p,
        role=role,
        is_active=True,
        metadata=meta,
    )
    return u, p


@pytest.fixture
def lt_user(org, program):
    return _make_person(org, program, "leadership_team", email_suffix="lt")


@pytest.fixture
def wellness_user(org, program):
    return _make_person(org, program, "camper_care", email_suffix="wl")


@pytest.fixture
def admin_user(org, program):
    return _make_person(org, program, "admin", email_suffix="adm")


@pytest.fixture
def counselor_user(org, program):
    return _make_person(org, program, "counselor", "alef", email_suffix="c1")


def _make_reflection(
    org,
    program,
    person,
    template,
    period_end: date,
    answers: dict,
) -> Reflection:
    return Reflection.all_objects.create(
        organization=org,
        program=program,
        subject=person,
        template=template,
        period_start=period_end,
        period_end=period_end,
        answers=answers,
        language="en",
    )


# ── Permission tests ───────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_unauthenticated_returns_401(api_client, org, lt_template):
    r = api_client.get(f"/api/v1/dashboards/template/{lt_template.id}/", **_hdr(org.slug))
    assert r.status_code == 401


@pytest.mark.django_db
def test_counselor_cannot_access_lt_dashboard(api_client, org, lt_template, counselor_user):
    u, _ = counselor_user
    api_client.force_authenticate(user=u)
    r = api_client.get(f"/api/v1/dashboards/template/{lt_template.id}/", **_hdr(org.slug))
    assert r.status_code == 403


@pytest.mark.django_db
def test_wellness_user_cannot_access_lt_dashboard(api_client, org, lt_template, wellness_user):
    u, _ = wellness_user
    api_client.force_authenticate(user=u)
    r = api_client.get(f"/api/v1/dashboards/template/{lt_template.id}/", **_hdr(org.slug))
    assert r.status_code == 403


@pytest.mark.django_db
def test_lt_user_can_access_lt_dashboard(api_client, org, lt_template, lt_user):
    u, _ = lt_user
    api_client.force_authenticate(user=u)
    r = api_client.get(f"/api/v1/dashboards/template/{lt_template.id}/", **_hdr(org.slug))
    assert r.status_code == 200


@pytest.mark.django_db
def test_admin_user_can_access_lt_dashboard(api_client, org, lt_template, admin_user):
    u, _ = admin_user
    api_client.force_authenticate(user=u)
    r = api_client.get(f"/api/v1/dashboards/template/{lt_template.id}/", **_hdr(org.slug))
    assert r.status_code == 200


@pytest.mark.django_db
def test_wellness_user_can_access_wellness_dashboard(api_client, org, wellness_template, wellness_user):
    u, _ = wellness_user
    api_client.force_authenticate(user=u)
    r = api_client.get(f"/api/v1/dashboards/template/{wellness_template.id}/", **_hdr(org.slug))
    assert r.status_code == 200


@pytest.mark.django_db
def test_lt_user_cannot_access_wellness_dashboard(api_client, org, wellness_template, lt_user):
    u, _ = lt_user
    api_client.force_authenticate(user=u)
    r = api_client.get(f"/api/v1/dashboards/template/{wellness_template.id}/", **_hdr(org.slug))
    assert r.status_code == 403


@pytest.mark.django_db
def test_superuser_can_access_any_template(api_client, org, lt_template):
    su = User.objects.create_superuser(email="super@example.com", password="pw")
    p = Person.all_objects.create(organization=org, first_name="S", last_name="U", user=su)  # noqa: F841
    api_client.force_authenticate(user=su)
    r = api_client.get(f"/api/v1/dashboards/template/{lt_template.id}/", **_hdr(org.slug))
    assert r.status_code == 200


@pytest.mark.django_db
def test_template_not_found_returns_404(api_client, org, lt_user):
    u, _ = lt_user
    api_client.force_authenticate(user=u)
    r = api_client.get("/api/v1/dashboards/template/99999/", **_hdr(org.slug))
    assert r.status_code == 404


# ── Aggregation correctness tests ──────────────────────────────────────────────


@pytest.mark.django_db
def test_summary_counts(api_client, org, program, lt_template, lt_user, counselor_user):
    u_lt, _ = lt_user
    _, p_c = counselor_user
    period_end = date(2026, 6, 14)
    _make_reflection(
        org,
        program,
        p_c,
        lt_template,
        period_end,
        {"overall": 4, "pulse": {"morale": 3, "energy": 4}},
    )
    api_client.force_authenticate(user=u_lt)
    r = api_client.get(
        f"/api/v1/dashboards/template/{lt_template.id}/",
        {"period_end": str(period_end), "period_days": "14"},
        **_hdr(org.slug),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["summary"]["response_count"] == 1
    assert body["summary"]["person_count"] == 1


@pytest.mark.django_db
def test_single_rating_aggregation(api_client, org, program, lt_template, lt_user, counselor_user):
    u_lt, _ = lt_user
    _, p_c = counselor_user
    u2 = User.objects.create_user(email="c2@example.com", password="pw")
    p2 = Person.all_objects.create(organization=org, first_name="C", last_name="2", user=u2)
    Membership.all_objects.create(
        program=program, person=p2, role="counselor", is_active=True,
    )
    period_end = date(2026, 6, 14)
    _make_reflection(org, program, p_c, lt_template, period_end, {"overall": 4})
    _make_reflection(org, program, p2, lt_template, period_end, {"overall": 2})
    api_client.force_authenticate(user=u_lt)
    r = api_client.get(
        f"/api/v1/dashboards/template/{lt_template.id}/",
        {"period_end": str(period_end), "period_days": "14"},
        **_hdr(org.slug),
    )
    body = r.json()
    overall_field = next(f for f in body["fields"] if f["key"] == "overall")
    assert overall_field["dashboard_role"] == "primary_rating"
    assert overall_field["data"]["mean"] == 3.0
    assert overall_field["data"]["response_count"] == 2
    assert overall_field["data"]["distribution"]["4"] == 1
    assert overall_field["data"]["distribution"]["2"] == 1


@pytest.mark.django_db
def test_rating_group_aggregation(api_client, org, program, lt_template, lt_user, counselor_user):
    u_lt, _ = lt_user
    _, p_c = counselor_user
    period_end = date(2026, 6, 14)
    _make_reflection(
        org,
        program,
        p_c,
        lt_template,
        period_end,
        {"pulse": {"morale": 4, "energy": 3}},
    )
    api_client.force_authenticate(user=u_lt)
    r = api_client.get(
        f"/api/v1/dashboards/template/{lt_template.id}/",
        {"period_end": str(period_end), "period_days": "14"},
        **_hdr(org.slug),
    )
    body = r.json()
    pulse_field = next(f for f in body["fields"] if f["key"] == "pulse")
    assert pulse_field["dashboard_role"] == "category_ratings"
    cats = {c["key"]: c for c in pulse_field["data"]["categories"]}
    assert cats["morale"]["mean"] == 4.0
    assert cats["energy"]["mean"] == 3.0


@pytest.mark.django_db
def test_text_list_aggregation(api_client, org, program, lt_template, lt_user, counselor_user):
    u_lt, _ = lt_user
    _, p_c = counselor_user
    u2 = User.objects.create_user(email="c3@example.com", password="pw")
    p2 = Person.all_objects.create(organization=org, first_name="C", last_name="3", user=u2)
    Membership.all_objects.create(program=program, person=p2, role="counselor", is_active=True)
    period_end = date(2026, 6, 14)
    _make_reflection(
        org, program, p_c, lt_template, period_end,
        {"win_items": ["teamwork", "communication"]},
    )
    _make_reflection(
        org, program, p2, lt_template, period_end,
        {"win_items": ["teamwork", "punctuality"]},
    )
    api_client.force_authenticate(user=u_lt)
    r = api_client.get(
        f"/api/v1/dashboards/template/{lt_template.id}/",
        {"period_end": str(period_end)},
        **_hdr(org.slug),
    )
    body = r.json()
    wins_field = next(f for f in body["fields"] if f["key"] == "win_items")
    items_by_text = {i["text"]: i["count"] for i in wins_field["data"]["items"]}
    assert items_by_text["teamwork"] == 2
    assert items_by_text["communication"] == 1
    assert items_by_text["punctuality"] == 1
    assert wins_field["data"]["total_mentions"] == 4


@pytest.mark.django_db
def test_yes_no_aggregation(api_client, org, program, lt_template, lt_user, counselor_user):
    u_lt, _ = lt_user
    _, p_c = counselor_user
    u2 = User.objects.create_user(email="c4@example.com", password="pw")
    p2 = Person.all_objects.create(organization=org, first_name="C", last_name="4", user=u2)
    Membership.all_objects.create(program=program, person=p2, role="counselor", is_active=True)
    u3 = User.objects.create_user(email="c5@example.com", password="pw")
    p3 = Person.all_objects.create(organization=org, first_name="C", last_name="5", user=u3)
    Membership.all_objects.create(program=program, person=p3, role="counselor", is_active=True)
    period_end = date(2026, 6, 14)
    _make_reflection(org, program, p_c, lt_template, period_end, {"yn_question": True})
    _make_reflection(org, program, p2, lt_template, period_end, {"yn_question": True})
    _make_reflection(org, program, p3, lt_template, period_end, {"yn_question": False})
    api_client.force_authenticate(user=u_lt)
    r = api_client.get(
        f"/api/v1/dashboards/template/{lt_template.id}/",
        {"period_end": str(period_end)},
        **_hdr(org.slug),
    )
    body = r.json()
    yn_field = next(f for f in body["fields"] if f["key"] == "yn_question")
    assert yn_field["data"]["yes_count"] == 2
    assert yn_field["data"]["no_count"] == 1
    assert abs(yn_field["data"]["yes_pct"] - 2 / 3) < 0.001


@pytest.mark.django_db
def test_meta_fields_not_in_output(api_client, org, program, lt_template, lt_user):
    u_lt, _ = lt_user
    api_client.force_authenticate(user=u_lt)
    r = api_client.get(
        f"/api/v1/dashboards/template/{lt_template.id}/",
        {"period_end": str(date(2026, 6, 14))},
        **_hdr(org.slug),
    )
    body = r.json()
    field_keys = [f["key"] for f in body["fields"]]
    assert "header_section" not in field_keys


@pytest.mark.django_db
def test_trend_vs_prior_period(api_client, org, program, lt_template, lt_user, counselor_user):
    u_lt, _ = lt_user
    _, p_c = counselor_user
    # Prior period: low rating
    prior_end = date(2026, 6, 7)
    _make_reflection(org, program, p_c, lt_template, prior_end, {"overall": 2})
    # Current period: high rating
    cur_end = date(2026, 6, 14)
    _make_reflection(org, program, p_c, lt_template, cur_end, {"overall": 4})
    api_client.force_authenticate(user=u_lt)
    r = api_client.get(
        f"/api/v1/dashboards/template/{lt_template.id}/",
        {"period_end": str(cur_end), "period_days": "7"},
        **_hdr(org.slug),
    )
    body = r.json()
    overall_field = next(f for f in body["fields"] if f["key"] == "overall")
    assert overall_field["data"]["mean"] == 4.0
    assert overall_field["data"]["prior_mean"] == 2.0
    assert overall_field["data"]["trend"] == "up"


# ── CSV export tests ───────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_csv_export_returns_parseable_csv(api_client, org, program, lt_template, lt_user, counselor_user):
    u_lt, _ = lt_user
    _, p_c = counselor_user
    period_end = date(2026, 6, 14)
    _make_reflection(
        org,
        program,
        p_c,
        lt_template,
        period_end,
        {
            "overall": 3,
            "pulse": {"morale": 4, "energy": 3},
            "win_items": ["collaboration", "initiative"],
            "concerns": "Some concern here",
        },
    )
    api_client.force_authenticate(user=u_lt)
    r = api_client.get(
        f"/api/v1/dashboards/template/{lt_template.id}/export/",
        {"period_end": str(period_end)},
        **_hdr(org.slug),
    )
    assert r.status_code == 200
    assert "text/csv" in r["Content-Type"]
    assert "attachment" in r["Content-Disposition"]
    content = r.content.decode("utf-8")
    reader = csv.reader(io.StringIO(content))
    rows = list(reader)
    assert len(rows) >= 2  # header + at least one data row
    header = rows[0]
    assert "person_name" in header
    assert "period_end" in header
    assert "overall" in header
    assert "pulse__morale" in header
    assert "pulse__energy" in header
    assert "win_items" in header
    assert "concerns" in header
    # section_header should not appear
    assert "header_section" not in header
    # Data row
    data_row = dict(zip(header, rows[1], strict=False))
    assert data_row["overall"] == "3"
    assert data_row["pulse__morale"] == "4"
    assert "collaboration" in data_row["win_items"]


@pytest.mark.django_db
def test_csv_export_permission_denied(api_client, org, wellness_template, lt_user):
    u_lt, _ = lt_user
    api_client.force_authenticate(user=u_lt)
    r = api_client.get(
        f"/api/v1/dashboards/template/{wellness_template.id}/export/",
        **_hdr(org.slug),
    )
    assert r.status_code == 403


@pytest.mark.django_db
def test_csv_export_filename_includes_slug_and_period(
    api_client, org, lt_template, lt_user,
):
    u_lt, _ = lt_user
    api_client.force_authenticate(user=u_lt)
    period_end = date(2026, 6, 14)
    r = api_client.get(
        f"/api/v1/dashboards/template/{lt_template.id}/export/",
        {"period_end": str(period_end)},
        **_hdr(org.slug),
    )
    assert r.status_code == 200
    assert "lt-weekly" in r["Content-Disposition"]
    assert "2026-06-14" in r["Content-Disposition"]


# ── Response structure tests ───────────────────────────────────────────────────


@pytest.mark.django_db
def test_response_includes_template_info(api_client, org, lt_template, lt_user):
    u_lt, _ = lt_user
    api_client.force_authenticate(user=u_lt)
    r = api_client.get(
        f"/api/v1/dashboards/template/{lt_template.id}/",
        **_hdr(org.slug),
    )
    body = r.json()
    assert body["template"]["id"] == lt_template.id
    assert body["template"]["slug"] == "lt-weekly"
    assert body["template"]["role"] == "leadership_team"
    assert "schema" in body["template"]


@pytest.mark.django_db
def test_response_includes_period(api_client, org, lt_template, lt_user):
    u_lt, _ = lt_user
    api_client.force_authenticate(user=u_lt)
    r = api_client.get(
        f"/api/v1/dashboards/template/{lt_template.id}/",
        {"period_end": "2026-06-14", "period_days": "7"},
        **_hdr(org.slug),
    )
    body = r.json()
    assert body["period"]["current_end"] == "2026-06-14"
    assert body["period"]["current_start"] == "2026-06-08"
    assert "prior_start" in body["period"]
    assert "prior_end" in body["period"]


@pytest.mark.django_db
def test_empty_period_returns_zeros(api_client, org, lt_template, lt_user):
    u_lt, _ = lt_user
    api_client.force_authenticate(user=u_lt)
    r = api_client.get(
        f"/api/v1/dashboards/template/{lt_template.id}/",
        {"period_end": "2020-01-01"},
        **_hdr(org.slug),
    )
    body = r.json()
    assert body["summary"]["response_count"] == 0
    assert body["summary"]["person_count"] == 0
