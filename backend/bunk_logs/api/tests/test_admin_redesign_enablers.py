"""Enablers behind the admin redesign: invite status, bulk invite, group counts.

Covers the three questions the merged People and Groups screens ask that the
old endpoints could not answer: who has never signed in, can we invite a
selection in one go, and does each group have an author, subjects, and logs.
"""

from __future__ import annotations

from datetime import date
from datetime import timedelta
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient

from bunk_logs.core.context import organization_context
from bunk_logs.core.models import AssignmentGroup
from bunk_logs.core.models import AssignmentGroupMembership
from bunk_logs.core.models import AuditEvent
from bunk_logs.core.models import Membership
from bunk_logs.core.models import Organization
from bunk_logs.core.models import Person
from bunk_logs.core.models import Program
from bunk_logs.core.models import Reflection
from bunk_logs.core.models import ReflectionTemplate
from bunk_logs.core.models import TemplateAssignment

User = get_user_model()
pytestmark = pytest.mark.django_db

PEOPLE_URL = "/api/v1/admin/people/"
BULK_INVITE_URL = "/api/v1/admin/people/invite/"
GROUPS_OVERVIEW_URL = "/api/v1/admin/groups/overview/"
DASHBOARD_URL = "/api/v1/admin/dashboard/"
NAV_BADGES_URL = "/api/v1/admin/nav-badges/"


def _hdr(slug: str) -> dict:
    return {"HTTP_X_ORGANIZATION_SLUG": slug}


@pytest.fixture
def api() -> APIClient:
    return APIClient()


@pytest.fixture
def org():
    return Organization.objects.create(name="Enabler Org", slug="enabler-org")


@pytest.fixture
def program(org):
    return Program.all_objects.create(
        organization=org, name="Enabler Org 2026-27", slug="enabler-2026-27",
        program_type="religious_school",
        start_date=date(2026, 9, 1), end_date=date(2027, 5, 31),
    )


@pytest.fixture
def admin_user(org, program):
    u = User.objects.create_user(email="admin-enabler@example.com", password="pw")
    person = Person.all_objects.create(
        organization=org, first_name="Ad", last_name="Min", user=u,
    )
    Membership.all_objects.create(
        program=program, person=person, role="admin", is_active=True,
    )
    return u


def _staff(org, program, *, first_name, email, invited_at=None, last_login=None):
    """A person with an active staff membership, so they are invitable."""
    user = None
    if last_login is not None:
        user = User.objects.create_user(email=email, password="pw")
        user.last_login = last_login
        user.save(update_fields=["last_login"])
    person = Person.all_objects.create(
        organization=org, first_name=first_name, last_name="Staff",
        email=email, invited_at=invited_at, user=user,
    )
    Membership.all_objects.create(
        program=program, person=person, role="faculty", is_active=True,
    )
    return person


class TestInviteStatus:
    @pytest.fixture(autouse=True)
    def people(self, org, program):
        self.never = _staff(
            org, program, first_name="Never", email="never@example.com",
        )
        self.invited = _staff(
            org, program, first_name="Invited", email="invited@example.com",
            invited_at=timezone.now() - timedelta(days=2),
        )
        self.active = _staff(
            org, program, first_name="Active", email="active@example.com",
            invited_at=timezone.now() - timedelta(days=9),
            last_login=timezone.now() - timedelta(days=1),
        )

    def _list(self, api, org, admin_user, **params):
        api.force_authenticate(user=admin_user)
        with organization_context(org):
            r = api.get(PEOPLE_URL, params, **_hdr(org.slug))
        assert r.status_code == 200, r.content
        return {row["first_name"]: row for row in r.data["results"]}

    def test_derives_the_three_states(self, api, org, admin_user):
        rows = self._list(api, org, admin_user)
        assert rows["Never"]["invite_status"] == "never"
        assert rows["Invited"]["invite_status"] == "invited"
        assert rows["Active"]["invite_status"] == "active"

    def test_signing_in_outranks_the_invitation_timestamp(self, api, org, admin_user):
        # Active was invited *and* signed in; signing in is the stronger signal.
        rows = self._list(api, org, admin_user)
        assert rows["Active"]["invited_at"] is not None
        assert rows["Active"]["invite_status"] == "active"

    @pytest.mark.parametrize(
        ("status_filter", "expected"),
        [("never", {"Never"}), ("invited", {"Invited"}), ("active", {"Active"})],
    )
    def test_filters_by_invite_status(
        self, api, org, admin_user, status_filter, expected,
    ):
        rows = self._list(api, org, admin_user, invite_status=status_filter)
        # The admin fixture's own person has no membership role filter applied,
        # so compare only against the staff we created.
        assert {n for n in rows if n != "Ad"} == expected

    def test_unknown_filter_value_is_ignored_rather_than_erroring(
        self, api, org, admin_user,
    ):
        rows = self._list(api, org, admin_user, invite_status="bogus")
        assert {"Never", "Invited", "Active"} <= set(rows)

    def test_requires_admin(self, api, org, program):
        outsider = User.objects.create_user(email="nobody@example.com", password="pw")
        api.force_authenticate(user=outsider)
        with organization_context(org):
            r = api.get(PEOPLE_URL, **_hdr(org.slug))
        assert r.status_code in (401, 403)


