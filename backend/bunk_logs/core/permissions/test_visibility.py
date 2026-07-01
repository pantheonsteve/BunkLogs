"""Tests for ``core.permissions.visibility.reflections_visible_to``."""
from __future__ import annotations

from datetime import date

import pytest
from django.contrib.auth import get_user_model
from django.db import connection
from django.test.utils import CaptureQueriesContext

from bunk_logs.core.context import organization_context
from bunk_logs.core.models import AssignmentGroup
from bunk_logs.core.models import AssignmentGroupMembership
from bunk_logs.core.models import Membership
from bunk_logs.core.models import Organization
from bunk_logs.core.models import Person
from bunk_logs.core.models import Program
from bunk_logs.core.models import Reflection
from bunk_logs.core.models import ReflectionTemplate
from bunk_logs.core.models import Supervision
from bunk_logs.core.permissions.visibility import has_supervisor_role
from bunk_logs.core.permissions.visibility import is_org_admin
from bunk_logs.core.permissions.visibility import reflections_visible_to

User = get_user_model()

pytestmark = pytest.mark.django_db


# ── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture
def org_a(db):
    return Organization.objects.create(name="Vis A", slug="vis-a")


@pytest.fixture
def org_b(db):
    return Organization.objects.create(name="Vis B", slug="vis-b")


@pytest.fixture
def program_a(org_a):
    return Program.all_objects.create(
        organization=org_a,
        name="Vis A Summer",
        slug="vis-a-prog",
        program_type="summer_camp",
        start_date=date(2026, 6, 1),
        end_date=date(2026, 8, 31),
    )


@pytest.fixture
def program_b(org_b):
    return Program.all_objects.create(
        organization=org_b,
        name="Vis B Summer",
        slug="vis-b-prog",
        program_type="summer_camp",
        start_date=date(2026, 6, 1),
        end_date=date(2026, 8, 31),
    )


def _make_user(email: str) -> User:
    return User.objects.create_user(email=email, password="pw")


def _make_person(org, first: str, last: str, user=None) -> Person:
    return Person.all_objects.create(
        organization=org, first_name=first, last_name=last, user=user,
    )


def _make_template(
    org: Organization,
    *,
    slug: str = "tpl",
    role: str | None = None,
    subject_visible: bool = False,
    subject_mode: str = "self",
    assignment_scope: str = "none",
) -> ReflectionTemplate:
    kwargs: dict = {
        "organization": org,
        "name": slug,
        "slug": slug,
        "cadence": "weekly",
        "subject_mode": subject_mode,
        "assignment_scope": assignment_scope,
        "subject_visible": subject_visible,
        "schema": {"fields": [{"key": "n", "type": "text", "prompts": {"en": "n"}}]},
    }
    if role is not None:
        kwargs["role"] = role
    if assignment_scope != "none":
        kwargs["assignment_group_types"] = ["bunk"]
    return ReflectionTemplate.all_objects.create(**kwargs)


def _make_reflection(
    org, program, template, *, subject=None, author=None, assignment_group=None,
    team_visibility=Reflection.TeamVisibility.TEAM,
) -> Reflection:
    return Reflection.all_objects.create(
        organization=org,
        program=program,
        template=template,
        subject=subject,
        author=author,
        assignment_group=assignment_group,
        period_start=date(2026, 6, 1),
        period_end=date(2026, 6, 7),
        answers={"n": "x"},
        language="en",
        team_visibility=team_visibility,
    )


# ── Path 1: anonymous & no-person users ──────────────────────────────────────


class TestUnauthenticatedAndNoPerson:
    def test_unauthenticated_user_sees_nothing(self, org_a, program_a):
        tpl = _make_template(org_a)
        _make_reflection(org_a, program_a, tpl)
        with organization_context(org_a):
            assert reflections_visible_to(None).count() == 0

    def test_user_without_person_profile_sees_nothing(self, org_a, program_a):
        user = _make_user("noperson@example.com")
        tpl = _make_template(org_a)
        _make_reflection(org_a, program_a, tpl)
        with organization_context(org_a):
            assert reflections_visible_to(user).count() == 0

    def test_superuser_without_person_still_sees_org(self, org_a, program_a):
        admin = User.objects.create_superuser(email="su@example.com", password="pw")
        tpl = _make_template(org_a)
        _make_reflection(org_a, program_a, tpl)
        with organization_context(org_a):
            assert reflections_visible_to(admin).count() == 1


# ── Super Admin consistency (3.25): is_staff alone is enough ────────────────


class TestSuperAdminConsistency:
    """``is_staff=True`` (without ``is_superuser``) must behave like a superuser
    for every bypass-all gate in the new RBAC code. See prompt 3_25 and the
    ``is_super_admin`` helper in ``bunk_logs.core.permissions.super_admin``.
    """

    @pytest.fixture
    def staff_user(self):
        return User.objects.create_user(
            email="staff@example.com", password="pw", is_staff=True,
        )

    def test_is_staff_user_without_person_sees_full_org(
        self, staff_user, org_a, program_a,
    ):
        tpl = _make_template(org_a)
        _make_reflection(org_a, program_a, tpl)
        assert staff_user.is_superuser is False
        with organization_context(org_a):
            assert reflections_visible_to(staff_user).count() == 1

    def test_is_staff_user_sees_all_org_reflections_regardless_of_author(
        self, staff_user, org_a, program_a,
    ):
        # Reflection authored by someone unrelated to the staff user.
        other = _make_person(org_a, "Other", "Person")
        tpl = _make_template(org_a)
        _make_reflection(org_a, program_a, tpl, subject=other, author=other)
        with organization_context(org_a):
            assert reflections_visible_to(staff_user).count() == 1

    def test_is_staff_user_is_treated_as_org_admin(self, staff_user):
        assert is_org_admin(staff_user) is True

    def test_is_staff_user_has_supervisor_role(self, staff_user):
        assert has_supervisor_role(staff_user) is True

    def test_is_staff_user_does_not_see_other_org_data(
        self, staff_user, org_a, org_b, program_b,
    ):
        """Staff bypass is org-scoped: org context determines which org's data shows."""
        b_person = _make_person(org_b, "B", "Person")
        tpl_b = _make_template(org_b, slug="tpl-b")
        _make_reflection(org_b, program_b, tpl_b, subject=b_person, author=b_person)
        with organization_context(org_a):
            assert reflections_visible_to(staff_user).count() == 0


