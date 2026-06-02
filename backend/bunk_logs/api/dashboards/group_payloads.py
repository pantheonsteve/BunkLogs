"""Per-group-type dashboard payload builders.

The unified ``GroupDashboardView`` dispatches on ``group.group_type``
to one of these builders. Bunk payloads live in
:mod:`bunk_logs.api.unit_head.bunk_dashboard` (no change there); this
module owns the rollup payloads for ``unit`` and ``division`` groups
and the minimal TBE ``classroom`` payload.

Design choices:

* Unit and Division payloads reuse the same per-bunk summary shape
  Camper Care's home dashboard exposes ({id, name, slug,
  counselor_names, completion, badges, camper_count}). That keeps the
  frontend roll-up component aligned with the existing CC patterns.
* Division payloads include unit-level counts only (no aggregated
  help-requested / off-camp lists) — the lists would be unwieldy at
  the division scope; users drill into a unit to see them.
* Classroom is a STUB: TBE classroom reflection templates aren't
  designed yet (Madrich self-reflections use ``assignment_group=None``
  per :mod:`bunk_logs.api.madrich.reflection`), so the payload returns
  roster + authors only. Real classroom reflections + completion math
  ship once the templates are specced.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from bunk_logs.api.camper_care.common import bunk_camper_ids
from bunk_logs.api.counselor.common import camper_reflection_template
from bunk_logs.api.counselor.common import person_display_name
from bunk_logs.api.unit_head.common import bunk_concerns_referencing
from bunk_logs.api.unit_head.common import compute_attention_badges
from bunk_logs.api.unit_head.common import expected_by_passed
from bunk_logs.api.unit_head.common import help_requested_camper_ids_from
from bunk_logs.api.unit_head.common import off_camp_camper_ids
from bunk_logs.core.models import AssignmentGroup
from bunk_logs.core.models import AssignmentGroupMembership
from bunk_logs.core.models import Reflection

if TYPE_CHECKING:
    from datetime import date

    from bunk_logs.core.models import Organization
    from bunk_logs.core.models import Person
    from bunk_logs.core.models import Program

# Mirror the constant used by Camper Care's dashboard so the
# low-completion badge fires at the same threshold across surfaces.
_LOW_COMPLETION_THRESHOLD = 0.5


# ---------------------------------------------------------------------------
# Shared bunk-row summary
# ---------------------------------------------------------------------------


def _counselor_names(bunk: AssignmentGroup) -> list[str]:
    """Active counselor display names for a bunk (same shape as CC dashboard)."""
    rows = (
        AssignmentGroupMembership.objects.filter(
            group=bunk, role_in_group="author", is_active=True,
        )
        .select_related("person")
        .order_by("person__last_name", "person__first_name")
    )
    return [person_display_name(agm.person) for agm in rows if agm.person]


def _summarize_bunk(
    *,
    bunk: AssignmentGroup,
    organization: Organization,
    program: Program,
    target_date: date,
    camper_template,
    expected_passed: bool,
    bc_bunk_ids: set[int],
) -> dict:
    """Per-bunk summary row identical to the Camper Care home dashboard shape.

    Returned keys: ``id``, ``name``, ``slug``, ``counselor_names``,
    ``completion {submitted, expected, off_camp}``, ``badges``,
    ``camper_count``. Callers stack these into a list and apply the
    standard sort (badged bunks first, alphabetical within band).
    """
    camper_ids = bunk_camper_ids(bunk)
    off_camp = off_camp_camper_ids(organization, target_date, camper_ids)

    submitted_ids: set[int] = set()
    help_ids: set[int] = set()
    if camper_template and camper_ids:
        reflections = {
            r.subject_id: r
            for r in Reflection.all_objects.filter(
                template=camper_template,
                assignment_group=bunk,
                period_start=target_date,
                period_end=target_date,
                is_complete=True,
            ).select_related("template")
        }
        submitted_ids = set(reflections.keys())
        help_ids = help_requested_camper_ids_from(reflections)

    badges = compute_attention_badges(
        bunk=bunk,
        bunk_camper_ids_list=camper_ids,
        off_camp_ids=off_camp,
        submitted_camper_ids=submitted_ids,
        help_requested_camper_ids=help_ids,
        bunk_concerns_referenced_bunk_ids=bc_bunk_ids,
        low_completion_threshold=_LOW_COMPLETION_THRESHOLD,
        expected_by_passed=expected_passed,
    )

    on_camp_total = len([c for c in camper_ids if c not in off_camp])
    submitted_on_camp = len([
        c for c in camper_ids if c in submitted_ids and c not in off_camp
    ])

    return {
        "id": bunk.id,
        "name": bunk.name,
        "slug": bunk.slug,
        "counselor_names": _counselor_names(bunk),
        "completion": {
            "submitted": submitted_on_camp,
            "expected": on_camp_total,
            "off_camp": len(off_camp),
        },
        "badges": badges,
        "camper_count": len(camper_ids),
        # Lifted out so unit-level callers can re-use these without
        # re-querying. Treated as a private extension; not part of the
        # public CC dashboard shape.
        "_help_requested_camper_ids": list(help_ids),
        "_off_camp_camper_ids": list(off_camp),
        "_camper_ids": camper_ids,
    }


def _sorted_bunks(bunks_payload: list[dict]) -> list[dict]:
    """Standard sort: badged bunks first, then alphabetical."""
    bunks_payload.sort(key=lambda b: (
        0 if b["badges"] else 1, (b["name"] or "").casefold(),
    ))
    return bunks_payload


def _strip_private(rows: list[dict]) -> list[dict]:
    """Drop ``_``-prefixed working fields before the row leaves the API boundary."""
    return [
        {k: v for k, v in row.items() if not k.startswith("_")}
        for row in rows
    ]


def _briefs_for_persons(persons: list[Person]) -> list[dict]:
    """Flatten Person rows into the brief shape the bunk payload uses."""
    return [
        {
            "id": p.id,
            "first_name": p.first_name,
            "last_name": p.last_name,
            "preferred_name": p.preferred_name or "",
        }
        for p in persons
    ]


# ---------------------------------------------------------------------------
# Unit dashboard
# ---------------------------------------------------------------------------


def build_unit_dashboard_payload(
    *,
    request,
    group: AssignmentGroup,
    target_date: date,
    organization: Organization,
    program: Program,
    today: date,
) -> dict:
    """Rollup payload for a ``unit`` group.

    Returns:
        header        — `{group: {id, name, slug, group_type, parent}, date, today}`
        bunks         — sorted per-bunk summaries (Camper Care shape)
        summary       — totals across the unit's bunks
        help_requested — union of help-requested campers across child bunks
        off_camp      — union of off-camp campers
        bunk_concerns — counselor/UH self-reflections referencing any
                        child bunk
    """
    del request  # reserved; future visibility filters can use it.

    bunks = list(
        AssignmentGroup.all_objects.filter(
            parent_id=group.id, group_type="bunk", is_active=True,
        ).select_related("organization", "program"),
    )

    camper_template = camper_reflection_template(
        organization, program, as_of=target_date,
    )
    expected_passed = expected_by_passed(organization, target_date)
    bc_map = bunk_concerns_referencing(
        organization=organization, program=program, target_date=target_date,
    )
    bc_bunk_ids = set(bc_map.keys())

    bunk_rows = [
        _summarize_bunk(
            bunk=b,
            organization=organization,
            program=program,
            target_date=target_date,
            camper_template=camper_template,
            expected_passed=expected_passed,
            bc_bunk_ids=bc_bunk_ids,
        )
        for b in bunks
    ]
    _sorted_bunks(bunk_rows)

    help_camper_ids: set[int] = set()
    off_camper_ids: set[int] = set()
    for row in bunk_rows:
        help_camper_ids.update(row["_help_requested_camper_ids"])
        off_camper_ids.update(row["_off_camp_camper_ids"])

    # Resolve briefs for the union sets (single query).
    from bunk_logs.core.models import Person

    all_brief_ids = help_camper_ids | off_camper_ids
    brief_by_id: dict[int, Person] = (
        {p.id: p for p in Person.all_objects.filter(id__in=all_brief_ids)}
        if all_brief_ids else {}
    )

    submitted = sum(r["completion"]["submitted"] for r in bunk_rows)
    expected = sum(r["completion"]["expected"] for r in bunk_rows)
    off_camp_total = sum(r["completion"]["off_camp"] for r in bunk_rows)
    attention_bunk_count = sum(1 for r in bunk_rows if r["badges"])

    # Bunk concerns scoped to this unit's bunks.
    own_bunk_ids = {b.id for b in bunks}
    concerns: list[dict] = []
    for bid, reflections in bc_map.items():
        if bid not in own_bunk_ids:
            continue
        for r in reflections:
            answers = r.answers or {}
            concerns.append({
                "bunk_id": bid,
                "reflection_id": r.id,
                "author": person_display_name(r.author),
                "author_role": _role_for_template(r.template),
                "submitted_at": r.created_at.isoformat() if r.created_at else None,
                "open_concern": (answers.get("concern") or "").strip()[:280],
                "note": (answers.get("bunk_concerns_note") or "").strip()[:280],
            })

    parent = group.parent
    return {
        "header": {
            "group": {
                "id": group.id,
                "name": group.name,
                "slug": group.slug,
                "group_type": "unit",
                "parent": (
                    {"id": parent.id, "name": parent.name} if parent else None
                ),
            },
            "date": target_date.isoformat(),
            "today": today.isoformat(),
        },
        "bunks": _strip_private(bunk_rows),
        "summary": {
            "submitted": submitted,
            "expected": expected,
            "off_camp": off_camp_total,
            "help_requested_count": len(help_camper_ids),
            "attention_bunk_count": attention_bunk_count,
            "bunk_count": len(bunks),
        },
        "help_requested": _briefs_for_persons(
            [brief_by_id[i] for i in sorted(help_camper_ids) if i in brief_by_id],
        ),
        "off_camp": _briefs_for_persons(
            [brief_by_id[i] for i in sorted(off_camper_ids) if i in brief_by_id],
        ),
        "bunk_concerns": concerns,
    }


# ---------------------------------------------------------------------------
# Division dashboard
# ---------------------------------------------------------------------------


def build_division_dashboard_payload(
    *,
    request,
    group: AssignmentGroup,
    target_date: date,
    organization: Organization,
    program: Program,
    today: date,
) -> dict:
    """Rollup payload for a ``division`` group.

    Returns one row per direct-child unit (counts only — no per-camper
    detail at this scope). The frontend renders this as a one-screen
    overview with drill-down links into each unit's dashboard.
    """
    del request

    units = list(
        AssignmentGroup.all_objects.filter(
            parent_id=group.id, group_type="unit", is_active=True,
        ),
    )

    camper_template = camper_reflection_template(
        organization, program, as_of=target_date,
    )
    expected_passed = expected_by_passed(organization, target_date)
    bc_map = bunk_concerns_referencing(
        organization=organization, program=program, target_date=target_date,
    )
    bc_bunk_ids = set(bc_map.keys())

    unit_rows: list[dict] = []
    grand_submitted = 0
    grand_expected = 0
    grand_off_camp = 0
    grand_bunk_count = 0
    grand_attention_count = 0
    for unit in units:
        bunks_in_unit = list(
            AssignmentGroup.all_objects.filter(
                parent_id=unit.id, group_type="bunk", is_active=True,
            ),
        )
        rows = [
            _summarize_bunk(
                bunk=b,
                organization=organization,
                program=program,
                target_date=target_date,
                camper_template=camper_template,
                expected_passed=expected_passed,
                bc_bunk_ids=bc_bunk_ids,
            )
            for b in bunks_in_unit
        ]
        sub = sum(r["completion"]["submitted"] for r in rows)
        exp = sum(r["completion"]["expected"] for r in rows)
        off = sum(r["completion"]["off_camp"] for r in rows)
        att = sum(1 for r in rows if r["badges"])
        unit_rows.append({
            "id": unit.id,
            "name": unit.name,
            "slug": unit.slug,
            "bunk_count": len(bunks_in_unit),
            "attention_bunk_count": att,
            "completion": {"submitted": sub, "expected": exp, "off_camp": off},
        })
        grand_submitted += sub
        grand_expected += exp
        grand_off_camp += off
        grand_bunk_count += len(bunks_in_unit)
        grand_attention_count += att

    unit_rows.sort(key=lambda r: (
        0 if r["attention_bunk_count"] else 1, (r["name"] or "").casefold(),
    ))

    return {
        "header": {
            "group": {
                "id": group.id,
                "name": group.name,
                "slug": group.slug,
                "group_type": "division",
                "parent": None,
            },
            "date": target_date.isoformat(),
            "today": today.isoformat(),
        },
        "units": unit_rows,
        "summary": {
            "submitted": grand_submitted,
            "expected": grand_expected,
            "off_camp": grand_off_camp,
            "bunk_count": grand_bunk_count,
            "unit_count": len(units),
            "attention_bunk_count": grand_attention_count,
        },
    }


# ---------------------------------------------------------------------------
# Classroom dashboard (minimal stub)
# ---------------------------------------------------------------------------


def build_classroom_dashboard_payload(
    *,
    request,
    group: AssignmentGroup,
    target_date: date,
    organization: Organization,
    program: Program,
    today: date,
) -> dict:
    """Roster + authors for a TBE ``classroom`` group.

    Intentionally minimal: classroom reflection templates are not yet
    designed (Madrich self-reflections use ``assignment_group=None``),
    so we expose only what we can render cleanly today — student
    roster, faculty/madrich authors, and counts. When classroom
    reflections land we can add ``completion`` and ``help_requested``
    sections that mirror the bunk shape.
    """
    del request, organization, program

    subjects = list(
        AssignmentGroupMembership.objects.filter(
            group=group, role_in_group="subject", is_active=True,
        )
        .select_related("person")
        .order_by("person__last_name", "person__first_name"),
    )
    authors = list(
        AssignmentGroupMembership.objects.filter(
            group=group, role_in_group="author", is_active=True,
        )
        .select_related("person")
        .order_by("person__last_name", "person__first_name"),
    )

    return {
        "header": {
            "group": {
                "id": group.id,
                "name": group.name,
                "slug": group.slug,
                "group_type": "classroom",
                "parent": None,
            },
            "date": target_date.isoformat(),
            "today": today.isoformat(),
        },
        "subjects": _briefs_for_persons([agm.person for agm in subjects if agm.person]),
        "authors": [
            {
                "id": agm.person.id,
                "name": person_display_name(agm.person),
            }
            for agm in authors if agm.person
        ],
        "summary": {
            "subject_count": len(subjects),
            "author_count": len(authors),
        },
    }


# ---------------------------------------------------------------------------
# Misc helpers
# ---------------------------------------------------------------------------


def _role_for_template(template) -> str:
    """Friendly role label for a self-reflection template (counselor / unit_head / camper_care)."""
    if template is None:
        return ""
    return getattr(template, "role", "") or ""
