from datetime import date
from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from bunk_logs.core.models import Membership
from bunk_logs.core.models import Organization
from bunk_logs.core.models import Person
from bunk_logs.core.models import Program

User = get_user_model()


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


@pytest.mark.django_db
class TestPerson:
    @pytest.fixture
    def org(self):
        return Organization.objects.create(name="Crane Lake", slug="crane-lake")

    def test_create_without_user(self, org):
        person = Person.objects.create(
            organization=org,
            first_name="Alex",
            last_name="Rivera",
        )
        assert person.pk is not None
        assert person.user_id is None

    def test_create_linked_to_user(self, org):
        user = User.objects.create_user(email="counselor@example.com", password="testpass123")
        person = Person.objects.create(
            organization=org,
            first_name="Sam",
            last_name="Lee",
            user=user,
        )
        assert person.user_id == user.pk
        assert user.person_record == person

    def test_full_name_uses_preferred_when_set(self, org):
        person = Person.objects.create(
            organization=org,
            first_name="Robert",
            last_name="Smith",
            preferred_name="Bob",
        )
        assert person.full_name == "Bob Smith"

    def test_full_name_falls_back_to_first_name(self, org):
        person = Person.objects.create(
            organization=org,
            first_name="Jane",
            last_name="Doe",
        )
        assert person.full_name == "Jane Doe"

    def test_external_ids_arbitrary_keys(self, org):
        payload = {"campminder_id": "12345", "other_system": "abc"}
        person = Person.objects.create(
            organization=org,
            first_name="Kid",
            last_name="Camper",
            external_ids=payload,
        )
        person.refresh_from_db()
        assert person.external_ids == payload

    def test_cannot_save_without_organization(self):
        person = Person(first_name="Orphan", last_name="Person")
        with pytest.raises(IntegrityError):
            person.save()

    def test_ordering_by_last_then_first_name(self, org):
        Person.objects.create(organization=org, first_name="Ann", last_name="Zed")
        Person.objects.create(organization=org, first_name="Bob", last_name="Ayer")
        names = list(Person.objects.values_list("last_name", "first_name"))
        assert names == [("Ayer", "Bob"), ("Zed", "Ann")]


@pytest.mark.django_db
class TestMembership:
    @pytest.fixture
    def org(self):
        return Organization.objects.create(name="Crane Lake", slug="crane-lake")

    @pytest.fixture
    def program(self, org):
        return Program.objects.create(
            organization=org,
            name="Summer 2026",
            slug="summer-2026",
            program_type="summer_camp",
            start_date=date(2026, 6, 15),
            end_date=date(2026, 8, 15),
        )

    @pytest.fixture
    def other_org_program(self):
        other = Organization.objects.create(name="Other", slug="other-org")
        return Program.objects.create(
            organization=other,
            name="Fall 2026",
            slug="fall-2026",
            program_type="religious_school",
            start_date=date(2026, 9, 1),
            end_date=date(2026, 12, 15),
        )

    @pytest.fixture
    def person(self, org):
        return Person.objects.create(
            organization=org,
            first_name="Jamie",
            last_name="Cohen",
        )

    def test_cannot_duplicate_program_person_role(self, program, person):
        Membership.objects.create(program=program, person=person, role="counselor")
        with pytest.raises(IntegrityError):
            Membership.objects.create(program=program, person=person, role="counselor")

    def test_same_person_multiple_programs(self, program, other_org_program, person):
        Membership.objects.create(program=program, person=person, role="counselor")
        Membership.objects.create(program=other_org_program, person=person, role="madrich")
        assert Membership.objects.filter(person=person).count() == 2

    def test_same_person_multiple_roles_one_program(self, program, person):
        Membership.objects.create(program=program, person=person, role="counselor")
        Membership.objects.create(program=program, person=person, role="admin")
        rows = list(Membership.objects.filter(program=program, person=person).values_list("role", flat=True))
        assert set(rows) == {"counselor", "admin"}

    def test_tags_list_of_strings(self, program, person):
        tags = ["international", "israeli", "specialist:waterfront"]
        m = Membership.objects.create(
            program=program,
            person=person,
            role="specialist",
            tags=tags,
        )
        m.refresh_from_db()
        assert m.tags == tags

    def test_all_role_choices_queryable(self, program, person):
        for value, _label in Membership.ROLES:
            Membership.objects.create(program=program, person=person, role=value)
        for value, _label in Membership.ROLES:
            assert Membership.objects.filter(role=value).exists()
