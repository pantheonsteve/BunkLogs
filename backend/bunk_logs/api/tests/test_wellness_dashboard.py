from datetime import date
from datetime import timedelta

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


def _hdr_org(slug: str):
    return {"HTTP_X_ORGANIZATION_SLUG": slug}


def _wellness_schema():
    return {
        "fields": [
            {
                "key": "pulse",
                "type": "rating_group",
                "scale": [1, 4],
                "scale_labels": {"en": ["1", "2", "3", "4"]},
                "categories": [
                    {"key": "workload", "labels": {"en": "Workload"}},
                    {"key": "morale", "labels": {"en": "Morale"}},
                ],
            },
            {
                "key": "primary_concern",
                "type": "textarea",
                "required": False,
                "prompts": {"en": "One concern?"},
            },
        ],
    }


def _counselor_schema():
    return {
        "fields": [
            {
                "key": "pulse",
                "type": "rating_group",
                "scale": [1, 4],
                "scale_labels": {"en": ["1", "2", "3", "4"]},
                "categories": [{"key": "morale", "labels": {"en": "Morale"}}],
            },
            {
                "key": "primary_concern",
                "type": "textarea",
                "required": False,
                "prompts": {"en": "One concern?"},
            },
        ],
    }


@pytest.fixture
def api():
    return APIClient()


@pytest.fixture
def org_w(db):
    return Organization.objects.create(name="Wellness Org", slug="wellness-org")


@pytest.fixture
def program_w(org_w):
    return Program.all_objects.create(
        organization=org_w,
        name="Wellness Org Summer",
        slug="wellness-prog",
        program_type="summer_camp",
        start_date=date(2026, 6, 1),
        end_date=date(2026, 8, 31),
    )


@pytest.fixture
def wellness_template(org_w):
    return ReflectionTemplate.all_objects.create(
        organization=org_w,
        name="Wellness pulse",
        slug="wellness-pulse",
        cadence="weekly",
        role="camper_care",
        program_type="summer_camp",
        schema=_wellness_schema(),
        languages=["en"],
    )


@pytest.fixture
def counselor_template(org_w):
    return ReflectionTemplate.all_objects.create(
        organization=org_w,
        name="Counselor pulse",
        slug="counselor-pulse",
        cadence="weekly",
        role="counselor",
        program_type="summer_camp",
        schema=_counselor_schema(),
        languages=["en"],
    )


def _make_membership_user(org, program, role, *, email_prefix, metadata=None, tags=None):
    u = User.objects.create_user(email=f"{email_prefix}@example.com", password="pw")
    p = Person.all_objects.create(
        organization=org,
        first_name=email_prefix.upper(),
        last_name="Test",
        user=u,
    )
    Membership.all_objects.create(
        program=program,
        person=p,
        role=role,
        is_active=True,
        metadata=metadata or {},
        tags=tags or [],
    )
    return u, p


@pytest.fixture
def camper_care_user(org_w, program_w):
    return _make_membership_user(org_w, program_w, "camper_care", email_prefix="cc")


@pytest.fixture
def health_center_user(org_w, program_w):
    return _make_membership_user(org_w, program_w, "health_center", email_prefix="hc")


@pytest.fixture
def special_diets_user(org_w, program_w):
    return _make_membership_user(org_w, program_w, "special_diets", email_prefix="sd")


@pytest.fixture
def admin_membership_user(org_w, program_w):
    return _make_membership_user(org_w, program_w, "admin", email_prefix="adm")


@pytest.fixture
def counselor_user(org_w, program_w):
    return _make_membership_user(
        org_w,
        program_w,
        "counselor",
        email_prefix="cn",
        metadata={"unit_slug": "alef"},
    )


@pytest.mark.django_db
def test_counselor_forbidden(api, org_w, program_w, counselor_user):
    user, _ = counselor_user
    api.force_authenticate(user=user)
    r = api.get("/api/v1/dashboards/wellness/", **_hdr_org(org_w.slug))
    assert r.status_code == 403


