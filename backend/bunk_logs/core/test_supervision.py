"""Unit + queryset tests for the Supervision primitive (Step 7_3).

Mirrors the four patterns documented in ``core/SUPERVISION.md`` so any
regression in the model / queryset surface lights up here.
"""

from __future__ import annotations

from datetime import date

_ACTIVE_DAY = date(2026, 6, 15)

import pytest
from django.core.exceptions import ValidationError

from bunk_logs.core.context import organization_context
from bunk_logs.core.models import AssignmentGroup
from bunk_logs.core.models import AssignmentGroupMembership
from bunk_logs.core.models import Membership
from bunk_logs.core.models import Organization
from bunk_logs.core.models import Person
from bunk_logs.core.models import Program
from bunk_logs.core.models import Supervision
from bunk_logs.core.models import SupervisionEvent
from bunk_logs.core.models import record_supervision_event

pytestmark = pytest.mark.django_db


# ---------------------------------------------------------------------------
# Fixtures: a small but realistic org with a UH, two Counselors, two bunks,
# Camper Care, LT, and a TBE Director / Madrich for the role-in-program case.
# ---------------------------------------------------------------------------


@pytest.fixture
def org():
    return Organization.objects.create(name="Sup Org", slug="sup-org")


@pytest.fixture
def other_org():
    return Organization.objects.create(name="Other Org", slug="other-org")


@pytest.fixture
def program(org):
    return Program.all_objects.create(
        organization=org,
        name="Sup Org Summer 2026",
        slug="sup-summer",
        program_type="summer_camp",
        start_date=date(2026, 6, 1),
        end_date=date(2026, 8, 31),
    )


@pytest.fixture
def other_program(other_org):
    return Program.all_objects.create(
        organization=other_org,
        name="Other Org Summer 2026",
        slug="other-summer",
        program_type="summer_camp",
        start_date=date(2026, 6, 1),
        end_date=date(2026, 8, 31),
    )


def _person(org, *, first, last="X"):
    return Person.all_objects.create(
        organization=org, first_name=first, last_name=last,
    )


def _member(program, person, *, role, is_active=True):
    return Membership.all_objects.create(
        program=program, person=person, role=role, is_active=is_active,
    )


def _bunk(program, *, slug, name=None):
    return AssignmentGroup.all_objects.create(
        organization=program.organization,
        program=program,
        name=name or slug.title(),
        slug=slug,
        group_type="bunk",
    )


def _author(group, person, *, is_active=True):
    return AssignmentGroupMembership.all_objects.create(
        group=group, person=person, role_in_group="author", is_active=is_active,
    )


def _subject(group, person, *, is_active=True):
    return AssignmentGroupMembership.all_objects.create(
        group=group, person=person, role_in_group="subject", is_active=is_active,
    )


# ---------------------------------------------------------------------------
# Model: validation
# ---------------------------------------------------------------------------


