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


def _tpl_schema_bilingual(key: str = "note") -> dict:
    return {"fields": [{"key": key, "type": "text", "prompts": {"en": "English", "es": "Español"}}]}


@pytest.fixture
def org_a(db):
    return Organization.objects.create(name="Alpha Ref", slug="org-ref-a")


@pytest.fixture
def org_b(db):
    return Organization.objects.create(name="Beta Ref", slug="org-ref-b")


@pytest.fixture
def program_a(org_a):
    return Program.all_objects.create(
        organization=org_a,
        name="Alpha Ref Summer",
        slug="prog-ref-a",
        program_type="summer_camp",
        start_date=date(2026, 6, 1),
        end_date=date(2026, 8, 31),
    )


@pytest.fixture
def program_b(org_b):
    return Program.all_objects.create(
        organization=org_b,
        name="Beta Ref Summer",
        slug="prog-ref-b",
        program_type="summer_camp",
        start_date=date(2026, 6, 1),
        end_date=date(2026, 8, 31),
    )


@pytest.fixture
def api():
    return APIClient()


@pytest.fixture
def counselor_template(org_a):
    return ReflectionTemplate.all_objects.create(
        organization=org_a,
        name="Counselor weekly",
        slug="cns-weekly",
        cadence="weekly",
        role="counselor",
        program_type="summer_camp",
        schema=_tpl_schema_bilingual(),
        languages=["en", "es"],
    )


@pytest.fixture
def program_second_session(org_a):
    return Program.all_objects.create(
        organization=org_a,
        name="Alpha Ref Session B",
        slug="prog-ref-session-b",
        program_type="summer_camp",
        start_date=date(2026, 7, 1),
        end_date=date(2026, 8, 15),
    )


@pytest.fixture
def kitchen_template(org_a):
    return ReflectionTemplate.all_objects.create(
        organization=org_a,
        name="Kitchen weekly",
        slug="kit-weekly",
        cadence="weekly",
        role="kitchen_staff",
        program_type="summer_camp",
        schema=_tpl_schema_bilingual("k"),
        languages=["en", "es"],
    )


@pytest.fixture
def org_admin_user(org_a, program_a):
    u = User.objects.create_user(email="adm@example.com", password="pw")
    p = Person.all_objects.create(organization=org_a, first_name="A", last_name="D", user=u)
    Membership.all_objects.create(program=program_a, person=p, role="admin", is_active=True)
    return u, p


@pytest.fixture
def counselor_user(org_a, program_a):
    u = User.objects.create_user(email="cns@example.com", password="pw")
    p = Person.all_objects.create(organization=org_a, first_name="C", last_name="One", user=u)
    Membership.all_objects.create(program=program_a, person=p, role="counselor", is_active=True)
    return u, p


@pytest.fixture
def other_counselor(org_a, program_a):
    u = User.objects.create_user(email="cns2@example.com", password="pw")
    p = Person.all_objects.create(organization=org_a, first_name="C", last_name="Two", user=u)
    Membership.all_objects.create(program=program_a, person=p, role="counselor", is_active=True)
    return u, p


def _hdr_org(slug: str):
    return {"HTTP_X_ORGANIZATION_SLUG": slug}


@pytest.mark.django_db
def test_person_can_submit(api, org_a, program_a, counselor_template, counselor_user):
    user, _person = counselor_user
    api.force_authenticate(user=user)
    resp = api.post(
        "/api/v1/reflections/",
        {
            "program_slug": program_a.slug,
            "template": counselor_template.id,
            "period_start": "2026-06-01",
            "period_end": "2026-06-07",
            "answers": {"note": "did well"},
            "language": "en",
        },
        format="json",
        **_hdr_org(org_a.slug),
    )
    assert resp.status_code == 201, resp.content
    assert resp.json()["answers"] == {"note": "did well"}


@pytest.mark.django_db
def test_team_visibility_defaults_to_team(
    api, org_a, program_a, counselor_template, counselor_user,
):
    user, _person = counselor_user
    api.force_authenticate(user=user)
    resp = api.post(
        "/api/v1/reflections/",
        {
            "program_slug": program_a.slug,
            "template": counselor_template.id,
            "period_start": "2026-06-01",
            "period_end": "2026-06-07",
            "answers": {"note": "default"},
            "language": "en",
        },
        format="json",
        **_hdr_org(org_a.slug),
    )
    assert resp.status_code == 201, resp.content
    body = resp.json()
    assert body["team_visibility"] == "team"
    assert Reflection.all_objects.get(pk=body["id"]).team_visibility == "team"


