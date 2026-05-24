# Consolidated Decisions

Approximately 60 decisions surfaced during the story tightening pass. Each has a recommended resolution. Decisions resolved during tightening are reflected directly in the stories; this document tracks the resolutions and any decisions still open.

## Status legend

- ✅ **Resolved** — reflected in stories, no action needed
- ⏳ **Awaiting confirmation** — recommendation pending Steve's sign-off
- 🔄 **Deferred** — Tier 2 or later

## Counselor

| # | Decision | Resolution | Status |
|---|---|---|---|
| C1 | Who marks a camper off-camp? | UH or Camper Care | ⏳ |
| C2 | Edit history visibility on camper reflections | Supervisors only (UH+); co-counselors do not see prior versions | ⏳ |
| C3 | Self-reflection drafts visible to supervisors? | No, private until submitted | ⏳ |
| C4 | Co-counselors see each other's open camper-care requests? | Yes, with submitter name attached | ⏳ |
| C5 | Counselors add follow-up photos/comments to their open maintenance tickets? | Yes | ⏳ |
| C6 | Who maintains the camper-care item list? | Admin, per program (Story 58) | ⏳ |

## Unit Head

| # | Decision | Resolution | Status |
|---|---|---|---|
| UH1 | Expected-by time for low-completion badge | End of dinner hour, configurable per program (default 19:00 camp, end-of-session school) | ⏳ |
| UH2 | What constitutes a "bunk concern"? | Optional field on Counselor self-reflection, not a separate submission | ⏳ |
| UH3 | Per-camper daily average column on score grid | No for Tier 1 | ⏳ |
| UH4 | UH private note on a camper | No for Tier 1 | ⏳ |
| UH5 | UH cadence | Daily for camp, weekly for religious-school equivalent | ⏳ |
| UH6 | UH-to-UH peer reflection visibility | No (LT and Admin see all UH reflections) | ⏳ |

## Camper Care

| # | Decision | Resolution | Status |
|---|---|---|---|
| CC1 | Caseload assignment model | Dedicated `CamperCareCaseload` (modeled as Supervision records with target_type=BUNK) | ⏳ |
| CC2 | Overlapping caseloads | Permitted; bunk appears on multiple Camper Care members' dashboards | ⏳ |
| CC3 | Who resolves a flag | Camper Care only; original raiser can add follow-up | ⏳ |
| CC4 | Flag severity dimension | None for Tier 1 | ⏳ |
| CC5 | Non-sensitive Camper Care note visibility | Camper Care + Leadership Team + Admin only (more restrictive than loose version) | ⏳ |
| CC6 | Note attachments (photos, etc.) | Out of scope for Tier 1 | 🔄 |
| CC7 | Order routing: team-shared or caseload-scoped | Team-shared with caseload filter available | ⏳ |
| CC8 | Fulfilled-order auto-archive | No; date filter on Resolved section | ⏳ |

## Specialist

| # | Decision | Resolution | Status |
|---|---|---|---|
| S1 | Cross-membership Specialist + Counselor case | Role switcher; defer to Tier 2 unless common | 🔄 |
| S2 | Multi-select for batch noting | Out of scope for Tier 1 | 🔄 |
| S3 | Group / session-level notes | Out of scope for Tier 1 | 🔄 |
| S4 | Note deletion | No; retraction via follow-up | ⏳ |
| S5 | Flag persistence after note edit | Specialist cannot retract a flag they raised | ⏳ |
| S6 | Search across user's own historical notes | Out of scope for Tier 1 | 🔄 |
| S7 | Specialist self-reflection visible to UH? | No (Leadership Team + Admin only) | ⏳ |

## Maintenance

| # | Decision | Resolution | Status |
|---|---|---|---|
| M1 | Awaiting parts / blocked status | No; stays In Progress with notes | ⏳ |
| M2 | Digest default send time | 06:00 org-local; configurable | ⏳ |

## Kitchen Staff

