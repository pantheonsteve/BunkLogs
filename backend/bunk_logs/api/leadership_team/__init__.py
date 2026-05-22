"""Leadership Team API endpoints (Step 7_12).

Implements Stories 45-53. PR A delivers the supervision-driven dashboard,
team dashboard, individual member reflection reader, self-reflection
submit/edit, and the mark-attention primitive. PR B layers the LT-scoped
template builder and assignment API on top; PR C adds the frontend.

Visibility relies on the existing ``content_visibility`` primitive (Step
7_1); supervision resolution uses ``Supervision.objects.team_members``
(Step 7_3); attention badges reuse helpers from
:mod:`api.unit_head.common` so the per-team card semantics stay
consistent across role flows.
"""
