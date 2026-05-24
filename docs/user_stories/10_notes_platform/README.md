# Notes Platform

Stories 66–70. Notes is a cross-role two-way communication primitive available to every role. It is not specific to any one role flow.

**Pattern:** Anywhere a structured workplace needs a thin, auditable conversation layer that sits alongside (not inside) operational content — a hospital pager-and-followup channel that doesn't replace the chart, a school-staff Slack channel that doesn't replace the gradebook — this flow applies.

See `../00_cross_cutting/visibility_model.md` for how Notes fit the platform visibility model, and `../00_cross_cutting/decisions.md` (Notes platform section, N1–N9) for the resolved decisions that shape these stories.

## Stories

66. Compose a Note with audience and optional camper reference
67. Notes Inbox, Sent, and Archive
68. Reply to a Note thread
69. Cross-reference — start a Note from a Bunk concern
70. Cross-reference — start a Note from a Specialist camper note

## Why Notes is a separate primitive

The platform already has three text-input surfaces for communication:

| Surface | Shape | Direction | Where it lives |
|---|---|---|---|
| Bunk concerns | Optional field on counselor self-reflection (per UH2 in decisions.md) | One-way escalation | Inside the reflection |
| Specialist camper notes | Attached to a camper (Stories 26–28) | Informational record | On the camper profile |
| Notes | Standalone, threaded, two-way | Author-addressed conversation | Its own surface |

The three are deliberately distinct (per decision N2). Notes covers the gaps the other two don't:

- Mid-week or mid-day communication that doesn't fit the daily reflection moment
- Heads-up to a co-worker about something happening tomorrow
- Questions to admin
- Two-way conversation where the existing surfaces are one-way

Cross-references (Stories 69, 70) let a supervisor or reader *escalate* an existing one-way surface into a two-way conversation without duplicating the content. The original Bunk concern or Specialist note is untouched; the Note thread is a separate object that references it.

## Scope in v1

Per decision N4: Counselor and Unit Head only in v1. UH is required because Story 69 (the most valuable cross-reference) lives on the UH side. Other roles get Notes as their flow revisions happen.

The Notes data model and API are designed to be role-agnostic from the start. Adding a role to the v1 stack is a matter of adding entries to `audience_matrices.md` and gating sidebar visibility — no schema changes required.

## Out of scope for Tier 1

- Note-to-self / private journaling (N1)
- Status field on Notes (N5)
- Thread locking by the original author (N6)
- Editing replies post-submission (N8)
- Roles beyond Counselor and Unit Head (N4)
- Attachments (photos, files) on Notes — defer for now; Specialist note attachments are also Tier 2
- Push notifications outside the app — Tier 2; v1 uses in-app unread badges and the my-tasks queue
