"""API tests for the Observations endpoints (Step 7_23).

Covers create (success + the three rejection paths), inbox, thread + read
receipt, reply, archive idempotency, unread-count, recipient-candidates,
subject search, and cross-org isolation.
"""

from __future__ import annotations

import pytest
from rest_framework.test import APIClient

from bunk_logs.core.models import AssignmentGroupMembership
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

    def test_rejects_unauthorized_subject(
        self, org, program, counselor_user, counselor_membership,
    ):
        # Camper not in any group the counselor authors -> not authorable.
        stranger = Person.all_objects.create(organization=org, first_name="No", last_name="Reach")
        client = _auth_client(counselor_user, org)
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

    def test_thread_updates_read_receipt(
        self, org, program, counselor_person, counselor_membership, uh_user, uh_membership, uh_person, camper,
    ):
        obs = _make_observation(org, program, counselor_person, subjects=[camper], recipients=[uh_person])
        client = _auth_client(uh_user, org)
        resp = client.get(f"/api/v1/observations/{obs.id}/")
        assert resp.status_code == 200
        assert obs.read_receipts.filter(person=uh_person).exists()

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
        Membership.all_objects.create(program=other_program, person=other_person, role="admin", is_active=True)
        client = _auth_client(other_user, other_org)
        resp = client.get(f"/api/v1/observations/{obs.id}/")
        assert resp.status_code == 404