| # | Decision | Resolution | Status |
|---|---|---|---|
| KS1 | Hebrew/RTL scope | Content-only for Tier 1; full UI in Tier 2 | 🔄 |
| KS2 | Kitchen operational signal on dashboard | Out of scope | 🔄 |
| KS3 | Translation maintenance workflow | Template author maintains translations in builder | ⏳ |
| KS4 | Translation audit retention | 90 days | ⏳ |
| KS5 | Live draft translation | No | ⏳ |
| KS6 | i18n library | `react-i18next` | ⏳ |
| KS7 | Translation target languages | English-only for Tier 1 | ⏳ |
| KS8 | Translation confidence flagging | Not in Tier 1 | 🔄 |

## Leadership Team

| # | Decision | Resolution | Status |
|---|---|---|---|
| LT1 | Template builder Tier 1/Tier 2 split | Defined; see Story 51 scope statement | ⏳ |
| LT2 | LT visibility scope | Explicit-supervision-only | ⏳ |
| LT3 | Co-supervisor model | Many-to-many; multiple LT supervisors per team | ⏳ |
| LT4 | Concerning ratings algorithm | Lowest scale value triggers automatic flag | ⏳ |
| LT5 | LT private note on reflection | Not in Tier 1 | 🔄 |
| LT6 | Free-text theme aggregation | Out of scope for Tier 1 | 🔄 |
| LT7 | Co-supervisor template visibility/cloning | See and clone, not edit | ⏳ |
| LT8 | Template approval workflow | Not in Tier 1; surface to Admin without gating | ⏳ |
| LT9 | System-provided base templates | Yes; shipped with platform | ⏳ |
| LT10 | Multi-team template assignment | Yes | ⏳ |
| LT11 | Cross-program assignment | No for Tier 1 | 🔄 |
| LT12 | Real-time response feed | Manual refresh for Tier 1 | ⏳ |
| LT13 | CSV export of free-text content | Yes, both languages when relevant | ⏳ |

## Admin

| # | Decision | Resolution | Status |
|---|---|---|---|
| A1 | Cross-org Admin scenario | Not a customer-facing role; superuser scope only | ⏳ |
| A2 | Attention conditions list | Six conditions for Tier 1 (see Story 54 criterion 5) | ⏳ |
| A3 | Bulk Membership deactivation at end-of-program | Yes, via End Program action | ⏳ |
| A4 | Backdated assignment effect on historical content | Forward from correction date only; no retroactive reattribution | ⏳ |
| A5 | Non-Admin assignment authority | Admin-only for Tier 1 | 🔄 |
| A6 | Tag vocabulary management | Admin owns; UH/LT apply existing only | ⏳ |
| A7 | System-template management | Anthropic/Steve at platform release | ⏳ |
| A8 | Brand and visual customization | Logo only for Tier 1 | 🔄 |
| A9 | Email reminder body customization | Not in Tier 1; scheduling only | 🔄 |
| A10 | Global search performance/scope | PostgreSQL FTS; sub-2-second for typical org | ⏳ |
| A11 | Audit trail retention | Lifetime of org | ⏳ |

## Madrich

| # | Decision | Resolution | Status |
|---|---|---|---|
| MA1 | Week boundary day for TBE | Monday-Sunday | ⏳ |
| MA2 | Reminder timing | Wednesday evening | ⏳ |
| MA3 | Grade-differentiated content | Single template Tier 1; differentiation Tier 2 | 🔄 |
| MA4 | Parent visibility | No for Tier 1 (Tier 2 per proposal) | 🔄 |
| MA5 | Co-Director model | Yes, reusing LT co-supervisor pattern | ⏳ |

## Notes platform

| # | Decision | Resolution | Status |
|---|---|---|---|
| N1 | Note-to-self path | Not supported; every Note has at least one other recipient | ⏳ |
| N2 | Notes vs Bunk concerns vs Specialist notes | Keep three primitives distinct with cross-references; Notes does not replace either | ⏳ |
| N3 | Notes scope | Platform primitive; available to every role with role-specific audience matrices | ⏳ |
| N4 | v1 rollout scope | Counselor + Unit Head only in v1 (UH is required for the Story 69 cross-reference path). Other roles wired in as their flows are revised. | ⏳ |
| N5 | Status field on Notes (Open/Acknowledged/Closed) | Not in Tier 1; defer to v2 based on usage signal | 🔄 |
| N6 | Thread locking by original author | Not in Tier 1; threads stay open while the note exists | 🔄 |
| N7 | Cross-reference access transitivity | Viewing a Note thread does NOT grant access to its referenced source; reader must independently have access | ⏳ |
| N8 | Reply edit-ability | Replies are not editable after submission (differs from reflections); corrections via follow-up reply | ⏳ |
| N9 | Archive semantics | Per-user archive that hides from the archiver's Inbox/Sent but preserves the note for other audience members and the audit trail | ⏳ |

