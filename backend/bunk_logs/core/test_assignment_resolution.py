"""Tests for ``bunk_logs.core.assignment_resolution`` (Step 7_21).

Covers
------
* ``resolve_template_for`` matches an active TemplateAssignment by
  (subject_mode, cadence, role).
* Returns ``None`` when no assignment is active.
* Org-shadow ordering: org-scoped template wins over global.
* ``cadence_override`` on the assignment overrides ``template.cadence``.
* ``assignment_group``-targeted assignment is preferred when supplied.
* ``active_assignments_for`` filters by audience membership.
* ``require_required=True`` excludes optional assignments; the optional
  list returns them.
"""

from __future__ import annotations

from datetime import date
from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model

from bunk_logs.core.assignment_resolution import active_assignments_for
from bunk_logs.core.assignment_resolution import list_optional_assignments_for
from bunk_logs.core.assignment_resolution import list_required_assignments_for
from bunk_logs.core.assignment_resolution import resolve_template_for
from bunk_logs.core.models import AssignmentGroup
from bunk_logs.core.models import AssignmentGroupMembership
from bunk_logs.core.models import Membership
from bunk_logs.core.models import Organization
from bunk_logs.core.models import Person
from bunk_logs.core.models import Program
from bunk_logs.core.models import ReflectionTemplate
from bunk_logs.core.models import TemplateAssignment

User = get_user_model()
pytestmark = pytest.mark.django_db

TODAY = date(2026, 6, 15)
SCHEMA = {"fields": [{"key": "note", "type": "textarea", "required": False, "prompts": {"en": "Notes"}}]}


@pytest.fixture
def org():
    return Organization.objects.create(name="Resolver Camp", slug="resolver-camp")


@pytest.fixture
def other_org():
    return Organization.objects.create(name="Other Camp", slug="other-camp")


@pytest.fixture
def program(org):
    return Program.all_objects.create(
        organization=org, name=f"{org.name} Summer 2026", slug="summer-2026",
        program_type="summer_camp",
        start_date=date(2026, 6, 1), end_date=date(2026, 8, 31),
    )


@pytest.fixture
def viewer(org, program):
    user = User.objects.create_user(email="v@resolver.test", password="pw")
    person = Person.all_objects.create(
        organization=org, first_name="View", last_name="Er", user=user,
    )
    Membership.all_objects.create(
        program=program, person=person, role="counselor", is_active=True,
    )
    return person


@pytest.fixture
def lt_membership(program, org):
    user = User.objects.create_user(email="lt@resolver.test", password="pw")
    person = Person.all_objects.create(
        organization=org, first_name="LT", last_name="Lead", user=user,
    )
    return Membership.all_objects.create(
        program=program, person=person, role="leadership_team", is_active=True,
    )


@pytest.fixture
def org_template(org):
    return ReflectionTemplate.all_objects.create(
        organization=org, name="Counselor Self", slug="counselor-self-org",
        cadence="daily", subject_mode="self", schema=SCHEMA, languages=["en"],
        is_active=True, role="counselor", author_role_filter=["counselor"],
    )


@pytest.fixture
def global_template():
    return ReflectionTemplate.all_objects.create(
        organization=None, name="Counselor Self Global", slug="counselor-self-global",
        cadence="daily", subject_mode="self", schema=SCHEMA, languages=["en"],
        is_active=True, role="counselor", author_role_filter=["counselor"],
    )


def _active_role_assignment(
    *, organization, program, template, role, lt_membership,
    start=None, end=None, is_required=True,
):
    return TemplateAssignment.all_objects.create(
        organization=organization, program=program, template=template,
        target_type=TemplateAssignment.TargetType.ROLE,
        target_payload={"role": role},
        start_date=start or (TODAY - timedelta(days=1)),
        end_date=end,
        status=TemplateAssignment.Status.ACTIVE,
        created_by=lt_membership,
        is_required=is_required,
    )


