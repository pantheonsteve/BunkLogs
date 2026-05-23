"""Rollover-aware "today" helper for per-organization day boundaries.

Story 2 criterion 4 / Story 58 / Step 7_6 spec:

> The date the dashboard considers "today" is determined by a single
> org-level **rollover hour** setting. Camp orgs default to 04:00 in
> the org's timezone; religious-school orgs default to 00:00.

The rollover hour means: between midnight and ``rollover_hour:00``, the
"camp day" is still *yesterday*. A counselor logging in at 02:30
should still see the prior calendar day's roster and submit reflections
for it, because their workday hasn't ended yet.

Configuration lives on ``Organization.settings`` (JSONField) so org admins
can tweak the boundary per tenant without a schema migration:

* ``rollover_hour`` (0..23, default 4) -- camp orgs.
* ``timezone`` (IANA name, default :data:`django.conf.settings.TIME_ZONE`).

If the org's only program is ``religious_school``, the default rollover
flips to 0 because religious-school days are calendar days, not late-night
shifts. Org admins can override either default by writing an explicit
``rollover_hour`` into ``Organization.settings``.

The helper is intentionally tiny -- it's called from every dashboard
endpoint, so it must stay branch-free and stub-friendly for tests.
"""
from __future__ import annotations

from datetime import date
from datetime import datetime
from datetime import timedelta
from typing import TYPE_CHECKING
from zoneinfo import ZoneInfo
from zoneinfo import ZoneInfoNotFoundError

from django.conf import settings
from django.utils import timezone

from bunk_logs.core.models import Program

if TYPE_CHECKING:
    from bunk_logs.core.models import Organization


CAMP_DEFAULT_ROLLOVER_HOUR = 4
SCHOOL_DEFAULT_ROLLOVER_HOUR = 0
_MIN_HOUR = 0
_MAX_HOUR = 23


def _coerce_hour(value: object, fallback: int) -> int:
    """Return ``value`` if it's a valid 0..23 int, else ``fallback``.

    Org settings come from a JSONField, so callers may have written a
    string by mistake. We accept ints only -- silently fall back rather
    than blow up a dashboard request.
    """
    if isinstance(value, bool):
        return fallback
    if isinstance(value, int) and _MIN_HOUR <= value <= _MAX_HOUR:
        return value
    return fallback


def _resolve_timezone(name: object) -> ZoneInfo:
    if isinstance(name, str) and name:
        try:
            return ZoneInfo(name)
        except ZoneInfoNotFoundError:
            pass
    return ZoneInfo(settings.TIME_ZONE)


def _default_rollover_for(org: Organization | None) -> int:
    """Religious-school-only orgs default to midnight; everyone else to 04:00.

    Detecting "religious school only" requires querying active Program rows
    for the org.
    """
    if org is None:
        return CAMP_DEFAULT_ROLLOVER_HOUR

    program_types = set(
        Program.all_objects.filter(organization=org, is_active=True).values_list(
            "program_type", flat=True,
        ),
    )
    if program_types and program_types <= {"religious_school"}:
        return SCHOOL_DEFAULT_ROLLOVER_HOUR
    return CAMP_DEFAULT_ROLLOVER_HOUR


def get_rollover_hour(org: Organization | None) -> int:
    """Return the active rollover hour for ``org`` (0..23)."""
    if org is None:
        return CAMP_DEFAULT_ROLLOVER_HOUR
    org_settings = org.settings or {}
    override = org_settings.get("rollover_hour")
    return _coerce_hour(override, _default_rollover_for(org))


def get_org_timezone(org: Organization | None) -> ZoneInfo:
    """Return the IANA timezone for ``org``, falling back to settings."""
    org_settings = (org.settings or {}) if org is not None else {}
    return _resolve_timezone(org_settings.get("timezone"))


