"""Tests for AssignmentGroup, AssignmentGroupMembership, and related 3.17 changes."""
from __future__ import annotations

import uuid
from datetime import date

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from bunk_logs.core.context import organization_context
from bunk_logs.core.models import AssignmentGroup
from bunk_logs.core.models import AssignmentGroupMembership
from bunk_logs.core.models import Organization
from bunk_logs.core.models import Person
from bunk_logs.core.models import Program
from bunk_logs.core.models import Reflection
from bunk_logs.core.models import ReflectionTemplate
from bunk_logs.core.validators.template_schema import validate_template_coherence

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def org(db):
    return Organization.objects.create(name="Test Org 317", slug="test-317")


@pytest.fixture
def org_b(db):
    return Organization.objects.create(name="Other Org 317", slug="other-317")


@pytest.fixture
def program(org):
    return Program.all_objects.create(
        organization=org,
        name="Test Org 317 Summer",
        slug="summer-317",
        program_type="summer_camp",
        start_date=date(2026, 6, 1),
        end_date=date(2026, 8, 31),
    )


@pytest.fixture
def program_b(org_b):
    return Program.all_objects.create(
        organization=org_b,
        name="Other Org 317 Summer",
        slug="summer-317-b",
        program_type="summer_camp",
        start_date=date(2026, 6, 1),
        end_date=date(2026, 8, 31),
    )


@pytest.fixture
def person_a(org):
    return Person.all_objects.create(organization=org, first_name="Alice", last_name="A")


@pytest.fixture
def person_b(org):
    return Person.all_objects.create(organization=org, first_name="Bob", last_name="B")


@pytest.fixture
def person_other_org(org_b):
    return Person.all_objects.create(organization=org_b, first_name="Xavier", last_name="X")


@pytest.fixture
def self_template(org):
    return ReflectionTemplate.all_objects.create(
        organization=org,
        name="Self Reflection 317",
        slug="self-317",
        cadence="weekly",
        schema={"fields": [{"key": "note", "type": "text", "prompts": {"en": "Note"}}]},
    )


@pytest.fixture
def group(org, program):
    return AssignmentGroup.all_objects.create(
        organization=org,
        program=program,
        name="Bunk Maple",
        slug="bunk-maple",
        group_type="bunk",
    )


@pytest.fixture
def group_b(org, program):
    return AssignmentGroup.all_objects.create(
        organization=org,
        program=program,
        name="Bunk Oak",
        slug="bunk-oak",
        group_type="bunk",
    )


# ---------------------------------------------------------------------------
# validate_template_coherence
# ---------------------------------------------------------------------------


