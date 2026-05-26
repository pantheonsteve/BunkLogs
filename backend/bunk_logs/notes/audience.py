"""Audience resolution for the Notes platform (Step 7_19, Story 66).

Implements per-role option matrices from docs/user_stories/10_notes_platform/audience_matrices.md.
v1 supports Counselor and Unit Head authors only; all other roles raise PermissionDenied.

Architecture:
  Each role has a list of (option_key, label, resolve_fn) triples. resolve_fn takes
  (author_membership, context_kwargs) and returns a queryset of Person records.
  Cross-cutting rules (self-exclusion, active Membership only, org-scoping,
  capture-don't-resolve) are applied centrally by `resolve_audience`.

Public API:
  audience_options_for(person, organization) -> list[{option_key, label}]
  resolve_audience(person, organization, program, audience_requests)
      -> list[{person, option_key, bunk_id}] (after dedup + self-exclusion)
"""

from __future__ import annotations

from typing import Any

from rest_framework.exceptions import PermissionDenied

from bunk_logs.core.models import AssignmentGroup
from bunk_logs.core.models import AssignmentGroupMembership
from bunk_logs.core.models import Membership
from bunk_logs.core.models import Organization
from bunk_logs.core.models import Person
from bunk_logs.core.models import Program
from bunk_logs.core.models import Supervision

V1_AUTHOR_ROLES: frozenset[str] = frozenset({"counselor", "junior_counselor", "unit_head"})

# ---------------------------------------------------------------------------
# Counselor option resolvers
# ---------------------------------------------------------------------------


def _counselor_my_unit_head(
    author_membership: Membership,
    org: Organization,
    program: Program,
    **kwargs: Any,
) -> list[dict]:
    """UH Persons who supervise this counselor (via target_type=MEMBERSHIP Supervision rows)."""
    uh_supervisions = (
        Supervision.all_objects.filter(
            target_type=Supervision.TargetType.MEMBERSHIP,
            target_membership=author_membership,
            supervisor_membership__role="unit_head",
            supervisor_membership__is_active=True,
            supervisor_membership__program=program,
        )
        .select_related("supervisor_membership__person")
        .distinct()
    )
    return [
        {
            "person": sup.supervisor_membership.person,
            "option_key": "my_unit_head",
            "bunk_id_at_capture": None,
        }
        for sup in uh_supervisions
    ]


def _counselor_administration(
    author_membership: Membership,
    org: Organization,
    program: Program,
    **kwargs: Any,
) -> list[dict]:
    """All Admins with active Membership in the org."""
    admin_memberships = Membership.all_objects.filter(
        program__organization=org,
        role="admin",
        is_active=True,
    ).select_related("person")
    return [{"person": m.person, "option_key": "administration", "bunk_id_at_capture": None}
            for m in admin_memberships]


def _counselor_co_counselors_on_bunk(
    author_membership: Membership,
    org: Organization,
    program: Program,
    **kwargs: Any,
) -> list[dict]:
    """Co-counselors on the author's current bunk(s)."""
    bunk_ids = _bunk_ids_for_counselor(author_membership)
    results = []
    for bunk_id in bunk_ids:
        counselor_persons = _counselors_on_bunk(bunk_id, program)
        for person in counselor_persons:
            results.append({
                "person": person,
                "option_key": "co_counselors_on_bunk",
                "bunk_id_at_capture": AssignmentGroup.all_objects.filter(id=bunk_id).first(),
            })
    return results


def _counselor_co_counselors_specific_bunk(
    author_membership: Membership,
    org: Organization,
    program: Program,
    bunk_id: int | None = None,
    **kwargs: Any,
) -> list[dict]:
    """Co-counselors on a specific named bunk (must be a bunk the author is or was a member of)."""
    if bunk_id is None:
        return []
    bunk = AssignmentGroup.all_objects.filter(id=bunk_id, organization=org).first()
    if bunk is None:
        return []
    counselor_persons = _counselors_on_bunk(bunk_id, program)
    return [
        {"person": p, "option_key": "co_counselors_specific_bunk", "bunk_id_at_capture": bunk}
        for p in counselor_persons
    ]


def _counselor_specific_person(
    author_membership: Membership,
    org: Organization,
    program: Program,
    person_id: int | None = None,
    **kwargs: Any,
) -> list[dict]:
    """A specific Person selected from the autocomplete union."""
    if person_id is None:
        return []
    person = Person.all_objects.filter(id=person_id, organization=org).first()
    if person is None:
        return []
    return [{"person": person, "option_key": "specific_person", "bunk_id_at_capture": None}]


# ---------------------------------------------------------------------------
# Unit Head option resolvers
# ---------------------------------------------------------------------------