@pytest.mark.django_db
def test_camper_care_user_can_access(
    api,
    org_w,
    program_w,
    wellness_template,
    camper_care_user,
):
    user, person = camper_care_user
    period_end = date(2026, 6, 14)
    period_start = date(2026, 6, 8)
    Reflection.all_objects.create(
        organization=org_w,
        program=program_w,
        subject=person,
        template=wellness_template,
        period_start=period_start,
        period_end=period_end,
        answers={"pulse": {"workload": 3, "morale": 4}, "primary_concern": "Need more breaks"},
        language="en",
    )
    api.force_authenticate(user=user)
    r = api.get(
        "/api/v1/dashboards/wellness/",
        {"period_end": str(period_end), "period_days": "14"},
        **_hdr_org(org_w.slug),
    )
    assert r.status_code == 200
    body = r.json()
    roles = {row["role"] for row in body["by_sub_role"]}
    assert roles == {"camper_care", "health_center", "special_diets"}
    cc_row = next(row for row in body["by_sub_role"] if row["role"] == "camper_care")
    assert cc_row["total_staff"] == 1
    assert cc_row["reflections_submitted"] == 1
    assert cc_row["completion_rate"] == 1.0
    assert cc_row["category_averages"]["morale"] == 4.0
    assert cc_row["category_averages"]["workload"] == 3.0
    assert any(oq["text"] == "Need more breaks" for oq in cc_row["open_questions"])


@pytest.mark.django_db
def test_health_center_and_special_diets_can_access(
    api,
    org_w,
    program_w,
    health_center_user,
    special_diets_user,
):
    user_hc, _ = health_center_user
    api.force_authenticate(user=user_hc)
    r = api.get("/api/v1/dashboards/wellness/", **_hdr_org(org_w.slug))
    assert r.status_code == 200

    user_sd, _ = special_diets_user
    api.force_authenticate(user=user_sd)
    r2 = api.get("/api/v1/dashboards/wellness/", **_hdr_org(org_w.slug))
    assert r2.status_code == 200


@pytest.mark.django_db
def test_admin_membership_user_can_access(
    api,
    org_w,
    program_w,
    admin_membership_user,
):
    user, _ = admin_membership_user
    api.force_authenticate(user=user)
    r = api.get("/api/v1/dashboards/wellness/", **_hdr_org(org_w.slug))
    assert r.status_code == 200


@pytest.mark.django_db
def test_legacy_django_admin_user_role_allowed_without_membership_admin(
    api,
    org_w,
    program_w,
    counselor_user,
):
    """Users with the legacy User.ADMIN role can open the wellness dashboard."""
    user, _ = counselor_user
    user.role = User.ADMIN
    user.save(update_fields=["role"])
    api.force_authenticate(user=user)
    r = api.get("/api/v1/dashboards/wellness/", **_hdr_org(org_w.slug))
    assert r.status_code == 200