# ── Path 2: org admin sees everything in own org, nothing in other org ───────


class TestAdmin:
    def test_org_admin_sees_all_org_reflections(self, org_a, program_a):
        admin_user = _make_user("admin@a.com")
        admin_person = _make_person(org_a, "Ad", "Min", admin_user)
        Membership.all_objects.create(
            program=program_a, person=admin_person, role="admin", is_active=True,
        )
        other = _make_person(org_a, "Other", "Person")
        tpl = _make_template(org_a)
        _make_reflection(org_a, program_a, tpl, subject=other, author=other)
        _make_reflection(org_a, program_a, tpl, subject=admin_person, author=admin_person)
        with organization_context(org_a):
            assert reflections_visible_to(admin_user).count() == 2
        assert is_org_admin(admin_user)
        assert has_supervisor_role(admin_user)

    def test_admin_in_org_a_does_not_see_org_b_data(
        self, org_a, org_b, program_a, program_b,
    ):
        admin_user = _make_user("admin@a.com")
        admin_person = _make_person(org_a, "Ad", "Min", admin_user)
        Membership.all_objects.create(
            program=program_a, person=admin_person, role="admin", is_active=True,
        )
        b_person = _make_person(org_b, "B", "Person")
        tpl_b = _make_template(org_b, slug="tpl-b")
        _make_reflection(org_b, program_b, tpl_b, subject=b_person, author=b_person)
        with organization_context(org_a):
            assert reflections_visible_to(admin_user).count() == 0


# ── Path 3: author sees own reflections ──────────────────────────────────────


class TestAuthorPath:
    def test_author_sees_own(self, org_a, program_a):
        u = _make_user("a@a.com")
        person = _make_person(org_a, "Au", "Thor", u)
        Membership.all_objects.create(
            program=program_a, person=person, role="counselor", is_active=True,
        )
        tpl = _make_template(org_a)
        target = _make_person(org_a, "Tar", "Get")
        # Author authored a reflection about someone else
        _make_reflection(org_a, program_a, tpl, subject=target, author=person)
        # Unrelated reflection by someone else, not visible
        other = _make_person(org_a, "Some", "OneElse")
        _make_reflection(org_a, program_a, tpl, subject=target, author=other)
        with organization_context(org_a):
            visible = reflections_visible_to(u)
            assert visible.count() == 1
            assert visible.first().author_id == person.id


# ── Path 4: subject sees own only when subject_visible=True ──────────────────


class TestSubjectVisible:
    def test_subject_visible_true_lets_subject_see_own(self, org_a, program_a):
        u = _make_user("camper@a.com")
        camper = _make_person(org_a, "Cam", "Per", u)
        Membership.all_objects.create(
            program=program_a, person=camper, role="camper", is_active=True,
        )
        author = _make_person(org_a, "Coun", "Selor")
        tpl = _make_template(
            org_a,
            slug="tpl-visible",
            subject_visible=True,
            subject_mode="single_subject",
            assignment_scope="per_subject_in_group",
        )
        _make_reflection(org_a, program_a, tpl, subject=camper, author=author)
        with organization_context(org_a):
            assert reflections_visible_to(u).count() == 1

    def test_subject_visible_false_hides_from_subject(self, org_a, program_a):
        u = _make_user("camper@a.com")
        camper = _make_person(org_a, "Cam", "Per", u)
        Membership.all_objects.create(
            program=program_a, person=camper, role="camper", is_active=True,
        )
        author = _make_person(org_a, "Coun", "Selor")
        tpl = _make_template(
            org_a,
            slug="tpl-hidden",
            subject_visible=False,
            subject_mode="single_subject",
            assignment_scope="per_subject_in_group",
        )
        _make_reflection(org_a, program_a, tpl, subject=camper, author=author)
        with organization_context(org_a):
            assert reflections_visible_to(u).count() == 0


# ── Path 5: assignment-group authors and descendants (the prompt's regression) ─