def _uh_specific_counselor(
    author_membership: Membership,
    org: Organization,
    program: Program,
    person_id: int | None = None,
    **kwargs: Any,
) -> list[dict]:
    """A specific counselor the UH supervises."""
    if person_id is None:
        return []
    person = Person.all_objects.filter(id=person_id, organization=org).first()
    if person is None:
        return []
    # Validate they are actually a counselor under this UH.
    supervised_bunk_ids = _supervised_bunk_ids_for_uh(author_membership)
    counselor_person_ids = _counselor_ids_on_bunks(supervised_bunk_ids, program)
    if person.id not in counselor_person_ids:
        return []
    return [{"person": person, "option_key": "specific_counselor", "bunk_id_at_capture": None}]


def _uh_counselors_on_bunk(
    author_membership: Membership,
    org: Organization,
    program: Program,
    bunk_id: int | None = None,
    **kwargs: Any,
) -> list[dict]:
    """All counselors on a specific bunk in the UH's unit."""
    if bunk_id is None:
        return []
    supervised = _supervised_bunk_ids_for_uh(author_membership)
    if bunk_id not in supervised:
        return []
    bunk = AssignmentGroup.all_objects.filter(id=bunk_id, organization=org).first()
    if bunk is None:
        return []
    return [
        {"person": p, "option_key": "counselors_on_bunk", "bunk_id_at_capture": bunk}
        for p in _counselors_on_bunk(bunk_id, program)
    ]


def _uh_all_counselors_in_unit(
    author_membership: Membership,
    org: Organization,
    program: Program,
    **kwargs: Any,
) -> list[dict]:
    """All counselors on all bunks in the UH's unit."""
    supervised_bunk_ids = _supervised_bunk_ids_for_uh(author_membership)
    results = []
    for bunk_id in supervised_bunk_ids:
        bunk = AssignmentGroup.all_objects.filter(id=bunk_id).first()
        for person in _counselors_on_bunk(bunk_id, program):
            results.append({
                "person": person,
                "option_key": "all_counselors_in_unit",
                "bunk_id_at_capture": bunk,
            })
    return results


def _uh_peer_unit_heads(
    author_membership: Membership,
    org: Organization,
    program: Program,
    **kwargs: Any,
) -> list[dict]:
    """Other UHs in the same Program."""
    memberships = Membership.all_objects.filter(
        program=program,
        role="unit_head",
        is_active=True,
    ).exclude(person=author_membership.person).select_related("person")
    return [{"person": m.person, "option_key": "peer_unit_heads", "bunk_id_at_capture": None}
            for m in memberships]


def _uh_leadership_team(
    author_membership: Membership,
    org: Organization,
    program: Program,
    **kwargs: Any,
) -> list[dict]:
    """All LT members of the Program."""
    memberships = Membership.all_objects.filter(
        program=program,
        role="leadership_team",
        is_active=True,
    ).select_related("person")
    return [{"person": m.person, "option_key": "leadership_team", "bunk_id_at_capture": None}
            for m in memberships]


def _uh_administration(
    author_membership: Membership,
    org: Organization,
    program: Program,
    **kwargs: Any,
) -> list[dict]:
    return _counselor_administration(author_membership, org, program)


def _uh_specific_person(
    author_membership: Membership,
    org: Organization,
    program: Program,
    person_id: int | None = None,
    **kwargs: Any,
) -> list[dict]:
    return _counselor_specific_person(author_membership, org, program, person_id=person_id)


# ---------------------------------------------------------------------------
# Option registry
# ---------------------------------------------------------------------------

COUNSELOR_OPTIONS: list[tuple[str, str]] = [
    ("my_unit_head", "My Unit Head"),
    ("administration", "Administration"),
    ("co_counselors_on_bunk", "Co-counselors on this bunk"),
    ("co_counselors_specific_bunk", "Co-counselors on a specific bunk"),
    ("specific_person", "A specific person"),
]

UH_OPTIONS: list[tuple[str, str]] = [
    ("specific_counselor", "A specific counselor I supervise"),
    ("counselors_on_bunk", "All counselors on a specific bunk"),
    ("all_counselors_in_unit", "All counselors in my unit"),
    ("peer_unit_heads", "Peer Unit Heads"),
    ("leadership_team", "Leadership Team"),
    ("administration", "Administration"),
    ("specific_person", "A specific person"),
]

_COUNSELOR_RESOLVERS: dict[str, Any] = {
    "my_unit_head": _counselor_my_unit_head,
    "administration": _counselor_administration,
    "co_counselors_on_bunk": _counselor_co_counselors_on_bunk,
    "co_counselors_specific_bunk": _counselor_co_counselors_specific_bunk,
    "specific_person": _counselor_specific_person,
}