class TestBulkInvite:
    def test_invites_each_person_and_stamps_invited_at(
        self, api, org, program, admin_user,
    ):
        a = _staff(org, program, first_name="Aviva", email="aviva@example.com")
        b = _staff(org, program, first_name="Boaz", email="boaz@example.com")
        service = MagicMock()
        service.send_email.return_value = True

        api.force_authenticate(user=admin_user)
        with patch(
            "bunk_logs.api.admin_flow.people.get_email_service", return_value=service,
        ), organization_context(org):
            r = api.post(
                BULK_INVITE_URL, {"person_ids": [a.id, b.id]},
                format="json", **_hdr(org.slug),
            )

        assert r.status_code == 200, r.content
        assert r.data["sent_count"] == 2
        assert r.data["skipped_count"] == 0
        a.refresh_from_db()
        b.refresh_from_db()
        assert a.invited_at is not None
        assert b.invited_at is not None

    def test_reports_partial_success_rather_than_failing_the_batch(
        self, api, org, program, admin_user,
    ):
        ok = _staff(org, program, first_name="Ok", email="ok@example.com")
        # No email, so this one cannot be invited.
        no_email = Person.all_objects.create(
            organization=org, first_name="Nomail", last_name="Staff",
        )
        Membership.all_objects.create(
            program=program, person=no_email, role="faculty", is_active=True,
        )
        service = MagicMock()
        service.send_email.return_value = True

        api.force_authenticate(user=admin_user)
        with patch(
            "bunk_logs.api.admin_flow.people.get_email_service", return_value=service,
        ), organization_context(org):
            r = api.post(
                BULK_INVITE_URL, {"person_ids": [ok.id, no_email.id]},
                format="json", **_hdr(org.slug),
            )

        assert r.status_code == 200, r.content
        assert r.data["sent_count"] == 1
        assert r.data["skipped_count"] == 1
        assert "no email" in r.data["skipped"][0]["reason"].lower()

    def test_will_not_invite_across_organizations(
        self, api, org, program, admin_user,
    ):
        other_org = Organization.objects.create(name="Other", slug="other-org")
        other_program = Program.all_objects.create(
            organization=other_org, name="Other 2026-27", slug="other-2026-27",
            program_type="religious_school",
            start_date=date(2026, 9, 1), end_date=date(2027, 5, 31),
        )
        outsider = _staff(
            other_org, other_program, first_name="Outsider",
            email="outsider@example.com",
        )

        api.force_authenticate(user=admin_user)
        with organization_context(org):
            r = api.post(
                BULK_INVITE_URL, {"person_ids": [outsider.id]},
                format="json", **_hdr(org.slug),
            )

        assert r.status_code == 200, r.content
        assert r.data["sent_count"] == 0
        assert r.data["skipped"][0]["reason"] == "Not found in this organization."
        outsider.refresh_from_db()
        assert outsider.invited_at is None

    def test_rejects_an_empty_selection(self, api, org, admin_user):
        api.force_authenticate(user=admin_user)
        with organization_context(org):
            r = api.post(
                BULK_INVITE_URL, {"person_ids": []}, format="json", **_hdr(org.slug),
            )
        assert r.status_code == 400


