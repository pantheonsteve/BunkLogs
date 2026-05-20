"""Cross-role isolation tests — one case per visibility-table content type."""
from __future__ import annotations

from datetime import date

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from bunk_logs.core.context import organization_context
from bunk_logs.core.filters import notes_visible_to
from bunk_logs.core.models import AssignmentGroup
from bunk_logs.core.models import AssignmentGroupMembership
from bunk_logs.core.models import Membership
from bunk_logs.core.models import Note
from bunk_logs.core.models import Organization
from bunk_logs.core.models import Person
from bunk_logs.core.models import Program
from bunk_logs.core.models import Reflection
from bunk_logs.core.models import ReflectionTemplate

User = get_user_model()

pytestmark = pytest.mark.django_db


def _schema() -> dict:
    return {"fields": [{"key": "n", "type": "text", "prompts": {"en": "n"}}]}


def _hdr(slug: str) -> dict:
    return {"HTTP_X_ORGANIZATION_SLUG": slug}


def _user(email: str) -> User:
    return User.objects.create_user(email=email, password="pw")


def _person(org, first: str, last: str, user=None) -> Person:
    return Person.all_objects.create(
        organization=org, first_name=first, last_name=last, user=user,
    )


def _program(org) -> Program:
    return Program.all_objects.create(
        organization=org,
        name=f"{org.name} Summer",
        slug=f"{org.slug}-summer",
        program_type="summer_camp",
        start_date=date(2026, 6, 1),
        end_date=date(2026, 8, 31),
    )


def _template(org, *, slug: str, role: str, subject_mode: str = "self", **kwargs) -> ReflectionTemplate:
    return ReflectionTemplate.all_objects.create(
        organization=org,
        name=slug,
        slug=slug,
        cadence="weekly",
        role=role,
        subject_mode=subject_mode,
        schema=_schema(),
        languages=["en"],
        **kwargs,
    )


def _reflection(org, program, tpl, *, subject, author, **kwargs) -> Reflection:
    return Reflection.all_objects.create(
        organization=org,
        program=program,
        template=tpl,
        subject=subject,
        author=author,
        period_start=date(2026, 6, 1),
        period_end=date(2026, 6, 7),
        answers={"n": "x"},
        language="en",
        **kwargs,
    )


@pytest.fixture
def org(db):
    return Organization.objects.create(name="Iso Org", slug="iso-org")


@pytest.fixture
def program(org):
    return _program(org)


@pytest.fixture
def api():
    return APIClient()


class TestCamperReflectionIsolation:
    """Counselor sees bunk reflection; unrelated counselor does not."""

    def test_counselor_sees_bunk_reflection_unit_head_does_not_without_scope(
        self, api, org, program,
    ):
        bunk = AssignmentGroup.all_objects.create(
            organization=org, program=program, name="Bunk", slug="bunk",
            group_type="bunk",
        )
        u_cns = _user("cns@iso.com")
        cns = _person(org, "Co", "Un", u_cns)
        Membership.all_objects.create(program=program, person=cns, role="counselor", is_active=True)
        AssignmentGroupMembership.all_objects.create(
            group=bunk, person=cns, role_in_group="author", is_active=True,
        )
        other_cns = _person(org, "Ot", "Her")
        Membership.all_objects.create(program=program, person=other_cns, role="counselor", is_active=True)

        camper = _person(org, "Cam", "Per")
        tpl = _template(
            org, slug="bunk-obs", role="counselor",
            subject_mode="single_subject", assignment_scope="per_subject_in_group",
        )
        _reflection(org, program, tpl, subject=camper, author=cns, assignment_group=bunk)

        api.force_authenticate(user=u_cns)
        with organization_context(org):
            r = api.get("/api/v1/reflections/", **_hdr(org.slug))
        assert r.status_code == 200
        assert len(r.json()) == 1

        u_other = _user("other@iso.com")
        other_cns.user = u_other
        other_cns.save(update_fields=["user"])
        api.force_authenticate(user=u_other)
        with organization_context(org):
            r2 = api.get("/api/v1/reflections/", **_hdr(org.slug))
        assert len(r2.json()) == 0


