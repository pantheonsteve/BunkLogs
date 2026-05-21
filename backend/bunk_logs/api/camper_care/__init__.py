"""Camper Care role flow API (Step 7_8).

Endpoints under ``/api/v1/camper-care/`` covering Stories 18-23:
caseload-tree dashboard, flagged-campers triage workspace, orders
workspace (team-shared per CC7), and Camper Care notes with the 24h
edit window.

Visibility is enforced via the cross-cutting visibility model (Step
7_1) and the supervision-derived caseload (Step 7_3). Order transition
endpoints proxy to the shared state-machine views from Step 7_2 so the
correction window + activity log behave identically across roles.
"""