class TestGroupsOverview:
    @pytest.fixture(autouse=True)
    def groups(self, org, program):
        self.staffed = AssignmentGroup.all_objects.create(
            organization=org, program=program, name="Kitah Alef",
            slug="kitah-alef", group_type="classroom",
        )
        self.orphan = AssignmentGroup.all_objects.create(
            organization=org, program=program, name="Kitah Bet",
            slug="kitah-bet", group_type="classroom",
        )
        author = _staff(org, program, first_name="Faculty", email="fac@example.com")
        AssignmentGroupMembership.all_objects.create(
            group=self.staffed, person=author, role_in_group="author", is_active=True,
        )
        self.subjects = []
        for i in range(3):
            subject = Person.all_objects.create(
                organization=org, first_name=f"Madrich{i}", last_name="Student",
            )
            Membership.all_objects.create(
                program=program, person=subject, role="madrich", is_active=True,
            )
            AssignmentGroupMembership.all_objects.create(
                group=self.staffed, person=subject,
                role_in_group="subject", is_active=True,
            )
            self.subjects.append(subject)
        self.author = author

    def _overview(self, api, org, admin_user, **params):
        api.force_authenticate(user=admin_user)
        with organization_context(org):
            r = api.get(GROUPS_OVERVIEW_URL, params, **_hdr(org.slug))
        assert r.status_code == 200, r.content
        return {row["name"]: row for row in r.data["results"]}

    def test_counts_subjects_and_authors_per_group(self, api, org, admin_user):
        rows = self._overview(api, org, admin_user, program=self.staffed.program_id)
        assert rows["Kitah Alef"]["subject_count"] == 3
        assert rows["Kitah Alef"]["author_count"] == 1
        assert rows["Kitah Bet"]["subject_count"] == 0
        assert rows["Kitah Bet"]["author_count"] == 0

    def test_counts_this_week_submissions_against_expected(
        self, api, org, program, admin_user,
    ):
        template = ReflectionTemplate.all_objects.create(
            organization=org, name="Weekly", slug="weekly", version=1,
            schema={"fields": []}, status=ReflectionTemplate.Status.PUBLISHED,
        )
        today = timezone.localdate()
        for subject in self.subjects[:2]:
            Reflection.all_objects.create(
                organization=org, program=program, subject=subject,
                author=self.author, assignment_group=self.staffed,
                template=template, period_start=today - timedelta(days=6),
                period_end=today, answers={},
            )

        rows = self._overview(api, org, admin_user, program=program.id)
        assert rows["Kitah Alef"]["submitted"] == 2
        assert rows["Kitah Alef"]["expected"] == 3

    def test_a_group_with_no_subjects_reports_zero_of_zero_not_complete(
        self, api, org, admin_user,
    ):
        rows = self._overview(api, org, admin_user)
        assert rows["Kitah Bet"]["submitted"] == 0
        assert rows["Kitah Bet"]["expected"] == 0

    def test_orders_by_display_order_before_name(self, api, org, admin_user):
        self.orphan.display_order = 1
        self.orphan.save(update_fields=["display_order"])
        self.staffed.display_order = 2
        self.staffed.save(update_fields=["display_order"])

        api.force_authenticate(user=admin_user)
        with organization_context(org):
            r = api.get(GROUPS_OVERVIEW_URL, **_hdr(org.slug))
        names = [row["name"] for row in r.data["results"]]
        assert names == ["Kitah Bet", "Kitah Alef"]

    def test_requires_admin(self, api, org):
        outsider = User.objects.create_user(email="nogroups@example.com", password="pw")
        api.force_authenticate(user=outsider)
        with organization_context(org):
            r = api.get(GROUPS_OVERVIEW_URL, **_hdr(org.slug))
        assert r.status_code in (401, 403)


