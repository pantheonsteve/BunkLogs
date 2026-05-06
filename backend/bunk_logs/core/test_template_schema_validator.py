"""Tests for the v1 ReflectionTemplate schema validator and key utility."""
from __future__ import annotations

import pytest
from django.core.exceptions import ValidationError

from bunk_logs.core.utils.keys import suggest_key_from_prompt
from bunk_logs.core.validators.template_schema import validate_template_schema

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _text(key="q1", lang="en"):
    return {"key": key, "type": "text", "prompts": {lang: "A question"}}


def _textarea(key="q1"):
    return {"key": key, "type": "textarea", "prompts": {"en": "A question"}}


def _text_list(key="q1"):
    return {
        "key": key,
        "type": "text_list",
        "prompts": {"en": "List items"},
        "min_items": 1,
        "max_items": 3,
    }


def _single_choice(key="q1"):
    return {
        "key": key,
        "type": "single_choice",
        "prompts": {"en": "Pick one"},
        "options": [
            {"key": "a", "labels": {"en": "Option A"}},
            {"key": "b", "labels": {"en": "Option B"}},
        ],
    }


def _multiple_choice(key="q1"):
    return {
        "key": key,
        "type": "multiple_choice",
        "prompts": {"en": "Pick many"},
        "options": [
            {"key": "a", "labels": {"en": "Option A"}},
            {"key": "b", "labels": {"en": "Option B"}},
        ],
    }


def _rating_group(key="ratings"):
    return {
        "key": key,
        "type": "rating_group",
        "scale": [1, 4],
        "scale_labels": {"en": ["Low", "Below", "Above", "High"]},
        "categories": [{"key": "cat1", "labels": {"en": "Category 1"}}],
    }


def _single_rating(key="score"):
    return {
        "key": key,
        "type": "single_rating",
        "scale": [1, 5],
        "scale_labels": {"en": ["1", "2", "3", "4", "5"]},
    }


def _yes_no(key="q1"):
    return {"key": key, "type": "yes_no", "prompts": {"en": "Yes or no?"}}


def _date(key="q1"):
    return {"key": key, "type": "date", "prompts": {"en": "Pick a date"}}


def _number(key="q1"):
    return {"key": key, "type": "number", "prompts": {"en": "Enter a number"}}


def _section_header(key="sec1"):
    return {"key": key, "type": "section_header", "prompts": {"en": "Section Title"}}


def _instructions(key="inst1"):
    return {"key": key, "type": "instructions", "prompts": {"en": "Read this."}}


def _schema(*fields):
    return {"fields": list(fields)}


# ---------------------------------------------------------------------------
# Top-level structure
# ---------------------------------------------------------------------------


class TestSchemaTopLevel:
    def test_rejects_non_dict(self):
        with pytest.raises(ValidationError):
            validate_template_schema([], [])

    def test_rejects_missing_fields(self):
        with pytest.raises(ValidationError):
            validate_template_schema({}, [])

    def test_rejects_empty_fields(self):
        with pytest.raises(ValidationError):
            validate_template_schema({"fields": []}, [])

    def test_valid_single_text_field(self):
        validate_template_schema(_schema(_text()), [])


# ---------------------------------------------------------------------------
# All field types validate with valid input
# ---------------------------------------------------------------------------


class TestFieldTypeValid:
    @pytest.mark.parametrize(
        "field",
        [
            _text(),
            _textarea(),
            _text_list(),
            _single_choice(),
            _multiple_choice(),
            _rating_group(),
            _single_rating(),
            _yes_no(),
            _date(),
            _number(),
            _section_header(),
            _instructions(),
        ],
        ids=[
            "text",
            "textarea",
            "text_list",
            "single_choice",
            "multiple_choice",
            "rating_group",
            "single_rating",
            "yes_no",
            "date",
            "number",
            "section_header",
            "instructions",
        ],
    )
    def test_valid(self, field):
        validate_template_schema(_schema(field), [])


# ---------------------------------------------------------------------------
# Malformed inputs rejected
# ---------------------------------------------------------------------------