class TestSupervisionValidation:
    def test_counselor_cannot_supervise(self, org, program):
        counselor = _member(program, _person(org, first="C"), role="counselor")
        target = _member(program, _person(org, first="T"), role="counselor")
        with pytest.raises(ValidationError) as exc:
            Supervision(
                supervisor_membership=counselor,
                target_type="membership",
                target_membership=target,
                start_date=date(2026, 6, 1),
            ).save()
        assert "supervisor_membership" in exc.value.message_dict

    def test_admin_can_supervise_anything(self, org, program):
        admin = _member(program, _person(org, first="A"), role="admin")
        target = _member(program, _person(org, first="T"), role="counselor")
        sup = Supervision(
            supervisor_membership=admin,
            target_type="membership",
            target_membership=target,
            start_date=date(2026, 6, 1),
        )
        sup.save()
        assert sup.pk is not None

    def test_unit_head_can_supervise_membership(self, org, program):
        uh = _member(program, _person(org, first="U"), role="unit_head")
        cn = _member(program, _person(org, first="C"), role="counselor")
        Supervision(
            supervisor_membership=uh,
            target_type="membership",
            target_membership=cn,
            start_date=date(2026, 6, 1),
        ).save()

    def test_camper_care_supervises_bunk(self, org, program):
        cc = _member(program, _person(org, first="Cc"), role="camper_care")
        b = _bunk(program, slug="bunk-12")
        Supervision(
            supervisor_membership=cc,
            target_type="bunk",
            target_bunk=b,
            start_date=date(2026, 6, 1),
        ).save()

    def test_camper_care_bunk_target_must_be_bunk_type(self, org, program):
        cc = _member(program, _person(org, first="Cc"), role="camper_care")
        unit = AssignmentGroup.all_objects.create(
            organization=org,
            program=program,
            name="Unit Lower",
            slug="unit-lower",
            group_type="unit",
        )
        with pytest.raises(ValidationError) as exc:
            Supervision(
                supervisor_membership=cc,
                target_type="bunk",
                target_bunk=unit,
                start_date=date(2026, 6, 1),
            ).save()
        assert "target_bunk" in exc.value.message_dict

    def test_lt_supervises_role_in_program(self, org, program):
        lt = _member(program, _person(org, first="L"), role="leadership_team")
        Supervision(
            supervisor_membership=lt,
            target_type="role_in_program",
            target_role="kitchen_staff",
            target_program=program,
            start_date=date(2026, 6, 1),
        ).save()

    def test_role_in_program_requires_program(self, org, program):
        lt = _member(program, _person(org, first="L"), role="leadership_team")
        with pytest.raises(ValidationError) as exc:
            Supervision(
                supervisor_membership=lt,
                target_type="role_in_program",
                target_role="kitchen_staff",
                start_date=date(2026, 6, 1),
            ).save()
        assert "target_program" in exc.value.message_dict

    def test_unknown_target_role_rejected(self, org, program):
        lt = _member(program, _person(org, first="L"), role="leadership_team")
        with pytest.raises(ValidationError) as exc:
            Supervision(
                supervisor_membership=lt,
                target_type="role_in_program",
                target_role="bogus_role",
                target_program=program,
                start_date=date(2026, 6, 1),
            ).save()
        assert "target_role" in exc.value.message_dict

    def test_membership_target_requires_target_membership(self, org, program):
        uh = _member(program, _person(org, first="U"), role="unit_head")
        with pytest.raises(ValidationError) as exc:
            Supervision(
                supervisor_membership=uh,
                target_type="membership",
                start_date=date(2026, 6, 1),
            ).save()
        assert "target_membership" in exc.value.message_dict

    def test_cross_wired_fields_rejected(self, org, program):
        uh = _member(program, _person(org, first="U"), role="unit_head")
        cn = _member(program, _person(org, first="C"), role="counselor")
        b = _bunk(program, slug="bunk-x")
        with pytest.raises(ValidationError) as exc:
            Supervision(
                supervisor_membership=uh,
                target_type="membership",
                target_membership=cn,
                target_bunk=b,
                start_date=date(2026, 6, 1),
            ).save()
        assert "target_bunk" in exc.value.message_dict

    def test_end_date_before_start_date_rejected(self, org, program):
        uh = _member(program, _person(org, first="U"), role="unit_head")
        cn = _member(program, _person(org, first="C"), role="counselor")
        with pytest.raises(ValidationError) as exc:
            Supervision(
                supervisor_membership=uh,
                target_type="membership",
                target_membership=cn,
                start_date=date(2026, 6, 10),
                end_date=date(2026, 6, 1),
            ).save()
        assert "end_date" in exc.value.message_dict

    def test_cross_org_target_membership_rejected(self, org, other_org, program, other_program):
        uh = _member(program, _person(org, first="U"), role="unit_head")
        foreign_cn = _member(
            other_program,
            _person(other_org, first="X"),
            role="counselor",
        )
        with pytest.raises(ValidationError) as exc:
            Supervision(
                supervisor_membership=uh,
                target_type="membership",
                target_membership=foreign_cn,
                start_date=date(2026, 6, 1),
            ).save()
        assert "target_membership" in exc.value.message_dict


# ---------------------------------------------------------------------------
# Model: is_active() computed property
# ---------------------------------------------------------------------------