class TestAssignmentGroupVisibility:
    def test_direct_group_author_sees_group_reflections(self, org_a, program_a):
        u = _make_user("counselor@a.com")
        counselor = _make_person(org_a, "Co", "Un", u)
        Membership.all_objects.create(
            program=program_a, person=counselor, role="counselor", is_active=True,
        )
        bunk = AssignmentGroup.all_objects.create(
            organization=org_a, program=program_a, name="Bunk Maple",
            slug="bunk-maple", group_type="bunk",
        )
        AssignmentGroupMembership.all_objects.create(
            group=bunk, person=counselor, role_in_group="author", is_active=True,
        )
        camper = _make_person(org_a, "Cam", "Per")
        tpl = _make_template(
            org_a,
            slug="bunk-obs",
            subject_mode="single_subject",
            assignment_scope="per_subject_in_group",
        )
        _make_reflection(
            org_a, program_a, tpl, subject=camper, author=counselor, assignment_group=bunk,
        )
        with organization_context(org_a):
            assert reflections_visible_to(u).count() == 1

    def test_unit_head_sees_descendant_bunks_even_without_being_direct_author(
        self, org_a, program_a,
    ):
        """The signature regression case from the prompt."""
        u = _make_user("unithead@a.com")
        unit_head = _make_person(org_a, "Un", "Head", u)
        Membership.all_objects.create(
            program=program_a, person=unit_head, role="unit_head", is_active=True,
        )
        unit = AssignmentGroup.all_objects.create(
            organization=org_a, program=program_a, name="Junior Unit",
            slug="junior-unit", group_type="unit",
        )
        bunk_maple = AssignmentGroup.all_objects.create(
            organization=org_a, program=program_a, name="Bunk Maple",
            slug="bunk-maple", group_type="bunk", parent=unit,
        )
        bunk_oak = AssignmentGroup.all_objects.create(
            organization=org_a, program=program_a, name="Bunk Oak",
            slug="bunk-oak", group_type="bunk", parent=unit,
        )
        # Unit head is an author of the UNIT, not of the bunks directly.
        AssignmentGroupMembership.all_objects.create(
            group=unit, person=unit_head, role_in_group="author", is_active=True,
        )
        counselor = _make_person(org_a, "Co", "Un")
        camper = _make_person(org_a, "Cam", "Per")
        tpl = _make_template(
            org_a,
            slug="bunk-obs",
            subject_mode="single_subject",
            assignment_scope="per_subject_in_group",
        )
        _make_reflection(
            org_a, program_a, tpl,
            subject=camper, author=counselor, assignment_group=bunk_maple,
        )
        _make_reflection(
            org_a, program_a, tpl,
            subject=camper, author=counselor, assignment_group=bunk_oak,
        )
        with organization_context(org_a):
            assert reflections_visible_to(u).count() == 2
        assert has_supervisor_role(u)

    def test_grandchild_descendants_also_visible(self, org_a, program_a):
        u = _make_user("director@a.com")
        director = _make_person(org_a, "Di", "Rector", u)
        Membership.all_objects.create(
            program=program_a, person=director, role="leadership_team", is_active=True,
            metadata={},
        )
        division = AssignmentGroup.all_objects.create(
            organization=org_a, program=program_a, name="Division",
            slug="div", group_type="division",
        )
        unit = AssignmentGroup.all_objects.create(
            organization=org_a, program=program_a, name="Unit",
            slug="unit", group_type="unit", parent=division,
        )
        bunk = AssignmentGroup.all_objects.create(
            organization=org_a, program=program_a, name="Bunk",
            slug="bunk", group_type="bunk", parent=unit,
        )
        AssignmentGroupMembership.all_objects.create(
            group=division, person=director, role_in_group="author", is_active=True,
        )
        author = _make_person(org_a, "Au", "Thor")
        camper = _make_person(org_a, "Cam", "Per")
        tpl = _make_template(
            org_a, slug="bunk-obs",
            subject_mode="single_subject", assignment_scope="per_subject_in_group",
        )
        _make_reflection(
            org_a, program_a, tpl,
            subject=camper, author=author, assignment_group=bunk,
        )
        with organization_context(org_a):
            # Director sees through division -> unit -> bunk
            assert reflections_visible_to(u).count() == 1

    def test_inactive_descendant_not_traversed(self, org_a, program_a):
        u = _make_user("uh@a.com")
        uh = _make_person(org_a, "U", "H", u)
        Membership.all_objects.create(
            program=program_a, person=uh, role="unit_head", is_active=True,
        )
        unit = AssignmentGroup.all_objects.create(
            organization=org_a, program=program_a, name="U", slug="u",
            group_type="unit",
        )
        inactive_bunk = AssignmentGroup.all_objects.create(
            organization=org_a, program=program_a, name="B", slug="b",
            group_type="bunk", parent=unit, is_active=False,
        )
        AssignmentGroupMembership.all_objects.create(
            group=unit, person=uh, role_in_group="author", is_active=True,
        )
        camper = _make_person(org_a, "C", "P")
        author = _make_person(org_a, "A", "U")
        tpl = _make_template(
            org_a, slug="bunk-obs",
            subject_mode="single_subject", assignment_scope="per_subject_in_group",
        )
        _make_reflection(
            org_a, program_a, tpl,
            subject=camper, author=author, assignment_group=inactive_bunk,
        )
        with organization_context(org_a):
            # Inactive child is not traversed; unit head sees nothing.
            assert reflections_visible_to(u).count() == 0


# ── Path 6: leadership team (unit-slug-scoped) ───────────────────────────────