class TestNavBadges:
    """The sidebar's two counts."""

    def _badges(self, api, org, admin_user, **params):
        api.force_authenticate(user=admin_user)
        with organization_context(org):
            r = api.get(NAV_BADGES_URL, params, **_hdr(org.slug))
        assert r.status_code == 200, r.content
        return r.data

    def test_counts_people_who_have_never_been_invited(
        self, api, org, program, admin_user,
    ):
        _staff(org, program, first_name="Fresh", email="fresh@example.com")
        _staff(
            org, program, first_name="Waiting", email="waiting@example.com",
            invited_at=timezone.now() - timedelta(days=3),
        )
        # Campers are subjects of logs, never users, so they don't count.
        camper = Person.all_objects.create(
            organization=org, first_name="Kid", last_name="Camper",
        )
        Membership.all_objects.create(
            program=program, person=camper, role="camper", is_active=True,
        )

        data = self._badges(api, org, admin_user, program=program.id)
        # Fresh plus the admin fixture's own person.
        assert data["people_never_invited"] == 2

    def test_counts_a_group_broken_two_ways_only_once(
        self, api, org, program, admin_user,
    ):
        # No author and no subjects.
        AssignmentGroup.all_objects.create(
            organization=org, program=program, name="Kitah Vav",
            slug="kitah-vav", group_type="classroom",
        )
        # A staff team with no author is still broken, but not for subjects.
        AssignmentGroup.all_objects.create(
            organization=org, program=program, name="Ed Team",
            slug="ed-team", group_type="team",
        )

        data = self._badges(api, org, admin_user, program=program.id)
        assert data["groups_needing_attention"] == 2

    def test_scopes_groups_to_the_selected_program(self, api, org, admin_user):
        other = Program.all_objects.create(
            organization=org, name="Enabler Org 2025-26", slug="enabler-2025-26",
            program_type="religious_school",
            start_date=date(2025, 9, 1), end_date=date(2026, 5, 31),
        )
        AssignmentGroup.all_objects.create(
            organization=org, program=other, name="Old Class",
            slug="old-class", group_type="classroom",
        )

        assert self._badges(
            api, org, admin_user, program=other.id,
        )["groups_needing_attention"] == 1

    def test_requires_admin(self, api, org):
        outsider = User.objects.create_user(email="nobadges@example.com", password="pw")
        api.force_authenticate(user=outsider)
        with organization_context(org):
            r = api.get(NAV_BADGES_URL, **_hdr(org.slug))
        assert r.status_code in (401, 403)