class TestSupervisionIsActive:
    def test_is_active_today(self, org, program):
        uh = _member(program, _person(org, first="U"), role="unit_head")
        cn = _member(program, _person(org, first="C"), role="counselor")
        s = Supervision.all_objects.create(
            supervisor_membership=uh,
            target_type="membership",
            target_membership=cn,
            start_date=date(2026, 6, 1),
        )
        assert s.is_active(today=date(2026, 6, 15)) is True

    def test_inactive_before_start(self, org, program):
        uh = _member(program, _person(org, first="U"), role="unit_head")
        cn = _member(program, _person(org, first="C"), role="counselor")
        s = Supervision.all_objects.create(
            supervisor_membership=uh,
            target_type="membership",
            target_membership=cn,
            start_date=date(2026, 6, 10),
        )
        assert s.is_active(today=date(2026, 6, 1)) is False

    def test_inactive_after_end(self, org, program):
        uh = _member(program, _person(org, first="U"), role="unit_head")
        cn = _member(program, _person(org, first="C"), role="counselor")
        s = Supervision.all_objects.create(
            supervisor_membership=uh,
            target_type="membership",
            target_membership=cn,
            start_date=date(2026, 6, 1),
            end_date=date(2026, 6, 10),
        )
        assert s.is_active(today=date(2026, 6, 15)) is False

    def test_active_on_boundary_dates(self, org, program):
        uh = _member(program, _person(org, first="U"), role="unit_head")
        cn = _member(program, _person(org, first="C"), role="counselor")
        s = Supervision.all_objects.create(
            supervisor_membership=uh,
            target_type="membership",
            target_membership=cn,
            start_date=date(2026, 6, 1),
            end_date=date(2026, 6, 10),
        )
        assert s.is_active(today=date(2026, 6, 1)) is True
        assert s.is_active(today=date(2026, 6, 10)) is True


# ---------------------------------------------------------------------------
# QuerySet helpers
# ---------------------------------------------------------------------------


class TestBunksForUH:
    def test_transitive_walk(self, org, program):
        uh = _member(program, _person(org, first="Uh"), role="unit_head")
        cn1_person = _person(org, first="Cn1")
        cn1 = _member(program, cn1_person, role="counselor")
        cn2_person = _person(org, first="Cn2")
        cn2 = _member(program, cn2_person, role="counselor")
        unrelated_person = _person(org, first="Un")
        _member(program, unrelated_person, role="counselor")

        b1 = _bunk(program, slug="bunk-1")
        b2 = _bunk(program, slug="bunk-2")
        b3 = _bunk(program, slug="bunk-3")
        _author(b1, cn1_person)
        _author(b2, cn2_person)
        _author(b3, unrelated_person)

        Supervision.all_objects.create(
            supervisor_membership=uh,
            target_type="membership",
            target_membership=cn1,
            start_date=date(2026, 6, 1),
        )
        Supervision.all_objects.create(
            supervisor_membership=uh,
            target_type="membership",
            target_membership=cn2,
            start_date=date(2026, 6, 1),
        )

        with organization_context(org):
            result = Supervision.objects.bunks_for_uh(uh, today=_ACTIVE_DAY)
            slugs = sorted(result.values_list("slug", flat=True))
        assert slugs == ["bunk-1", "bunk-2"]

    def test_ended_supervision_excluded(self, org, program):
        uh = _member(program, _person(org, first="Uh"), role="unit_head")
        cn_person = _person(org, first="Cn")
        cn = _member(program, cn_person, role="counselor")
        b = _bunk(program, slug="bunk-1")
        _author(b, cn_person)

        Supervision.all_objects.create(
            supervisor_membership=uh,
            target_type="membership",
            target_membership=cn,
            start_date=date(2026, 5, 1),
            end_date=date(2026, 5, 31),
        )
        with organization_context(org):
            result = Supervision.objects.bunks_for_uh(uh, today=_ACTIVE_DAY)
        assert list(result) == []

    def test_uh_author_on_unit_resolves_child_bunks(self, org, program):
        """A UH attached as author on a unit sees the unit's child bunks.

        Mirrors the admin workflow where a Unit Head has no counselor
        supervisions but is added directly to a unit group (e.g. "Upper
        Bonim"), which contains bunks.
        """
        uh_person = _person(org, first="Uh")
        uh = _member(program, uh_person, role="unit_head")
        unit = AssignmentGroup.all_objects.create(
            organization=org,
            program=program,
            name="Upper Bonim",
            slug="upper-bonim",
            group_type="unit",
        )
        child = _bunk(program, slug="bunk-23", name="Bunk 23")
        child.parent = unit
        child.save()
        _author(unit, uh_person)

        with organization_context(org):
            result = Supervision.objects.bunks_for_uh(uh, today=_ACTIVE_DAY)
            slugs = sorted(result.values_list("slug", flat=True))
        assert slugs == ["bunk-23"]

    def test_uh_group_supervision_resolves_child_bunks(self, org, program):
        """``target_type=assignment_group`` supervision expands to bunks."""
        uh = _member(program, _person(org, first="Uh"), role="unit_head")
        unit = AssignmentGroup.all_objects.create(
            organization=org,
            program=program,
            name="Lower Bonim",
            slug="lower-bonim",
            group_type="unit",
        )
        child = _bunk(program, slug="bunk-9", name="Bunk 9")
        child.parent = unit
        child.save()
        Supervision.all_objects.create(
            supervisor_membership=uh,
            target_type="assignment_group",
            target_group=unit,
            start_date=date(2026, 6, 1),
        )

        with organization_context(org):
            result = Supervision.objects.bunks_for_uh(uh, today=_ACTIVE_DAY)
            slugs = sorted(result.values_list("slug", flat=True))
        assert slugs == ["bunk-9"]