class TestLeadershipScope:
    def test_unrestricted_leadership_sees_all_program_reflections(
        self, org_a, program_a,
    ):
        u = _make_user("lead@a.com")
        lead = _make_person(org_a, "Le", "Ad", u)
        Membership.all_objects.create(
            program=program_a, person=lead, role="leadership_team", is_active=True,
            metadata={},
        )
        cns = _make_person(org_a, "Cns", "Or")
        Membership.all_objects.create(
            program=program_a, person=cns, role="counselor", is_active=True,
            metadata={"unit_slug": "tsofim"},
        )
        tpl = _make_template(org_a, role="counselor")
        _make_reflection(org_a, program_a, tpl, subject=cns, author=cns)
        with organization_context(org_a):
            assert reflections_visible_to(u).count() == 1

    def test_unit_scoped_leadership_only_sees_assigned_units(self, org_a, program_a):
        u = _make_user("lead@a.com")
        lead = _make_person(org_a, "Le", "Ad", u)
        Membership.all_objects.create(
            program=program_a, person=lead, role="leadership_team", is_active=True,
            metadata={"assigned_unit_slugs": ["tsofim"]},
        )
        in_unit = _make_person(org_a, "In", "Unit")
        Membership.all_objects.create(
            program=program_a, person=in_unit, role="counselor", is_active=True,
            metadata={"unit_slug": "tsofim"},
        )
        not_in_unit = _make_person(org_a, "Not", "Unit")
        Membership.all_objects.create(
            program=program_a, person=not_in_unit, role="counselor", is_active=True,
            metadata={"unit_slug": "other"},
        )
        tpl = _make_template(org_a, role="counselor")
        _make_reflection(org_a, program_a, tpl, subject=in_unit, author=in_unit)
        _make_reflection(org_a, program_a, tpl, subject=not_in_unit, author=not_in_unit)
        with organization_context(org_a):
            visible = reflections_visible_to(u)
            assert visible.count() == 1
            assert visible.first().subject_id == in_unit.id


# ── Path 7: wellness scope ───────────────────────────────────────────────────


class TestWellnessScope:
    def test_wellness_user_sees_wellness_template_reflections(self, org_a, program_a):
        u = _make_user("hc@a.com")
        hc = _make_person(org_a, "Hc", "User", u)
        Membership.all_objects.create(
            program=program_a, person=hc, role="health_center", is_active=True,
        )
        wellness_tpl = _make_template(org_a, slug="wellness-tpl", role="health_center")
        kitchen_tpl = _make_template(org_a, slug="kitchen-tpl", role="kitchen_staff")
        cns = _make_person(org_a, "Cns", "Or")
        _make_reflection(org_a, program_a, wellness_tpl, subject=cns, author=cns)
        _make_reflection(org_a, program_a, kitchen_tpl, subject=cns, author=cns)
        with organization_context(org_a):
            visible = reflections_visible_to(u)
            ids = list(visible.values_list("template__role", flat=True))
            assert "health_center" in ids
            assert "kitchen_staff" not in ids


# ── Path 7b: camper_care is a unit-scoped supervisor (3.21) ─────────────────


