"""Step 4_9 role homepages: threads, cohort feed, and the §7 permission matrix.

Organized by the thing that would break in production:

* ``TestMaterialization`` — submit-time thread/share creation, including the
  regression that a template with no flags creates nothing.
* ``TestThreadPermissions`` — every row of the §7 table, positive and
  negative, plus cross-org isolation.
* ``TestQueues`` — routed items land in the right queue, sort oldest-first,
  and leave it on resolve.
* ``TestCohortFeed`` — visibility, self-like refusal, director moderation.
* ``TestTrends`` — series come from the schema, not from hardcoded keys.
* ``TestDirector`` — pulse, coverage vocabulary, theme suppression, export.
* ``TestQueryCounts`` — the three homepages stay bounded as rosters grow.
"""

from __future__ import annotations

from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from bunk_logs.core.context import organization_context
from bunk_logs.core.models import AssignmentGroup
from bunk_logs.core.models import AssignmentGroupMembership
from bunk_logs.core.models import CohortShare
from bunk_logs.core.models import EntryThread
from bunk_logs.core.models import MadrichAvailability
from bunk_logs.core.models import Membership
from bunk_logs.core.models import Organization
from bunk_logs.core.models import Person
from bunk_logs.core.models import Program
from bunk_logs.core.models import Reflection
from bunk_logs.core.models import ReflectionTemplate
from bunk_logs.core.models import ShareReaction
from bunk_logs.core.models import ThreadMessage
from bunk_logs.core.reflection_threads import materialize_threads_and_shares
from bunk_logs.core.time_utils import get_today

User = get_user_model()
pytestmark = pytest.mark.django_db

MADRICH_TEMPLATE_SLUG = "tbe-madrich-3-2-1-weekly"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _hdr(slug: str) -> dict:
    return {"HTTP_X_ORGANIZATION_SLUG": slug}


@pytest.fixture
def api() -> APIClient:
    return APIClient()


@pytest.fixture
def org():
    return Organization.objects.create(name="Homepages TBE", slug="hp-tbe")


@pytest.fixture
def next_sunday(org):
    today = get_today(org)
    return today + timedelta(days=(6 - today.weekday()) % 7 or 7)


@pytest.fixture
def program(org, next_sunday):
    today = get_today(org)
    return Program.all_objects.create(
        organization=org,
        name=f"{org.name} Religious School",
        slug="hp-rs",
        program_type="religious_school",
        start_date=today - timedelta(days=60),
        end_date=today + timedelta(days=200),
        settings={"session_dates": [next_sunday.isoformat()]},
    )


@pytest.fixture
def classroom(org, program):
    return AssignmentGroup.all_objects.create(
        organization=org, program=program, name="Tzedakah 101",
        slug="hp-tzedakah", group_type="classroom", is_active=True,
    )


@pytest.fixture
def template():
    return ReflectionTemplate.all_objects.get(slug=MADRICH_TEMPLATE_SLUG)


def _person(org, first, last, email=None):
    user = User.objects.create_user(email=email, password="pw") if email else None
    person = Person.all_objects.create(
        organization=org, first_name=first, last_name=last, user=user,
    )
    return person, user


def _madrich(org, program, classroom, first, email=None, grade=10):
    person, user = _person(org, first, "Rich", email)
    Membership.all_objects.create(
        program=program, person=person, role="madrich",
        grade_level=grade, is_active=True,
    )
    if classroom is not None:
        AssignmentGroupMembership.all_objects.create(
            group=classroom, person=person, role_in_group="subject", is_active=True,
        )
    return person, user


def _faculty(org, program, classroom, first="Fay", email="fac@hp.test"):
    person, user = _person(org, first, "Teacher", email)
    Membership.all_objects.create(
        program=program, person=person, role="faculty", is_active=True,
    )
    if classroom is not None:
        AssignmentGroupMembership.all_objects.create(
            group=classroom, person=person, role_in_group="author", is_active=True,
        )
    return person, user


def _admin(org, program, email="dir@hp.test"):
    person, user = _person(org, "Dee", "Rector", email)
    Membership.all_objects.create(
        program=program, person=person, role="admin", is_active=True,
    )
    return person, user


def _submit(org, program, template, author, *, answers, weeks_ago=0):
    today = get_today(org)
    monday = today - timedelta(days=today.weekday() + 7 * weeks_ago)
    reflection = Reflection.all_objects.create(
        organization=org, program=program, template=template,
        author=author, subject=author,
        period_start=monday, period_end=monday + timedelta(days=6),
        answers=answers, language="en", is_complete=True,
    )
    materialize_threads_and_shares(reflection)
    return reflection