class TestFieldTypeInvalid:
    def test_unknown_type_rejected(self):
        field = {"key": "f", "type": "magic_field", "prompts": {"en": "x"}}
        with pytest.raises(ValidationError, match="Unknown or missing type"):
            validate_template_schema(_schema(field), [])

    def test_missing_prompts_rejected(self):
        field = {"key": "f", "type": "text"}
        with pytest.raises(ValidationError, match="prompts"):
            validate_template_schema(_schema(field), [])

    def test_empty_prompts_dict_rejected(self):
        field = {"key": "f", "type": "text", "prompts": {}}
        with pytest.raises(ValidationError, match="prompts"):
            validate_template_schema(_schema(field), [])

    def test_single_choice_missing_options_rejected(self):
        field = {"key": "f", "type": "single_choice", "prompts": {"en": "Pick"}}
        with pytest.raises(ValidationError, match="options"):
            validate_template_schema(_schema(field), [])

    def test_multiple_choice_empty_options_rejected(self):
        field = {
            "key": "f",
            "type": "multiple_choice",
            "prompts": {"en": "Pick"},
            "options": [],
        }
        with pytest.raises(ValidationError, match="options"):
            validate_template_schema(_schema(field), [])

    def test_option_missing_labels_rejected(self):
        field = {
            "key": "f",
            "type": "single_choice",
            "prompts": {"en": "Pick"},
            "options": [{"key": "a"}],
        }
        with pytest.raises(ValidationError, match="labels"):
            validate_template_schema(_schema(field), [])

    def test_rating_group_missing_scale_rejected(self):
        field = {
            "key": "r",
            "type": "rating_group",
            "scale_labels": {"en": ["Low", "High"]},
            "categories": [{"key": "c", "labels": {"en": "Cat"}}],
        }
        with pytest.raises(ValidationError, match="scale"):
            validate_template_schema(_schema(field), [])

    def test_rating_group_bad_scale_order_rejected(self):
        field = {
            "key": "r",
            "type": "rating_group",
            "scale": [5, 1],
            "scale_labels": {"en": ["Low", "High"]},
            "categories": [{"key": "c", "labels": {"en": "Cat"}}],
        }
        with pytest.raises(ValidationError, match="scale"):
            validate_template_schema(_schema(field), [])

    def test_rating_group_missing_categories_rejected(self):
        field = {
            "key": "r",
            "type": "rating_group",
            "scale": [1, 4],
            "scale_labels": {"en": ["1", "2", "3", "4"]},
            "categories": [],
        }
        with pytest.raises(ValidationError, match="categories"):
            validate_template_schema(_schema(field), [])

    def test_single_rating_missing_scale_rejected(self):
        field = {"key": "s", "type": "single_rating", "scale_labels": {"en": ["L", "H"]}}
        with pytest.raises(ValidationError, match="scale"):
            validate_template_schema(_schema(field), [])

    def test_legacy_option_value_key_accepted(self):
        """Options using 'value' instead of 'key' (legacy format) must still pass."""
        field = {
            "key": "f",
            "type": "single_choice",
            "prompts": {"en": "Pick"},
            "options": [{"value": "yes", "labels": {"en": "Yes"}}],
        }
        validate_template_schema(_schema(field), [])


# ---------------------------------------------------------------------------
# dashboard_role validation
# ---------------------------------------------------------------------------


class TestDashboardRole:
    def test_category_ratings_on_rating_group_accepted(self):
        field = {**_rating_group(), "dashboard_role": "category_ratings"}
        validate_template_schema(_schema(field), [])

    def test_primary_rating_on_single_rating_accepted(self):
        field = {**_single_rating(), "dashboard_role": "primary_rating"}
        validate_template_schema(_schema(field), [])

    def test_wins_on_text_list_accepted(self):
        field = {**_text_list(), "dashboard_role": "wins"}
        validate_template_schema(_schema(field), [])

    def test_improvements_on_text_list_accepted(self):
        field = {**_text_list(), "dashboard_role": "improvements"}
        validate_template_schema(_schema(field), [])

    def test_open_concern_on_text_accepted(self):
        field = {**_text(), "dashboard_role": "open_concern"}
        validate_template_schema(_schema(field), [])

    def test_open_concern_on_textarea_accepted(self):
        field = {**_textarea(), "dashboard_role": "open_concern"}
        validate_template_schema(_schema(field), [])

    def test_primary_rating_on_text_rejected(self):
        field = {**_text(), "dashboard_role": "primary_rating"}
        with pytest.raises(ValidationError, match="primary_rating"):
            validate_template_schema(_schema(field), [])

    def test_category_ratings_on_textarea_rejected(self):
        field = {**_textarea(), "dashboard_role": "category_ratings"}
        with pytest.raises(ValidationError, match="category_ratings"):
            validate_template_schema(_schema(field), [])

    def test_wins_on_textarea_rejected(self):
        field = {**_textarea(), "dashboard_role": "wins"}
        with pytest.raises(ValidationError, match="wins"):
            validate_template_schema(_schema(field), [])

    def test_invalid_dashboard_role_rejected(self):
        field = {**_text(), "dashboard_role": "bogus_role"}
        with pytest.raises(ValidationError, match="dashboard_role"):
            validate_template_schema(_schema(field), [])

    def test_null_dashboard_role_accepted(self):
        field = {**_text(), "dashboard_role": None}
        validate_template_schema(_schema(field), [])