@pytest.mark.django_db
def test_team_visibility_round_trip(
    api, org_a, program_a, counselor_template, counselor_user,
):
    user, _person = counselor_user
    api.force_authenticate(user=user)
    resp = api.post(
        "/api/v1/reflections/",
        {
            "program_slug": program_a.slug,
            "template": counselor_template.id,
            "period_start": "2026-06-01",
            "period_end": "2026-06-07",
            "answers": {"note": "private"},
            "language": "en",
            "team_visibility": "supervisors_only",
        },
        format="json",
        **_hdr_org(org_a.slug),
    )
    assert resp.status_code == 201, resp.content
    assert resp.json()["team_visibility"] == "supervisors_only"

    rid = resp.json()["id"]
    g = api.get(f"/api/v1/reflections/{rid}/", **_hdr_org(org_a.slug))
    assert g.status_code == 200
    assert g.json()["team_visibility"] == "supervisors_only"


@pytest.mark.django_db
def test_person_cannot_see_other_reflection(
    api,
    org_a,
    program_a,
    counselor_template,
    counselor_user,
    other_counselor,
):
    user_a, person_a = counselor_user
    _user_b, person_b = other_counselor
    ref_b = Reflection.all_objects.create(
        organization=org_a,
        program=program_a,
        subject=person_b,
        template=counselor_template,
        period_start=date(2026, 6, 1),
        period_end=date(2026, 6, 7),
        answers={"note": "b"},
        language="en",
    )
    api.force_authenticate(user=user_a)
    r = api.get(f"/api/v1/reflections/{ref_b.id}/", **_hdr_org(org_a.slug))
    assert r.status_code == 404


@pytest.mark.django_db
def test_leadership_sees_unit_level_reflections(
    api,
    org_a,
    program_a,
    counselor_template,
    counselor_user,
):
    user_c, person_c = counselor_user
    Membership.all_objects.filter(person=person_c, program=program_a).update(
        metadata={"unit_slug": "tsofim"},
    )
    leader = User.objects.create_user(email="lead@example.com", password="pw")
    person_l = Person.all_objects.create(organization=org_a, first_name="L", last_name="T", user=leader)
    Membership.all_objects.create(
        program=program_a,
        person=person_l,
        role="leadership_team",
        is_active=True,
        metadata={"assigned_unit_slugs": ["tsofim"]},
    )
    api.force_authenticate(user=user_c)
    rc = api.post(
        "/api/v1/reflections/",
        {
            "program_slug": program_a.slug,
            "template": counselor_template.id,
            "period_start": "2026-06-01",
            "period_end": "2026-06-07",
            "answers": {"note": "hello"},
            "language": "en",
        },
        format="json",
        **_hdr_org(org_a.slug),
    )
    assert rc.status_code == 201
    rid = rc.json()["id"]

    api.force_authenticate(user=leader)
    rr = api.get(f"/api/v1/reflections/{rid}/", **_hdr_org(org_a.slug))
    assert rr.status_code == 200
    assert rr.json()["answers"]["note"] == "hello"


@pytest.mark.django_db
def test_cross_org_access_impossible(
    api,
    org_a,
    org_b,
    program_a,
    program_b,
    counselor_user,
):
    user_a, person_a = counselor_user
    tpl_b = ReflectionTemplate.all_objects.create(
        organization=org_b,
        name="Other",
        slug="other-tpl",
        cadence="weekly",
        role="counselor",
        program_type="summer_camp",
        schema=_tpl_schema_bilingual("x"),
        languages=["en"],
    )
    ref_b = Reflection.all_objects.create(
        organization=org_b,
        program=program_b,
        subject=Person.all_objects.create(organization=org_b, first_name="X", last_name="Y"),
        template=tpl_b,
        period_start=date(2026, 6, 1),
        period_end=date(2026, 6, 7),
        answers={"x": "secret"},
        language="en",
    )
    api.force_authenticate(user=user_a)
    r = api.get(f"/api/v1/reflections/{ref_b.id}/", **_hdr_org(org_a.slug))
    assert r.status_code == 404


@pytest.mark.django_db
def test_schema_validation_rejects_malformed_answers(
    api,
    org_a,
    program_a,
    counselor_template,
    counselor_user,
):
    user, _ = counselor_user
    api.force_authenticate(user=user)
    resp = api.post(
        "/api/v1/reflections/",
        {
            "program_slug": program_a.slug,
            "template": counselor_template.id,
            "period_start": "2026-06-01",
            "period_end": "2026-06-07",
            "answers": {},
            "language": "en",
        },
        format="json",
        **_hdr_org(org_a.slug),
    )
    assert resp.status_code == 400