ANSWERS = {
    "wins": ["Led a great game", "Helped a shy kid", "Ran snack solo"],
    "improvements": ["Arrive earlier", "Speak up more"],
    "question_or_concern": "How do I handle a kid who won't participate?",
    "shared_idea": "We tried a name game and it worked really well.",
    "ratings": {
        "reliability_punctuality": 3,
        "initiative": 4,
        "communication": 3,
        "problem_solving": 2,
        "interpersonal": 4,
    },
}


def _get(api, org, url, **params):
    with organization_context(org):
        return api.get(url, params or None, **_hdr(org.slug))


def _post(api, org, url, payload=None):
    with organization_context(org):
        return api.post(url, payload or {}, format="json", **_hdr(org.slug))


# ---------------------------------------------------------------------------
# Materialization
# ---------------------------------------------------------------------------


class TestMaterialization:
    def test_flagged_fields_become_threads_and_shares(
        self, org, program, classroom, template,
    ):
        madrich, _ = _madrich(org, program, classroom, "Ari")
        reflection = _submit(org, program, template, madrich, answers=ANSWERS)

        threads = EntryThread.all_objects.filter(reflection=reflection)
        keys = sorted((t.field_key, t.item_index) for t in threads)
        assert keys == [
            ("improvements", 0), ("improvements", 1),
            ("question_or_concern", None),
            ("shared_idea", None),
            ("wins", 0), ("wins", 1), ("wins", 2),
        ]
        # routes_to is snapshotted off the schema, not read live.
        routed = threads.get(field_key="question_or_concern")
        assert routed.routes_to == EntryThread.ROUTES_TO_DIRECTOR

        share = CohortShare.all_objects.get(reflection=reflection)
        assert share.field_key == "shared_idea"
        assert share.assignment_group_id == classroom.id
        assert share.body == ANSWERS["shared_idea"]

    def test_template_without_flags_creates_nothing(self, org, program):
        """§8 regression: an unflagged template must stay inert."""
        plain = ReflectionTemplate.all_objects.create(
            organization=org, name="Plain", slug="hp-plain", version=1,
            schema={"fields": [
                {"key": "note", "type": "textarea", "prompts": {"en": "Note"}},
            ]},
            languages=["en"], subject_mode="self", assignment_scope="none",
            is_active=True,
        )
        person, _ = _madrich(org, program, None, "Solo")
        reflection = _submit(
            org, program, plain, person, answers={"note": "hello"},
        )
        assert not EntryThread.all_objects.filter(reflection=reflection).exists()
        assert not CohortShare.all_objects.filter(reflection=reflection).exists()

    def test_empty_optional_answer_creates_no_thread(
        self, org, program, classroom, template,
    ):
        madrich, _ = _madrich(org, program, classroom, "Bex")
        answers = dict(ANSWERS, shared_idea="")
        reflection = _submit(org, program, template, madrich, answers=answers)
        assert not EntryThread.all_objects.filter(
            reflection=reflection, field_key="shared_idea",
        ).exists()
        assert not CohortShare.all_objects.filter(reflection=reflection).exists()

    def test_resubmit_is_idempotent_and_refreshes_the_share(
        self, org, program, classroom, template,
    ):
        madrich, _ = _madrich(org, program, classroom, "Cy")
        reflection = _submit(org, program, template, madrich, answers=ANSWERS)
        before = EntryThread.all_objects.filter(reflection=reflection).count()

        reflection.answers = dict(ANSWERS, shared_idea="Revised idea.")
        reflection.save(update_fields=["answers"])
        materialize_threads_and_shares(reflection)

        assert EntryThread.all_objects.filter(reflection=reflection).count() == before
        assert CohortShare.all_objects.get(reflection=reflection).body == "Revised idea."

    def test_conversation_survives_the_answer_being_cleared(
        self, org, program, classroom, template,
    ):
        """An edit must not delete a thread somebody has already replied on."""
        madrich, _ = _madrich(org, program, classroom, "Dov")
        faculty, _ = _faculty(org, program, classroom)
        reflection = _submit(org, program, template, madrich, answers=ANSWERS)
        thread = EntryThread.all_objects.get(
            reflection=reflection, field_key="shared_idea",
        )
        message = ThreadMessage.all_objects.create(
            thread=thread, author=faculty, body="Love this.",
        )
        thread.last_message_at = message.created_at
        thread.save(update_fields=["last_message_at"])

        reflection.answers = dict(ANSWERS, shared_idea="")
        reflection.save(update_fields=["answers"])
        materialize_threads_and_shares(reflection)

        assert EntryThread.all_objects.filter(id=thread.id).exists()


# ---------------------------------------------------------------------------
# §7 permission matrix
# ---------------------------------------------------------------------------


