"""Match CSV rows to existing Person records for Campminder roster imports."""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from enum import Enum

from bunk_logs.core.models import Organization
from bunk_logs.core.models import Person


class MatchStrategy(str, Enum):
    CAMPMINDER_ID = "campminder_id"
    MERGE_EMAIL = "merge_email"
    MERGE_NAME = "merge_name"
    NEW = "new"
    DUPLICATE_AMBIGUOUS_NAME = "duplicate_ambiguous_name"
    DUPLICATE_EMAIL_CONFLICT = "duplicate_email_conflict"
    DUPLICATE_NAME_DIFFERENT_ID = "duplicate_name_different_id"


@dataclass
class PersonMatch:
    person: Person | None
    strategy: MatchStrategy
    candidate_ids: list[int] = field(default_factory=list)


def _existing_campminder_id(person: Person) -> str:
    return str(person.external_ids.get("campminder_id") or "").strip()


def match_campminder_person(
    org: Organization,
    *,
    campminder_id: str,
    first_name: str,
    last_name: str,
    email: str,
) -> PersonMatch:
    """Resolve a CSV row to an existing Person or classify how to create one."""
    by_id = Person.all_objects.filter(
        organization=org,
        external_ids__campminder_id=campminder_id,
    ).first()
    if by_id is not None:
        return PersonMatch(person=by_id, strategy=MatchStrategy.CAMPMINDER_ID)

    if email:
        by_email = Person.all_objects.filter(
            organization=org,
            email__iexact=email,
        ).first()
        if by_email is not None:
            existing_id = _existing_campminder_id(by_email)
            if not existing_id or existing_id == campminder_id:
                return PersonMatch(person=by_email, strategy=MatchStrategy.MERGE_EMAIL)
            return PersonMatch(
                person=by_email,
                strategy=MatchStrategy.DUPLICATE_EMAIL_CONFLICT,
                candidate_ids=[by_email.id],
            )

    name_matches = list(
        Person.all_objects.filter(
            organization=org,
            first_name__iexact=first_name,
            last_name__iexact=last_name,
        ),
    )
    without_id = [p for p in name_matches if not _existing_campminder_id(p)]
    with_other_id = [
        p for p in name_matches
        if _existing_campminder_id(p) and _existing_campminder_id(p) != campminder_id
    ]

    if len(without_id) == 1:
        return PersonMatch(person=without_id[0], strategy=MatchStrategy.MERGE_NAME)
    if len(without_id) > 1:
        return PersonMatch(
            person=None,
            strategy=MatchStrategy.DUPLICATE_AMBIGUOUS_NAME,
            candidate_ids=[p.id for p in without_id],
        )
    if with_other_id:
        return PersonMatch(
            person=None,
            strategy=MatchStrategy.DUPLICATE_NAME_DIFFERENT_ID,
            candidate_ids=[p.id for p in with_other_id],
        )

    return PersonMatch(person=None, strategy=MatchStrategy.NEW)


def strategy_is_merge(strategy: MatchStrategy) -> bool:
    return strategy in {
        MatchStrategy.CAMPMINDER_ID,
        MatchStrategy.MERGE_EMAIL,
        MatchStrategy.MERGE_NAME,
    }


def strategy_is_duplicate(strategy: MatchStrategy) -> bool:
    return strategy in {
        MatchStrategy.DUPLICATE_AMBIGUOUS_NAME,
        MatchStrategy.DUPLICATE_EMAIL_CONFLICT,
        MatchStrategy.DUPLICATE_NAME_DIFFERENT_ID,
    }