class TestResolveTemplateFor:
    def test_returns_none_when_no_assignment(self, org, program, org_template):
        result = resolve_template_for(
            organization=org, program=program, as_of=TODAY,
            role="counselor", subject_mode="self", cadence="daily",
        )
        assert result is None

    def test_matches_active_role_assignment(
        self, org, program, org_template, lt_membership,
    ):
        _active_role_assignment(
            organization=org, program=program, template=org_template,
            role="counselor", lt_membership=lt_membership,
        )
        result = resolve_template_for(
            organization=org, program=program, as_of=TODAY,
            role="counselor", subject_mode="self", cadence="daily",
        )
        assert result == org_template

    def test_org_shadows_global(
        self, org, program, org_template, global_template, lt_membership,
    ):
        _active_role_assignment(
            organization=org, program=program, template=global_template,
            role="counselor", lt_membership=lt_membership,
        )
        _active_role_assignment(
            organization=org, program=program, template=org_template,
            role="counselor", lt_membership=lt_membership,
        )
        result = resolve_template_for(
            organization=org, program=program, as_of=TODAY,
            role="counselor", subject_mode="self", cadence="daily",
        )
        assert result == org_template

    def test_excludes_assignment_outside_window(
        self, org, program, org_template, lt_membership,
    ):
        _active_role_assignment(
            organization=org, program=program, template=org_template,
            role="counselor", lt_membership=lt_membership,
            start=TODAY - timedelta(days=30),
            end=TODAY - timedelta(days=1),
        )
        result = resolve_template_for(
            organization=org, program=program, as_of=TODAY,
            role="counselor", subject_mode="self", cadence="daily",
        )
        assert result is None

    def test_resolves_ended_assignment_on_historical_date(
        self, org, program, org_template, lt_membership,
    ):
        """Ended assignments still resolve when ``as_of`` falls in their window."""
        historical = date(2025, 7, 17)
        TemplateAssignment.all_objects.create(
            organization=org, program=program, template=org_template,
            target_type=TemplateAssignment.TargetType.ROLE,
            target_payload={"role": "counselor"},
            start_date=date(2025, 6, 28),
            end_date=date(2025, 7, 26),
            status=TemplateAssignment.Status.ENDED,
            created_by=lt_membership,
        )
        result = resolve_template_for(
            organization=org, program=program, as_of=historical,
            role="counselor", subject_mode="self", cadence="daily",
        )
        assert result == org_template

    def test_excludes_other_org(
        self, org, other_org, program, org_template, lt_membership,
    ):
        _active_role_assignment(
            organization=org, program=program, template=org_template,
            role="counselor", lt_membership=lt_membership,
        )
        result = resolve_template_for(
            organization=other_org, program=program, as_of=TODAY,
            role="counselor", subject_mode="self", cadence="daily",
        )
        assert result is None

    def test_cadence_override_wins(
        self, org, program, org_template, lt_membership,
    ):
        assignment = _active_role_assignment(
            organization=org, program=program, template=org_template,
            role="counselor", lt_membership=lt_membership,
        )
        assignment.cadence_override = "weekly"
        assignment.save(update_fields=["cadence_override"])
        # daily resolution should now miss; weekly should hit.
        assert resolve_template_for(
            organization=org, program=program, as_of=TODAY,
            role="counselor", subject_mode="self", cadence="daily",
        ) is None
        assert resolve_template_for(
            organization=org, program=program, as_of=TODAY,
            role="counselor", subject_mode="self", cadence="weekly",
        ) == org_template

    def test_subject_mode_must_match(
        self, org, program, org_template, lt_membership,
    ):
        _active_role_assignment(
            organization=org, program=program, template=org_template,
            role="counselor", lt_membership=lt_membership,
        )
        result = resolve_template_for(
            organization=org, program=program, as_of=TODAY,
            role="counselor", subject_mode="single_subject", cadence="daily",
        )
        assert result is None

    def test_role_matches_author_role_filter(
        self, org, program, lt_membership,
    ):
        template = ReflectionTemplate.all_objects.create(
            organization=org, name="Camper Reflection", slug="camper-reflection",
            cadence="daily", subject_mode="single_subject",
            assignment_group_types=["bunk"],
            schema=SCHEMA, languages=["en"], is_active=True,
            author_role_filter=["counselor", "junior_counselor"],
        )
        _active_role_assignment(
            organization=org, program=program, template=template,
            role="counselor", lt_membership=lt_membership,
        )
        assert resolve_template_for(
            organization=org, program=program, as_of=TODAY,
            role="junior_counselor", subject_mode="single_subject", cadence="daily",
        ) == template

    def test_assignment_group_specific_preferred(
        self, org, program, lt_membership,
    ):
        template = ReflectionTemplate.all_objects.create(
            organization=org, name="Camper Reflection", slug="camper-reflection",
            cadence="daily", subject_mode="single_subject",
            assignment_group_types=["bunk"],
            schema=SCHEMA, languages=["en"], is_active=True,
            author_role_filter=["counselor"],
        )
        bunk = AssignmentGroup.objects.create(
            organization=org, program=program, name="Bunk Pine", slug="bunk-pine",
            group_type="bunk", is_active=True,
        )
        other_bunk = AssignmentGroup.objects.create(
            organization=org, program=program, name="Bunk Oak", slug="bunk-oak",
            group_type="bunk", is_active=True,
        )
        # Program-wide role assignment.
        _active_role_assignment(
            organization=org, program=program, template=template,
            role="counselor", lt_membership=lt_membership,
        )
        # Group-specific assignment for the OTHER bunk.
        TemplateAssignment.all_objects.create(
            organization=org, program=program, template=template,
            target_type=TemplateAssignment.TargetType.ASSIGNMENT_GROUP,
            target_payload={}, assignment_group=other_bunk,
            start_date=TODAY - timedelta(days=1),
            status=TemplateAssignment.Status.ACTIVE,
            created_by=lt_membership,
        )
        # Resolving for ``bunk`` (no group-specific row) falls back to
        # the program-wide role assignment.
        result_bunk = resolve_template_for(
            organization=org, program=program, as_of=TODAY,
            role="counselor", subject_mode="single_subject", cadence="daily",
            assignment_group=bunk,
        )
        assert result_bunk == template
        # Resolving for ``other_bunk`` is also fine — both rows match,
        # the group-specific one wins by ``_group_priority`` ordering.
        result_other = resolve_template_for(
            organization=org, program=program, as_of=TODAY,
            role="counselor", subject_mode="single_subject", cadence="daily",
            assignment_group=other_bunk,
        )
        assert result_other == template