class TestCamperCareScope:
    """Step 3.21 moves camper_care from domain_specialist -> supervisor.

    Visibility flows through ``assigned_unit_slugs`` metadata and/or the
    ``Supervision`` caseload (bunks + expanded units). Camper Care no longer
    gets program-wide visibility when both are empty.
    """

    def test_camper_care_without_caseload_sees_nothing_extra(
        self, org_a, program_a,
    ):
        u = _make_user("cc@a.com")
        cc = _make_person(org_a, "Cc", "User", u)
        Membership.all_objects.create(
            program=program_a, person=cc, role="camper_care", is_active=True,
            metadata={},
        )
        author = _make_person(org_a, "Au", "Thor")
        subject = _make_person(org_a, "Sub", "Ject")
        tpl = _make_template(org_a, role="counselor")
        _make_reflection(org_a, program_a, tpl, subject=subject, author=author)
        with organization_context(org_a):
            assert reflections_visible_to(u).count() == 0

    def test_camper_care_caseload_supervision_limits_to_assigned_bunks(
        self, org_a, program_a,
    ):
        u = _make_user("cc@a.com")
        cc = _make_person(org_a, "Cc", "User", u)
        cc_membership = Membership.all_objects.create(
            program=program_a, person=cc, role="camper_care", is_active=True,
            metadata={},
        )
        unit = AssignmentGroup.all_objects.create(
            organization=org_a, program=program_a, name="Unit",
            slug="cc-unit", group_type="unit",
        )
        on_caseload = AssignmentGroup.all_objects.create(
            organization=org_a, program=program_a, name="Bunk A",
            slug="cc-bunk-a", group_type="bunk", parent=unit,
        )
        off_caseload = AssignmentGroup.all_objects.create(
            organization=org_a, program=program_a, name="Bunk B",
            slug="cc-bunk-b", group_type="bunk", parent=unit,
        )
        Supervision.all_objects.create(
            supervisor_membership=cc_membership,
            target_type="bunk",
            target_bunk=on_caseload,
            start_date=date(2026, 1, 1),
        )
        camper_on = _make_person(org_a, "On", "Caseload")
        camper_off = _make_person(org_a, "Off", "Caseload")
        AssignmentGroupMembership.all_objects.create(
            group=on_caseload, person=camper_on, role_in_group="subject", is_active=True,
        )
        AssignmentGroupMembership.all_objects.create(
            group=off_caseload, person=camper_off, role_in_group="subject", is_active=True,
        )
        counselor = _make_person(org_a, "Co", "Un")
        tpl = _make_template(
            org_a, slug="bunk-obs-cc",
            role="counselor",
            subject_mode="single_subject",
            assignment_scope="per_subject_in_group",
        )
        _make_reflection(
            org_a, program_a, tpl,
            subject=camper_on, author=counselor, assignment_group=on_caseload,
        )
        _make_reflection(
            org_a, program_a, tpl,
            subject=camper_off, author=counselor, assignment_group=off_caseload,
        )
        with organization_context(org_a):
            visible = reflections_visible_to(u)
            assert visible.count() == 1
            assert visible.first().assignment_group_id == on_caseload.id

    def test_unit_scoped_camper_care_only_sees_assigned_units(
        self, org_a, program_a,
    ):
        u = _make_user("cc@a.com")
        cc = _make_person(org_a, "Cc", "User", u)
        Membership.all_objects.create(
            program=program_a, person=cc, role="camper_care", is_active=True,
            metadata={"assigned_unit_slugs": ["tsofim"]},
        )
        in_unit = _make_person(org_a, "In", "Unit")
        Membership.all_objects.create(
            program=program_a, person=in_unit, role="counselor", is_active=True,
            metadata={"unit_slug": "tsofim"},
        )
        not_in_unit = _make_person(org_a, "Not", "Unit")
        Membership.all_objects.create(
            program=program_a, person=not_in_unit, role="counselor", is_active=True,
            metadata={"unit_slug": "other"},
        )
        tpl = _make_template(org_a, role="counselor")
        _make_reflection(org_a, program_a, tpl, subject=in_unit, author=in_unit)
        _make_reflection(org_a, program_a, tpl, subject=not_in_unit, author=not_in_unit)
        with organization_context(org_a):
            visible = reflections_visible_to(u)
            assert visible.count() == 1
            assert visible.first().subject_id == in_unit.id

    def test_camper_care_does_not_get_wellness_shortcut(
        self, org_a, program_a,
    ):
        """A wellness-template reflection about a subject in a different unit
        is NOT visible to a camper_care user — they lost the wellness shortcut
        when they moved to the supervisor capability."""
        u = _make_user("cc@a.com")
        cc = _make_person(org_a, "Cc", "User", u)
        Membership.all_objects.create(
            program=program_a, person=cc, role="camper_care", is_active=True,
            metadata={"assigned_unit_slugs": ["unit-a"]},
        )
        # Subject lives in unit-b, so unit-scope path won't grant access.
        subject = _make_person(org_a, "Sub", "Ject")
        Membership.all_objects.create(
            program=program_a, person=subject, role="counselor", is_active=True,
            metadata={"unit_slug": "unit-b"},
        )
        author = _make_person(org_a, "Au", "Thor")
        # Wellness-tagged template (health_center). Pre-3.21 this would
        # have been visible via _wellness_q; post-3.21 it must not be.
        wellness_tpl = _make_template(org_a, slug="wellness-tpl", role="health_center")
        _make_reflection(
            org_a, program_a, wellness_tpl, subject=subject, author=author,
        )
        with organization_context(org_a):
            assert reflections_visible_to(u).count() == 0

    def test_health_center_keeps_wellness_shortcut(self, org_a, program_a):
        """Regression check: dropping camper_care from WELLNESS_ROLES must not
        affect health_center, which is still a domain_specialist."""
        u = _make_user("hc@a.com")
        hc = _make_person(org_a, "Hc", "User", u)
        Membership.all_objects.create(
            program=program_a, person=hc, role="health_center", is_active=True,
        )
        author = _make_person(org_a, "Au", "Thor")
        subject = _make_person(org_a, "Sub", "Ject")
        Membership.all_objects.create(
            program=program_a, person=subject, role="counselor", is_active=True,
            metadata={"unit_slug": "anywhere"},
        )
        wellness_tpl = _make_template(org_a, slug="wellness-tpl", role="health_center")
        _make_reflection(
            org_a, program_a, wellness_tpl, subject=subject, author=author,
        )
        with organization_context(org_a):
            assert reflections_visible_to(u).count() == 1

    def test_wellness_viewer_still_sees_camper_care_templates(
        self, org_a, program_a,
    ):
        """The wellness team collaborates: a nurse must still see
        camper-care-tagged reflections about subjects in their org, even
        though ``camper_care`` no longer triggers the wellness shortcut on
        the *membership* side. This is enforced by ``WELLNESS_TEMPLATE_ROLES``
        being a superset of ``WELLNESS_ROLES``.
        """
        u = _make_user("nurse@a.com")
        nurse = _make_person(org_a, "Nu", "Rse", u)
        Membership.all_objects.create(
            program=program_a, person=nurse, role="health_center", is_active=True,
        )
        cc_tpl = _make_template(org_a, slug="cc-tpl", role="camper_care")
        author = _make_person(org_a, "Au", "Thor")
        subject = _make_person(org_a, "Sub", "Ject")
        _make_reflection(
            org_a, program_a, cc_tpl, subject=subject, author=author,
        )
        with organization_context(org_a):
            assert reflections_visible_to(u).count() == 1


# ── Path 7c: per-reflection team_visibility (3.22) ───────────────────────────


