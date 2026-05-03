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


def _hdr_org(slug: str):
    return {"HTTP_X_ORGANIZATION_SLUG": slug}


def _rating_schema():
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
def org_td(db):
    return Organization.objects.create(name="Team Dash Org", slug="team-dash-org")


@pytest.fixture
def program_td(org_td):
    return Program.all_objects.create(
        organization=org_td,
        name="Team Dash Org Summer",
        slug="team-dash-prog",
        program_type="summer_camp",
        start_date=date(2026, 6, 1),
        end_date=date(2026, 8, 31),
    )


@pytest.fixture
def rating_template(org_td):
    return ReflectionTemplate.all_objects.create(
        organization=org_td,
        name="Weekly pulse",
        slug="weekly-pulse",
        cadence="weekly",
        role="counselor",
        program_type="summer_camp",
        schema=_rating_schema(),
        languages=["en"],
    )


@pytest.fixture
def counselor_user(org_td, program_td):
    u = User.objects.create_user(email="td-counselor@example.com", password="pw")
    p = Person.all_objects.create(organization=org_td, first_name="C", last_name="S", user=u)
    Membership.all_objects.create(
        program=program_td,
        person=p,
        role="counselor",
        is_active=True,
        metadata={"unit_slug": "alef"},
    )
    return u, p


@pytest.fixture
def counselor_b_other_unit(org_td, program_td):
    u = User.objects.create_user(email="td-counselor-b@example.com", password="pw")
    p = Person.all_objects.create(organization=org_td, first_name="C", last_name="B", user=u)
    Membership.all_objects.create(
        program=program_td,
        person=p,
        role="counselor",
        is_active=True,
        metadata={"unit_slug": "bet"},
    )
    return u, p


@pytest.fixture
def lt_user_restricted(org_td, program_td):
    u = User.objects.create_user(email="td-lt@example.com", password="pw")
    p = Person.all_objects.create(organization=org_td, first_name="L", last_name="T", user=u)
    Membership.all_objects.create(
        program=program_td,
        person=p,
        role="leadership_team",
        is_active=True,
        metadata={"assigned_unit_slugs": ["alef"]},
    )
    return u, p


@pytest.fixture
def admin_membership_user(org_td, program_td):
    u = User.objects.create_user(email="td-admin-mem@example.com", password="pw")
    p = Person.all_objects.create(organization=org_td, first_name="A", last_name="M", user=u)
    Membership.all_objects.create(program=program_td, person=p, role="admin", is_active=True)
    return u, p


@pytest.mark.django_db
def test_counselor_team_dashboard_forbidden(api, org_td, program_td, counselor_user):
    user, _ = counselor_user
    api.force_authenticate(user=user)
    r = api.get("/api/v1/dashboards/team/", **_hdr_org(org_td.slug))
    assert r.status_code == 403


@pytest.mark.django_db
def test_legacy_django_admin_user_role_allowed_without_membership_admin(
    api,
    org_td,
    program_td,
    rating_template,
    counselor_user,
):
    """Users.app Admin role (e.g. dev-admin) can open the dashboard with only counselor Membership."""
    user, person = counselor_user
    user.role = User.ADMIN
    user.save(update_fields=["role"])
    period_end = date(2026, 6, 14)
    period_start = date(2026, 6, 8)
    Reflection.all_objects.create(
        organization=org_td,
        program=program_td,
        person=person,
        template=rating_template,
        period_start=period_start,
        period_end=period_end,
        answers={"pulse": {"morale": 3}},
        language="en",
    )
    api.force_authenticate(user=user)
    r = api.get(
        "/api/v1/dashboards/team/",
        {"period_end": str(period_end), "period_days": "14"},
        **_hdr_org(org_td.slug),
    )
    assert r.status_code == 200
    assert len(r.json()["units"]) == 1
    assert r.json()["units"][0]["unit_slug"] == "alef"


@pytest.mark.django_db
def test_lt_only_sees_assigned_units(
    api,
    org_td,
    program_td,
    rating_template,
    counselor_user,
    counselor_b_other_unit,
    lt_user_restricted,
):
    _u_a, person_a = counselor_user
    _u_b, person_b = counselor_b_other_unit
    period_end = date(2026, 6, 14)
    period_start = date(2026, 6, 8)
    Reflection.all_objects.create(
        organization=org_td,
        program=program_td,
        person=person_a,
        template=rating_template,
        period_start=period_start,
        period_end=period_end,
        answers={"pulse": {"morale": 4}, "primary_concern": "ok"},
        language="en",
    )
    Reflection.all_objects.create(
        organization=org_td,
        program=program_td,
        person=person_b,
        template=rating_template,
        period_start=period_start,
        period_end=period_end,
        answers={"pulse": {"morale": 3}},
        language="en",
    )

    user_lt, _ = lt_user_restricted
    api.force_authenticate(user=user_lt)
    r = api.get(
        "/api/v1/dashboards/team/",
        {"period_end": str(period_end), "period_days": "14"},
        **_hdr_org(org_td.slug),
    )
    assert r.status_code == 200
    body = r.json()
    assert len(body["units"]) == 1
    assert body["units"][0]["unit_slug"] == "alef"
    assert body["units"][0]["total_staff"] == 1
    assert body["units"][0]["completion_rate"] == 1.0
    assert body["units"][0]["category_averages"]["morale"] == 4.0
    assert len(body["open_questions"]) >= 1


