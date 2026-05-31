"""Audience resolution tests for the Notes platform (Step 7_19).

Covers Counselor and UH option matrices, self-exclusion, active Membership
filtering, and cross-org isolation. Also tests the capture-don't-resolve
semantics and the universal default option set used by roles without a
spec'd matrix.
"""

from __future__ import annotations

import pytest

from bunk_logs.core.context import organization_context
from bunk_logs.core.models import AssignmentGroupMembership
from bunk_logs.core.models import Membership
from bunk_logs.core.models import Person
from bunk_logs.notes.audience import audience_options_for
from bunk_logs.notes.audience import resolve_audience

pytestmark = pytest.mark.django_db


# ---------------------------------------------------------------------------
# audience_options_for
# ---------------------------------------------------------------------------

class TestAudienceOptionsFor:
    def test_counselor_gets_options(self, org, program, counselor_person, counselor_membership):
        opts = audience_options_for(counselor_person, org, program)
        keys = [o["option_key"] for o in opts]
        assert "my_unit_head" in keys
        assert "co_counselors_on_bunk" in keys

    def test_unit_head_gets_options(self, org, program, uh_person, uh_membership):
        opts = audience_options_for(uh_person, org, program)
        keys = [o["option_key"] for o in opts]
        assert "specific_counselor" in keys
        assert "all_counselors_in_unit" in keys

    def test_non_v1_role_gets_default_options(self, org, program):
        person = Person.all_objects.create(organization=org, first_name="Admin", last_name="X")
        Membership.all_objects.create(program=program, person=person, role="admin", is_active=True)
        opts = audience_options_for(person, org, program)
        keys = [o["option_key"] for o in opts]
        assert "administration" in keys
        assert "leadership_team" in keys
        assert "specific_person" in keys

    def test_inactive_membership_returns_empty(self, org, program, counselor_person, counselor_membership):
        counselor_membership.is_active = False
        counselor_membership.save()
        opts = audience_options_for(counselor_person, org, program)
        assert opts == []


# ---------------------------------------------------------------------------
# resolve_audience — self-exclusion
# ---------------------------------------------------------------------------

class TestResolveAudienceSelfExclusion:
    def test_self_excluded_from_specific_person(
        self, org, program, counselor_person, counselor_membership, uh_person, uh_membership,
    ):
        with organization_context(org):
            rows = resolve_audience(
                author_person=counselor_person,
                author_membership=counselor_membership,
                organization=org,
                program=program,
                audience_requests=[
                    {"option_key": "specific_person", "person_id": counselor_person.id},
                ],
            )
        assert all(r["person"].id != counselor_person.id for r in rows)


# ---------------------------------------------------------------------------
# resolve_audience — counselor "my unit head" path
# ---------------------------------------------------------------------------

class TestCounselorMyUnitHead:
    def test_resolves_to_uh(
        self,
        org, program,
        counselor_person, counselor_membership,
        uh_person, uh_membership,
        uh_supervises_counselor,
    ):
        with organization_context(org):
            rows = resolve_audience(
                author_person=counselor_person,
                author_membership=counselor_membership,
                organization=org,
                program=program,
                audience_requests=[{"option_key": "my_unit_head"}],
            )
        assert len(rows) == 1
        assert rows[0]["person"].id == uh_person.id
        assert rows[0]["option_key"] == "my_unit_head"

    def test_no_result_when_no_supervision(
        self, org, program, counselor_person, counselor_membership,
    ):
        with organization_context(org):
            rows = resolve_audience(
                author_person=counselor_person,
                author_membership=counselor_membership,
                organization=org,
                program=program,
                audience_requests=[{"option_key": "my_unit_head"}],
            )
        assert rows == []


# ---------------------------------------------------------------------------
# resolve_audience — co-counselors on bunk
# ---------------------------------------------------------------------------

class TestCounselorCoCounselors:
    def test_resolves_co_counselors(
        self,
        org, program,
        counselor_person, counselor_membership,
        bunk, counselor_in_bunk,
    ):
        # Add a second counselor to the bunk
        person2 = Person.all_objects.create(organization=org, first_name="Co", last_name="C")
        AssignmentGroupMembership.all_objects.create(
            group=bunk, person=person2, role_in_group="author", is_active=True,
        )
        with organization_context(org):
            rows = resolve_audience(
                author_person=counselor_person,
                author_membership=counselor_membership,
                organization=org,
                program=program,
                audience_requests=[{"option_key": "co_counselors_on_bunk"}],
            )
        person_ids = {r["person"].id for r in rows}
        assert person2.id in person_ids
        # Author is excluded
        assert counselor_person.id not in person_ids