class TestPrivateReflection:
    """Step 3.22 adds ``Reflection.team_visibility``. A reflection marked
    ``supervisors_only`` opts out of two visibility paths:

      - direct-peer access (path 4-direct in ``reflections_visible_to``)
      - the wellness-template shortcut (path 6)

    Author, subject (with subject_visible), ancestor-group authors,
    unit-scoped supervisors, and admins still see private reflections --
    "supervisors only" is the literal name of the gate.
    """

    def _bunk_with_two_counselors(self, org, program):
        """Seed two counselors as co-authors of a single bunk group."""
        bunk = AssignmentGroup.all_objects.create(
            organization=org, program=program, name="Bunk Maple",
            slug="bunk-maple-priv", group_type="bunk",
        )
        u_a = _make_user("counselor-a@a.com")
        p_a = _make_person(org, "Co", "A", u_a)
        Membership.all_objects.create(
            program=program, person=p_a, role="counselor", is_active=True,
        )
        AssignmentGroupMembership.all_objects.create(
            group=bunk, person=p_a, role_in_group="author", is_active=True,
        )
        u_b = _make_user("counselor-b@a.com")
        p_b = _make_person(org, "Co", "B", u_b)
        Membership.all_objects.create(
            program=program, person=p_b, role="counselor", is_active=True,
        )
        AssignmentGroupMembership.all_objects.create(
            group=bunk, person=p_b, role_in_group="author", is_active=True,
        )
        return bunk, (u_a, p_a), (u_b, p_b)

    def test_peer_author_cannot_see_supervisors_only(self, org_a, program_a):
        bunk, (u_a, p_a), (u_b, p_b) = self._bunk_with_two_counselors(org_a, program_a)
        camper = _make_person(org_a, "Cam", "Per")
        tpl = _make_template(
            org_a, slug="bunk-obs-priv",
            subject_mode="single_subject",
            assignment_scope="per_subject_in_group",
        )
        _make_reflection(
            org_a, program_a, tpl,
            subject=camper, author=p_a, assignment_group=bunk,
            team_visibility=Reflection.TeamVisibility.SUPERVISORS_ONLY,
        )
        _make_reflection(
            org_a, program_a, tpl,
            subject=camper, author=p_a, assignment_group=bunk,
            team_visibility=Reflection.TeamVisibility.TEAM,
        )
        with organization_context(org_a):
            # Counselor B can see the team one (peer path) but NOT the private one.
            visible = reflections_visible_to(u_b)
            assert visible.count() == 1
            assert visible.first().team_visibility == Reflection.TeamVisibility.TEAM
            # Counselor A (the author) still sees both via the author path.
            assert reflections_visible_to(u_a).count() == 2

    def test_ancestor_author_sees_supervisors_only(self, org_a, program_a):
        u_uh = _make_user("uh@a.com")
        uh = _make_person(org_a, "U", "H", u_uh)
        Membership.all_objects.create(
            program=program_a, person=uh, role="unit_head", is_active=True,
        )
        unit = AssignmentGroup.all_objects.create(
            organization=org_a, program=program_a, name="Unit",
            slug="u-priv", group_type="unit",
        )
        bunk = AssignmentGroup.all_objects.create(
            organization=org_a, program=program_a, name="Bunk",
            slug="b-priv", group_type="bunk", parent=unit,
        )
        AssignmentGroupMembership.all_objects.create(
            group=unit, person=uh, role_in_group="author", is_active=True,
        )
        counselor = _make_person(org_a, "Cn", "Sl")
        camper = _make_person(org_a, "Cam", "Per")
        tpl = _make_template(
            org_a, slug="bunk-obs-priv2",
            subject_mode="single_subject",
            assignment_scope="per_subject_in_group",
        )
        _make_reflection(
            org_a, program_a, tpl,
            subject=camper, author=counselor, assignment_group=bunk,
            team_visibility=Reflection.TeamVisibility.SUPERVISORS_ONLY,
        )
        _make_reflection(
            org_a, program_a, tpl,
            subject=camper, author=counselor, assignment_group=bunk,
            team_visibility=Reflection.TeamVisibility.TEAM,
        )
        with organization_context(org_a):
            assert reflections_visible_to(u_uh).count() == 2

    def test_unit_scoped_supervisor_sees_supervisors_only(self, org_a, program_a):
        u_cc = _make_user("cc@a.com")
        cc = _make_person(org_a, "Cc", "User", u_cc)
        Membership.all_objects.create(
            program=program_a, person=cc, role="camper_care", is_active=True,
            metadata={"assigned_unit_slugs": ["pioneers"]},
        )
        subject = _make_person(org_a, "Sub", "Ject")
        Membership.all_objects.create(
            program=program_a, person=subject, role="counselor", is_active=True,
            metadata={"unit_slug": "pioneers"},
        )
        author = _make_person(org_a, "Au", "Thor")
        tpl = _make_template(org_a, role="counselor")
        _make_reflection(
            org_a, program_a, tpl,
            subject=subject, author=author,
            team_visibility=Reflection.TeamVisibility.SUPERVISORS_ONLY,
        )
        with organization_context(org_a):
            assert reflections_visible_to(u_cc).count() == 1

    def test_admin_sees_supervisors_only(self, org_a, program_a):
        u_admin = _make_user("admin@a.com")
        admin_p = _make_person(org_a, "Ad", "Min", u_admin)
        Membership.all_objects.create(
            program=program_a, person=admin_p, role="admin", is_active=True,
        )
        author = _make_person(org_a, "Au", "Thor")
        subject = _make_person(org_a, "Sub", "Ject")
        tpl = _make_template(org_a, role="counselor")
        _make_reflection(
            org_a, program_a, tpl, subject=subject, author=author,
            team_visibility=Reflection.TeamVisibility.SUPERVISORS_ONLY,
        )
        with organization_context(org_a):
            assert reflections_visible_to(u_admin).count() == 1

    def test_subject_visible_overrides_supervisors_only(self, org_a, program_a):
        u = _make_user("camper@a.com")
        camper = _make_person(org_a, "Cam", "Per", u)
        Membership.all_objects.create(
            program=program_a, person=camper, role="camper", is_active=True,
        )
        author = _make_person(org_a, "Coun", "Selor")
        tpl = _make_template(
            org_a, slug="tpl-vis-priv",
            subject_visible=True,
            subject_mode="single_subject",
            assignment_scope="per_subject_in_group",
        )
        _make_reflection(
            org_a, program_a, tpl, subject=camper, author=author,
            team_visibility=Reflection.TeamVisibility.SUPERVISORS_ONLY,
        )
        with organization_context(org_a):
            # The "supervisors only" flag is about peers, not subjects.
            # A camper still sees data about themselves when the template
            # opts into subject visibility.
            assert reflections_visible_to(u).count() == 1

    def test_author_sees_own_supervisors_only(self, org_a, program_a):
        u = _make_user("author@a.com")
        author = _make_person(org_a, "Au", "Thor", u)
        Membership.all_objects.create(
            program=program_a, person=author, role="counselor", is_active=True,
        )
        subject = _make_person(org_a, "Sub", "Ject")
        tpl = _make_template(org_a, role="counselor")
        _make_reflection(
            org_a, program_a, tpl, subject=subject, author=author,
            team_visibility=Reflection.TeamVisibility.SUPERVISORS_ONLY,
        )
        with organization_context(org_a):
            assert reflections_visible_to(u).count() == 1

    def test_wellness_viewer_does_not_see_private_camper_care_reflection(
        self, org_a, program_a,
    ):
        u_nurse = _make_user("nurse@a.com")
        nurse = _make_person(org_a, "Nu", "Rse", u_nurse)
        Membership.all_objects.create(
            program=program_a, person=nurse, role="health_center", is_active=True,
        )
        author = _make_person(org_a, "Au", "Thor")
        subject = _make_person(org_a, "Sub", "Ject")
        cc_tpl = _make_template(org_a, slug="cc-tpl-priv", role="camper_care")
        # Two camper-care reflections; one team, one private.
        _make_reflection(
            org_a, program_a, cc_tpl, subject=subject, author=author,
            team_visibility=Reflection.TeamVisibility.TEAM,
        )
        _make_reflection(
            org_a, program_a, cc_tpl, subject=subject, author=author,
            team_visibility=Reflection.TeamVisibility.SUPERVISORS_ONLY,
        )
        with organization_context(org_a):
            visible = reflections_visible_to(u_nurse)
            assert visible.count() == 1
            assert visible.first().team_visibility == Reflection.TeamVisibility.TEAM