class TestThreadPermissions:
    @pytest.fixture
    def scene(self, org, program, classroom, template):
        madrich, madrich_user = _madrich(
            org, program, classroom, "Ari", email="ari@hp.test",
        )
        peer, peer_user = _madrich(
            org, program, classroom, "Peer", email="peer@hp.test",
        )
        faculty, faculty_user = _faculty(org, program, classroom)
        admin, admin_user = _admin(org, program)
        reflection = _submit(org, program, template, madrich, answers=ANSWERS)
        threads = {
            (t.field_key, t.item_index): t
            for t in EntryThread.all_objects.filter(reflection=reflection)
        }
        return {
            "madrich": madrich_user, "peer": peer_user,
            "faculty": faculty_user, "admin": admin_user,
            "madrich_person": madrich, "faculty_person": faculty,
            "win": threads[("wins", 0)],
            "director_routed": threads[("question_or_concern", None)],
            "reflection": reflection,
        }

    def test_author_reads_own_entry(self, api, org, scene):
        api.force_authenticate(user=scene["madrich"])
        url = f"/api/v1/threads/{scene['win'].id}/"
        resp = _get(api, org, url)
        assert resp.status_code == 200, resp.content
        assert resp.json()["body"] == "Led a great game"

    def test_peer_madrich_cannot_read_another_entry(self, api, org, scene):
        api.force_authenticate(user=scene["peer"])
        resp = _get(api, org, f"/api/v1/threads/{scene['win'].id}/")
        assert resp.status_code == 403

    def test_peer_madrich_cannot_read_director_routed_entry(self, api, org, scene):
        """§7: a peer never sees another Madrich's question or concern."""
        api.force_authenticate(user=scene["peer"])
        resp = _get(api, org, f"/api/v1/threads/{scene['director_routed'].id}/")
        assert resp.status_code == 403

    def test_supervising_faculty_reads_a_supervised_entry(self, api, org, scene):
        api.force_authenticate(user=scene["faculty"])
        resp = _get(api, org, f"/api/v1/threads/{scene['win'].id}/")
        assert resp.status_code == 200, resp.content

    def test_faculty_cannot_read_director_routed_entry(self, api, org, scene):
        api.force_authenticate(user=scene["faculty"])
        resp = _get(api, org, f"/api/v1/threads/{scene['director_routed'].id}/")
        assert resp.status_code == 403

    def test_non_supervising_faculty_denied(
        self, api, org, program, classroom, scene,
    ):
        other_room = AssignmentGroup.all_objects.create(
            organization=org, program=program, name="Torah 201",
            slug="hp-torah", group_type="classroom", is_active=True,
        )
        _, outsider = _faculty(
            org, program, other_room, first="Otto", email="otto@hp.test",
        )
        api.force_authenticate(user=outsider)
        resp = _get(api, org, f"/api/v1/threads/{scene['win'].id}/")
        assert resp.status_code == 403

    def test_admin_reads_everything_including_director_routed(self, api, org, scene):
        api.force_authenticate(user=scene["admin"])
        for thread in (scene["win"], scene["director_routed"]):
            resp = _get(api, org, f"/api/v1/threads/{thread.id}/")
            assert resp.status_code == 200, resp.content

    def test_author_message_is_marked_as_a_self_update(self, api, org, scene):
        api.force_authenticate(user=scene["madrich"])
        resp = _post(
            api, org, f"/api/v1/threads/{scene['win'].id}/messages/",
            {"body": "I did this again this week."},
        )
        assert resp.status_code == 201, resp.content
        assert resp.json()["is_self_update"] is True

    def test_faculty_reply_is_not_a_self_update(self, api, org, scene):
        api.force_authenticate(user=scene["faculty"])
        resp = _post(
            api, org, f"/api/v1/threads/{scene['win'].id}/messages/",
            {"body": "Nicely done."},
        )
        assert resp.status_code == 201, resp.content
        body = resp.json()
        assert body["is_self_update"] is False
        assert body["author"]["role"] == "faculty"

    def test_madrich_cannot_resolve(self, api, org, scene):
        api.force_authenticate(user=scene["madrich"])
        resp = _post(api, org, f"/api/v1/threads/{scene['win'].id}/resolve/")
        assert resp.status_code == 403

    def test_faculty_cannot_resolve_an_unrouted_entry(self, api, org, scene):
        api.force_authenticate(user=scene["faculty"])
        resp = _post(api, org, f"/api/v1/threads/{scene['win'].id}/resolve/")
        assert resp.status_code == 403

    def test_admin_resolves_a_director_routed_entry(self, api, org, scene):
        api.force_authenticate(user=scene["admin"])
        resp = _post(
            api, org, f"/api/v1/threads/{scene['director_routed'].id}/resolve/",
        )
        assert resp.status_code == 200, resp.content
        assert resp.json()["resolved_at"] is not None

    def test_resolved_thread_rejects_further_messages(self, api, org, scene):
        api.force_authenticate(user=scene["admin"])
        _post(api, org, f"/api/v1/threads/{scene['director_routed'].id}/resolve/")
        resp = _post(
            api, org, f"/api/v1/threads/{scene['director_routed'].id}/messages/",
            {"body": "One more thing."},
        )
        assert resp.status_code == 403

    def test_cross_org_thread_is_not_reachable(self, api, org, scene):
        other_org = Organization.objects.create(name="Other", slug="hp-other")
        today = get_today(other_org)
        other_program = Program.all_objects.create(
            organization=other_org, name="Other RS", slug="hp-other-rs",
            program_type="religious_school",
            start_date=today - timedelta(days=30),
            end_date=today + timedelta(days=200),
        )
        _, intruder = _admin(other_org, other_program, email="intruder@other.test")
        api.force_authenticate(user=intruder)
        resp = _get(api, other_org, f"/api/v1/threads/{scene['win'].id}/")
        assert resp.status_code == 403

    def test_unread_clears_once_the_author_opens_the_thread(self, api, org, scene):
        api.force_authenticate(user=scene["faculty"])
        _post(
            api, org, f"/api/v1/threads/{scene['win'].id}/messages/",
            {"body": "Great work."},
        )
        api.force_authenticate(user=scene["madrich"])
        listing = _get(api, org, "/api/v1/threads/", field_key="wins").json()
        row = next(r for r in listing["results"] if r["id"] == scene["win"].id)
        assert row["unread"] is True

        _get(api, org, f"/api/v1/threads/{scene['win'].id}/")
        listing = _get(api, org, "/api/v1/threads/", field_key="wins").json()
        row = next(r for r in listing["results"] if r["id"] == scene["win"].id)
        assert row["unread"] is False

    def test_own_message_does_not_badge_the_author(self, api, org, scene):
        api.force_authenticate(user=scene["madrich"])
        _post(
            api, org, f"/api/v1/threads/{scene['win'].id}/messages/",
            {"body": "Self note."},
        )
        listing = _get(api, org, "/api/v1/threads/", unread="true").json()
        assert all(r["id"] != scene["win"].id for r in listing["results"])