@pytest.mark.django_db
def test_sub_role_filter_returns_only_requested(
    api,
    org_w,
    program_w,
    wellness_template,
    camper_care_user,
    health_center_user,
):
    user, _ = camper_care_user
    api.force_authenticate(user=user)
    r = api.get(
        "/api/v1/dashboards/wellness/",
        {"sub_role": "health_center"},
        **_hdr_org(org_w.slug),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["sub_role_filter"] == "health_center"
    assert {row["role"] for row in body["by_sub_role"]} == {"health_center"}


@pytest.mark.django_db
def test_invalid_sub_role_rejected(api, org_w, camper_care_user):
    user, _ = camper_care_user
    api.force_authenticate(user=user)
    r = api.get(
        "/api/v1/dashboards/wellness/",
        {"sub_role": "counselor"},
        **_hdr_org(org_w.slug),
    )
    assert r.status_code == 400


@pytest.mark.django_db
def test_low_ratings_flagged_as_concerning(
    api,
    org_w,
    program_w,
    wellness_template,
    camper_care_user,
):
    user, person = camper_care_user
    period_end = date(2026, 6, 14)
    period_start = date(2026, 6, 8)
    Reflection.all_objects.create(
        organization=org_w,
        program=program_w,
        subject=person,
        template=wellness_template,
        period_start=period_start,
        period_end=period_end,
        answers={"pulse": {"workload": 1, "morale": 2}},
        language="en",
    )
    api.force_authenticate(user=user)
    r = api.get(
        "/api/v1/dashboards/wellness/",
        {"period_end": str(period_end), "period_days": "14"},
        **_hdr_org(org_w.slug),
    )
    assert r.status_code == 200
    cc_row = next(row for row in r.json()["by_sub_role"] if row["role"] == "camper_care")
    flagged = {(c["category"], c["value"]) for c in cc_row["concerning"]}
    assert flagged == {("workload", 1.0), ("morale", 2.0)}


@pytest.mark.django_db
def test_cross_team_patterns_surface_wellness_mentions(
    api,
    org_w,
    program_w,
    counselor_template,
    camper_care_user,
    counselor_user,
):
    user_cc, _ = camper_care_user
    _u_cn, person_cn = counselor_user
    period_end = date(2026, 6, 14)
    period_start = date(2026, 6, 8)
    Reflection.all_objects.create(
        organization=org_w,
        program=program_w,
        subject=person_cn,
        template=counselor_template,
        period_start=period_start,
        period_end=period_end,
        answers={
            "pulse": {"morale": 3},
            "primary_concern": "Camper Aviva needs Camper Care follow-up after rough night.",
        },
        language="en",
    )
    Reflection.all_objects.create(
        organization=org_w,
        program=program_w,
        subject=person_cn,
        template=counselor_template,
        period_start=period_start,
        period_end=period_end - timedelta(days=1),
        answers={"pulse": {"morale": 4}, "primary_concern": "All good this week."},
        language="en",
    )

    api.force_authenticate(user=user_cc)
    r = api.get(
        "/api/v1/dashboards/wellness/",
        {"period_end": str(period_end), "period_days": "14"},
        **_hdr_org(org_w.slug),
    )
    assert r.status_code == 200
    patterns = r.json()["cross_team_patterns"]
    assert len(patterns) == 1
    assert "camper care" in patterns[0]["text"].lower()
    assert patterns[0]["template_role"] == "counselor"


@pytest.mark.django_db
def test_completion_aggregation(
    api,
    org_w,
    program_w,
    wellness_template,
    camper_care_user,
    health_center_user,
):
    _u_cc, person_cc = camper_care_user
    period_end = date(2026, 6, 14)
    period_start = date(2026, 6, 8)
    Reflection.all_objects.create(
        organization=org_w,
        program=program_w,
        subject=person_cc,
        template=wellness_template,
        period_start=period_start,
        period_end=period_end,
        answers={"pulse": {"workload": 3, "morale": 3}},
        language="en",
    )

    user_hc, _ = health_center_user
    api.force_authenticate(user=user_hc)
    r = api.get(
        "/api/v1/dashboards/wellness/",
        {"period_end": str(period_end), "period_days": "14"},
        **_hdr_org(org_w.slug),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["completion"]["total_staff"] == 2
    assert body["completion"]["reflections_submitted"] == 1
    assert body["completion"]["completion_rate"] == 0.5
    by_role = {b["role"]: b for b in body["completion"]["by_sub_role"]}
    assert by_role["camper_care"]["completion_rate"] == 1.0
    assert by_role["health_center"]["completion_rate"] == 0.0
    assert by_role["special_diets"]["total_staff"] == 0


@pytest.mark.django_db
def test_program_filter_unknown_returns_404(api, org_w, camper_care_user):
    user, _ = camper_care_user
    api.force_authenticate(user=user)
    r = api.get(
        "/api/v1/dashboards/wellness/",
        {"program": "no-such-program"},
        **_hdr_org(org_w.slug),
    )
    assert r.status_code == 404