class TestValidateTemplateCoherence:
    VALID_ROLES = frozenset({"counselor", "camper", "unit_head", "admin"})

    def test_self_mode_requires_scope_none(self):
        with pytest.raises(ValidationError, match="assignment_scope"):
            validate_template_coherence(
                subject_mode="self",
                assignment_scope="per_subject_in_group",
                assignment_group_types=["bunk"],
                author_role_filter=[],
                subject_role_filter=[],
                subject_visible=False,
                valid_roles=self.VALID_ROLES,
            )

    def test_group_mode_requires_per_group_scope(self):
        with pytest.raises(ValidationError, match="assignment_scope"):
            validate_template_coherence(
                subject_mode="group",
                assignment_scope="none",
                assignment_group_types=[],
                author_role_filter=[],
                subject_role_filter=[],
                subject_visible=False,
                valid_roles=self.VALID_ROLES,
            )

    def test_single_subject_requires_per_subject_scope(self):
        with pytest.raises(ValidationError, match="assignment_scope"):
            validate_template_coherence(
                subject_mode="single_subject",
                assignment_scope="per_group",
                assignment_group_types=["bunk"],
                author_role_filter=[],
                subject_role_filter=[],
                subject_visible=False,
                valid_roles=self.VALID_ROLES,
            )

    def test_scope_set_requires_group_types(self):
        with pytest.raises(ValidationError, match="assignment_group_types"):
            validate_template_coherence(
                subject_mode="single_subject",
                assignment_scope="per_subject_in_group",
                assignment_group_types=[],
                author_role_filter=[],
                subject_role_filter=[],
                subject_visible=False,
                valid_roles=self.VALID_ROLES,
            )

    def test_subject_visible_not_allowed_for_self(self):
        with pytest.raises(ValidationError, match="subject_visible"):
            validate_template_coherence(
                subject_mode="self",
                assignment_scope="none",
                assignment_group_types=[],
                author_role_filter=[],
                subject_role_filter=[],
                subject_visible=True,
                valid_roles=self.VALID_ROLES,
            )

    def test_invalid_author_role(self):
        with pytest.raises(ValidationError, match="author_role_filter"):
            validate_template_coherence(
                subject_mode="self",
                assignment_scope="none",
                assignment_group_types=[],
                author_role_filter=["not_a_real_role"],
                subject_role_filter=[],
                subject_visible=False,
                valid_roles=self.VALID_ROLES,
            )

    def test_invalid_subject_role(self):
        with pytest.raises(ValidationError, match="subject_role_filter"):
            validate_template_coherence(
                subject_mode="single_subject",
                assignment_scope="per_subject_in_group",
                assignment_group_types=["bunk"],
                author_role_filter=[],
                subject_role_filter=["ghost"],
                subject_visible=False,
                valid_roles=self.VALID_ROLES,
            )

    def test_valid_self_template_passes(self):
        # Should not raise
        validate_template_coherence(
            subject_mode="self",
            assignment_scope="none",
            assignment_group_types=[],
            author_role_filter=["counselor"],
            subject_role_filter=[],
            subject_visible=False,
            valid_roles=self.VALID_ROLES,
        )

    def test_valid_single_subject_template_passes(self):
        validate_template_coherence(
            subject_mode="single_subject",
            assignment_scope="per_subject_in_group",
            assignment_group_types=["bunk"],
            author_role_filter=["counselor"],
            subject_role_filter=["camper"],
            subject_visible=True,
            valid_roles=self.VALID_ROLES,
        )

    def test_valid_group_template_passes(self):
        validate_template_coherence(
            subject_mode="group",
            assignment_scope="per_group",
            assignment_group_types=["unit"],
            author_role_filter=["unit_head"],
            subject_role_filter=[],
            subject_visible=False,
            valid_roles=self.VALID_ROLES,
        )


class TestReflectionTemplateCoherenceViaClean:
    """Coherence rules enforced through ReflectionTemplate.clean()."""

    def test_existing_self_templates_still_valid(self, org, self_template):
        self_template.full_clean()

    def test_bunk_observation_template_valid(self, org):
        tpl = ReflectionTemplate.all_objects.create(
            organization=org,
            name="Bunk Observation",
            slug="bunk-obs",
            cadence="daily",
            subject_mode="single_subject",
            assignment_scope="per_subject_in_group",
            assignment_group_types=["bunk"],
            author_role_filter=["counselor"],
            subject_role_filter=["camper"],
            subject_visible=False,
            schema={"fields": [{"key": "note", "type": "text", "prompts": {"en": "Note"}}]},
        )
        tpl.full_clean()
        assert tpl.subject_mode == "single_subject"

    def test_incoherent_template_rejected_on_clean(self, org):
        tpl = ReflectionTemplate(
            organization=org,
            name="Bad Template",
            slug="bad-tpl",
            cadence="daily",
            subject_mode="self",
            assignment_scope="per_subject_in_group",
            assignment_group_types=["bunk"],
            schema={"fields": [{"key": "note", "type": "text", "prompts": {"en": "Note"}}]},
        )
        with pytest.raises(ValidationError):
            tpl.full_clean()


# ---------------------------------------------------------------------------
# AssignmentGroup
# ---------------------------------------------------------------------------