class TestCaseloadCampers:
    def test_returns_active_subjects(self, org, program):
        cc = _member(program, _person(org, first="Cc"), role="camper_care")
        b12 = _bunk(program, slug="bunk-12")
        b13 = _bunk(program, slug="bunk-13")
        camper_a = _person(org, first="A")
        camper_b = _person(org, first="B")
        camper_c = _person(org, first="C")
        _subject(b12, camper_a)
        _subject(b12, camper_b)
        _subject(b13, camper_c)
        # Camper in a bunk not in this caseload should not be returned.
        b14 = _bunk(program, slug="bunk-14")
        _subject(b14, _person(org, first="D"))

        Supervision.all_objects.create(
            supervisor_membership=cc,
            target_type="bunk",
            target_bunk=b12,
            start_date=date(2026, 6, 1),
        )
        Supervision.all_objects.create(
            supervisor_membership=cc,
            target_type="bunk",
            target_bunk=b13,
            start_date=date(2026, 6, 1),
        )
        with organization_context(org):
            result = Supervision.objects.caseload_campers(cc, today=_ACTIVE_DAY)
            firsts = sorted(result.values_list("first_name", flat=True))
        assert firsts == ["A", "B", "C"]


class TestTeamMembers:
    def test_role_in_program_filter(self, org, program):
        lt = _member(program, _person(org, first="L"), role="leadership_team")
        Supervision.all_objects.create(
            supervisor_membership=lt,
            target_type="role_in_program",
            target_role="kitchen_staff",
            target_program=program,
            start_date=date(2026, 6, 1),
        )
        k1 = _member(program, _person(org, first="K1"), role="kitchen_staff")
        k2 = _member(program, _person(org, first="K2"), role="kitchen_staff")
        # Specialist should not match.
        _member(program, _person(org, first="S"), role="specialist")

        with organization_context(org):
            result = Supervision.objects.team_members(
                lt, target_role="kitchen_staff", today=_ACTIVE_DAY,
            )
            ids = sorted(result.values_list("id", flat=True))
        assert ids == sorted([k1.id, k2.id])

    def test_no_supervision_returns_empty(self, org, program):
        lt = _member(program, _person(org, first="L"), role="leadership_team")
        _member(program, _person(org, first="K"), role="kitchen_staff")
        with organization_context(org):
            assert list(Supervision.objects.team_members(lt, today=_ACTIVE_DAY)) == []