class TestCounselorSelfReflectionIsolation:
    def test_peer_counselor_does_not_see_self_reflection(self, api, org, program):
        bunk = AssignmentGroup.all_objects.create(
            organization=org, program=program, name="B", slug="b", group_type="bunk",
        )
        u_a, u_b = _user("a@iso.com"), _user("b@iso.com")
        p_a = _person(org, "A", "A", u_a)
        p_b = _person(org, "B", "B", u_b)
        for p in (p_a, p_b):
            Membership.all_objects.create(program=program, person=p, role="counselor", is_active=True)
            AssignmentGroupMembership.all_objects.create(
                group=bunk, person=p, role_in_group="author", is_active=True,
            )
        tpl = _template(org, slug="cns-self", role="counselor", subject_mode="self")
        _reflection(org, program, tpl, subject=p_a, author=p_a)

        api.force_authenticate(user=u_b)
        with organization_context(org):
            assert len(api.get("/api/v1/reflections/", **_hdr(org.slug)).json()) == 0


class TestUnitHeadSelfReflectionIsolation:
    def test_counselor_cannot_read_uh_self_reflection(self, api, org, program):
        u_uh, u_cns = _user("uh@iso.com"), _user("cns@iso.com")
        uh = _person(org, "U", "H", u_uh)
        cns = _person(org, "C", "S", u_cns)
        Membership.all_objects.create(program=program, person=uh, role="unit_head", is_active=True)
        Membership.all_objects.create(program=program, person=cns, role="counselor", is_active=True)
        tpl = _template(org, slug="uh-self", role="unit_head", subject_mode="self")
        _reflection(org, program, tpl, subject=uh, author=uh)

        api.force_authenticate(user=u_cns)
        with organization_context(org):
            assert len(api.get("/api/v1/reflections/", **_hdr(org.slug)).json()) == 0

        api.force_authenticate(user=u_uh)
        with organization_context(org):
            assert len(api.get("/api/v1/reflections/", **_hdr(org.slug)).json()) == 1


class TestSpecialistSelfReflectionIsolation:
    def test_other_specialist_cannot_read(self, api, org, program):
        u_a, u_b = _user("sp1@iso.com"), _user("sp2@iso.com")
        p_a = _person(org, "S", "One", u_a)
        p_b = _person(org, "S", "Two", u_b)
        Membership.all_objects.create(program=program, person=p_a, role="specialist", is_active=True)
        Membership.all_objects.create(program=program, person=p_b, role="specialist", is_active=True)
        tpl = _template(org, slug="sp-self", role="specialist", subject_mode="self")
        _reflection(org, program, tpl, subject=p_a, author=p_a)

        api.force_authenticate(user=u_b)
        with organization_context(org):
            assert len(api.get("/api/v1/reflections/", **_hdr(org.slug)).json()) == 0


class TestKitchenStaffReflectionIsolation:
    def test_counselor_cannot_read_kitchen_reflection(self, api, org, program):
        u_kit, u_cns = _user("kit@iso.com"), _user("cns2@iso.com")
        kit = _person(org, "Ki", "Tchen", u_kit)
        cns = _person(org, "Co", "Un", u_cns)
        Membership.all_objects.create(program=program, person=kit, role="kitchen_staff", is_active=True)
        Membership.all_objects.create(program=program, person=cns, role="counselor", is_active=True)
        tpl = _template(org, slug="kit-self", role="kitchen_staff", subject_mode="self")
        _reflection(org, program, tpl, subject=kit, author=kit)

        api.force_authenticate(user=u_cns)
        with organization_context(org):
            assert len(api.get("/api/v1/reflections/", **_hdr(org.slug)).json()) == 0

        u_lt = _user("lt@iso.com")
        lt = _person(org, "Le", "Ad", u_lt)
        Membership.all_objects.create(program=program, person=lt, role="leadership_team", is_active=True)
        api.force_authenticate(user=u_lt)
        with organization_context(org):
            assert len(api.get("/api/v1/reflections/", **_hdr(org.slug)).json()) == 1


class TestLeadershipTeamPrivateIsolation:
    def test_counselor_cannot_read_private_lt_self_reflection(self, api, org, program):
        u_lt, u_cns = _user("lt@iso.com"), _user("cns3@iso.com")
        lt = _person(org, "Le", "Ad", u_lt)
        cns = _person(org, "Co", "Un", u_cns)
        Membership.all_objects.create(program=program, person=lt, role="leadership_team", is_active=True)
        Membership.all_objects.create(program=program, person=cns, role="counselor", is_active=True)
        tpl = _template(
            org, slug="lt-self", role="leadership_team", subject_mode="self",
            supports_privacy=True,
        )
        _reflection(
            org, program, tpl, subject=lt, author=lt,
            team_visibility=Reflection.TeamVisibility.SUPERVISORS_ONLY,
        )

        api.force_authenticate(user=u_cns)
        with organization_context(org):
            assert len(api.get("/api/v1/reflections/", **_hdr(org.slug)).json()) == 0


