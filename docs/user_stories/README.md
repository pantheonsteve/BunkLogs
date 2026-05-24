# BunkLogs User Stories — Canonical Product Spec

This directory is the spec of record for the role-based UI work targeting Crane Lake Summer 2026 (June 5) and Temple Beth-El Fall 2026 (September). Every implementation prompt under `migration_prompts/7_*` references these stories as the source of truth for what the UI does, who can do it, and what acceptance looks like.

## How to read this

Each role flow lives in its own folder (`01_counselor/`, `02_unit_head/`, etc.). Within a folder, stories are numbered sequentially with the same numbers used throughout product conversations and implementation prompts. Cross-cutting primitives that aren't owned by any one role (visibility model, state machine, supervision relationship, audit trail, internationalization) live in `00_cross_cutting/` and are referenced by multiple role flows.

Stories are **canonical**. If a prompt and a story disagree, the story wins; the prompt should be corrected. If real-world implementation surfaces a need to change behavior, update the story first, then update any in-flight prompt.

## The roles

| # | Role | Folder | Pattern |
|---|---|---|---|
| 1 | Counselor | `01_counselor/` | Primary daily observer of a fixed roster |
| 2 | Unit Head | `02_unit_head/` | Mid-level supervisor with scoped read access |
| 3 | Camper Care | `03_camper_care/` | Horizontal support function with a caseload |
| 4 | Specialist | `04_specialist/` | High-traffic shallow contributor across many subjects |
| 5 | Maintenance | `05_maintenance/` | Work-queue operator |
| 6 | Kitchen Staff | `06_kitchen_staff/` | Operationally separate contributor with multilingual needs |
| 7 | Leadership Team | `07_leadership_team/` | Broad-visibility supervisor + platform shaper |
| 8 | Admin | `08_admin/` | Org-scoped configurator and overseer |
| 9 | Madrich (TBE) | `09_madrich/` | Teen contributor at religious school (Kitchen Staff variant) |
| 10 | Notes platform | `10_notes_platform/` | Cross-role two-way communication primitive (not a role) |

## Cross-cutting primitives

Every role flow leans on these. Defined once in `00_cross_cutting/`:

- **Visibility model** — who can read what, audience disclosure, sensitivity flag
- **Order/ticket state machine** — shared by Camper Care orders and Maintenance tickets
- **Supervision relationship** — UH-Counselor, Camper Care-Caseload, LT-Team, Director-Madrich
- **Audit trail** — content edits, status changes, admin overrides
- **Internationalization layers** — content language vs. UI translation vs. auto-translation

## Decision log

Stories surfaced ~60 "decisions needed" during the tightening pass. The consolidated list lives in `00_cross_cutting/decisions.md`. Decisions resolved during tightening are reflected directly in the stories; decisions still open are listed in `decisions.md` with their recommended resolution and the stories they affect.

## Tier 1 / Tier 2 boundary

Stories in this directory are **Tier 1** unless explicitly noted otherwise. Tier 1 = shipping for Crane Lake Summer 2026 and TBE Fall 2026. Deferred features are flagged inline with "Tier 2:" annotations or listed in role-specific "Out of scope" sections.

The most important Tier 1 / Tier 2 split is the **template builder** scope (`07_leadership_team/STORIES.md`). That story states the boundary explicitly.

## Status

| Role flow | Status |
|---|---|
| Counselor | Tightened |
| Unit Head | Tightened |
| Camper Care | Tightened |
| Specialist | Tightened |
| Maintenance | Tightened |
| Kitchen Staff | Tightened |
| Leadership Team | Tightened |
| Admin | Tightened |
| Madrich | Tightened |
| Notes platform | New — v1 scope Counselor + Unit Head per decision N4 |
