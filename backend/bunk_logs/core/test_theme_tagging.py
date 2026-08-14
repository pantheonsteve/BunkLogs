"""Theme-tagging pipeline tests (Growth Dashboard by Grade Level).

Covers the three layers:

* The synchronous :mod:`client` helper -- success path, the retryable /
  non-retryable failure split, and the validation that drops hallucinated
  theme keys instead of trusting them.
* The :mod:`tasks` Celery wrapper -- pending -> completed with tag rows
  written, grade level denormalized from the author's Membership, terminal
  failure on empty input, retryable failure staying in ``failed_retryable``,
  and the template allowlist gate.
* The :mod:`taxonomy` constants -- complexity tiers and field selection.

The Anthropic call is always dependency-injected; no test touches the network.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from unittest.mock import patch

import pytest
from celery.exceptions import Retry

from bunk_logs.core.models import Membership
from bunk_logs.core.models import Organization
from bunk_logs.core.models import Person
from bunk_logs.core.models import Program
from bunk_logs.core.models import Reflection
from bunk_logs.core.models import ReflectionTemplate
from bunk_logs.core.models import ReflectionThemeTag
from bunk_logs.core.models import ReflectionThemeTagging
from bunk_logs.core.theme_tagging import tasks as tasks_module
from bunk_logs.core.theme_tagging.client import ThemeTaggingFailureError
from bunk_logs.core.theme_tagging.client import ThemeTaggingResult
from bunk_logs.core.theme_tagging.client import tag_reflection_text
from bunk_logs.core.theme_tagging.taxonomy import TAXONOMY_VERSION
from bunk_logs.core.theme_tagging.taxonomy import complexity_tier
from bunk_logs.core.theme_tagging.taxonomy import taggable_fields

pytestmark = pytest.mark.django_db

TAGGED_SLUG = "test-3-2-1-weekly"

SCHEMA = {
    "fields": [
        {
            "key": "wins",
            "type": "text_list",
            "prompts": {"en": "Three wins"},
            "dashboard_role": "wins",
        },
        {
            "key": "improvements",
            "type": "text_list",
            "prompts": {"en": "Two improvements"},
            "dashboard_role": "improvements",
        },
        {
            "key": "question_or_concern",
            "type": "text",
            "prompts": {"en": "One question"},
            "dashboard_role": "open_concern",
        },
        {
            "key": "ratings",
            "type": "rating_group",
            "scale": [1, 4],
            "scale_labels": {"en": ["Low", "Mid", "Good", "Great"]},
            "categories": [{"key": "initiative", "labels": {"en": "Initiative"}}],
            "prompts": {"en": "Rate yourself"},
            "dashboard_role": "primary_rating",
        },
    ],
}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def org():
    return Organization.objects.create(name="Theme Org", slug="theme-org")


@pytest.fixture
def program(org):
    return Program.all_objects.create(
        organization=org,
        name=f"{org.name} Religious School",
        slug="theme-rs",
        program_type="religious_school",
        start_date=date(2026, 9, 1),
        end_date=date(2027, 5, 31),
        is_active=True,
    )


@pytest.fixture
def template(org):
    return ReflectionTemplate.all_objects.create(
        organization=org,
        name="Test 3-2-1 Weekly",
        slug=TAGGED_SLUG,
        cadence="weekly",
        role="madrich",
        program_type="religious_school",
        schema=SCHEMA,
        languages=["en"],
        is_active=True,
    )


@pytest.fixture
def author(org):
    return Person.all_objects.create(
        organization=org, first_name="Mara", last_name="Madrich",
    )


@pytest.fixture
def membership(program, author):
    return Membership.all_objects.create(
        program=program, person=author, role="madrich",
        is_active=True, grade_level=11,
    )


@pytest.fixture(autouse=True)
def _allow_test_template(settings):
    settings.THEME_TAGGING_TEMPLATE_SLUGS = [TAGGED_SLUG]


def _answers() -> dict:
    return {
        "wins": ["Led the opening prayer", "Helped a shy student"],
        "improvements": ["Prep the craft earlier", "Speak up more"],
        "question_or_concern": "How do I handle two students who keep fighting?",
        "ratings": {"initiative": 3},
    }


def _reflection(org, program, template, author, *, answers=None):
    return Reflection.all_objects.create(
        organization=org,
        program=program,
        template=template,
        subject=author,
        author=author,
        period_start=date(2026, 10, 5),
        period_end=date(2026, 10, 11),
        answers=answers if answers is not None else _answers(),
        language="en",
        is_complete=True,
    )


# ---------------------------------------------------------------------------
# Mock Anthropic client
# ---------------------------------------------------------------------------


@dataclass
class _StubUsage:
    input_tokens: int
    output_tokens: int


@dataclass
class _StubBlock:
    type: str
    text: str


class _StubResponse:
    def __init__(self, text: str, *, input_tokens: int = 40, output_tokens: int = 15):
        self.content = [_StubBlock(type="text", text=text)]
        self.usage = _StubUsage(input_tokens=input_tokens, output_tokens=output_tokens)


class _StubMessages:
    def __init__(self, response=None, raises=None):
        self._response = response
        self._raises = raises
        self.calls: list[dict] = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if self._raises is not None:
            raise self._raises
        return self._response


class _StubClient:
    def __init__(self, response=None, raises=None):
        self.messages = _StubMessages(response=response, raises=raises)


class _SimulatedAuthError(Exception):
    """Mimics the SDK's ``AuthenticationError`` for the heuristic classifier."""


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------