class TestActiveAssignmentsFor:
    def test_role_targeted_audience(
        self, org, program, viewer, org_template, lt_membership,
    ):
        _active_role_assignment(
            organization=org, program=program, template=org_template,
            role="counselor", lt_membership=lt_membership,
        )
        out = active_assignments_for(
            viewer=viewer, organization=org, program=program,
            as_of=TODAY, target_role="counselor",
        )
        assert len(out) == 1

    def test_role_targeted_excludes_other_role(
        self, org, program, viewer, org_template, lt_membership,
    ):
        # Viewer is a counselor; assignment targets kitchen_staff.
        ks_template = ReflectionTemplate.all_objects.create(
            organization=org, name="Kitchen", slug="ks-self",
            cadence="daily", subject_mode="self", schema=SCHEMA,
            languages=["en"], is_active=True, role="kitchen_staff",
            author_role_filter=["kitchen_staff"],
        )
        _active_role_assignment(
            organization=org, program=program, template=ks_template,
            role="kitchen_staff", lt_membership=lt_membership,
        )
        out = active_assignments_for(
            viewer=viewer, organization=org, program=program,
            as_of=TODAY, target_role="kitchen_staff",
        )
        assert out == []

    def test_required_vs_optional(
        self, org, program, viewer, org_template, lt_membership,
    ):
        _active_role_assignment(
            organization=org, program=program, template=org_template,
            role="counselor", lt_membership=lt_membership, is_required=False,
        )
        required = list_required_assignments_for(
            viewer, organization=org, program=program, as_of=TODAY,
        )
        optional = list_optional_assignments_for(
            viewer, organization=org, program=program, as_of=TODAY,
        )
        assert required == []
        assert len(optional) == 1

    def test_individuals_audience(
        self, org, program, viewer, org_template, lt_membership,
    ):
        my_membership = Membership.all_objects.get(person=viewer)
        TemplateAssignment.all_objects.create(
            organization=org, program=program, template=org_template,
            target_type=TemplateAssignment.TargetType.INDIVIDUALS,
            target_payload={"membership_ids": [my_membership.id]},
            start_date=TODAY - timedelta(days=1),
            status=TemplateAssignment.Status.ACTIVE,
            created_by=lt_membership,
        )
        out = active_assignments_for(
            viewer=viewer, organization=org, program=program, as_of=TODAY,
        )
        assert len(out) == 1

    def test_assignment_group_audience(
        self, org, program, viewer, lt_membership,
    ):
        template = ReflectionTemplate.all_objects.create(
            organization=org, name="Bunk Reflection", slug="bunk-reflection",
            cadence="daily", subject_mode="single_subject",
            assignment_group_types=["bunk"],
            schema=SCHEMA, languages=["en"], is_active=True,
            author_role_filter=["counselor"],
        )
        bunk = AssignmentGroup.objects.create(
            organization=org, program=program, name="Bunk Maple", slug="bunk-maple",
            group_type="bunk", is_active=True,
        )
        AssignmentGroupMembership.objects.create(
            group=bunk, person=viewer, role_in_group="author", is_active=True,
        )
        TemplateAssignment.all_objects.create(
            organization=org, program=program, template=template,
            target_type=TemplateAssignment.TargetType.ASSIGNMENT_GROUP,
            target_payload={}, assignment_group=bunk,
            start_date=TODAY - timedelta(days=1),
            status=TemplateAssignment.Status.ACTIVE,
            created_by=lt_membership,
        )
        out = active_assignments_for(
            viewer=viewer, organization=org, program=program, as_of=TODAY,
        )
        assert len(out) == 1