# ---------------------------------------------------------------------------
# Queues
# ---------------------------------------------------------------------------


class TestQueues:
    @pytest.fixture
    def routed_scene(self, org, program, classroom, template):
        faculty, faculty_user = _faculty(org, program, classroom)
        _, admin_user = _admin(org, program)
        older, _ = _madrich(org, program, classroom, "Older")
        newer, _ = _madrich(org, program, classroom, "Newer")
        old_reflection = _submit(
            org, program, template, older, answers=ANSWERS, weeks_ago=3,
        )
        new_reflection = _submit(org, program, template, newer, answers=ANSWERS)
        # Age the older reflection's threads so escalation has something to see.
        EntryThread.all_objects.filter(reflection=old_reflection).update(
            created_at=old_reflection.period_start,
        )
        return {
            "faculty": faculty_user, "admin": admin_user,
            "faculty_person": faculty,
            "older": older, "newer": newer,
            "old_reflection": old_reflection, "new_reflection": new_reflection,
        }

    def test_director_queue_holds_only_director_routed_entries(
        self, api, org, routed_scene,
    ):
        api.force_authenticate(user=routed_scene["admin"])
        resp = _get(api, org, "/api/v1/admin/reflections/queue/")
        assert resp.status_code == 200, resp.content
        rows = resp.json()["results"]
        assert rows
        assert {r["field_key"] for r in rows} == {"question_or_concern"}

    def test_director_queue_sorts_oldest_first_and_escalates(
        self, api, org, routed_scene,
    ):
        api.force_authenticate(user=routed_scene["admin"])
        rows = _get(api, org, "/api/v1/admin/reflections/queue/").json()["results"]
        assert rows[0]["subject_person"]["id"] == routed_scene["older"].id
        assert rows[0]["escalation"] == "overdue"
        assert rows[-1]["escalation"] == "fresh"

    def test_faculty_queue_excludes_director_routed_entries(
        self, api, org, routed_scene,
    ):
        api.force_authenticate(user=routed_scene["faculty"])
        resp = _get(api, org, "/api/v1/faculty/queue/")
        assert resp.status_code == 200, resp.content
        assert all(
            r["field_key"] != "question_or_concern" for r in resp.json()["results"]
        )

    def test_resolving_removes_an_item_from_the_queue(self, api, org, routed_scene):
        api.force_authenticate(user=routed_scene["admin"])
        rows = _get(api, org, "/api/v1/admin/reflections/queue/").json()["results"]
        target = rows[0]["id"]
        _post(api, org, f"/api/v1/threads/{target}/resolve/")
        remaining = _get(api, org, "/api/v1/admin/reflections/queue/").json()["results"]
        assert all(r["id"] != target for r in remaining)

    def test_awaiting_reply_flags_an_unanswered_routed_entry(
        self, api, org, routed_scene,
    ):
        api.force_authenticate(user=routed_scene["admin"])
        rows = _get(api, org, "/api/v1/admin/reflections/queue/").json()["results"]
        assert rows[0]["awaiting_reply"] is True

    def test_faculty_roster_row_carries_the_action_signals(
        self, api, org, routed_scene,
    ):
        api.force_authenticate(user=routed_scene["faculty"])
        resp = _get(api, org, "/api/v1/faculty/roster/")
        assert resp.status_code == 200, resp.content
        rows = {r["person_id"]: r for r in resp.json()["results"]}
        assert routed_scene["newer"].id in rows
        row = rows[routed_scene["newer"].id]
        assert row["reflection_state"] == "complete"
        assert row["next_session_availability"] is None

    def test_faculty_roster_detail_denied_for_unsupervised_person(
        self, api, org, program, routed_scene,
    ):
        other_room = AssignmentGroup.all_objects.create(
            organization=org, program=program, name="Elsewhere",
            slug="hp-elsewhere", group_type="classroom", is_active=True,
        )
        _, outsider = _faculty(
            org, program, other_room, first="Otto", email="otto2@hp.test",
        )
        api.force_authenticate(user=outsider)
        resp = _get(api, org, f"/api/v1/faculty/roster/{routed_scene['newer'].id}/")
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Cohort feed
# ---------------------------------------------------------------------------