# ── Path 8: cross-org isolation holds for every code path ───────────────────


class TestCrossOrgIsolation:
    def test_admin_in_other_org_blocked(self, org_a, org_b, program_a, program_b):
        admin_user = _make_user("admin@a.com")
        admin_person = _make_person(org_a, "Ad", "Min", admin_user)
        Membership.all_objects.create(
            program=program_a, person=admin_person, role="admin", is_active=True,
        )
        b_person = _make_person(org_b, "B", "Person")
        tpl_b = _make_template(org_b, slug="tpl-b")
        _make_reflection(org_b, program_b, tpl_b, subject=b_person, author=b_person)
        # Even with org_b context active, the admin's person is in org_a
        # and should not see org_b data.
        with organization_context(org_b):
            assert reflections_visible_to(admin_user).count() == 0

    def test_subject_visible_does_not_leak_across_orgs(
        self, org_a, org_b, program_a, program_b,
    ):
        u = _make_user("camper@a.com")
        camper = _make_person(org_a, "Cam", "Per", u)
        Membership.all_objects.create(
            program=program_a, person=camper, role="camper", is_active=True,
        )
        # Make a (different-org) reflection that happens to mention 'camper' nowhere
        b_subj = _make_person(org_b, "Bsubj", "X")
        tpl_b = _make_template(
            org_b,
            slug="tpl-b-vis",
            subject_visible=True,
            subject_mode="single_subject",
            assignment_scope="per_subject_in_group",
        )
        _make_reflection(org_b, program_b, tpl_b, subject=b_subj, author=b_subj)
        with organization_context(org_a):
            assert reflections_visible_to(u).count() == 0


# ── Derived supervisor pipe: self + other reflections of supervised people ───