class TestAssignmentGroup:
    def test_create_basic_group(self, org, program, group):
        assert group.pk is not None
        assert group.group_type == "bunk"
        assert group.is_active is True

    def test_create_team_group(self, org, program):
        team = AssignmentGroup.all_objects.create(
            organization=org,
            program=program,
            name="Kitchen Staff",
            slug="kitchen-staff",
            group_type="team",
        )
        assert team.group_type == "team"
        assert "Team" in str(team)

    def test_unique_slug_per_program(self, org, program, group):
        with pytest.raises(IntegrityError):
            AssignmentGroup.all_objects.create(
                organization=org,
                program=program,
                name="Bunk Maple Duplicate",
                slug="bunk-maple",
                group_type="bunk",
            )

    def test_parent_child_hierarchy(self, org, program, group):
        unit = AssignmentGroup.all_objects.create(
            organization=org,
            program=program,
            name="Unit Alef",
            slug="unit-alef",
            group_type="unit",
        )
        group.parent = unit
        group.save()
        children = list(AssignmentGroup.all_objects.filter(parent=unit))
        assert group in children

    def test_get_descendants(self, org, program):
        division = AssignmentGroup.all_objects.create(
            organization=org, program=program, name="Division A", slug="div-a", group_type="division",
        )
        unit = AssignmentGroup.all_objects.create(
            organization=org, program=program, name="Unit A1", slug="unit-a1", group_type="unit",
            parent=division,
        )
        bunk = AssignmentGroup.all_objects.create(
            organization=org, program=program, name="Bunk X", slug="bunk-x", group_type="bunk",
            parent=unit,
        )
        descendants = division.get_descendants()
        pks = {d.pk for d in descendants}
        assert unit.pk in pks
        assert bunk.pk in pks

    def test_str_representation(self, group):
        assert "Bunk" in str(group)
        assert "Maple" in str(group)

    def test_inactive_children_excluded_from_get_descendants(self, org, program):
        parent = AssignmentGroup.all_objects.create(
            organization=org, program=program, name="Parent", slug="p-desc", group_type="unit",
        )
        child = AssignmentGroup.all_objects.create(
            organization=org, program=program, name="InactiveChild", slug="inactive-c",
            group_type="bunk", parent=parent, is_active=False,
        )
        descendants = parent.get_descendants()
        assert child not in descendants


# ---------------------------------------------------------------------------
# AssignmentGroupMembership
# ---------------------------------------------------------------------------


class TestAssignmentGroupMembership:
    def test_create_subject_membership(self, group, person_a):
        mem = AssignmentGroupMembership.all_objects.create(
            group=group, person=person_a, role_in_group="subject",
        )
        assert mem.pk is not None
        assert mem.role_in_group == "subject"

    def test_create_author_membership(self, group, person_b):
        mem = AssignmentGroupMembership.all_objects.create(
            group=group, person=person_b, role_in_group="author",
        )
        assert mem.role_in_group == "author"

    def test_person_can_be_subject_and_author_in_same_group(self, group, person_a):
        """The unique_together allows same person to hold both roles in same group (e.g. peer mentoring)."""
        AssignmentGroupMembership.all_objects.create(
            group=group, person=person_a, role_in_group="subject",
        )
        # This should NOT raise - different role_in_group is allowed
        mem2 = AssignmentGroupMembership.all_objects.create(
            group=group, person=person_a, role_in_group="author",
        )
        assert mem2.pk is not None

    def test_unique_constraint_same_role(self, group, person_a):
        AssignmentGroupMembership.all_objects.create(
            group=group, person=person_a, role_in_group="subject",
        )
        with pytest.raises(IntegrityError):
            AssignmentGroupMembership.all_objects.create(
                group=group, person=person_a, role_in_group="subject",
            )

    def test_person_in_multiple_groups(self, group, group_b, person_a):
        """A Person can be in multiple groups with different roles."""
        m1 = AssignmentGroupMembership.all_objects.create(
            group=group, person=person_a, role_in_group="subject",
        )
        m2 = AssignmentGroupMembership.all_objects.create(
            group=group_b, person=person_a, role_in_group="author",
        )
        assert m1.pk != m2.pk
        count = AssignmentGroupMembership.all_objects.filter(person=person_a).count()
        assert count == 2

    def test_str_representation(self, group, person_a):
        mem = AssignmentGroupMembership.all_objects.create(
            group=group, person=person_a, role_in_group="subject",
        )
        assert "Alice" in str(mem) or "Subject" in str(mem)


# ---------------------------------------------------------------------------
# Reflection model: subject/author/submission_id
# ---------------------------------------------------------------------------