class TestCoSupervisors:
    def test_finds_other_supervisors_of_same_bunk(self, org, program):
        cc1 = _member(program, _person(org, first="Cc1"), role="camper_care")
        cc2 = _member(program, _person(org, first="Cc2"), role="camper_care")
        b = _bunk(program, slug="bunk-1")
        s1 = Supervision.all_objects.create(
            supervisor_membership=cc1,
            target_type="bunk",
            target_bunk=b,
            start_date=date(2026, 6, 1),
        )
        s2 = Supervision.all_objects.create(
            supervisor_membership=cc2,
            target_type="bunk",
            target_bunk=b,
            start_date=date(2026, 6, 1),
        )
        with organization_context(org):
            result = Supervision.objects.co_supervisors(s1, today=_ACTIVE_DAY)
        assert list(result) == [s2]

    def test_excludes_self(self, org, program):
        cc = _member(program, _person(org, first="Cc"), role="camper_care")
        b = _bunk(program, slug="bunk-1")
        s = Supervision.all_objects.create(
            supervisor_membership=cc,
            target_type="bunk",
            target_bunk=b,
            start_date=date(2026, 6, 1),
        )
        with organization_context(org):
            assert list(Supervision.objects.co_supervisors(s, today=_ACTIVE_DAY)) == []

    def test_ended_supervision_not_a_co_supervisor(self, org, program):
        cc1 = _member(program, _person(org, first="Cc1"), role="camper_care")
        cc2 = _member(program, _person(org, first="Cc2"), role="camper_care")
        b = _bunk(program, slug="bunk-1")
        s1 = Supervision.all_objects.create(
            supervisor_membership=cc1,
            target_type="bunk",
            target_bunk=b,
            start_date=date(2026, 6, 1),
        )
        Supervision.all_objects.create(
            supervisor_membership=cc2,
            target_type="bunk",
            target_bunk=b,
            start_date=date(2026, 5, 1),
            end_date=date(2026, 5, 31),
        )
        with organization_context(org):
            assert list(Supervision.objects.co_supervisors(s1, today=_ACTIVE_DAY)) == []


# ---------------------------------------------------------------------------
# Tenant isolation via the default org-scoped manager
# ---------------------------------------------------------------------------


class TestSupervisionManagerScoping:
    def test_other_org_rows_invisible(
        self, org, other_org, program, other_program,
    ):
        local_uh = _member(program, _person(org, first="U"), role="unit_head")
        local_cn = _member(program, _person(org, first="C"), role="counselor")
        Supervision.all_objects.create(
            supervisor_membership=local_uh,
            target_type="membership",
            target_membership=local_cn,
            start_date=date(2026, 6, 1),
        )
        other_uh = _member(other_program, _person(other_org, first="OU"), role="unit_head")
        other_cn = _member(other_program, _person(other_org, first="OC"), role="counselor")
        Supervision.all_objects.create(
            supervisor_membership=other_uh,
            target_type="membership",
            target_membership=other_cn,
            start_date=date(2026, 6, 1),
        )

        with organization_context(org):
            assert Supervision.objects.count() == 1
        with organization_context(other_org):
            assert Supervision.objects.count() == 1


# ---------------------------------------------------------------------------
# Audit event helper
# ---------------------------------------------------------------------------


class TestRecordSupervisionEvent:
    def test_writes_event_with_actor(self, org, program):
        uh = _member(program, _person(org, first="U"), role="unit_head")
        cn = _member(program, _person(org, first="C"), role="counselor")
        admin = _member(program, _person(org, first="A"), role="admin")
        s = Supervision.all_objects.create(
            supervisor_membership=uh,
            target_type="membership",
            target_membership=cn,
            start_date=date(2026, 6, 1),
        )
        record_supervision_event(
            supervision=s,
            event_type="created",
            actor_membership=admin,
            after_state={"k": "v"},
        )
        assert SupervisionEvent.all_objects.filter(
            supervision=s, event_type="created", actor_membership=admin,
        ).count() == 1
