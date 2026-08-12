"""Program session-date parsing shared by Madrich, admin, and faculty views.

``session_dates`` lives on ``Program.settings`` (Step 4_1 ``setup_tbe``) as a
JSON list of ISO date strings, one per program Sunday.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.utils.dateparse import parse_date

if TYPE_CHECKING:
    from datetime import date

    from bunk_logs.core.models import Program


def program_session_dates(program: Program) -> list[date]:
    """Parsed, sorted ``Program.settings['session_dates']``."""
    raw = (program.settings or {}).get("session_dates") or []
    parsed = [parse_date(s) for s in raw if isinstance(s, str)]
    return sorted(d for d in parsed if d is not None)
