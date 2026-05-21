"""Counselor-facing read endpoints (Step 7_6b).

Endpoints under ``/api/v1/counselor/`` for the mobile-first counselor flow:

- ``GET /dashboard/`` — Story 2: roster + self + requests, with "all set"
- ``GET /camper-reflections/?date=<>`` — Story 3: bunk roster for a date
- ``GET /self-reflection/history/`` — Story 6: counselor's prior reflections
- ``GET /requests/`` — Stories 7, 8: my + co-counselors' open Orders & Tickets

Write endpoints (submit / edit) live in 7_6c.
"""