# ---------------------------------------------------------------------------
# Key validation
# ---------------------------------------------------------------------------


class TestKeyValidation:
    def test_reserved_key_id_rejected(self):
        field = {"key": "id", "type": "text", "prompts": {"en": "x"}}
        with pytest.raises(ValidationError, match="reserved"):
            validate_template_schema(_schema(field), [])

    def test_reserved_key_organization_rejected(self):
        field = {"key": "organization", "type": "text", "prompts": {"en": "x"}}
        with pytest.raises(ValidationError, match="reserved"):
            validate_template_schema(_schema(field), [])

    def test_reserved_key_submitted_by_rejected(self):
        field = {"key": "submitted_by", "type": "text", "prompts": {"en": "x"}}
        with pytest.raises(ValidationError, match="reserved"):
            validate_template_schema(_schema(field), [])

    def test_duplicate_keys_rejected(self):
        fields = [_text("same"), _textarea("same")]
        with pytest.raises(ValidationError, match="Duplicate"):
            validate_template_schema({"fields": fields}, [])

    def test_unique_keys_accepted(self):
        fields = [_text("q1"), _textarea("q2"), _number("q3")]
        validate_template_schema({"fields": fields}, [])

    def test_missing_key_rejected(self):
        field = {"type": "text", "prompts": {"en": "x"}}
        with pytest.raises(ValidationError, match="key"):
            validate_template_schema(_schema(field), [])


# ---------------------------------------------------------------------------
# Language coverage validation
# ---------------------------------------------------------------------------


class TestLanguageCoverage:
    def test_single_language_covered(self):
        validate_template_schema(_schema(_text("q1", "en")), ["en"])

    def test_bilingual_covered(self):
        field = {
            "key": "q1",
            "type": "text",
            "prompts": {"en": "English", "es": "Spanish"},
        }
        validate_template_schema(_schema(field), ["en", "es"])

    def test_missing_language_rejected(self):
        field = {"key": "q1", "type": "text", "prompts": {"en": "Only English"}}
        with pytest.raises(ValidationError, match='"es"'):
            validate_template_schema(_schema(field), ["en", "es"])

    def test_rating_group_missing_language_rejected(self):
        field = {
            "key": "r",
            "type": "rating_group",
            "scale": [1, 4],
            "scale_labels": {"en": ["L", "M", "G", "H"]},
            "categories": [{"key": "c", "labels": {"en": "Cat"}}],
        }
        with pytest.raises(ValidationError, match='"es"'):
            validate_template_schema(_schema(field), ["en", "es"])

    def test_single_rating_missing_language_rejected(self):
        field = {
            "key": "s",
            "type": "single_rating",
            "scale": [1, 4],
            "scale_labels": {"en": ["L", "M", "G", "H"]},
        }
        with pytest.raises(ValidationError, match='"es"'):
            validate_template_schema(_schema(field), ["en", "es"])

    def test_empty_languages_skips_coverage_check(self):
        field = {"key": "q1", "type": "text", "prompts": {"en": "Only English"}}
        validate_template_schema(_schema(field), [])


# ---------------------------------------------------------------------------
# suggest_key_from_prompt
# ---------------------------------------------------------------------------


class TestSuggestKeyFromPrompt:
    def test_simple_phrase(self):
        assert suggest_key_from_prompt("List 3 things you did well") == "list_3_things_you_did_well"

    def test_punctuation_removed(self):
        key = suggest_key_from_prompt("What was your biggest highlight?")
        assert key == "what_was_your_biggest_highlight"

    def test_uppercase_lowercased(self):
        assert suggest_key_from_prompt("BIG Title Here") == "big_title_here"

    def test_multiple_spaces_become_single_underscore(self):
        assert suggest_key_from_prompt("a   b") == "a_b"

    def test_truncated_at_50_chars(self):
        long = "word " * 20
        result = suggest_key_from_prompt(long)
        assert len(result) <= 50

    def test_truncated_at_word_boundary(self):
        long = "abcde " * 12
        result = suggest_key_from_prompt(long)
        assert not result.endswith("_")
        assert len(result) <= 50

    def test_stable_output(self):
        prompt = "How did you feel today?"
        assert suggest_key_from_prompt(prompt) == suggest_key_from_prompt(prompt)

    def test_unicode_normalized(self):
        result = suggest_key_from_prompt("café résumé")
        assert result == "cafe_resume"