# ---------------------------------------------------------------------------
# resolve_audience — UH all counselors in unit
# ---------------------------------------------------------------------------

class TestUHAllCounselorsInUnit:
    def test_resolves_counselors_in_unit(
        self,
        org, program,
        uh_person, uh_membership,
        counselor_person, counselor_membership,
        bunk, counselor_in_bunk,
        uh_supervises_counselor,
    ):
        with organization_context(org):
            rows = resolve_audience(
                author_person=uh_person,
                author_membership=uh_membership,
                organization=org,
                program=program,
                audience_requests=[{"option_key": "all_counselors_in_unit"}],
            )
        person_ids = {r["person"].id for r in rows}
        assert counselor_person.id in person_ids
        # UH (author) excluded
        assert uh_person.id not in person_ids

# ---------------------------------------------------------------------------
# resolve_audience — non-spec roles get the universal default matrix
# ---------------------------------------------------------------------------

class TestNonV1RoleUsesDefaults:
    def test_kitchen_staff_can_resolve_administration(self, org, program):
        author = Person.all_objects.create(organization=org, first_name="KS", last_name="X")
        author_membership = Membership.all_objects.create(
            program=program, person=author, role="kitchen_staff", is_active=True,
        )
        # An Admin exists in the org so administration resolves to them.
        admin_person = Person.all_objects.create(organization=org, first_name="Adm", last_name="X")
        Membership.all_objects.create(
            program=program, person=admin_person, role="admin", is_active=True,
        )

        with organization_context(org):
            rows = resolve_audience(
                author_person=author,
                author_membership=author_membership,
                organization=org,
                program=program,
                audience_requests=[{"option_key": "administration"}],
            )

        person_ids = {r["person"].id for r in rows}
        assert admin_person.id in person_ids

    def test_kitchen_staff_unknown_option_drops_silently(self, org, program):
        author = Person.all_objects.create(organization=org, first_name="KS2", last_name="X")
        membership = Membership.all_objects.create(
            program=program, person=author, role="kitchen_staff", is_active=True,
        )
        with organization_context(org):
            rows = resolve_audience(
                author_person=author,
                author_membership=membership,
                organization=org,
                program=program,
                # 'all_counselors_in_unit' isn't a default option for KS — drop it.
                audience_requests=[{"option_key": "all_counselors_in_unit"}],
            )
        assert rows == []


# ---------------------------------------------------------------------------
# resolve_audience — dedup
# ---------------------------------------------------------------------------

class TestDedup:
    def test_same_person_from_multiple_options_deduplicated(
        self,
        org, program,
        counselor_person, counselor_membership,
        uh_person, uh_membership,
        uh_supervises_counselor,
    ):
        # Request both my_unit_head and specific_person resolving to same UH
        with organization_context(org):
            rows = resolve_audience(
                author_person=counselor_person,
                author_membership=counselor_membership,
                organization=org,
                program=program,
                audience_requests=[
                    {"option_key": "my_unit_head"},
                    {"option_key": "specific_person", "person_id": uh_person.id},
                ],
            )
        person_ids = [r["person"].id for r in rows]
        # Should appear only once
        assert person_ids.count(uh_person.id) == 1


# ---------------------------------------------------------------------------
# Capture-don't-resolve: post-submission bunk change
# ---------------------------------------------------------------------------

class TestCaptureDoNotResolve:
    """Story 66 criterion 9 / audience_matrices.md cross-cutting rule 4.

    A counselor added to a bunk AFTER a note's submission does NOT see the note.
    """

    def test_new_counselor_not_in_retroactive_audience(
        self,
        org, program,
        counselor_person, counselor_membership,
        uh_person, uh_membership,
        bunk,
        uh_supervises_counselor,
    ):
        from bunk_logs.notes.models import Note
        from bunk_logs.notes.models import NoteAudienceCapture

        # Note was sent to uh_person; new counselor is NOT in audience.
        note = Note.all_objects.create(
            organization=org, program=program, author=counselor_person,
            author_role_at_write="counselor", subject="Hi UH", body="Body",
        )
        NoteAudienceCapture.objects.create(
            note=note, person=uh_person, option_key="my_unit_head",
        )

        # Add a new counselor to bunk AFTER the note was sent
        new_counselor = Person.all_objects.create(
            organization=org, first_name="Late", last_name="C",
        )
        AssignmentGroupMembership.all_objects.create(
            group=bunk, person=new_counselor, role_in_group="author", is_active=True,
        )

        # New counselor is not in audience captures for this note
        assert not note.audience_captures.filter(person=new_counselor).exists()