@pytest.mark.django_db
def test_admin_sees_all_units(
    api,
    org_td,
    program_td,
    rating_template,
    counselor_user,
    counselor_b_other_unit,
    admin_membership_user,
):
    _u_a, person_a = counselor_user
    _u_b, person_b = counselor_b_other_unit
    period_end = date(2026, 6, 14)
    period_start = date(2026, 6, 8)
    Reflection.all_objects.create(
        organization=org_td,
        program=program_td,
        person=person_a,
        template=rating_template,
        period_start=period_start,
        period_end=period_end,
        answers={"pulse": {"morale": 4}},
        language="en",
    )
    Reflection.all_objects.create(
        organization=org_td,
        program=program_td,
        person=person_b,
        template=rating_template,
        period_start=period_start,
        period_end=period_end,
        answers={"pulse": {"morale": 2}},
        language="en",
    )

    user_adm, _ = admin_membership_user
    api.force_authenticate(user=user_adm)
    r = api.get(
        "/api/v1/dashboards/team/",
        {"period_end": str(period_end), "period_days": "14"},
        **_hdr_org(org_td.slug),
    )
    assert r.status_code == 200
    slugs = {u["unit_slug"] for u in r.json()["units"]}
    assert slugs == {"alef", "bet"}


@pytest.mark.django_db
def test_year_round_filter(api, org_td, program_td, rating_template, lt_user_restricted):
    user_lt, _ = lt_user_restricted
    u_y = User.objects.create_user(email="td-yr@example.com", password="pw")
    py = Person.all_objects.create(organization=org_td, first_name="Y", last_name="R", user=u_y)
    Membership.all_objects.create(
        program=program_td,
        person=py,
        role="counselor",
        is_active=True,
        metadata={"unit_slug": "alef"},
        tags=["year_round"],
    )
    u_s = User.objects.create_user(email="td-sn@example.com", password="pw")
    ps = Person.all_objects.create(organization=org_td, first_name="S", last_name="N", user=u_s)
    Membership.all_objects.create(
        program=program_td,
        person=ps,
        role="counselor",
        is_active=True,
        metadata={"unit_slug": "alef"},
        tags=[],
    )
    period_end = date(2026, 6, 14)
    period_start = date(2026, 6, 8)
    Reflection.all_objects.create(
        organization=org_td,
        program=program_td,
        person=py,
        template=rating_template,
        period_start=period_start,
        period_end=period_end,
        answers={"pulse": {"morale": 4}},
        language="en",
    )
    Reflection.all_objects.create(
        organization=org_td,
        program=program_td,
        person=ps,
        template=rating_template,
        period_start=period_start,
        period_end=period_end,
        answers={"pulse": {"morale": 2}},
        language="en",
    )

    api.force_authenticate(user=user_lt)
    r_all = api.get(
        "/api/v1/dashboards/team/",
        {"period_end": str(period_end), "period_days": "14"},
        **_hdr_org(org_td.slug),
    )
    assert r_all.status_code == 200
    urow_all = r_all.json()["units"][0]
    assert urow_all["total_staff"] == 2
    assert urow_all["reflections_submitted"] == 2

    r_yr = api.get(
        "/api/v1/dashboards/team/",
        {"period_end": str(period_end), "period_days": "14", "year_round_only": "true"},
        **_hdr_org(org_td.slug),
    )
    assert r_yr.status_code == 200
    urow = r_yr.json()["units"][0]
    assert urow["total_staff"] == 1
    assert urow["reflections_submitted"] == 1
    assert urow["category_averages"]["morale"] == 4.0


@pytest.mark.django_db
def test_low_ratings_flagged(
    api,
    org_td,
    program_td,
    rating_template,
    counselor_user,
    admin_membership_user,
):
    _u, person = counselor_user
    period_end = date(2026, 6, 14)
    period_start = date(2026, 6, 8)
    Reflection.all_objects.create(
        organization=org_td,
        program=program_td,
        person=person,
        template=rating_template,
        period_start=period_start,
        period_end=period_end,
        answers={"pulse": {"morale": 1}},
        language="en",
    )
    user_adm, _ = admin_membership_user
    api.force_authenticate(user=user_adm)
    r = api.get(
        "/api/v1/dashboards/team/",
        {"period_end": str(period_end), "period_days": "14"},
        **_hdr_org(org_td.slug),
    )
    assert r.status_code == 200
    c = r.json()["concerning"]
    assert len(c) == 1
    assert c[0]["category"] == "morale"
    assert c[0]["value"] == 1.0


@pytest.mark.django_db
def test_category_average_aggregation(
    api,
    org_td,
    program_td,
    rating_template,
    counselor_user,
    admin_membership_user,
):
    _user_c, person_c = counselor_user
    u2 = User.objects.create_user(email="td-c2@example.com", password="pw")
    p2 = Person.all_objects.create(organization=org_td, first_name="C", last_name="Two", user=u2)
    Membership.all_objects.create(
        program=program_td,
        person=p2,
        role="counselor",
        is_active=True,
        metadata={"unit_slug": "alef"},
    )
    period_end = date(2026, 6, 14)
    period_start = date(2026, 6, 8)
    Reflection.all_objects.create(
        organization=org_td,
        program=program_td,
        person=person_c,
        template=rating_template,
        period_start=period_start,
        period_end=period_end,
        answers={"pulse": {"morale": 4}},
        language="en",
    )
    Reflection.all_objects.create(
        organization=org_td,
        program=program_td,
        person=p2,
        template=rating_template,
        period_start=period_start,
        period_end=period_end,
        answers={"pulse": {"morale": 2}},
        language="en",
    )

    user_adm, _ = admin_membership_user
    api.force_authenticate(user=user_adm)
    r = api.get(
        "/api/v1/dashboards/team/",
        {"period_end": str(period_end), "period_days": "14"},
        **_hdr_org(org_td.slug),
    )
    assert r.status_code == 200
    urow = next(x for x in r.json()["units"] if x["unit_slug"] == "alef")
    assert urow["category_averages"]["morale"] == 3.0
    assert urow["completion_rate"] == 1.0