class TestCohortFeed:
    @pytest.fixture
    def feed(self, org, program, classroom, template):
        author, author_user = _madrich(
            org, program, classroom, "Ari", email="ari-feed@hp.test",
        )
        peer, peer_user = _madrich(
            org, program, classroom, "Peer", email="peer-feed@hp.test",
        )
        _, admin_user = _admin(org, program)
        reflection = _submit(org, program, template, author, answers=ANSWERS)
        share = CohortShare.all_objects.get(reflection=reflection)
        return {
            "author": author_user, "peer": peer_user, "admin": admin_user,
            "author_person": author, "peer_person": peer, "share": share,
        }

    def test_cohort_peer_sees_the_post(self, api, org, feed):
        api.force_authenticate(user=feed["peer"])
        resp = _get(api, org, "/api/v1/cohort/feed/")
        assert resp.status_code == 200, resp.content
        rows = resp.json()["results"]
        assert [r["id"] for r in rows] == [feed["share"].id]
        assert rows[0]["is_mine"] is False
        assert rows[0]["can_like"] is True

    def test_author_cannot_like_their_own_post(self, api, org, feed):
        api.force_authenticate(user=feed["author"])
        resp = _post(api, org, f"/api/v1/cohort/shares/{feed['share'].id}/react/")
        assert resp.status_code == 403
        assert not ShareReaction.all_objects.filter(cohort_share=feed["share"]).exists()

    def test_peer_like_toggles(self, api, org, feed):
        api.force_authenticate(user=feed["peer"])
        url = f"/api/v1/cohort/shares/{feed['share'].id}/react/"
        first = _post(api, org, url).json()
        assert first == {
            "id": feed["share"].id, "liked_by_me": True, "like_count": 1,
        }
        second = _post(api, org, url).json()
        assert second["liked_by_me"] is False
        assert second["like_count"] == 0

    def test_madrich_outside_the_cohort_sees_nothing(
        self, api, org, program, feed,
    ):
        other_room = AssignmentGroup.all_objects.create(
            organization=org, program=program, name="Other Room",
            slug="hp-other-room", group_type="classroom", is_active=True,
        )
        _, outsider = _madrich(
            org, program, other_room, "Out", email="out-feed@hp.test",
        )
        api.force_authenticate(user=outsider)
        assert _get(api, org, "/api/v1/cohort/feed/").json()["results"] == []

    def test_director_hide_removes_the_post_for_peers(self, api, org, feed):
        api.force_authenticate(user=feed["admin"])
        resp = _post(
            api, org, f"/api/v1/cohort/shares/{feed['share'].id}/hide/",
            {"is_hidden": True},
        )
        assert resp.status_code == 200, resp.content

        api.force_authenticate(user=feed["peer"])
        assert _get(api, org, "/api/v1/cohort/feed/").json()["results"] == []

        # The author still sees their own post, so it doesn't vanish silently.
        api.force_authenticate(user=feed["author"])
        assert len(_get(api, org, "/api/v1/cohort/feed/").json()["results"]) == 1

    def test_peer_cannot_hide_a_post(self, api, org, feed):
        api.force_authenticate(user=feed["peer"])
        resp = _post(
            api, org, f"/api/v1/cohort/shares/{feed['share'].id}/hide/",
            {"is_hidden": True},
        )
        assert resp.status_code == 403

    def test_cohort_members_lists_the_classroom(self, api, org, feed):
        api.force_authenticate(user=feed["peer"])
        resp = _get(api, org, "/api/v1/cohort/members/")
        assert resp.status_code == 200, resp.content
        rows = {r["id"]: r for r in resp.json()["results"]}
        assert set(rows) == {feed["author_person"].id, feed["peer_person"].id}
        assert rows[feed["peer_person"].id]["is_me"] is True
        assert rows[feed["author_person"].id]["grade_level"] == 10