class TestTagReflectionText:
    def test_success_maps_entries_back_to_field_keys(self):
        stub = _StubClient(
            response=_StubResponse(
                json.dumps({"1": ["classroom_management"], "2": ["lesson_content"]}),
            ),
        )
        result = tag_reflection_text(
            [("question_or_concern", "kids keep fighting"), ("wins", "led prayer")],
            client=stub,
            model_id="claude-test",
        )
        assert isinstance(result, ThemeTaggingResult)
        assert result.themes_by_field == {
            "question_or_concern": ["classroom_management"],
            "wins": ["lesson_content"],
        }
        assert result.model_id == "claude-test"
        assert result.tokens_used == 55
        # The taxonomy must reach the model, otherwise it is guessing.
        prompt = stub.messages.calls[0]["messages"][0]["content"]
        assert "classroom_management" in prompt
        assert "kids keep fighting" in prompt

    def test_unknown_theme_keys_are_dropped(self):
        stub = _StubClient(
            response=_StubResponse(
                json.dumps({"1": ["classroom_management", "vibes", "not_a_theme"]}),
            ),
        )
        result = tag_reflection_text([("question_or_concern", "text")], client=stub)
        assert result.themes_by_field == {
            "question_or_concern": ["classroom_management"],
        }

    def test_entry_with_only_unknown_themes_is_omitted(self):
        stub = _StubClient(response=_StubResponse(json.dumps({"1": ["nonsense"]})))
        result = tag_reflection_text([("question_or_concern", "text")], client=stub)
        assert result.themes_by_field == {}

    def test_out_of_range_entry_number_is_ignored(self):
        stub = _StubClient(
            response=_StubResponse(json.dumps({"1": ["initiative_typo"], "7": ["other"]})),
        )
        result = tag_reflection_text([("wins", "text")], client=stub)
        assert result.themes_by_field == {}

    def test_themes_are_capped_per_field(self):
        stub = _StubClient(
            response=_StubResponse(
                json.dumps({
                    "1": [
                        "classroom_management",
                        "lesson_content",
                        "own_confidence",
                        "conflict_resolution",
                    ],
                }),
            ),
        )
        result = tag_reflection_text([("wins", "text")], client=stub)
        assert len(result.themes_by_field["wins"]) == 3

    def test_code_fenced_json_is_parsed(self):
        stub = _StubClient(
            response=_StubResponse(
                '```json\n{"1": ["own_confidence"]}\n```',
            ),
        )
        result = tag_reflection_text([("wins", "text")], client=stub)
        assert result.themes_by_field == {"wins": ["own_confidence"]}

    def test_non_json_response_is_non_retryable(self):
        stub = _StubClient(response=_StubResponse("I think it's about classrooms."))
        with pytest.raises(ThemeTaggingFailureError) as exc:
            tag_reflection_text([("wins", "text")], client=stub)
        assert exc.value.retryable is False

    def test_empty_input_is_non_retryable(self):
        with pytest.raises(ThemeTaggingFailureError) as exc:
            tag_reflection_text([("wins", "   ")], client=_StubClient())
        assert exc.value.retryable is False

    def test_sdk_error_is_retryable_by_default(self):
        stub = _StubClient(raises=RuntimeError("transient flake"))
        with pytest.raises(ThemeTaggingFailureError) as exc:
            tag_reflection_text([("wins", "text")], client=stub)
        assert exc.value.retryable is True

    def test_auth_like_error_is_non_retryable(self):
        stub = _StubClient(raises=_SimulatedAuthError("bad key"))
        with pytest.raises(ThemeTaggingFailureError) as exc:
            tag_reflection_text([("wins", "text")], client=stub)
        assert exc.value.retryable is False

    def test_missing_api_key_when_no_client_provided(self, settings):
        settings.ANTHROPIC_API_KEY = ""
        with pytest.raises(ThemeTaggingFailureError) as exc:
            tag_reflection_text([("wins", "text")])
        assert exc.value.retryable is False