## Form Assignment

See `docs/design/form_orchestration_reframe.md` for the design narrative behind these decisions.

| # | Decision | Resolution | Status |
|---|---|---|---|
| FA1 | Implicit vs explicit assignment | Explicit only. Publishing a template does not create tasks. The template author opens a published template and clicks "Assign form" to open a dialog capturing: target assignment group, dashboard title, cadence, required/optional flag, start date, end date. Submitted assignments immediately produce tasks on appropriate role dashboards. Published-but-unassigned templates sit dormant in the library. | ⏳ |
| FA2 | Multiple assignments per template | Allowed. The same published template can be assigned to multiple `(assignment_group, cadence)` tuples. Enables time-saving reuse across groups and cadences. | ⏳ |
| FA3 | Mid-flight assignment changes | End-date the old `FormAssignment` and create a new one. Never destructive in-place. The builder UI offers a "change cadence" affordance that performs the end-date-and-create-new pattern atomically. Audit-logged. | ⏳ |
| FA4 | Numeric color-coding | Per-field, palette-based. The platform ships a library of named palettes (each declaring its scale length, e.g., a 5-point severity palette, a 4-point performance palette). The builder offers only scale-compatible palettes for a given field. The author can either pick a palette or define a custom color-per-value mapping. The numeric value is always rendered in the cell alongside color, and the lowest-quartile cell gets a hatched pattern overlay for accessibility. Initial 5-point palette: 1=#E76846, 2=#DE8D6F, 3=#E5E824, 4=#8FD258, 5=#14D127. | ⏳ |
| FA5 | Optional assignments | Surfaced separately from tasks; do not appear in the task queue. Available in a per-role "forms I can also fill out" library. Do not affect the "all set" semantic. | ⏳ |
| FA6 | Subject landing for non-camper subjects | Yes. A counselor's own landing page includes a "things written about me" widget, visibility-filtered per the platform visibility model. `supervisors_only`-flagged content renders as a placeholder count, never the body. | ⏳ |
| FA7 | Who can create assignments | LT (`program_lead` capability) and Admin (`admin` capability). UH (`supervisor`) can view all assignments scoped to their supervised groups but cannot create or modify. Allowing Admin to create/edit assignments expands the existing template-builder permission scope; the builder UI gate must be widened from `program_lead`-only to `program_lead OR admin`. | ⏳ |
| FA8 | Notes in tasks queue | Notes are NOT FormAssignments. The Notes-with-unread-replies section of the task queue (per prompt 7_19) remains a separate concept rendered alongside FormAssignment-driven tasks. Conceptually distinct: Notes have no template, no submission, no completion semantic. | ⏳ |
| FA9 | Tickets/orders relative to FormAssignment | Tickets/orders are NOT FormAssignments. Camper Care orders and Maintenance tickets retain their own state machine and surface on landing pages as their own widgets. | ⏳ |
| FA10 | Rollout strategy | **Aggressive: ship the FormAssignment substrate BEFORE June 5, 2026.** The new role flows launch on the new substrate from day one. No shadow mode, no backfill, no incremental cutover — because no live user data exists on the new architecture yet. Existing template-driven implicit tasks are converted to explicit FormAssignment rows as part of seeding for Summer 2026. The implicit task-derivation logic is removed in the same release. Risk and timing implications are captured in `docs/design/form_orchestration_reframe.md` §7. | ⏳ |

## Confirmation needed before implementation begins

All ⏳ "awaiting confirmation" items above should be confirmed (or overridden) by Steve before the corresponding implementation prompts begin. A single sign-off session covering this document is the recommended workflow.
