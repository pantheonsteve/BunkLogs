"""Per-org display vocabulary resolution (``core.terminology``).

The load-bearing property is the fallback: an org that sets nothing -- or
sets one key, or sets a malformed value -- must still render the camp
wording everywhere else, because Crane Lake has no ``terminology`` block.
"""
from __future__ import annotations

from bunk_logs.api.threads.common import entry_field_label
from bunk_logs.core.terminology import DEFAULT_TERMS
from bunk_logs.core.terminology import term
from bunk_logs.core.terminology import terms_for_organization


class _Org:
    """Stand-in for Organization; only ``settings`` is read."""

    def __init__(self, settings=None):
        self.settings = settings


def test_org_without_terminology_gets_camp_defaults():
    assert terms_for_organization(_Org()) == DEFAULT_TERMS
    assert terms_for_organization(_Org({})) == DEFAULT_TERMS
    assert terms_for_organization(None) == DEFAULT_TERMS


def test_tbe_overrides_apply_and_unset_keys_fall_back():
    org = _Org({
        "terminology": {
            "camper": {"one": "student", "other": "students"},
            "cohort": {"one": "Teaching Team", "other": "Teaching Teams"},
            "director": {"one": "Ed Team", "other": "Ed Team"},
        },
    })

    assert term(org, "camper") == "student"
    assert term(org, "camper", plural=True) == "students"
    assert term(org, "cohort", capitalize=True) == "Teaching Team"
    # A collective noun that does not pluralize still answers both forms.
    assert term(org, "director", plural=True) == "Ed Team"
    assert term(org, "student") == DEFAULT_TERMS["student"]["one"]


def test_partial_and_malformed_overrides_never_drop_a_key():
    org = _Org({
        "terminology": {
            "camper": "student",       # bare string, no plural
            "cohort": {"other": ""},   # empty form
            "director": ["nonsense"],  # wrong type entirely
        },
    })
    terms = terms_for_organization(org)

    assert terms["camper"] == {"one": "student", "other": "student"}
    assert terms["cohort"] == DEFAULT_TERMS["cohort"]
    assert terms["director"] == DEFAULT_TERMS["director"]
    assert set(terms) == set(DEFAULT_TERMS)


def test_capitalize_only_touches_the_first_character():
    org = _Org({"terminology": {"cohort": {"one": "teaching team"}}})

    assert term(org, "cohort", capitalize=True) == "Teaching team"
    assert term(org, "cohort") == "teaching team"


def test_unknown_key_returns_itself():
    assert term(None, "not_a_term") == "not_a_term"


def test_cohort_thread_label_follows_org_vocabulary():
    """The one server-rendered noun on a TBE surface (queue rows say "... post")."""
    class _Thread:
        cohort_share_id = 7

    tbe = _Org({"terminology": {"cohort": {"one": "Teaching Team"}}})

    assert entry_field_label(_Thread(), org=tbe) == "Teaching Team post"
    assert entry_field_label(_Thread(), org=None) == "Cohort post"