# ---------------------------------------------------------------------------
# Trends
# ---------------------------------------------------------------------------


class TestTrends:
    def test_series_come_from_the_schema_not_hardcoded_keys(
        self, api, org, program, template,
    ):
        person, user = _madrich(org, program, None, "Tre", email="tre@hp.test")
        _submit(org, program, template, person, answers=ANSWERS)
        api.force_authenticate(user=user)
        resp = _get(api, org, "/api/v1/madrich/trends/")
        assert resp.status_code == 200, resp.content
        series = {s["category_key"]: s for s in resp.json()["series"]}
        schema_categories = {
            c["key"]
            for f in template.schema["fields"]
            if f["type"] == "rating_group"
            for c in f["categories"]
        }
        assert set(series) == schema_categories
        one = series["initiative"]
        assert one["trend_key"] == "ratings.initiative"
        assert one["scale_min"] == 1
        assert one["scale_max"] == 4
        assert one["points"] == [
            {
                "date": one["points"][0]["date"],
                "value": 4,
                "reflection_id": one["points"][0]["reflection_id"],
            },
        ]

    def test_zero_data_points_returns_empty_series_not_an_error(
        self, api, org, program,
    ):
        _, user = _madrich(org, program, None, "Zero", email="zero@hp.test")
        api.force_authenticate(user=user)
        resp = _get(api, org, "/api/v1/madrich/trends/")
        assert resp.status_code == 200, resp.content
        assert all(s["points"] == [] for s in resp.json()["series"])

    def test_two_points_are_ordered_oldest_first(
        self, api, org, program, template,
    ):
        person, user = _madrich(org, program, None, "Two", email="two@hp.test")
        _submit(
            org, program, template, person,
            answers=dict(ANSWERS, ratings=dict(ANSWERS["ratings"], initiative=2)),
            weeks_ago=1,
        )
        _submit(org, program, template, person, answers=ANSWERS)
        api.force_authenticate(user=user)
        series = {
            s["category_key"]: s
            for s in _get(api, org, "/api/v1/madrich/trends/").json()["series"]
        }
        values = [p["value"] for p in series["initiative"]["points"]]
        assert values == [2, 4]

    def test_entry_cards_are_discovered_from_the_schema(
        self, api, org, program, classroom, template,
    ):
        person, user = _madrich(
            org, program, classroom, "Card", email="card@hp.test",
        )
        _submit(org, program, template, person, answers=ANSWERS)
        api.force_authenticate(user=user)
        resp = _get(api, org, "/api/v1/madrich/entries/")
        assert resp.status_code == 200, resp.content
        cards = {c["field_key"]: c for c in resp.json()["cards"]}
        assert set(cards) == {
            "wins", "improvements", "question_or_concern", "shared_idea",
        }
        assert cards["wins"]["total"] == 3
        assert cards["wins"]["thread_scope"] == "item"
        assert cards["question_or_concern"]["routes_to"] == "director"
        assert cards["question_or_concern"]["entries"][0]["awaiting_reply"] is True


# ---------------------------------------------------------------------------
# Director
# ---------------------------------------------------------------------------