@pytest.mark.django_db
def test_template_for_me_language_parameter(api, org_a, program_a, counselor_template, counselor_user):
    user, _ = counselor_user
    api.force_authenticate(user=user)
    resp = api.get(
        "/api/v1/reflections/template-for-me/",
        {"language": "es"},
        **_hdr_org(org_a.slug),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["language"] == "es"
    assert body["program_slug"] == program_a.slug
    assert body["schema"]["fields"][0]["prompts"] == {"es": "Español"}


@pytest.mark.django_db
def test_wellness_team_readonly_enforced(
    api,
    org_a,
    program_a,
    counselor_template,
    counselor_user,
):
    tpl_well = ReflectionTemplate.all_objects.create(
        organization=org_a,
        name="Care check-in",
        slug="care-in",
        cadence="weekly",
        role="camper_care",
        program_type="summer_camp",
        schema=_tpl_schema_bilingual("w"),
        languages=["en", "es"],
    )
    user_c, person_c = counselor_user
    nurse = User.objects.create_user(email="nurse@example.com", password="pw")
    person_n = Person.all_objects.create(organization=org_a, first_name="N", last_name="C", user=nurse)
    Membership.all_objects.create(program=program_a, person=person_n, role="health_center", is_active=True)

    api.force_authenticate(user=nurse)
    wellness_other = Reflection.all_objects.create(
        organization=org_a,
        program=program_a,
        subject=person_c,
        template=tpl_well,
        period_start=date(2026, 6, 1),
        period_end=date(2026, 6, 7),
        answers={"w": "well"},
        language="en",
    )
    g = api.get(f"/api/v1/reflections/{wellness_other.id}/", **_hdr_org(org_a.slug))
    assert g.status_code == 200

    bad = api.patch(
        f"/api/v1/reflections/{wellness_other.id}/",
        {"answers": {"w": "hacked"}},
        format="json",
        **_hdr_org(org_a.slug),
    )
    assert bad.status_code == 403


@pytest.mark.django_db
def test_membership_role_filter(api, org_a, program_a, counselor_template, counselor_user, other_counselor):
    user_a, person_a = counselor_user
    user_b, person_b = other_counselor
    m_b = Membership.all_objects.get(person=person_b, program=program_a)
    m_b.role = "specialist"
    m_b.save(update_fields=["role", "capability"])

    tpl_sp = ReflectionTemplate.all_objects.create(
        organization=org_a,
        name="Spec",
        slug="spec-w",
        cadence="weekly",
        role="specialist",
        program_type="summer_camp",
        schema=_tpl_schema_bilingual("s"),
        languages=["en"],
    )

    api.force_authenticate(user=user_a)
    api.post(
        "/api/v1/reflections/",
        {
            "program_slug": program_a.slug,
            "template": counselor_template.id,
            "period_start": "2026-06-01",
            "period_end": "2026-06-07",
            "answers": {"note": "a"},
            "language": "en",
        },
        format="json",
        **_hdr_org(org_a.slug),
    )
    api.force_authenticate(user=user_b)
    api.post(
        "/api/v1/reflections/",
        {
            "program_slug": program_a.slug,
            "template": tpl_sp.id,
            "period_start": "2026-06-02",
            "period_end": "2026-06-08",
            "answers": {"s": "b"},
            "language": "en",
        },
        format="json",
        **_hdr_org(org_a.slug),
    )

    api.force_authenticate(user=user_a)
    r = api.get(
        "/api/v1/reflections/",
        {"membership_role": "specialist"},
        **_hdr_org(org_a.slug),
    )
    assert r.status_code == 200
    assert r.json() == []


@pytest.mark.django_db
def test_incomplete_reflection_can_patch(api, org_a, program_a, counselor_template, counselor_user):
    user, person = counselor_user
    ref = Reflection.all_objects.create(
        organization=org_a,
        program=program_a,
        subject=person,
        author=person,
        template=counselor_template,
        period_start=date(2026, 6, 1),
        period_end=date(2026, 6, 7),
        answers={"note": "draft"},
        language="en",
        is_complete=False,
    )
    api.force_authenticate(user=user)
    resp = api.patch(
        f"/api/v1/reflections/{ref.id}/",
        {"answers": {"note": "updated"}},
        format="json",
        **_hdr_org(org_a.slug),
    )
    assert resp.status_code == 200
    assert resp.json()["answers"]["note"] == "updated"


@pytest.mark.django_db
def test_org_admin_can_submit_reflection_without_membership_on_target_program(
    api,
    org_a,
    program_second_session,
    kitchen_template,
    org_admin_user,
):
    """Org admin on any program in the org may submit using any template on another program in the same org."""
    user, _person = org_admin_user
    api.force_authenticate(user=user)
    resp = api.post(
        "/api/v1/reflections/",
        {
            "program_slug": program_second_session.slug,
            "template": kitchen_template.id,
            "period_start": "2026-07-01",
            "period_end": "2026-07-07",
            "answers": {"k": "prep lists"},
            "language": "en",
        },
        format="json",
        **_hdr_org(org_a.slug),
    )
    assert resp.status_code == 201, resp.content
    assert resp.json()["answers"] == {"k": "prep lists"}


@pytest.mark.django_db
def test_counselor_rejected_for_mismatched_template_role(
    api,
    org_a,
    program_a,
    kitchen_template,
    counselor_user,
):
    user, _ = counselor_user
    api.force_authenticate(user=user)
    resp = api.post(
        "/api/v1/reflections/",
        {
            "program_slug": program_a.slug,
            "template": kitchen_template.id,
            "period_start": "2026-06-01",
            "period_end": "2026-06-07",
            "answers": {"k": "nope"},
            "language": "en",
        },
        format="json",
        **_hdr_org(org_a.slug),
    )
    assert resp.status_code == 400
    body = resp.json()
    assert "template" in body


@pytest.mark.django_db
def test_superuser_can_submit_without_program_membership(
    api,
    org_a,
    program_second_session,
    kitchen_template,
):
    u = User.objects.create_superuser(email="su@example.com", password="pw")
    Person.all_objects.create(organization=org_a, first_name="S", last_name="U", user=u)
    api.force_authenticate(user=u)
    resp = api.post(
        "/api/v1/reflections/",
        {
            "program_slug": program_second_session.slug,
            "template": kitchen_template.id,
            "period_start": "2026-07-01",
            "period_end": "2026-07-07",
            "answers": {"k": "su note"},
            "language": "en",
        },
        format="json",
        **_hdr_org(org_a.slug),
    )
    assert resp.status_code == 201, resp.content


@pytest.mark.django_db
def test_template_for_me_org_admin_with_program_and_role(
    api,
    org_a,
    program_second_session,
    kitchen_template,
    org_admin_user,
):
    user, _ = org_admin_user
    api.force_authenticate(user=user)
    resp = api.get(
        "/api/v1/reflections/template-for-me/",
        {"program": program_second_session.slug, "role": "kitchen_staff", "language": "en"},
        **_hdr_org(org_a.slug),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == kitchen_template.id
    assert body["program_slug"] == program_second_session.slug
    assert body["schema"]["fields"][0]["prompts"] == {"en": "English"}


@pytest.mark.django_db
def test_template_for_me_org_admin_requires_role_when_not_on_program(
    api,
    org_a,
    program_second_session,
    org_admin_user,
):
    user, _ = org_admin_user
    api.force_authenticate(user=user)
    resp = api.get(
        "/api/v1/reflections/template-for-me/",
        {"program": program_second_session.slug},
        **_hdr_org(org_a.slug),
    )
    assert resp.status_code == 400
    assert "role" in resp.json()["detail"].lower()


@pytest.mark.django_db
def test_rejects_template_from_other_organization(
    api,
    org_a,
    org_b,
    program_a,
    program_b,
    counselor_user,
):
    """Even privileged users cannot attach another org's template to a program."""
    tpl_other = ReflectionTemplate.all_objects.create(
        organization=org_b,
        name="Other org tpl",
        slug="other-org-tpl",
        cadence="weekly",
        role="counselor",
        program_type="summer_camp",
        schema=_tpl_schema_bilingual("z"),
        languages=["en"],
    )
    user, _ = counselor_user
    api.force_authenticate(user=user)
    resp = api.post(
        "/api/v1/reflections/",
        {
            "program_slug": program_a.slug,
            "template": tpl_other.id,
            "period_start": "2026-06-01",
            "period_end": "2026-06-07",
            "answers": {"z": "x"},
            "language": "en",
        },
        format="json",
        **_hdr_org(org_a.slug),
    )
    assert resp.status_code == 400
    assert "template" in resp.json()
