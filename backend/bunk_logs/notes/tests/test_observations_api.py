"""API tests for the Observations endpoints (Step 7_23).

Covers create (success + the three rejection paths), inbox, thread + read
receipt, reply, archive idempotency, unread-count, recipient-candidates,
subject search, and cross-org isolation.
"""

from __future__ import annotations

from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from bunk_logs.core.models import AssignmentGroup
from bunk_logs.core.models import AssignmentGroupMembership
from bunk_logs.core.models import Membership
from bunk_logs.core.models import Person
from bunk_logs.notes.models import Observation
from bunk_logs.notes.models import ObservationArchive
from bunk_logs.notes.models import ObservationRecipient
from bunk_logs.notes.models import ObservationSubject

pytestmark = pytest.mark.django_db


def _auth_client(user, org):
    client = APIClient()
    client.force_authenticate(user=user)
    client.defaults["HTTP_X_ORGANIZATION_SLUG"] = org.slug
    return client


@pytest.fixture
def camper(org, bunk):
    person = Person.all_objects.create(organization=org, first_name="Cam", last_name="Per")
    AssignmentGroupMembership.all_objects.create(
        group=bunk, person=person, role_in_group="subject", is_active=True,
    )
    return person


def _make_observation(org, program, author, *, sensitivity="normal", subjects=None, recipients=None):
    obs = Observation.all_objects.create(
        organization=org, program=program, author=author,
        author_role_at_write="counselor", body="b", sensitivity=sensitivity,
    )
    for s in subjects or []:
        ObservationSubject.objects.create(observation=obs, subject=s)
    for r in recipients or []:
        ObservationRecipient.objects.create(observation=obs, person=r, option_key="specific_person")
    return obs


# ---------------------------------------------------------------------------
# POST /api/v1/observations/
# ---------------------------------------------------------------------------
class TestCreate:
    def test_counselor_creates_about_supervised_camper(
        self, org, program, counselor_user, counselor_membership, counselor_in_bunk, camper, uh_membership, uh_person,
    ):
        client = _auth_client(counselor_user, org)
        resp = client.post(
            "/api/v1/observations/",
            {
                "subject_ids": [camper.id],
                "recipient_ids": [uh_person.id],
                "body": "Saw something at swim.",
                "sensitivity": "normal",
                "context": "swim",
            },
            format="json",
        )
        assert resp.status_code == 201, resp.json()
        data = resp.json()
        assert [s["id"] for s in data["subjects"]] == [camper.id]
        assert any(r["person"]["id"] == uh_person.id for r in data["recipients"])

    def test_allows_org_person_without_bunk_agm(
        self, org, program, counselor_user, counselor_membership,
    ):
        """Observation subjects are org-wide for staff who may write observations."""
        stranger = Person.all_objects.create(organization=org, first_name="No", last_name="Reach")
        client = _auth_client(counselor_user, org)
        resp = client.post(
            "/api/v1/observations/",
            {"subject_ids": [stranger.id], "body": "x", "sensitivity": "normal"},
            format="json",
        )
        assert resp.status_code == 201, resp.json()

    def test_rejects_subject_when_author_scope_none(self, org, program):
        from bunk_logs.users.models import User

        kitchen_user = User.objects.create_user(
            email="kitchen-obs@t.test", password="pw",
        )
        kitchen_person = Person.all_objects.create(
            organization=org, first_name="Kit", last_name="Chen", user=kitchen_user,
        )
        Membership.all_objects.create(
            program=program, person=kitchen_person, role="kitchen_staff", is_active=True,
        )
        stranger = Person.all_objects.create(organization=org, first_name="No", last_name="Reach")
        client = _auth_client(kitchen_user, org)
        resp = client.post(
            "/api/v1/observations/",
            {"subject_ids": [stranger.id], "body": "x", "sensitivity": "normal"},
            format="json",
        )
        assert resp.status_code == 400
        assert "subject_ids" in resp.json()

    def test_rejects_under_cleared_recipient(
        self, org, program, counselor_user, counselor_membership, counselor_in_bunk, camper,
        uh_membership, uh_person,
    ):
        # UH (supervisor) does not clear 'confidential'.
        client = _auth_client(counselor_user, org)
        resp = client.post(
            "/api/v1/observations/",
            {
                "subject_ids": [camper.id],
                "recipient_ids": [uh_person.id],
                "body": "secret",
                "sensitivity": "confidential",
            },
            format="json",
        )
        assert resp.status_code == 400
        assert "recipient_ids" in resp.json()

    def test_rejects_no_subject(self, org, program, counselor_user, counselor_membership):
        client = _auth_client(counselor_user, org)
        resp = client.post(
            "/api/v1/observations/",
            {"subject_ids": [], "body": "x"},
            format="json",
        )
        assert resp.status_code == 400

    def test_create_with_backdated_observed_at(
        self, org, program, counselor_user, counselor_membership, counselor_in_bunk, camper,
    ):
        past = (timezone.now() - timedelta(days=1)).isoformat()
        client = _auth_client(counselor_user, org)
        resp = client.post(
            "/api/v1/observations/",
            {
                "subject_ids": [camper.id],
                "body": "Yesterday at swim.",
                "sensitivity": "normal",
                "observed_at": past,
            },
            format="json",
        )
        assert resp.status_code == 201, resp.json()
        assert resp.json()["observed_at"] is not None

    def test_rejects_future_observed_at(
        self, org, program, counselor_user, counselor_membership, counselor_in_bunk, camper,
    ):
        future = (timezone.now() + timedelta(hours=2)).isoformat()
        client = _auth_client(counselor_user, org)
        resp = client.post(
            "/api/v1/observations/",
            {
                "subject_ids": [camper.id],
                "body": "x",
                "sensitivity": "normal",
                "observed_at": future,
            },
            format="json",
        )
        assert resp.status_code == 400
        assert "observed_at" in resp.json()