class TestMadrichReflectionIsolation:
    def test_counselor_cannot_read_madrich_reflection(self, api, org, program):
        u_md, u_cns = _user("md@iso.com"), _user("cns4@iso.com")
        md = _person(org, "Ma", "Drich", u_md)
        cns = _person(org, "Co", "Un", u_cns)
        Membership.all_objects.create(program=program, person=md, role="madrich", is_active=True)
        Membership.all_objects.create(program=program, person=cns, role="counselor", is_active=True)
        tpl = _template(org, slug="md-self", role="madrich", subject_mode="self")
        _reflection(org, program, tpl, subject=md, author=md)

        api.force_authenticate(user=u_cns)
        with organization_context(org):
            assert len(api.get("/api/v1/reflections/", **_hdr(org.slug)).json()) == 0

        u_dir = _user("dir@iso.com")
        director = _person(org, "Di", "Rector", u_dir)
        Membership.all_objects.create(
            program=program, person=director, role="leadership_team", is_active=True,
        )
        api.force_authenticate(user=u_dir)
        with organization_context(org):
            assert len(api.get("/api/v1/reflections/", **_hdr(org.slug)).json()) == 1


class TestAdminSelfReflectionPrivateIsolation:
    def test_non_admin_cannot_read_private_admin_reflection(self, api, org, program):
        u_admin, u_cns = _user("adm@iso.com"), _user("cns5@iso.com")
        admin_p = _person(org, "Ad", "Min", u_admin)
        cns = _person(org, "Co", "Un", u_cns)
        Membership.all_objects.create(program=program, person=admin_p, role="admin", is_active=True)
        Membership.all_objects.create(program=program, person=cns, role="counselor", is_active=True)
        tpl = _template(
            org, slug="adm-self", role="admin", subject_mode="self", supports_privacy=True,
        )
        _reflection(
            org, program, tpl, subject=admin_p, author=admin_p,
            team_visibility=Reflection.TeamVisibility.SUPERVISORS_ONLY,
        )

        api.force_authenticate(user=u_cns)
        with organization_context(org):
            assert len(api.get("/api/v1/reflections/", **_hdr(org.slug)).json()) == 0


class TestNoteContentIsolation:
    """Note types: camper_care, specialist, maintenance — via notes_visible_to."""

    def _note(self, org, program, author, subject, note_type, **kwargs) -> Note:
        return Note.all_objects.create(
            organization=org,
            program=program,
            author=author,
            subject=subject,
            note_type=note_type,
            body="note body",
            **kwargs,
        )

    def test_camper_care_note_counselor_vs_health_center_sensitive(
        self, org, program,
    ):
        camper = _person(org, "Cam", "Per")
        cc_author = _person(org, "Cc", "Auth")
        u_cns = _user("cns6@iso.com")
        cns = _person(org, "Co", "Un", u_cns)
        u_hc = _user("hc@iso.com")
        hc = _person(org, "He", "Alth", u_hc)
        Membership.all_objects.create(program=program, person=cns, role="counselor", is_active=True)
        Membership.all_objects.create(program=program, person=hc, role="health_center", is_active=True)

        self._note(
            org, program, cc_author, camper,
            Note.NoteType.CAMPER_CARE, is_sensitive=True,
        )

        with organization_context(org):
            assert notes_visible_to(u_cns).count() == 0
            assert notes_visible_to(u_hc).count() == 1

    def test_specialist_note_sensitive_hides_from_counselor(self, org, program):
        camper = _person(org, "Cam", "Per")
        sp = _person(org, "Sp", "Ec")
        u_cns = _user("cns7@iso.com")
        cns = _person(org, "Co", "Un", u_cns)
        Membership.all_objects.create(program=program, person=cns, role="counselor", is_active=True)
        self._note(
            org, program, sp, camper, Note.NoteType.SPECIALIST, is_sensitive=True,
        )
        with organization_context(org):
            assert notes_visible_to(u_cns).count() == 0

    def test_maintenance_team_only_hides_from_counselor(self, org, program):
        maint = _person(org, "Ma", "Int")
        camper = _person(org, "Cam", "Per")
        u_cns = _user("cns8@iso.com")
        cns = _person(org, "Co", "Un", u_cns)
        Membership.all_objects.create(program=program, person=cns, role="counselor", is_active=True)
        self._note(
            org, program, maint, camper, Note.NoteType.MAINTENANCE,
            maintenance_visibility=Note.MaintenanceVisibility.TEAM_ONLY,
        )
        with organization_context(org):
            assert notes_visible_to(u_cns).count() == 0