def get_today(org: Organization | None, *, now: datetime | None = None) -> date:
    """Return the date the org currently considers "today".

    Between local midnight and ``rollover_hour:00`` the previous calendar
    day is returned; from ``rollover_hour:00`` onward the current calendar
    day is. Callers should treat the return value as the canonical
    ``period_start`` / ``period_end`` for daily reflections.

    ``now`` is exposed for deterministic tests; production callers should
    let it default to :func:`django.utils.timezone.now`.
    """
    moment = now or timezone.now()
    if moment.tzinfo is None:
        # ``timezone.now()`` is always aware when ``USE_TZ`` is True; this
        # branch covers tests that pass a naive datetime so we don't trip
        # on ``astimezone`` raising.
        moment = moment.replace(tzinfo=ZoneInfo("UTC"))

    tz = get_org_timezone(org)
    local_now = moment.astimezone(tz)
    rollover = get_rollover_hour(org)
    if local_now.hour < rollover:
        return (local_now - timedelta(days=1)).date()
    return local_now.date()


def get_today_for_program(
    program: Program | None, *, now: datetime | None = None,
) -> date:
    """Convenience wrapper for callers that have a Program in hand."""
    if program is None:
        return get_today(None, now=now)
    return get_today(program.organization, now=now)


# ---------------------------------------------------------------------------
# Cadence-driven period bounds (Step 7_14 — MA1 Monday-Sunday weekly)
# ---------------------------------------------------------------------------

# Weekly cadence boundary used by TBE Madrich (MA1: Monday-Sunday). Programs
# may override via ``Program.settings['week_boundary_day']`` (0=Mon..6=Sun)
# when their cohort meets on a different day. The default keeps Story 65's
# "Week of [start]-[end]" framing aligned with the ISO week.
_DEFAULT_WEEK_START_DAY = 0  # Monday


def _coerce_week_start_day(value: object) -> int:
    """Return ``value`` if it's a valid 0..6 int (Mon..Sun), else Monday."""
    if isinstance(value, bool):
        return _DEFAULT_WEEK_START_DAY
    if isinstance(value, int) and 0 <= value <= 6:
        return value
    return _DEFAULT_WEEK_START_DAY


def get_current_period(
    template_cadence: str | None,
    org: Organization | None,
    *,
    program: Program | None = None,
    anchor: date | None = None,
    now: datetime | None = None,
) -> tuple[date, date]:
    """Return ``(period_start, period_end)`` for the current cadence period.

    Anchored on ``anchor`` when provided, else the org's rollover-aware
    "today". Mirrors the per-cadence semantics already used by the
    leadership-team ``resolve_period`` helper so that read views and
    submission endpoints agree on period bounds.

    Weekly default is Monday-Sunday per Step 7_14 MA1; a program can
    override via ``Program.settings['week_boundary_day']`` (0=Mon..6=Sun)
    when its cohort meets on a different day.
    """
    target_date = anchor or get_today(org, now=now)
    cadence = (template_cadence or "daily").lower()

    if cadence in ("daily", "on_demand"):
        return target_date, target_date

    if cadence == "weekly":
        week_start_day = _DEFAULT_WEEK_START_DAY
        if program is not None:
            week_start_day = _coerce_week_start_day(
                (program.settings or {}).get("week_boundary_day"),
            )
        offset = (target_date.weekday() - week_start_day) % 7
        start = target_date - timedelta(days=offset)
        return start, start + timedelta(days=6)

    if cadence == "biweekly":
        if program is not None and program.start_date:
            ref = program.start_date
        else:
            ref = target_date - timedelta(days=target_date.weekday())
        delta_days = (target_date - ref).days
        period_index = delta_days // 14
        start = ref + timedelta(days=period_index * 14)
        return start, start + timedelta(days=13)

    if cadence == "monthly":
        start = target_date.replace(day=1)
        if start.month == 12:
            next_first = start.replace(year=start.year + 1, month=1)
        else:
            next_first = start.replace(month=start.month + 1)
        return start, next_first - timedelta(days=1)

    return target_date, target_date
