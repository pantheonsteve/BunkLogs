from datetime import date

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.http import HttpResponse
from django.test import RequestFactory

from bunk_logs.core.context import get_current_organization
from bunk_logs.core.context import organization_context
from bunk_logs.core.middleware import OrganizationMiddleware
from bunk_logs.core.models import Membership
from bunk_logs.core.models import Organization
from bunk_logs.core.models import Person
from bunk_logs.core.models import Program
from bunk_logs.core.models import Reflection
from bunk_logs.core.models import ReflectionTemplate

User = get_user_model()


def _field_schema(key: str = "n") -> dict:
    return {"key": key, "type": "text", "prompts": {"en": "Q"}}


@pytest.fixture
def org_alpha(db):
    return Organization.objects.create(name="Alpha Camp", slug="alpha-mt")


@pytest.fixture
def org_beta(db):
    return Organization.objects.create(name="Beta Camp", slug="beta-mt")


@pytest.fixture
def program_alpha(org_alpha):
    return Program.all_objects.create(
        organization=org_alpha,
        name="P Alpha",
        slug="p-alpha",
        program_type="summer_camp",
        start_date=date(2026, 6, 1),
        end_date=date(2026, 8, 1),
    )


@pytest.fixture
def program_beta(org_beta):
    return Program.all_objects.create(
        organization=org_beta,
        name="P Beta",
        slug="p-beta",
        program_type="summer_camp",
        start_date=date(2026, 6, 1),
        end_date=date(2026, 8, 1),
    )


@pytest.mark.django_db
def test_no_org_context_scoped_querysets_empty(org_alpha, program_alpha):
    assert not Program.objects.exists()
    assert not Person.objects.exists()
    assert not Membership.objects.exists()
    assert not ReflectionTemplate.objects.exists()
    assert not Reflection.objects.exists()
    assert Organization.objects.filter(pk=org_alpha.pk).exists()


@pytest.mark.django_db
def test_with_org_context_only_that_org_data(org_alpha, org_beta, program_alpha, program_beta):
    with organization_context(org_alpha):
        ids = set(Program.objects.values_list("id", flat=True))
        assert ids == {program_alpha.id}
    with organization_context(org_beta):
        ids = set(Program.objects.values_list("id", flat=True))
        assert ids == {program_beta.id}


@pytest.mark.django_db
def test_all_objects_bypasses_scoping(org_alpha, org_beta, program_alpha, program_beta):
    assert set(Program.all_objects.values_list("id", flat=True)) == {program_alpha.id, program_beta.id}


@pytest.mark.django_db
def test_two_orgs_person_isolation(org_alpha, org_beta):
    pa = Person.all_objects.create(organization=org_alpha, first_name="A", last_name="One")
    pb = Person.all_objects.create(organization=org_beta, first_name="B", last_name="Two")
    with organization_context(org_alpha):
        assert set(Person.objects.values_list("id", flat=True)) == {pa.id}
    with organization_context(org_beta):
        assert set(Person.objects.values_list("id", flat=True)) == {pb.id}


@pytest.mark.django_db
def test_membership_scoped_by_program_organization(org_alpha, org_beta, program_alpha, program_beta):
    pa = Person.all_objects.create(organization=org_alpha, first_name="A", last_name="Camper")
    mb_alpha = Membership.all_objects.create(program=program_alpha, person=pa, role="camper")
    Membership.all_objects.create(program=program_beta, person=pa, role="madrich")

    with organization_context(org_alpha):
        assert list(Membership.objects.values_list("id", flat=True)) == [mb_alpha.id]


@pytest.mark.django_db
def test_reflection_template_includes_global_for_org(org_alpha):
    global_t = ReflectionTemplate.all_objects.create(
        organization=None,
        name="Global",
        slug="global-tpl-mt",
        cadence="daily",
        schema={"fields": [_field_schema()]},
    )
    org_t = ReflectionTemplate.all_objects.create(
        organization=org_alpha,
        name="Org",
        slug="org-tpl-mt",
        cadence="daily",
        schema={"fields": [_field_schema("o")]},
    )
    other = Organization.objects.create(name="Other", slug="other-mt")
    ReflectionTemplate.all_objects.create(
        organization=other,
        name="Other",
        slug="other-tpl-mt",
        cadence="daily",
        schema={"fields": [_field_schema("x")]},
    )
    with organization_context(org_alpha):
        slugs = set(ReflectionTemplate.objects.values_list("slug", flat=True))
        assert slugs == {"global-tpl-mt", "org-tpl-mt"}
        assert global_t.slug in slugs
        assert org_t.slug in slugs