# ---------------------------------------------------------------------------
# Inbox / thread / reply / unread
# ---------------------------------------------------------------------------
class TestInboxAndThread:
    def test_inbox_shows_recipient_observations(
        self, org, program, counselor_person, counselor_membership, uh_user, uh_membership, uh_person, camper,
    ):
        obs = _make_observation(org, program, counselor_person, subjects=[camper], recipients=[uh_person])
        client = _auth_client(uh_user, org)
        resp = client.get("/api/v1/observations/inbox/")
        assert resp.status_code == 200
        ids = [o["id"] for o in resp.json().get("results", resp.json())]
        assert obs.id in ids

    def test_sent_shows_authored_observations(
        self, org, program, counselor_user, counselor_membership, counselor_person, camper,
    ):
        obs = _make_observation(org, program, counselor_person, subjects=[camper], recipients=[])
        client = _auth_client(counselor_user, org)
        resp = client.get("/api/v1/observations/sent/")
        assert resp.status_code == 200
        ids = [o["id"] for o in resp.json().get("results", resp.json())]
        assert obs.id in ids

        inbox = client.get("/api/v1/observations/inbox/")
        inbox_ids = [o["id"] for o in inbox.json().get("results", inbox.json())]
        assert obs.id not in inbox_ids

    def test_thread_updates_read_receipt(
        self, org, program, counselor_person, counselor_membership, uh_user, uh_membership, uh_person, camper,
    ):
        obs = _make_observation(org, program, counselor_person, subjects=[camper], recipients=[uh_person])
        client = _auth_client(uh_user, org)
        resp = client.get(f"/api/v1/observations/{obs.id}/")
        assert resp.status_code == 200
        assert obs.read_receipts.filter(person=uh_person).exists()

    def test_thread_subject_can_view_profile_supervised_camper(
        self, org, program, counselor_user, counselor_membership, counselor_person,
        counselor_in_bunk, camper,
    ):
        obs = _make_observation(org, program, counselor_person, subjects=[camper])
        client = _auth_client(counselor_user, org)
        resp = client.get(f"/api/v1/observations/{obs.id}/")
        assert resp.status_code == 200
        subjects = resp.json()["subjects"]
        assert subjects[0]["id"] == camper.id
        assert subjects[0]["can_view_profile"] is True

    def test_thread_subject_can_view_profile_false_outside_supervision(
        self, org, program, counselor_user, counselor_membership, counselor_in_bunk, bunk,
    ):
        other_bunk = AssignmentGroup.all_objects.create(
            organization=org, program=bunk.program, name="Bunk Oak",
            slug="bunk-oak", group_type="bunk",
        )
        distant = Person.all_objects.create(organization=org, first_name="Far", last_name="Away")
        AssignmentGroupMembership.all_objects.create(
            group=other_bunk, person=distant, role_in_group="subject", is_active=True,
        )
        author = Person.all_objects.filter(user=counselor_user).first()
        obs = _make_observation(org, program, author, subjects=[distant])
        client = _auth_client(counselor_user, org)
        resp = client.get(f"/api/v1/observations/{obs.id}/")
        assert resp.status_code == 200
        assert resp.json()["subjects"][0]["can_view_profile"] is False

    def test_thread_subject_can_view_profile_true_for_supervisor(
        self, org, program, uh_user, uh_membership, uh_person, bunk, camper,
    ):
        AssignmentGroupMembership.all_objects.create(
            group=bunk, person=uh_person, role_in_group="author", is_active=True,
        )
        obs = _make_observation(org, program, uh_person, subjects=[camper])
        client = _auth_client(uh_user, org)
        resp = client.get(f"/api/v1/observations/{obs.id}/")
        assert resp.status_code == 200
        assert resp.json()["subjects"][0]["can_view_profile"] is True

    def test_thread_subject_can_view_profile_true_for_org_admin(
        self, org, program, camper,
    ):
        from bunk_logs.users.models import User

        admin_user = User.objects.create_user(
            email="org-admin-obs@t.test", password="pw", role=User.ADMIN,
        )
        admin_person = Person.all_objects.create(
            organization=org, first_name="Org", last_name="Admin", user=admin_user,
        )
        Membership.all_objects.create(
            program=program, person=admin_person, role="admin", is_active=True,
        )
        author = Person.all_objects.create(organization=org, first_name="Auth", last_name="Or")
        obs = _make_observation(org, program, author, subjects=[camper])
        client = _auth_client(admin_user, org)
        resp = client.get(f"/api/v1/observations/{obs.id}/")
        assert resp.status_code == 200
        assert resp.json()["subjects"][0]["can_view_profile"] is True

    def test_thread_subject_can_view_profile_true_for_legacy_user_role_admin(
        self, org, program, counselor_in_bunk, camper,
    ):
        """User.role Admin with only counselor membership still sees profile links."""
        from bunk_logs.users.models import User

        admin_user = User.objects.create_user(
            email="legacy-admin-obs@t.test", password="pw", role=User.ADMIN,
        )
        admin_person = Person.all_objects.create(
            organization=org, first_name="Legacy", last_name="Admin", user=admin_user,
        )
        Membership.all_objects.create(
            program=program, person=admin_person, role="counselor", is_active=True,
        )
        other_bunk = AssignmentGroup.all_objects.create(
            organization=org, program=program, name="Bunk Pine",
            slug="bunk-pine", group_type="bunk",
        )
        distant = Person.all_objects.create(organization=org, first_name="Far", last_name="Camper")
        AssignmentGroupMembership.all_objects.create(
            group=other_bunk, person=distant, role_in_group="subject", is_active=True,
        )
        author = Person.all_objects.filter(user=admin_user).first()
        obs = _make_observation(org, program, author, subjects=[distant])
        client = _auth_client(admin_user, org)
        resp = client.get(f"/api/v1/observations/{obs.id}/")
        assert resp.status_code == 200
        assert resp.json()["subjects"][0]["can_view_profile"] is True

    def test_reply_appends(
        self, org, program, counselor_person, counselor_membership, uh_user, uh_membership, uh_person, camper,
    ):
        obs = _make_observation(org, program, counselor_person, subjects=[camper], recipients=[uh_person])
        client = _auth_client(uh_user, org)
        resp = client.post(f"/api/v1/observations/{obs.id}/replies/", {"body": "Thanks"}, format="json")
        assert resp.status_code == 201
        assert obs.replies.count() == 1

    def test_unread_count(
        self, org, program, counselor_person, counselor_membership, uh_user, uh_membership, uh_person, camper,
    ):
        _make_observation(org, program, counselor_person, subjects=[camper], recipients=[uh_person])
        client = _auth_client(uh_user, org)
        resp = client.get("/api/v1/observations/unread-count/")
        assert resp.status_code == 200
        assert resp.json()["count"] >= 1


