from datetime import date
from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from bunk_logs.core.models import ROLE_TO_CAPABILITY
from bunk_logs.core.models import Membership
from bunk_logs.core.models import Organization
from bunk_logs.core.models import Person
from bunk_logs.core.models import Program
from bunk_logs.core.models import Reflection
from bunk_logs.core.models import ReflectionTemplate
from bunk_logs.core.models import validate_reflection_answers
from bunk_logs.core.models import validate_reflection_template_schema

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
        program = Program.all_objects.create(
            organization=org,
            name="Crane Lake - Summer 2026",
            slug="summer-2026",
            program_type="summer_camp",
            start_date=start,
            end_date=end,
        )
        assert program.pk is not None
        assert program.organization_id == org.pk
        assert str(program) == "[crane-lake] Crane Lake - Summer 2026"

    def test_cannot_duplicate_slug_within_org(self, org):
        start = date(2026, 6, 1)
        end = date(2026, 8, 1)
        Program.all_objects.create(
            organization=org,
            name="Crane Lake - First",
            slug="shared-slug",
            program_type="summer_camp",
            start_date=start,
            end_date=end,
        )
        with pytest.raises(IntegrityError):
            Program.all_objects.create(
                organization=org,
                name="Crane Lake - Second",
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
        p_a = Program.all_objects.create(
            organization=org_a,
            name="Camp A - Program A",
            slug="fall",
            program_type="summer_camp",
            start_date=start,
            end_date=end,
        )
        p_b = Program.all_objects.create(
            organization=org_b,
            name="Camp B - Program B",
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
            name="Crane Lake - Bad",
            slug="bad-dates",
            program_type="summer_camp",
            start_date=start,
            end_date=end,
        )
        with pytest.raises(ValidationError):
            program.full_clean()
        with pytest.raises(ValidationError):
            Program.all_objects.create(
                organization=org,
                name="Crane Lake - Bad",
                slug="bad-dates-orm",
                program_type="summer_camp",
                start_date=start,
                end_date=end,
            )

    def test_program_name_must_start_with_organization_name(self, org):
        start = date(2026, 6, 1)
        end = date(2026, 8, 1)
        program = Program(
            organization=org,
            name="Wrong prefix - Summer",
            slug="bad-name",
            program_type="summer_camp",
            start_date=start,
            end_date=end,
        )
        with pytest.raises(ValidationError) as exc:
            program.full_clean()
        assert "organization name" in str(exc.value).lower()


@pytest.mark.django_db
class TestPerson:
    @pytest.fixture
    def org(self):
        return Organization.objects.create(name="Crane Lake", slug="crane-lake")

    def test_create_without_user(self, org):
        person = Person.all_objects.create(
            organization=org,
            first_name="Alex",
            last_name="Rivera",
        )
        assert person.pk is not None
        assert person.user_id is None

    def test_create_linked_to_user(self, org):
        user = User.objects.create_user(email="counselor@example.com", password="testpass123")
        person = Person.all_objects.create(
            organization=org,
            first_name="Sam",
            last_name="Lee",
            user=user,
        )
        assert person.user_id == user.pk
        assert Person.all_objects.get(user=user) == person

    def test_full_name_uses_preferred_when_set(self, org):
        person = Person.all_objects.create(
            organization=org,
            first_name="Robert",
            last_name="Smith",
            preferred_name="Bob",
        )
        assert person.full_name == "Bob Smith"

    def test_full_name_falls_back_to_first_name(self, org):
        person = Person.all_objects.create(
            organization=org,
            first_name="Jane",
            last_name="Doe",
        )
        assert person.full_name == "Jane Doe"

    def test_external_ids_arbitrary_keys(self, org):
        payload = {"campminder_id": "12345", "other_system": "abc"}
        person = Person.all_objects.create(
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
        Person.all_objects.create(organization=org, first_name="Ann", last_name="Zed")
        Person.all_objects.create(organization=org, first_name="Bob", last_name="Ayer")
        names = list(Person.all_objects.values_list("last_name", "first_name"))
        assert names == [("Ayer", "Bob"), ("Zed", "Ann")]


@pytest.mark.django_db
class TestMembership:
    @pytest.fixture
    def org(self):
        return Organization.objects.create(name="Crane Lake", slug="crane-lake")

    @pytest.fixture
    def program(self, org):
        return Program.all_objects.create(
            organization=org,
            name="Crane Lake - Summer 2026",
            slug="summer-2026",
            program_type="summer_camp",
            start_date=date(2026, 6, 15),
            end_date=date(2026, 8, 15),
        )

    @pytest.fixture
    def other_org_program(self):
        other = Organization.objects.create(name="Other", slug="other-org")
        return Program.all_objects.create(
            organization=other,
            name="Other - Fall 2026",
            slug="fall-2026",
            program_type="religious_school",
            start_date=date(2026, 9, 1),
            end_date=date(2026, 12, 15),
        )

    @pytest.fixture
    def person(self, org):
        return Person.all_objects.create(
            organization=org,
            first_name="Jamie",
            last_name="Cohen",
        )

    def test_cannot_duplicate_program_person_role(self, program, person):
        Membership.all_objects.create(program=program, person=person, role="counselor")
        with pytest.raises(IntegrityError):
            Membership.all_objects.create(program=program, person=person, role="counselor")

    def test_same_person_multiple_programs(self, program, other_org_program, person):
        Membership.all_objects.create(program=program, person=person, role="counselor")
        Membership.all_objects.create(program=other_org_program, person=person, role="madrich")
        assert Membership.all_objects.filter(person=person).count() == 2

    def test_same_person_multiple_roles_one_program(self, program, person):
        Membership.all_objects.create(program=program, person=person, role="counselor")
        Membership.all_objects.create(program=program, person=person, role="admin")
        rows = list(Membership.all_objects.filter(program=program, person=person).values_list("role", flat=True))
        assert set(rows) == {"counselor", "admin"}

    def test_tags_list_of_strings(self, program, person):
        tags = ["international", "israeli", "specialist:waterfront"]
        m = Membership.all_objects.create(
            program=program,
            person=person,
            role="specialist",
            tags=tags,
        )
        m.refresh_from_db()
        assert m.tags == tags

    def test_all_role_choices_queryable(self, program, person):
        for value, _label in Membership.ROLES:
            Membership.all_objects.create(program=program, person=person, role=value)
        for value, _label in Membership.ROLES:
            assert Membership.all_objects.filter(role=value).exists()


@pytest.mark.django_db
class TestMembershipCapability:
    """Capability is a derived RBAC layer kept in sync with role on every save()."""

    @pytest.fixture
    def org(self):
        return Organization.objects.create(name="Cap Org", slug="cap-org")

    @pytest.fixture
    def program(self, org):
        return Program.all_objects.create(
            organization=org,
            name="Cap Org - Summer 2026",
            slug="cap-summer-2026",
            program_type="summer_camp",
            start_date=date(2026, 6, 15),
            end_date=date(2026, 8, 15),
        )

    def _person(self, org, first="P", last="Erson"):
        return Person.all_objects.create(organization=org, first_name=first, last_name=last)

    def test_mapping_covers_every_role(self):
        all_roles = {value for value, _label in Membership.ROLES}
        assert set(ROLE_TO_CAPABILITY.keys()) == all_roles, (
            "ROLE_TO_CAPABILITY must cover every role in Membership.ROLES. "
            f"Missing: {all_roles - set(ROLE_TO_CAPABILITY.keys())}. "
            f"Extra: {set(ROLE_TO_CAPABILITY.keys()) - all_roles}."
        )

    def test_capability_values_are_the_five_documented_ones(self):
        assert set(ROLE_TO_CAPABILITY.values()) == {
            "participant",
            "supervisor",
            "program_lead",
            "domain_specialist",
            "admin",
        }
        assert {value for value, _ in Membership.CAPABILITIES} == set(ROLE_TO_CAPABILITY.values())

    def test_save_assigns_capability_for_every_role(self, org, program):
        for value, _label in Membership.ROLES:
            person = self._person(org, last=f"Person-{value}")
            m = Membership.all_objects.create(program=program, person=person, role=value)
            m.refresh_from_db()
            assert m.capability == ROLE_TO_CAPABILITY[value]

    def test_changing_role_updates_capability(self, org, program):
        person = self._person(org, last="Promoted")
        m = Membership.all_objects.create(program=program, person=person, role="counselor")
        assert m.capability == "participant"

        m.role = "unit_head"
        m.save()
        m.refresh_from_db()
        assert m.capability == "supervisor"

        m.role = "admin"
        m.save()
        m.refresh_from_db()
        assert m.capability == "admin"

    def test_unmapped_role_raises_validation_error(self, org, program):
        person = self._person(org, last="Unknown")
        m = Membership(program=program, person=person, role="not_a_real_role")
        with pytest.raises(ValidationError) as exc_info:
            m.save()
        assert "role" in exc_info.value.message_dict

    def test_filter_by_capability_returns_expected_rows(self, org, program):
        roles_in_program = [
            "camper",
            "counselor",
            "unit_head",
            "leadership_team",
            "camper_care",
            "health_center",
            "admin",
        ]
        for r in roles_in_program:
            Membership.all_objects.create(
                program=program,
                person=self._person(org, last=f"P-{r}"),
                role=r,
            )

        # After 3.21, camper_care lives on the supervisor capability (unit-scoped)
        # while health_center keeps the domain_specialist (wellness-template) shortcut.
        expected_by_capability = {
            "participant": {"camper", "counselor"},
            "supervisor": {"unit_head", "camper_care"},
            "program_lead": {"leadership_team"},
            "domain_specialist": {"health_center"},
            "admin": {"admin"},
        }
        for cap, expected_roles in expected_by_capability.items():
            rows = Membership.all_objects.filter(capability=cap, program=program)
            assert {m.role for m in rows} == expected_roles

    def test_capability_admin_field_is_indexed(self):
        """Capability is meant to be queried at scale; ensure db_index=True is set."""
        field = Membership._meta.get_field("capability")
        assert field.db_index is True


_CHOICE_OPTIONS = [{"key": "a", "labels": {"en": "Option A"}}, {"key": "b", "labels": {"en": "Option B"}}]


def _minimal_prompts_field(ftype: str, key: str) -> dict:
    base = {"key": key, "type": ftype, "prompts": {"en": f"Prompt for {key}"}}
    if ftype in ("single_choice", "multiple_choice"):
        base["options"] = _CHOICE_OPTIONS
    return base


@pytest.mark.django_db
class TestReflectionTemplate:
    @pytest.fixture
    def org(self):
        return Organization.objects.create(name="Crane Lake", slug="crane-lake")

    def _valid_rating_schema(self) -> dict:
        return {
            "fields": [
                {
                    "key": "ratings",
                    "type": "rating_group",
                    "scale": [1, 3],
                    "scale_labels": {
                        "en": ["Low", "Mid", "High"],
                    },
                    "categories": [
                        {"key": "effort", "labels": {"en": "Effort"}},
                    ],
                },
            ],
        }

    @pytest.mark.parametrize(
        "ftype",
        ["text", "textarea", "text_list", "multiple_choice", "single_choice"],
    )
    def test_create_with_each_prompt_field_type(self, org, ftype):
        fields = [_minimal_prompts_field(ftype, "f1")]
        t = ReflectionTemplate.all_objects.create(
            organization=org,
            name="Weekly",
            slug=f"weekly-{ftype}",
            cadence="weekly",
            schema={"fields": fields},
            languages=["en"],
        )
        t.full_clean()
        assert t.pk is not None

    def test_create_rating_group(self, org):
        t = ReflectionTemplate.all_objects.create(
            organization=org,
            name="Ratings",
            slug="ratings-weekly",
            cadence="weekly",
            schema=self._valid_rating_schema(),
        )
        t.full_clean()

    def test_schema_rejects_non_object(self):
        with pytest.raises(ValidationError):
            validate_reflection_template_schema([])

    def test_schema_rejects_missing_fields_array(self):
        with pytest.raises(ValidationError):
            validate_reflection_template_schema({})

    def test_schema_rejects_empty_fields(self):
        with pytest.raises(ValidationError):
            validate_reflection_template_schema({"fields": []})

    def test_schema_rejects_missing_prompts_language(self, org):
        bad = {"fields": [{"key": "x", "type": "text", "prompts": {}}]}
        t = ReflectionTemplate(
            organization=org,
            name="Bad",
            slug="bad-prompts",
            cadence="daily",
            schema=bad,
        )
        with pytest.raises(ValidationError):
            t.full_clean()

    def test_parent_template_version_chain(self, org):
        v1 = ReflectionTemplate.all_objects.create(
            organization=org,
            name="Same",
            slug="same-template",
            version=1,
            cadence="weekly",
            schema={"fields": [_minimal_prompts_field("text", "note")]},
        )
        v2 = ReflectionTemplate.all_objects.create(
            organization=org,
            name="Same",
            slug="same-template",
            version=2,
            cadence="weekly",
            parent_template=v1,
            schema={"fields": [_minimal_prompts_field("textarea", "note")]},
        )
        v1.refresh_from_db()
        assert list(ReflectionTemplate.all_objects.filter(parent_template=v1)) == [v2]
        assert v2.parent_template_id == v1.pk

    def test_unique_org_slug_version(self, org):
        ReflectionTemplate.all_objects.create(
            organization=org,
            name="A",
            slug="shared",
            version=1,
            cadence="daily",
            schema={"fields": [_minimal_prompts_field("text", "a")]},
        )
        with pytest.raises(IntegrityError):
            ReflectionTemplate.all_objects.create(
                organization=org,
                name="B",
                slug="shared",
                version=1,
                cadence="daily",
                schema={"fields": [_minimal_prompts_field("text", "b")]},
            )

    def test_global_template_str(self):
        t = ReflectionTemplate.all_objects.create(
            organization=None,
            name="Global",
            slug="global-daily",
            cadence="daily",
            schema={"fields": [_minimal_prompts_field("text", "t")]},
        )
        assert "global" in str(t).lower()


@pytest.mark.django_db
class TestReflection:
    @pytest.fixture
    def org(self):
        return Organization.objects.create(name="Crane Lake", slug="crane-lake")

    @pytest.fixture
    def program(self, org):
        return Program.all_objects.create(
            organization=org,
            name="Crane Lake - Summer 2026",
            slug="summer-2026",
            program_type="summer_camp",
            start_date=date(2026, 6, 15),
            end_date=date(2026, 8, 15),
        )

    @pytest.fixture
    def person(self, org):
        return Person.all_objects.create(
            organization=org,
            first_name="Jamie",
            last_name="Cohen",
        )

    @pytest.fixture
    def template(self, org):
        return ReflectionTemplate.all_objects.create(
            organization=org,
            name="Weekly check-in",
            slug="weekly-checkin",
            cadence="weekly",
            role="counselor",
            schema={"fields": [_minimal_prompts_field("textarea", "highlight")]},
        )

    @pytest.fixture
    def other_role_template(self, org):
        return ReflectionTemplate.all_objects.create(
            organization=org,
            name="Kitchen weekly",
            slug="kitchen-weekly",
            cadence="weekly",
            role="kitchen_staff",
            schema={"fields": [_minimal_prompts_field("text", "shift")]},
        )

    def _make_reflection(self, org, program, person, template, **kwargs):
        period_start = kwargs.pop("period_start", date(2026, 7, 1))
        period_end = kwargs.pop("period_end", date(2026, 7, 7))
        answers = kwargs.pop("answers", {"highlight": "Great week."})
        language = kwargs.pop("language", "en")
        r = Reflection(
            organization=org,
            program=program,
            subject=person,
            template=template,
            period_start=period_start,
            period_end=period_end,
            answers=answers,
            language=language,
            **kwargs,
        )
        r.full_clean()
        r.save()
        return r

    def test_create_with_valid_answers(self, org, program, person, template):
        r = self._make_reflection(org, program, person, template)
        assert r.pk is not None
        assert r.answers == {"highlight": "Great week."}

    def test_validate_answers_instance_method(self, org, program, person, template):
        r = Reflection(
            organization=org,
            program=program,
            subject=person,
            template=template,
            period_start=date(2026, 7, 1),
            period_end=date(2026, 7, 7),
            answers={"highlight": "ok"},
        )
        r.validate_answers()

    def test_rejects_missing_required_field(self, org, program, person, template):
        r = Reflection(
            organization=org,
            program=program,
            subject=person,
            template=template,
            period_start=date(2026, 7, 1),
            period_end=date(2026, 7, 7),
            answers={},
        )
        with pytest.raises(ValidationError) as exc:
            r.full_clean()
        assert "highlight" in str(exc.value).lower() or "required" in str(exc.value).lower()

    def test_rejects_wrong_answer_type(self, org, program, person, template):
        r = Reflection(
            organization=org,
            program=program,
            subject=person,
            template=template,
            period_start=date(2026, 7, 1),
            period_end=date(2026, 7, 7),
            answers={"highlight": 123},
        )
        with pytest.raises(ValidationError):
            r.full_clean()

    def test_optional_field_may_be_omitted(self, org, program, person):
        tmpl = ReflectionTemplate.all_objects.create(
            organization=org,
            name="Optional extra",
            slug="optional-extra",
            cadence="weekly",
            schema={
                "fields": [
                    _minimal_prompts_field("text", "required_note"),
                    {**_minimal_prompts_field("text", "extra"), "required": False},
                ],
            },
        )
        r = Reflection(
            organization=org,
            program=program,
            subject=person,
            template=tmpl,
            period_start=date(2026, 7, 1),
            period_end=date(2026, 7, 7),
            answers={"required_note": "only this"},
        )
        r.full_clean()
        r.save()
        assert "extra" not in r.answers

    def test_period_end_before_start_rejected_on_clean(self, org, program, person, template):
        r = Reflection(
            organization=org,
            program=program,
            subject=person,
            template=template,
            period_start=date(2026, 7, 10),
            period_end=date(2026, 7, 1),
            answers={"highlight": "x"},
        )
        with pytest.raises(ValidationError):
            r.full_clean()

    def test_period_end_before_start_rejected_at_db(self, org, program, person, template):
        with pytest.raises(IntegrityError):
            Reflection.all_objects.create(
                organization=org,
                program=program,
                subject=person,
                template=template,
                period_start=date(2026, 7, 10),
                period_end=date(2026, 7, 1),
                answers={"highlight": "x"},
            )

    def test_query_by_person(self, org, program, person, template):
        self._make_reflection(org, program, person, template)
        other = Person.all_objects.create(organization=org, first_name="Other", last_name="Person")
        self._make_reflection(org, program, other, template, answers={"highlight": "other"})
        qs = Reflection.all_objects.filter(subject=person)
        assert qs.count() == 1
        assert qs.get().subject_id == person.pk

    def test_query_by_program(self, org, program, person, template):
        p2 = Program.all_objects.create(
            organization=org,
            name="Crane Lake - Fall",
            slug="fall-2026",
            program_type="religious_school",
            start_date=date(2026, 9, 1),
            end_date=date(2026, 12, 1),
        )
        self._make_reflection(org, program, person, template)
        self._make_reflection(org, p2, person, template, answers={"highlight": "fall"})
        assert Reflection.all_objects.filter(program=program).count() == 1

    def test_query_by_date_range(self, org, program, person, template):
        self._make_reflection(
            org,
            program,
            person,
            template,
            period_start=date(2026, 6, 1),
            period_end=date(2026, 6, 7),
            answers={"highlight": "week1"},
        )
        self._make_reflection(
            org,
            program,
            person,
            template,
            period_start=date(2026, 8, 1),
            period_end=date(2026, 8, 7),
            answers={"highlight": "week2"},
        )
        qs = Reflection.all_objects.filter(period_end__gte=date(2026, 7, 1), period_end__lte=date(2026, 7, 31))
        assert qs.count() == 0
        qs2 = Reflection.all_objects.filter(period_end__gte=date(2026, 6, 1), period_end__lte=date(2026, 6, 30))
        assert qs2.count() == 1

    def test_query_by_template_role(self, org, program, person, template, other_role_template):
        self._make_reflection(org, program, person, template)
        self._make_reflection(
            org,
            program,
            person,
            other_role_template,
            answers={"shift": "ok"},
        )
        counselor_only = Reflection.all_objects.filter(template__role="counselor")
        assert counselor_only.count() == 1
        assert counselor_only.get().template_id == template.pk

    def test_language_persisted(self, org, program, person, template):
        r = self._make_reflection(org, program, person, template, language="es")
        r.refresh_from_db()
        assert r.language == "es"

    def test_submitted_by_optional(self, org, program, person, template):
        user = User.objects.create_user(email="admin@example.com", password="x")
        r = self._make_reflection(org, program, person, template, submitted_by=user)
        assert r.submitted_by_id == user.pk

    def test_validate_reflection_answers_rating_group_complete(self, org):
        schema = {
            "fields": [
                {
                    "key": "ratings",
                    "type": "rating_group",
                    "scale_labels": {"en": ["L", "H"]},
                    "categories": [{"key": "effort", "labels": {"en": "Effort"}}],
                },
            ],
        }
        validate_reflection_answers(schema, {"ratings": {"effort": 3}})

    def test_validate_reflection_answers_rating_group_missing_category(self, org):
        schema = {
            "fields": [
                {
                    "key": "ratings",
                    "type": "rating_group",
                    "scale_labels": {"en": ["L", "M", "H"]},
                    "categories": [
                        {"key": "a", "labels": {"en": "A"}},
                        {"key": "b", "labels": {"en": "B"}},
                    ],
                },
            ],
        }
        with pytest.raises(ValidationError):
            validate_reflection_answers(schema, {"ratings": {"a": 1}})