# ---------------------------------------------------------------------------
# Celery task
# ---------------------------------------------------------------------------


class TestTagReflectionThemesTask:
    def test_completed_writes_tags_with_denormalized_grade(
        self, org, program, template, author, membership,
    ):
        reflection = _reflection(org, program, template, author)
        with patch.object(tasks_module, "tag_reflection_text") as fake:
            fake.return_value = ThemeTaggingResult(
                themes_by_field={
                    "question_or_concern": ["conflict_resolution"],
                    "wins": ["own_confidence", "student_engagement"],
                },
                model_id="claude-test",
                tokens_used=99,
            )
            result = tasks_module.tag_reflection_themes.run(reflection.pk)

        assert result["status"] == "completed"
        assert result["tags"] == 3

        record = ReflectionThemeTagging.all_objects.get(reflection=reflection)
        assert record.status == ReflectionThemeTagging.Status.COMPLETED
        assert record.taxonomy_version == TAXONOMY_VERSION
        assert record.model_id == "claude-test"
        assert record.tokens_used == 99

        tags = ReflectionThemeTag.all_objects.filter(tagging=record)
        assert tags.count() == 3
        # Grade level and period are denormalized off the author's Membership
        # so the dashboard aggregates without joins.
        assert {t.grade_level for t in tags} == {11}
        assert {t.period_start for t in tags} == {reflection.period_start}
        assert tags.get(theme_key="conflict_resolution").dashboard_role == "open_concern"
        assert set(
            tags.filter(field_key="wins").values_list("theme_key", flat=True),
        ) == {"own_confidence", "student_engagement"}

    def test_rerun_replaces_prior_tags(
        self, org, program, template, author, membership,
    ):
        reflection = _reflection(org, program, template, author)
        with patch.object(tasks_module, "tag_reflection_text") as fake:
            fake.return_value = ThemeTaggingResult(
                themes_by_field={"question_or_concern": ["logistics_scheduling"]},
                model_id="m", tokens_used=1,
            )
            tasks_module.tag_reflection_themes.run(reflection.pk)
            fake.return_value = ThemeTaggingResult(
                themes_by_field={"question_or_concern": ["conflict_resolution"]},
                model_id="m", tokens_used=1,
            )
            tasks_module.tag_reflection_themes.run(reflection.pk)

        assert ReflectionThemeTagging.all_objects.filter(reflection=reflection).count() == 1
        tags = ReflectionThemeTag.all_objects.filter(reflection=reflection)
        assert [t.theme_key for t in tags] == ["conflict_resolution"]

    def test_template_not_on_allowlist_is_skipped(
        self, org, program, template, author, membership, settings,
    ):
        settings.THEME_TAGGING_TEMPLATE_SLUGS = ["some-other-template"]
        reflection = _reflection(org, program, template, author)
        result = tasks_module.tag_reflection_themes.run(reflection.pk)
        assert result == {"status": "skipped", "reason": "template_not_tagged"}
        assert not ReflectionThemeTagging.all_objects.exists()

    def test_missing_reflection_is_skipped(self):
        result = tasks_module.tag_reflection_themes.run(999_999)
        assert result == {"status": "skipped", "reason": "reflection_missing"}

    def test_no_free_text_is_terminal(
        self, org, program, template, author, membership,
    ):
        reflection = _reflection(
            org, program, template, author,
            answers={"ratings": {"initiative": 3}},
        )
        result = tasks_module.tag_reflection_themes.run(reflection.pk)
        assert result["status"] == "failed_terminal"
        assert result["reason"] == "empty_source"
        record = ReflectionThemeTagging.all_objects.get(reflection=reflection)
        assert record.status == ReflectionThemeTagging.Status.FAILED_TERMINAL

    def test_retryable_failure_schedules_retry(
        self, org, program, template, author, membership,
    ):
        reflection = _reflection(org, program, template, author)
        with patch.object(tasks_module, "tag_reflection_text") as fake, \
             patch.object(
                 tasks_module.tag_reflection_themes,
                 "retry",
                 side_effect=Retry("scheduled"),
             ):
            fake.side_effect = ThemeTaggingFailureError("transient", retryable=True)
            with pytest.raises(Retry):
                tasks_module.tag_reflection_themes.run(reflection.pk)

        record = ReflectionThemeTagging.all_objects.get(reflection=reflection)
        assert record.status == ReflectionThemeTagging.Status.FAILED_RETRYABLE
        assert record.attempt_count == 1

    def test_non_retryable_failure_is_terminal(
        self, org, program, template, author, membership,
    ):
        reflection = _reflection(org, program, template, author)
        with patch.object(tasks_module, "tag_reflection_text") as fake:
            fake.side_effect = ThemeTaggingFailureError("bad key", retryable=False)
            result = tasks_module.tag_reflection_themes.run(reflection.pk)

        assert result["status"] == "failed_terminal"
        record = ReflectionThemeTagging.all_objects.get(reflection=reflection)
        assert record.status == ReflectionThemeTagging.Status.FAILED_TERMINAL

    def test_grade_level_is_null_without_membership(
        self, org, program, template, author,
    ):
        reflection = _reflection(org, program, template, author)
        with patch.object(tasks_module, "tag_reflection_text") as fake:
            fake.return_value = ThemeTaggingResult(
                themes_by_field={"question_or_concern": ["other"]},
                model_id="m", tokens_used=1,
            )
            tasks_module.tag_reflection_themes.run(reflection.pk)
        tag = ReflectionThemeTag.all_objects.get(reflection=reflection)
        assert tag.grade_level is None


# ---------------------------------------------------------------------------
# Enqueue helper + taxonomy
# ---------------------------------------------------------------------------


class TestEnqueueHelper:
    def test_returns_none_for_untagged_template(
        self, org, program, template, author, settings,
    ):
        settings.THEME_TAGGING_TEMPLATE_SLUGS = ["other"]
        reflection = _reflection(org, program, template, author)
        assert tasks_module.enqueue_theme_tagging_for_reflection(reflection) is None


class TestTaxonomy:
    def test_taggable_fields_excludes_ratings(self):
        keys = [f["key"] for f in taggable_fields(SCHEMA)]
        assert keys == ["wins", "improvements", "question_or_concern"]

    def test_complexity_tiers_span_fundamentals_to_sophisticated(self):
        assert complexity_tier("logistics_scheduling") == 1
        assert complexity_tier("conflict_resolution") == 3
        # Unknown keys must not blow up the per-grade index calculation.
        assert complexity_tier("made_up") == 1