# ---------------------------------------------------------------------------
# Archive idempotency
# ---------------------------------------------------------------------------
class TestArchive:
    def test_archive_then_unarchive(
        self, org, program, counselor_person, counselor_membership, uh_user, uh_membership, uh_person, camper,
    ):
        obs = _make_observation(org, program, counselor_person, subjects=[camper], recipients=[uh_person])
        client = _auth_client(uh_user, org)
        assert client.post(f"/api/v1/observations/{obs.id}/archive/").status_code == 200
        assert client.post(f"/api/v1/observations/{obs.id}/archive/").status_code == 200  # idempotent
        assert ObservationArchive.objects.filter(observation=obs, person=uh_person).count() == 1
        assert client.post(f"/api/v1/observations/{obs.id}/unarchive/").status_code == 200
        assert not ObservationArchive.objects.filter(observation=obs, person=uh_person).exists()


# ---------------------------------------------------------------------------
# recipient-candidates + subjects search + cross-org
# ---------------------------------------------------------------------------
class TestCandidatesAndSearch:
    def test_recipient_candidates_filtered_by_tier(
        self, org, program, counselor_user, counselor_membership, uh_membership, uh_person,
    ):
        client = _auth_client(counselor_user, org)
        normal = client.get("/api/v1/observations/recipient-candidates/?sensitivity=normal")
        assert normal.status_code == 200
        normal_ids = [p["id"] for p in normal.json()["persons"]]
        assert uh_person.id in normal_ids  # supervisor clears normal

        conf = client.get("/api/v1/observations/recipient-candidates/?sensitivity=confidential")
        conf_ids = [p["id"] for p in conf.json()["persons"]]
        assert uh_person.id not in conf_ids  # supervisor does not clear confidential

    def test_subjects_search(
        self, org, program, counselor_user, counselor_membership, counselor_in_bunk, camper,
    ):
        client = _auth_client(counselor_user, org)
        resp = client.get("/api/v1/observations/subjects/?q=Cam")
        assert resp.status_code == 200
        ids = [s["id"] for s in resp.json()["subjects"]]
        assert camper.id in ids

    def test_subjects_search_full_name(
        self, org, program, counselor_user, counselor_membership, counselor_in_bunk, camper,
    ):
        client = _auth_client(counselor_user, org)
        resp = client.get("/api/v1/observations/subjects/?q=Cam%20Per")
        assert resp.status_code == 200
        ids = [s["id"] for s in resp.json()["subjects"]]
        assert camper.id in ids

    def test_subjects_search_without_bunk_author_agm(
        self, org, program, counselor_user, counselor_membership, camper,
    ):
        """Observations subjects are org-wide — no counselor AGM author required."""
        client = _auth_client(counselor_user, org)
        resp = client.get("/api/v1/observations/subjects/?q=Cam")
        assert resp.status_code == 200
        ids = [s["id"] for s in resp.json()["subjects"]]
        assert camper.id in ids

    def test_cross_org_thread_not_found(
        self, org, other_org, other_program, program, counselor_person, counselor_membership, camper,
    ):
        from bunk_logs.users.models import User
        obs = _make_observation(org, program, counselor_person, subjects=[camper])
        other_user = User.objects.create_user(email="other-obs@t.test", password="pw")
        other_person = Person.all_objects.create(
            organization=other_org, first_name="O", last_name="Ther", user=other_user,
        )
        from bunk_logs.core.models import Membership
        Membership.all_objects.create(
            program=other_program, person=other_person, role="counselor", is_active=True,
        )
        client = _auth_client(other_user, other_org)
        resp = client.get(f"/api/v1/observations/{obs.id}/")
        assert resp.status_code == 404