class TestDirector:
    def test_pulse_reports_completion_for_the_current_period(
        self, api, org, program, classroom, template,
    ):
        filed, _ = _madrich(org, program, classroom, "Filed")
        _madrich(org, program, classroom, "Missing")
        _submit(org, program, template, filed, answers=ANSWERS)
        _, admin_user = _admin(org, program)
        api.force_authenticate(user=admin_user)
        resp = _get(api, org, "/api/v1/admin/reflections/pulse/")
        assert resp.status_code == 200, resp.content
        body = resp.json()
        assert body["available"] is True
        assert body["active_madrichim"] == 2
        assert body["current"]["submitted"] == 1
        assert body["current"]["expected"] == 2
        assert body["current"]["rate"] == 0.5
        assert len(body["periods"]) == 8
        assert body["open_question_count"] == 1

    def test_coverage_uses_the_4_7_status_vocabulary(
        self, api, org, program, classroom, next_sunday,
    ):
        available, _ = _madrich(org, program, classroom, "Yes")
        tentative, _ = _madrich(org, program, classroom, "Maybe")
        _madrich(org, program, classroom, "Silent")
        MadrichAvailability.objects.create(
            organization=org, program=program, person=available,
            session_date=next_sunday,
            status=MadrichAvailability.STATUS_AVAILABLE,
        )
        MadrichAvailability.objects.create(
            organization=org, program=program, person=tentative,
            session_date=next_sunday,
            status=MadrichAvailability.STATUS_TENTATIVE,
        )
        _, admin_user = _admin(org, program)
        api.force_authenticate(user=admin_user)
        resp = _get(api, org, "/api/v1/admin/reflections/coverage/")
        assert resp.status_code == 200, resp.content
        body = resp.json()
        assert body["sessions"] == [next_sunday.isoformat()]
        cell = body["classrooms"][0]["cells"][0]
        assert cell["available"] == 1
        assert cell["tentative"] == 1
        assert cell["unavailable"] == 0
        assert cell["unset"] == 1
        # Flagged on unset/tentative -- there is no required-headcount target.
        assert cell["flagged"] is True

    def test_faculty_activity_reports_null_latency_before_any_reply(
        self, api, org, program, classroom, template,
    ):
        madrich, _ = _madrich(org, program, classroom, "Ari")
        faculty, _ = _faculty(org, program, classroom)
        _submit(org, program, template, madrich, answers=ANSWERS)
        _, admin_user = _admin(org, program)
        api.force_authenticate(user=admin_user)
        resp = _get(api, org, "/api/v1/admin/reflections/faculty-activity/")
        assert resp.status_code == 200, resp.content
        row = next(
            r for r in resp.json()["results"] if r["person_id"] == faculty.id
        )
        assert row["assigned_madrich_count"] == 1
        assert row["median_response_hours"] is None
        assert row["open_thread_count"] > 0

    def test_faculty_activity_measures_latency_once_answered(
        self, api, org, program, classroom, template,
    ):
        madrich, _ = _madrich(org, program, classroom, "Ari")
        faculty, faculty_user = _faculty(org, program, classroom)
        reflection = _submit(org, program, template, madrich, answers=ANSWERS)
        thread = EntryThread.all_objects.filter(
            reflection=reflection, field_key="wins", item_index=0,
        ).get()
        api.force_authenticate(user=faculty_user)
        _post(api, org, f"/api/v1/threads/{thread.id}/messages/", {"body": "Nice."})

        _, admin_user = _admin(org, program)
        api.force_authenticate(user=admin_user)
        row = next(
            r
            for r in _get(
                api, org, "/api/v1/admin/reflections/faculty-activity/",
            ).json()["results"]
            if r["person_id"] == faculty.id
        )
        assert row["median_response_hours"] is not None

    def test_themes_suppress_groups_under_the_contributor_threshold(
        self, api, org, program, classroom, template,
    ):
        """§6.6: fewer than five contributors is re-identifying."""
        from bunk_logs.core.models import ReflectionThemeTag
        from bunk_logs.core.models import ReflectionThemeTagging

        for i in range(6):
            person, _ = _madrich(org, program, classroom, f"P{i}")
            reflection = _submit(org, program, template, person, answers=ANSWERS)
            tagging = ReflectionThemeTagging.all_objects.create(
                organization=org, reflection=reflection, taxonomy_version="v1",
                status=ReflectionThemeTagging.Status.COMPLETED,
            )
            # "belonging" gets six distinct contributors; "other" gets two.
            themes = ["belonging"] if i >= 2 else ["belonging", "other"]
            for theme in themes:
                ReflectionThemeTag.all_objects.create(
                    tagging=tagging, organization=org, reflection=reflection,
                    program=program, field_key="question_or_concern",
                    dashboard_role="open_concern", theme_key=theme,
                    period_start=reflection.period_start,
                )

        _, admin_user = _admin(org, program)
        api.force_authenticate(user=admin_user)
        resp = _get(api, org, "/api/v1/admin/reflections/themes/")
        assert resp.status_code == 200, resp.content
        body = resp.json()
        assert [t["theme_key"] for t in body["themes"]] == ["belonging"]
        assert body["suppressed_count"] == 1
        assert body["min_contributors"] == 5

    def test_roster_export_is_csv(self, api, org, program, classroom, template):
        madrich, _ = _madrich(org, program, classroom, "Ari", grade=9)
        _submit(org, program, template, madrich, answers=ANSWERS)
        _, admin_user = _admin(org, program)
        api.force_authenticate(user=admin_user)
        resp = _get(api, org, "/api/v1/admin/reflections/madrichim/export/")
        assert resp.status_code == 200
        assert resp["Content-Type"] == "text/csv"
        text = resp.content.decode()
        assert "Name,Grade,Classroom" in text
        assert "Ari Rich,9,Tzedakah 101,complete" in text

    @pytest.mark.parametrize(
        "url",
        [
            "/api/v1/admin/reflections/pulse/",
            "/api/v1/admin/reflections/queue/",
            "/api/v1/admin/reflections/coverage/",
            "/api/v1/admin/reflections/faculty-activity/",
            "/api/v1/admin/reflections/themes/",
            "/api/v1/admin/reflections/madrichim/",
        ],
    )
    def test_non_admin_denied_on_every_director_endpoint(
        self, api, org, program, classroom, url,
    ):
        _, user = _madrich(org, program, classroom, "Nope", email="nope@hp.test")
        api.force_authenticate(user=user)
        assert _get(api, org, url).status_code == 403