@pytest.mark.django_db
def test_subdomain_resolves_organization():
    org = Organization.objects.create(name="Temple", slug="tbe")

    def get_response(request):
        return HttpResponse("ok")

    rf = RequestFactory()
    request = rf.get("/", HTTP_HOST="tbe.bunklogs.net")
    request.user = AnonymousUser()
    OrganizationMiddleware(get_response)(request)

    assert request.organization == org


@pytest.mark.django_db
def test_subdomain_skips_admin_host():
    Organization.objects.create(name="X", slug="admin-should-not-match")

    def get_response(request):
        return HttpResponse("ok")

    rf = RequestFactory()
    request = rf.get("/", HTTP_HOST="admin.bunklogs.net")
    request.user = AnonymousUser()
    OrganizationMiddleware(get_response)(request)

    assert request.organization is None


@pytest.mark.django_db
def test_middleware_clears_thread_local_after_request():
    org = Organization.objects.create(name="Clear", slug="clear-mt")

    def get_response(request):
        assert get_current_organization() == org
        return HttpResponse("ok")

    rf = RequestFactory()
    request = rf.get("/", HTTP_HOST="clear-mt.bunklogs.net")
    request.user = AnonymousUser()
    OrganizationMiddleware(get_response)(request)

    assert get_current_organization() is None


@pytest.mark.django_db
def test_subdomain_clc_resolves_organization():
    org = Organization.objects.create(name="Crane Lake", slug="clc")

    def get_response(request):
        return HttpResponse("ok")

    rf = RequestFactory()
    request = rf.get("/", HTTP_HOST="clc.bunklogs.net")
    request.user = AnonymousUser()
    OrganizationMiddleware(get_response)(request)

    assert request.organization == org


@pytest.mark.django_db
def test_subdomain_unknown_returns_no_organization():
    Organization.objects.create(name="Real Org", slug="realorg")

    def get_response(request):
        return HttpResponse("ok")

    rf = RequestFactory()
    request = rf.get("/", HTTP_HOST="notrealorg.bunklogs.net")
    request.user = AnonymousUser()
    OrganizationMiddleware(get_response)(request)

    assert request.organization is None


@pytest.mark.django_db
def test_dev_header_resolves_organization(org_alpha, settings):
    settings.ORGANIZATION_ROUTING_DEV_OVERRIDES = True

    def get_response(request):
        return HttpResponse("ok")

    rf = RequestFactory()
    request = rf.get("/", HTTP_HOST="localhost", HTTP_X_ORGANIZATION_SLUG="alpha-mt")
    request.user = AnonymousUser()
    OrganizationMiddleware(get_response)(request)

    assert request.organization == org_alpha


@pytest.mark.django_db
def test_dev_query_param_resolves_organization(org_alpha, settings):
    settings.ORGANIZATION_ROUTING_DEV_OVERRIDES = True

    def get_response(request):
        return HttpResponse("ok")

    rf = RequestFactory()
    request = rf.get("/?org=alpha-mt", HTTP_HOST="localhost")
    request.user = AnonymousUser()
    OrganizationMiddleware(get_response)(request)

    assert request.organization == org_alpha


@pytest.mark.django_db
def test_dev_override_disabled_ignores_header(org_alpha, settings):
    settings.DEBUG = False
    settings.ORGANIZATION_ROUTING_DEV_OVERRIDES = False

    def get_response(request):
        return HttpResponse("ok")

    rf = RequestFactory()
    request = rf.get("/", HTTP_HOST="localhost", HTTP_X_ORGANIZATION_SLUG="alpha-mt")
    request.user = AnonymousUser()
    OrganizationMiddleware(get_response)(request)

    assert request.organization is None


@pytest.mark.django_db
def test_authenticated_fallback_when_host_has_no_tenant(org_alpha):
    user = User.objects.create_user(email="staff@example.com", password="pw")
    Person.all_objects.create(
        organization=org_alpha,
        first_name="S",
        last_name="Taff",
        user=user,
    )

    def get_response(request):
        return HttpResponse("ok")

    rf = RequestFactory()
    request = rf.get("/", HTTP_HOST="bunklogs.net")
    request.user = user
    OrganizationMiddleware(get_response)(request)

    assert request.organization == org_alpha