_UH_RESOLVERS: dict[str, Any] = {
    "specific_counselor": _uh_specific_counselor,
    "counselors_on_bunk": _uh_counselors_on_bunk,
    "all_counselors_in_unit": _uh_all_counselors_in_unit,
    "peer_unit_heads": _uh_peer_unit_heads,
    "leadership_team": _uh_leadership_team,
    "administration": _uh_administration,
    "specific_person": _uh_specific_person,
}


def _role_resolvers(role: str) -> dict[str, Any] | None:
    if role in ("counselor", "junior_counselor"):
        return _COUNSELOR_RESOLVERS
    if role == "unit_head":
        return _UH_RESOLVERS
    return None


def _role_options(role: str) -> list[tuple[str, str]] | None:
    if role in ("counselor", "junior_counselor"):
        return COUNSELOR_OPTIONS
    if role == "unit_head":
        return UH_OPTIONS
    return None


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------


def _bunk_ids_for_counselor(membership: Membership) -> list[int]:
    """Bunk AssignmentGroup IDs where this person is an author (counselor)."""
    return list(
        AssignmentGroupMembership.all_objects.filter(
            person=membership.person,
            group__group_type="bunk",
            role_in_group="author",
            is_active=True,
        ).values_list("group_id", flat=True).distinct(),
    )


def _counselors_on_bunk(bunk_id: int, program: Program) -> list[Person]:
    """Active author (counselor) Persons on a bunk via AssignmentGroupMembership."""
    agm_qs = AssignmentGroupMembership.all_objects.filter(
        group_id=bunk_id,
        role_in_group="author",
        is_active=True,
    ).select_related("person")
    return [agm.person for agm in agm_qs]


def _supervised_bunk_ids_for_uh(membership: Membership) -> set[int]:
    """Bunk IDs supervised by the UH, derived transitively via supervised counselors."""
    return set(
        Supervision.objects.bunks_for_uh(membership).values_list("id", flat=True),
    )


def _counselor_ids_on_bunks(bunk_ids: set[int], program: Program) -> set[int]:
    return set(
        AssignmentGroupMembership.all_objects.filter(
            group_id__in=bunk_ids,
            role_in_group="author",
            is_active=True,
        ).values_list("person_id", flat=True),
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def audience_options_for(
    person: Person,
    organization: Organization,
    program: Program,
) -> list[dict]:
    """Return the list of audience option keys + labels for person's active roles.

    Returns empty list if no v1-enabled role is active for the person.
    """
    roles = set(
        Membership.all_objects.filter(
            person=person,
            program__organization=organization,
            is_active=True,
            role__in=V1_AUTHOR_ROLES,
        ).values_list("role", flat=True),
    )
    # Prefer unit_head over counselor if the person has both (edge case).
    if "unit_head" in roles:
        options = UH_OPTIONS
    elif roles & {"counselor", "junior_counselor"}:
        options = COUNSELOR_OPTIONS
    else:
        return []
    return [{"option_key": key, "label": label} for key, label in options]


def resolve_audience(
    author_person: Person,
    author_membership: Membership,
    organization: Organization,
    program: Program,
    audience_requests: list[dict],
) -> list[dict]:
    """Resolve audience options to captured Person rows.

    audience_requests is a list of dicts: {option_key, bunk_id?, person_id?}
    Returns a deduplicated list of {person, option_key, bunk_id_at_capture} dicts
    after applying cross-cutting rules:
      1. Self-exclusion
      2. Active Membership only (enforced inside each resolver)
      3. Org-scoping (enforced inside each resolver)
      4. Dedup by person — one capture row per person

    Raises PermissionDenied if the author role is not v1-enabled.
    Raises ValidationError (via caller) if the resolved audience is empty after
    self-exclusion (decision N1).
    """
    resolvers = _role_resolvers(author_membership.role)
    if resolvers is None:
        msg = "Notes not yet enabled for this role."
        raise PermissionDenied(msg)

    seen_person_ids: set[int] = set()
    results: list[dict] = []

    for req in audience_requests:
        option_key = req.get("option_key")
        if not option_key:
            continue
        resolver = resolvers.get(option_key)
        if resolver is None:
            continue
        rows = resolver(
            author_membership=author_membership,
            org=organization,
            program=program,
            bunk_id=req.get("bunk_id"),
            person_id=req.get("person_id"),
        )
        for row in rows:
            person = row["person"]
            # Self-exclusion (cross-cutting rule 1)
            if person.id == author_person.id:
                continue
            # Dedup
            if person.id in seen_person_ids:
                continue
            seen_person_ids.add(person.id)
            results.append(row)

    return results