class TestReflectionSubjectAuthor:
    def test_create_self_reflection_subject_equals_author(self, org, program, person_a, self_template):
        ref = Reflection.all_objects.create(
            organization=org,
            program=program,
            subject=person_a,
            author=person_a,
            template=self_template,
            period_start=date(2026, 7, 1),
            period_end=date(2026, 7, 7),
            answers={"note": "good week"},
            language="en",
        )
        assert ref.subject_id == person_a.pk
        assert ref.author_id == person_a.pk
        assert ref.subject_id == ref.author_id

    def test_reflection_with_different_author_and_subject(self, org, program, person_a, person_b, self_template):
        ref = Reflection.all_objects.create(
            organization=org,
            program=program,
            subject=person_b,
            author=person_a,
            template=self_template,
            period_start=date(2026, 7, 1),
            period_end=date(2026, 7, 7),
            answers={"note": "observed"},
            language="en",
        )
        assert ref.subject_id == person_b.pk
        assert ref.author_id == person_a.pk

    def test_submission_id_auto_generated(self, org, program, person_a, self_template):
        ref = Reflection.all_objects.create(
            organization=org,
            program=program,
            subject=person_a,
            template=self_template,
            period_start=date(2026, 7, 1),
            period_end=date(2026, 7, 7),
            answers={"note": "ok"},
            language="en",
        )
        assert ref.submission_id is not None
        assert isinstance(ref.submission_id, uuid.UUID)

    def test_multi_subject_submissions_share_submission_id(self, org, program, person_a, person_b, self_template):
        sid = uuid.uuid4()
        ref_a = Reflection.all_objects.create(
            organization=org, program=program, subject=person_a, author=person_a,
            template=self_template, period_start=date(2026, 7, 1), period_end=date(2026, 7, 7),
            answers={"note": "a"}, submission_id=sid,
        )
        ref_b = Reflection.all_objects.create(
            organization=org, program=program, subject=person_b, author=person_a,
            template=self_template, period_start=date(2026, 7, 1), period_end=date(2026, 7, 7),
            answers={"note": "b"}, submission_id=sid,
        )
        assert ref_a.submission_id == ref_b.submission_id == sid

    def test_subject_null_for_group_reflections(self, org, program, person_a, self_template, group):
        ref = Reflection.all_objects.create(
            organization=org, program=program,
            subject=None, subject_group=group, author=person_a,
            template=self_template, period_start=date(2026, 7, 1), period_end=date(2026, 7, 7),
            answers={"note": "whole bunk"}, language="en",
        )
        assert ref.subject is None
        assert ref.subject_group_id == group.pk

    def test_assignment_group_set(self, org, program, person_a, person_b, self_template, group):
        ref = Reflection.all_objects.create(
            organization=org, program=program,
            subject=person_b, author=person_a, assignment_group=group,
            template=self_template, period_start=date(2026, 7, 1), period_end=date(2026, 7, 7),
            answers={"note": "bunk ref"}, language="en",
        )
        assert ref.assignment_group_id == group.pk

    def test_filter_by_subject(self, org, program, person_a, person_b, self_template):
        Reflection.all_objects.create(
            organization=org, program=program, subject=person_a,
            template=self_template, period_start=date(2026, 7, 1), period_end=date(2026, 7, 7),
            answers={"note": "a"},
        )
        Reflection.all_objects.create(
            organization=org, program=program, subject=person_b,
            template=self_template, period_start=date(2026, 7, 1), period_end=date(2026, 7, 7),
            answers={"note": "b"},
        )
        qs = Reflection.all_objects.filter(subject=person_a)
        assert qs.count() == 1
        assert qs.first().subject_id == person_a.pk

    def test_filter_by_author(self, org, program, person_a, person_b, self_template):
        Reflection.all_objects.create(
            organization=org, program=program, subject=person_b, author=person_a,
            template=self_template, period_start=date(2026, 7, 1), period_end=date(2026, 7, 7),
            answers={"note": "authored by a"},
        )
        qs = Reflection.all_objects.filter(author=person_a)
        assert qs.count() == 1


# ---------------------------------------------------------------------------
# Data migration: existing reflections have author set
# ---------------------------------------------------------------------------


class TestDataMigrationBackfill:
    """Simulate the data migration by verifying new reflections have author populated."""

    def test_new_self_reflection_has_author(self, org, program, person_a, self_template):
        ref = Reflection.all_objects.create(
            organization=org, program=program, subject=person_a, author=person_a,
            template=self_template, period_start=date(2026, 7, 1), period_end=date(2026, 7, 7),
            answers={"note": "backfill test"},
        )
        assert ref.author_id == ref.subject_id


# ---------------------------------------------------------------------------
# Cross-org isolation
# ---------------------------------------------------------------------------


class TestCrossOrgIsolation:
    def test_assignment_group_org_scoped(self, org, org_b, program, program_b):
        grp_a = AssignmentGroup.all_objects.create(
            organization=org, program=program, name="Bunk A", slug="bunk-a-iso", group_type="bunk",
        )
        grp_b = AssignmentGroup.all_objects.create(
            organization=org_b, program=program_b, name="Bunk B", slug="bunk-b-iso", group_type="bunk",
        )
        with organization_context(org):
            qs = AssignmentGroup.objects.all()
            pks = list(qs.values_list("pk", flat=True))
            assert grp_a.pk in pks
            assert grp_b.pk not in pks
