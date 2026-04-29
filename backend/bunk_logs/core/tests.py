from datetime import date
from datetime import timedelta

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from bunk_logs.core.models import Organization
from bunk_logs.core.models import Program


@pytest.mark.django_db
class TestOrganization:
    def test_create_organization(self):
        org = Organization.objects.create(name="Test Camp", slug="test-camp")
        assert org.pk is not None
        assert str(org) == "Test Camp"

    def test_slug_uniqueness_enforced(self):
        Organization.objects.create(name="Camp One", slug="camp-one")
        with pytest.raises(IntegrityError):
            Organization.objects.create(name="Camp One Duplicate", slug="camp-one")

    def test_settings_json_accepts_arbitrary_dict(self):
        payload = {"theme": "dark", "features": ["messaging", "reflections"], "max_users": 500}
        org = Organization.objects.create(name="Rich Camp", slug="rich-camp", settings=payload)
        org.refresh_from_db()
        assert org.settings == payload

    def test_settings_defaults_to_empty_dict(self):
        org = Organization.objects.create(name="Minimal Camp", slug="minimal-camp")
        assert org.settings == {}

    def test_is_active_defaults_to_true(self):
        org = Organization.objects.create(name="Active Camp", slug="active-camp")
        assert org.is_active is True

    def test_ordering_by_name(self):
        Organization.objects.create(name="Zeta Camp", slug="zeta-camp")
        Organization.objects.create(name="Alpha Camp", slug="alpha-camp")
        names = list(Organization.objects.values_list("name", flat=True))
        assert names == sorted(names)


@pytest.mark.django_db
class TestProgram:
    @pytest.fixture
    def org(self):
        return Organization.objects.create(name="Crane Lake", slug="crane-lake")

    def test_create_program(self, org):
        start = date(2026, 6, 15)
        end = date(2026, 8, 15)
        program = Program.objects.create(
            organization=org,
            name="Summer 2026",
            slug="summer-2026",
            program_type="summer_camp",
            start_date=start,
            end_date=end,
        )
        assert program.pk is not None
        assert program.organization_id == org.pk
        assert str(program) == "Summer 2026"

    def test_cannot_duplicate_slug_within_org(self, org):
        start = date(2026, 6, 1)
        end = date(2026, 8, 1)
        Program.objects.create(
            organization=org,
            name="First",
            slug="shared-slug",
            program_type="summer_camp",
            start_date=start,
            end_date=end,
        )
        with pytest.raises(IntegrityError):
            Program.objects.create(
                organization=org,
                name="Second",
                slug="shared-slug",
                program_type="religious_school",
                start_date=start,
                end_date=end,
            )

    def test_same_slug_allowed_across_orgs(self):
        org_a = Organization.objects.create(name="Camp A", slug="camp-a")
        org_b = Organization.objects.create(name="Camp B", slug="camp-b")
        start = date(2026, 6, 1)
        end = date(2026, 8, 1)
        p_a = Program.objects.create(
            organization=org_a,
            name="Program A",
            slug="fall",
            program_type="summer_camp",
            start_date=start,
            end_date=end,
        )
        p_b = Program.objects.create(
            organization=org_b,
            name="Program B",
            slug="fall",
            program_type="religious_school",
            start_date=start,
            end_date=end,
        )
        assert p_a.slug == p_b.slug == "fall"
        assert p_a.organization_id != p_b.organization_id

    def test_end_date_before_start_date_rejected(self, org):
        start = date(2026, 8, 1)
        end = start - timedelta(days=1)
        program = Program(
            organization=org,
            name="Bad",
            slug="bad-dates",
            program_type="summer_camp",
            start_date=start,
            end_date=end,
        )
        with pytest.raises(ValidationError):
            program.full_clean()
        with pytest.raises(IntegrityError):
            Program.objects.create(
                organization=org,
                name="Bad",
                slug="bad-dates-orm",
                program_type="summer_camp",
                start_date=start,
                end_date=end,
            )
