"""Edit-window helper for Madrich Sunday availability (Step 4_7, decision MA6).

MA6: a Madrich may create/update/delete their commitment for session Sunday
``S`` until **Saturday 18:00 America/New_York** -- the calendar day
immediately before ``S`` -- after which the row locks for the Madrich (an
Admin may still override via Django admin per the Out of Scope note). Since
the deadline always falls before the session date itself, a locked deadline
also covers every past session -- there is no separate "is it in the past"
branch needed.

Kept apart from the reflection-period helpers in ``time_utils.py`` because
this locks relative to a fixed wall-clock moment, not the org's
rollover-aware "today".
"""

from __future__ import annotations

from datetime import date
from datetime import datetime
from datetime import time
from datetime import timedelta
from typing import TYPE_CHECKING

from django.utils import timezone

from bunk_logs.core.time_utils import get_org_timezone

if TYPE_CHECKING:
    from bunk_logs.core.models import Organization


DEADLINE_HOUR = 18  # Saturday 18:00 local time.


def availability_deadline(session_date: date, org: Organization | None) -> datetime:
    """Return the aware Saturday-18:00 deadline moment for ``session_date``."""
    tz = get_org_timezone(org)
    saturday = session_date - timedelta(days=1)
    return datetime.combine(saturday, time(DEADLINE_HOUR, 0), tzinfo=tz)


def is_editable(
    session_date: date,
    org: Organization | None,
    *,
    now: datetime | None = None,
) -> bool:
    """True while ``now`` is still before the Saturday-18:00 lock for ``session_date``."""
    moment = now or timezone.now()
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=get_org_timezone(org))
    return moment < availability_deadline(session_date, org)
