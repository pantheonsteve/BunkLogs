"""Test-support constants. Not imported by application code.

Program fixtures across the suite hardcoded a June 1 - August 31 2026
window, so every test that needed "today falls inside a running program"
started failing the moment the calendar passed August 31 -- roughly 200 of
them, with no code change. Those tests want *a program that is running
now*, not a specific summer, so anchor the window on today.

The bounds are module-level constants rather than functions on purpose:
computed once at first import, every fixture in a session agrees even if
the run crosses midnight.
"""
from __future__ import annotations

from datetime import date
from datetime import timedelta

# Wide enough that period math (weekly, biweekly, monthly cadences) has room
# on both sides of today without a fixture landing on a boundary.
SEASON_HALF_WIDTH_DAYS = 60

SEASON_START = date.today() - timedelta(days=SEASON_HALF_WIDTH_DAYS)
SEASON_END = date.today() + timedelta(days=SEASON_HALF_WIDTH_DAYS)
