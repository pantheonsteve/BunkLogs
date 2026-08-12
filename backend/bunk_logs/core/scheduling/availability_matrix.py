"""Row/column matrix builder for Madrich availability staffing views.

Shared by the org-admin staffing matrix (``api/admin_flow``) and the
classroom-scoped faculty view (``api/faculty``, Step 4_7 AC4) so both agree
on cell shape, sort order, and the default "next 8 sessions" window.
"""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

from bunk_logs.core.models import MadrichAvailability
from bunk_logs.core.scheduling.sessions import program_session_dates

if TYPE_CHECKING:
    from bunk_logs.core.models import Membership
    from bunk_logs.core.models import Person
    from bunk_logs.core.models import Program


DEFAULT_SESSION_COUNT = 8


def resolve_session_window(
    program: Program,
    *,
    from_date: date | None = None,
    to_date: date | None = None,
    today: date,
) -> list[date]:
    """Explicit ``from``/``to`` window when given, else the next 8 sessions."""
    all_dates = program_session_dates(program)
    if from_date is not None or to_date is not None:
        lo = from_date or today
        hi = to_date or date.max
        return [d for d in all_dates if lo <= d <= hi]
    return [d for d in all_dates if d >= today][:DEFAULT_SESSION_COUNT]


def build_matrix_rows(
    program: Program,
    memberships: list[Membership],
    session_dates: list[date],
) -> list[dict]:
    """One row per membership, ordered by grade then name (AC4.1/AC4.4 shape)."""
    person_ids = [m.person_id for m in memberships if m.person_id]
    by_person: dict[int, dict[date, MadrichAvailability]] = {}
    if person_ids and session_dates:
        qs = MadrichAvailability.objects.filter(
            program=program, person_id__in=person_ids, session_date__in=session_dates,
        )
        for row in qs:
            by_person.setdefault(row.person_id, {})[row.session_date] = row

    rows: list[dict] = []
    for m in memberships:
        person = m.person
        person_rows = by_person.get(m.person_id, {})
        cells = [
            {
                "session_date": d.isoformat(),
                "status": (person_rows[d].status if d in person_rows else None),
                "note": (person_rows[d].note if d in person_rows else ""),
            }
            for d in session_dates
        ]
        rows.append({
            "person_id": person.id if person else None,
            "display_name": _display_name(person) if person else "",
            "grade_level": m.grade_level,
            "cells": cells,
        })
    rows.sort(
        key=lambda r: (r["grade_level"] is None, r["grade_level"] or 0, r["display_name"].casefold()),
    )
    return rows


def summarize_counts(rows: list[dict], session_dates: list[date]) -> dict:
    """``{available_counts, unset_counts}`` keyed by ISO session date."""
    available_counts = {d.isoformat(): 0 for d in session_dates}
    unset_counts = {d.isoformat(): 0 for d in session_dates}
    for row in rows:
        for cell in row["cells"]:
            if cell["status"] == MadrichAvailability.STATUS_AVAILABLE:
                available_counts[cell["session_date"]] += 1
            elif cell["status"] is None:
                unset_counts[cell["session_date"]] += 1
    return {"available_counts": available_counts, "unset_counts": unset_counts}


def _display_name(person: Person) -> str:
    first = (person.preferred_name or person.first_name or "").strip()
    last = (person.last_name or "").strip()
    return f"{first} {last}".strip() if (first or last) else ""