class TestDerivedSupervisorSelfReflections:
    """A supervisor (derived from unit/bunk authorship or Supervision rows)
    sees the self-reflections of the people they supervise, even though those
    rows are not attached to the supervised AssignmentGroup.
    """

    def _self_reflection(self, org, program, counselor, *, team_visibility):
        tpl = _make_template(
            org, slug="counselor-self", role="counselor", subject_mode="self",
        )
        return _make_reflection(
            org, program, tpl,
            subject=counselor, author=counselor, assignment_group=None,
            team_visibility=team_visibility,
        )

    def test_unit_head_via_unit_authorship_sees_counselor_self_reflection(
        self, org_a, program_a,
    ):
        u = _make_user("uh-self@a.com")
        unit_head = _make_person(org_a, "Un", "Head", u)
        Membership.all_objects.create(
            program=program_a, person=unit_head, role="unit_head", is_active=True,
        )
        unit = AssignmentGroup.all_objects.create(
            organization=org_a, program=program_a, name="Unit",
            slug="unit-self", group_type="unit",
        )
        bunk = AssignmentGroup.all_objects.create(
            organization=org_a, program=program_a, name="Bunk",
            slug="bunk-self", group_type="bunk", parent=unit,
        )
        AssignmentGroupMembership.all_objects.create(
            group=unit, person=unit_head, role_in_group="author", is_active=True,
        )
        counselor = _make_person(org_a, "Co", "Un")
        AssignmentGroupMembership.all_objects.create(
            group=bunk, person=counselor, role_in_group="author", is_active=True,
        )
        # Private (supervisors_only) self-reflection: still visible to the UH.
        self._self_reflection(
            org_a, program_a, counselor,
            team_visibility=Reflection.TeamVisibility.SUPERVISORS_ONLY,
        )
        with organization_context(org_a):
            assert reflections_visible_to(u).count() == 1

    def test_camper_care_caseload_sees_counselor_self_reflection(
        self, org_a, program_a,
    ):
        u = _make_user("cc-self@a.com")
        cc = _make_person(org_a, "Ca", "Re", u)
        cc_membership = Membership.all_objects.create(
            program=program_a, person=cc, role="camper_care", is_active=True,
        )
        bunk = AssignmentGroup.all_objects.create(
            organization=org_a, program=program_a, name="Caseload Bunk",
            slug="cc-bunk-self", group_type="bunk",
        )
        Supervision.all_objects.create(
            supervisor_membership=cc_membership,
            target_type=Supervision.TargetType.BUNK,
            target_bunk=bunk,
            start_date=date(2026, 1, 1),
        )
        counselor = _make_person(org_a, "Co", "Un")
        AssignmentGroupMembership.all_objects.create(
            group=bunk, person=counselor, role_in_group="author", is_active=True,
        )
        self._self_reflection(
            org_a, program_a, counselor,
            team_visibility=Reflection.TeamVisibility.SUPERVISORS_ONLY,
        )
        with organization_context(org_a):
            assert reflections_visible_to(u).count() == 1

    def test_peer_counselor_does_not_see_co_counselor_self_reflection(
        self, org_a, program_a,
    ):
        u = _make_user("peer@a.com")
        counselor_a = _make_person(org_a, "Co", "A", u)
        Membership.all_objects.create(
            program=program_a, person=counselor_a, role="counselor", is_active=True,
        )
        bunk = AssignmentGroup.all_objects.create(
            organization=org_a, program=program_a, name="Bunk",
            slug="peer-bunk", group_type="bunk",
        )
        AssignmentGroupMembership.all_objects.create(
            group=bunk, person=counselor_a, role_in_group="author", is_active=True,
        )
        counselor_b = _make_person(org_a, "Co", "B")
        AssignmentGroupMembership.all_objects.create(
            group=bunk, person=counselor_b, role_in_group="author", is_active=True,
        )
        # B's self-reflection must not leak to peer A (A supervises no one).
        self._self_reflection(
            org_a, program_a, counselor_b,
            team_visibility=Reflection.TeamVisibility.SUPERVISORS_ONLY,
        )
        with organization_context(org_a):
            assert reflections_visible_to(u).count() == 0

    def test_ended_program_self_reflection_not_leaked(self, org_a):
        ended_program = Program.all_objects.create(
            organization=org_a,
            name="Vis A Ended Session",
            slug="ended-session",
            program_type="summer_camp",
            start_date=date(2020, 6, 1),
            end_date=date(2020, 8, 31),
        )
        u = _make_user("uh-ended@a.com")
        unit_head = _make_person(org_a, "Un", "Head", u)
        Membership.all_objects.create(
            program=ended_program, person=unit_head, role="unit_head", is_active=True,
        )
        unit = AssignmentGroup.all_objects.create(
            organization=org_a, program=ended_program, name="Old Unit",
            slug="old-unit", group_type="unit",
        )
        bunk = AssignmentGroup.all_objects.create(
            organization=org_a, program=ended_program, name="Old Bunk",
            slug="old-bunk", group_type="bunk", parent=unit,
        )
        AssignmentGroupMembership.all_objects.create(
            group=unit, person=unit_head, role_in_group="author", is_active=True,
        )
        counselor = _make_person(org_a, "Co", "Un")
        AssignmentGroupMembership.all_objects.create(
            group=bunk, person=counselor, role_in_group="author", is_active=True,
        )
        self._self_reflection(
            org_a, ended_program, counselor,
            team_visibility=Reflection.TeamVisibility.SUPERVISORS_ONLY,
        )
        with organization_context(org_a):
            # Ended program is not operational -> author pipe does not resolve.
            assert reflections_visible_to(u).count() == 0


# ── Performance: bulk-resolve, no N+1 ─────────────────────────────────────────


class TestQueryCount:
    def test_descendant_resolution_is_constant_query_count(
        self, org_a, program_a,
    ):
        u = _make_user("uh@a.com")
        uh = _make_person(org_a, "U", "H", u)
        Membership.all_objects.create(
            program=program_a, person=uh, role="unit_head", is_active=True,
        )
        unit = AssignmentGroup.all_objects.create(
            organization=org_a, program=program_a, name="U", slug="u",
            group_type="unit",
        )
        AssignmentGroupMembership.all_objects.create(
            group=unit, person=uh, role_in_group="author", is_active=True,
        )
        bunks = []
        for i in range(8):
            b = AssignmentGroup.all_objects.create(
                organization=org_a, program=program_a, name=f"Bunk {i}",
                slug=f"bunk-{i}", group_type="bunk", parent=unit,
            )
            bunks.append(b)
        camper = _make_person(org_a, "C", "P")
        author = _make_person(org_a, "A", "U")
        tpl = _make_template(
            org_a, slug="bunk-obs",
            subject_mode="single_subject", assignment_scope="per_subject_in_group",
        )
        for b in bunks:
            for _ in range(3):
                _make_reflection(
                    org_a, program_a, tpl,
                    subject=camper, author=author, assignment_group=b,
                )

        with organization_context(org_a):
            with CaptureQueriesContext(connection) as ctx:
                count = reflections_visible_to(u).count()
            assert count == 24
            # Person lookup, admin check, direct-author groups, descendant rows,
            # leadership memberships, wellness check, the derived supervisor pipe
            # (one Supervision read + one membership resolve), then the COUNT(*).
            # Allow some slack but ensure it doesn't scale with reflection count.
            assert len(ctx.captured_queries) < 16, [
                q["sql"] for q in ctx.captured_queries
            ]