# ---------------------------------------------------------------------------
# Query counts
# ---------------------------------------------------------------------------


class TestQueryCounts:
    """§8: the homepages must not fan out as rosters grow.

    Each test runs the same request against a small and a large roster and
    asserts the query count is identical, which is a stronger and less
    brittle guarantee than pinning an absolute number.
    """

    def _roster(self, org, program, classroom, template, count, *, prefix):
        for i in range(count):
            person, _ = _madrich(org, program, classroom, f"{prefix}{i}")
            _submit(org, program, template, person, answers=ANSWERS)

    def _measure(self, api, org, url) -> int:
        from django.db import connection
        from django.test.utils import CaptureQueriesContext

        with CaptureQueriesContext(connection) as captured:
            _get(api, org, url)
        return len(captured.captured_queries)

    def test_faculty_dashboard_cost_is_flat(
        self, api, org, program, classroom, template, django_assert_num_queries,
    ):
        self._roster(org, program, classroom, template, 2, prefix="S")
        _, faculty_user = _faculty(org, program, classroom)
        api.force_authenticate(user=faculty_user)
        small = self._measure(api, org, "/api/v1/faculty/dashboard/")

        self._roster(org, program, classroom, template, 8, prefix="L")
        with django_assert_num_queries(small):
            _get(api, org, "/api/v1/faculty/dashboard/")

    def test_faculty_roster_cost_is_flat(
        self, api, org, program, classroom, template, django_assert_num_queries,
    ):
        self._roster(org, program, classroom, template, 2, prefix="S")
        _, faculty_user = _faculty(org, program, classroom)
        api.force_authenticate(user=faculty_user)
        small = self._measure(api, org, "/api/v1/faculty/roster/")

        self._roster(org, program, classroom, template, 8, prefix="L")
        with django_assert_num_queries(small):
            _get(api, org, "/api/v1/faculty/roster/")

    def test_director_coverage_cost_is_flat(
        self, api, org, program, classroom, template, django_assert_num_queries,
    ):
        self._roster(org, program, classroom, template, 2, prefix="S")
        _, admin_user = _admin(org, program)
        api.force_authenticate(user=admin_user)
        small = self._measure(api, org, "/api/v1/admin/reflections/coverage/")

        self._roster(org, program, classroom, template, 8, prefix="L")
        with django_assert_num_queries(small):
            _get(api, org, "/api/v1/admin/reflections/coverage/")

    def test_director_pulse_cost_is_flat(
        self, api, org, program, classroom, template, django_assert_num_queries,
    ):
        self._roster(org, program, classroom, template, 2, prefix="S")
        _, admin_user = _admin(org, program)
        api.force_authenticate(user=admin_user)
        small = self._measure(api, org, "/api/v1/admin/reflections/pulse/")

        self._roster(org, program, classroom, template, 8, prefix="L")
        with django_assert_num_queries(small):
            _get(api, org, "/api/v1/admin/reflections/pulse/")

    def test_madrich_dashboard_cost_is_flat_as_entries_accumulate(
        self, api, org, program, classroom, template, django_assert_num_queries,
    ):
        person, user = _madrich(
            org, program, classroom, "Grow", email="grow@hp.test",
        )
        _submit(org, program, template, person, answers=ANSWERS)
        api.force_authenticate(user=user)
        small = self._measure(api, org, "/api/v1/madrich/dashboard/")

        for week in range(1, 5):
            _submit(org, program, template, person, answers=ANSWERS, weeks_ago=week)
        with django_assert_num_queries(small):
            _get(api, org, "/api/v1/madrich/dashboard/")