class TestDashboardSetupAttention:
    def _dashboard(self, api, org, admin_user, **params):
        api.force_authenticate(user=admin_user)
        with organization_context(org):
            r = api.get(DASHBOARD_URL, params, **_hdr(org.slug))
        assert r.status_code == 200, r.content
        return r.data

    def test_names_the_groups_that_have_no_author(
        self, api, org, program, admin_user,
    ):
        AssignmentGroup.all_objects.create(
            organization=org, program=program, name="Kitah Gimel",
            slug="kitah-gimel", group_type="classroom",
        )
        data = self._dashboard(api, org, admin_user, program=program.id)

        attention = data["setup_attention"]["groups_without_author"]
        assert attention["count"] == 1
        assert attention["groups"][0]["name"] == "Kitah Gimel"

    def test_does_not_nag_staff_teams_about_having_no_subjects(
        self, api, org, program, admin_user,
    ):
        AssignmentGroup.all_objects.create(
            organization=org, program=program, name="Ed Team",
            slug="ed-team", group_type="team",
        )
        AssignmentGroup.all_objects.create(
            organization=org, program=program, name="Kitah Dalet",
            slug="kitah-dalet", group_type="classroom",
        )
        data = self._dashboard(api, org, admin_user, program=program.id)

        names = {g["name"] for g in data["setup_attention"]["groups_without_subjects"]["groups"]}
        assert names == {"Kitah Dalet"}

    def test_counts_never_invited_separately_from_invited_but_not_signed_in(
        self, api, org, program, admin_user,
    ):
        _staff(org, program, first_name="Fresh", email="fresh@example.com")
        _staff(
            org, program, first_name="Waiting", email="waiting@example.com",
            invited_at=timezone.now() - timedelta(days=3),
        )
        data = self._dashboard(api, org, admin_user, program=program.id)

        attention = data["setup_attention"]
        # The admin fixture's own person is also never-invited.
        assert attention["people_never_invited"]["count"] == 2
        assert attention["people_invited_not_signed_in"]["count"] == 1

    def test_lists_groups_behind_on_logs_most_behind_first(
        self, api, org, program, admin_user,
    ):
        template = ReflectionTemplate.all_objects.create(
            organization=org, name="Weekly", slug="weekly", version=1,
            schema={"fields": []}, status=ReflectionTemplate.Status.PUBLISHED,
        )
        today = timezone.localdate()

        def make_group(name, slug, subject_count, submitted_count):
            group = AssignmentGroup.all_objects.create(
                organization=org, program=program, name=name,
                slug=slug, group_type="classroom",
            )
            for i in range(subject_count):
                person = Person.all_objects.create(
                    organization=org, first_name=f"{slug}{i}", last_name="S",
                )
                AssignmentGroupMembership.all_objects.create(
                    group=group, person=person,
                    role_in_group="subject", is_active=True,
                )
                if i < submitted_count:
                    Reflection.all_objects.create(
                        organization=org, program=program, subject=person,
                        assignment_group=group, template=template,
                        period_start=today - timedelta(days=6),
                        period_end=today, answers={},
                    )
            return group

        make_group("Mostly done", "mostly-done", 4, 3)
        make_group("Way behind", "way-behind", 4, 1)
        # Staff-only group: no subjects, so it must not inflate the totals.
        AssignmentGroup.all_objects.create(
            organization=org, program=program, name="Staff only",
            slug="staff-only", group_type="team",
        )

        data = self._dashboard(api, org, admin_user, program=program.id)
        logs = data["logs_this_week"]

        assert logs["expected"] == 8
        assert logs["submitted"] == 4
        assert [g["name"] for g in logs["behind"]] == ["Way behind", "Mostly done"]

    def test_scopes_to_the_selected_program(self, api, org, admin_user):
        other = Program.all_objects.create(
            organization=org, name="Enabler Org 2025-26", slug="enabler-2025-26",
            program_type="religious_school",
            start_date=date(2025, 9, 1), end_date=date(2026, 5, 31),
        )
        AssignmentGroup.all_objects.create(
            organization=org, program=other, name="Old Class",
            slug="old-class", group_type="classroom",
        )
        data = self._dashboard(api, org, admin_user, program=other.id)

        names = {g["name"] for g in data["setup_attention"]["groups_without_author"]["groups"]}
        assert names == {"Old Class"}

    def test_reports_what_setup_already_got_right(
        self, api, org, program, admin_user,
    ):
        """The green rows: a card of only problems reads as "nothing works"."""
        group = AssignmentGroup.all_objects.create(
            organization=org, program=program, name="Kitah Hey",
            slug="kitah-hey", group_type="classroom",
        )
        AssignmentGroup.all_objects.create(
            organization=org, program=program, name="Kitah Zayin",
            slug="kitah-zayin", group_type="classroom",
        )
        for i in range(2):
            person = Person.all_objects.create(
                organization=org, first_name=f"Sub{i}", last_name="Ject",
            )
            AssignmentGroupMembership.all_objects.create(
                group=group, person=person, role_in_group="subject", is_active=True,
            )
        template = ReflectionTemplate.all_objects.create(
            organization=org, name="Weekly", slug="weekly", version=1,
            schema={"fields": []}, status=ReflectionTemplate.Status.PUBLISHED,
        )
        TemplateAssignment.all_objects.create(
            organization=org, program=program, template=template,
            target_type=TemplateAssignment.TargetType.ASSIGNMENT_GROUP,
            assignment_group=group, start_date=program.start_date,
            status=TemplateAssignment.Status.ACTIVE,
        )

        completed = self._dashboard(
            api, org, admin_user, program=program.id,
        )["setup_attention"]["completed"]

        assert completed["groups_total"] == 2
        assert completed["subjects_enrolled"] == 2
        # Kitah Zayin has no template assignment, so it isn't counted.
        assert completed["groups_with_forms"] == 1


class TestActivityDeepLinks:
    """Activity rows have to land somewhere that still exists."""

    def test_a_membership_row_opens_its_person_not_a_dead_route(
        self, api, org, program, admin_user,
    ):
        person = _staff(org, program, first_name="Linked", email="linked@example.com")
        membership = Membership.all_objects.get(person=person)
        AuditEvent.all_objects.create(
            organization=org, event_type=AuditEvent.EventType.DEACTIVATED,
            content_type="membership", content_id=membership.id,
        )

        api.force_authenticate(user=admin_user)
        with organization_context(org):
            r = api.get(DASHBOARD_URL, **_hdr(org.slug))

        row = next(
            e for e in r.data["recent_activity"] if e["content_type"] == "membership"
        )
        assert row["deep_link"] == f"/admin/people/{person.id}"

    def test_a_supervision_row_falls_back_to_the_groups_list(
        self, api, org, admin_user,
    ):
        AuditEvent.all_objects.create(
            organization=org, event_type=AuditEvent.EventType.CREATED,
            content_type="supervision", content_id=999,
        )

        api.force_authenticate(user=admin_user)
        with organization_context(org):
            r = api.get(DASHBOARD_URL, **_hdr(org.slug))

        row = next(
            e for e in r.data["recent_activity"] if e["content_type"] == "supervision"
        )
        assert row["deep_link"] == "/admin/groups"
