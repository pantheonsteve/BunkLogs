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

## Confirmation needed before implementation begins

All ⏳ "awaiting confirmation" items above should be confirmed (or overridden) by Steve before the corresponding implementation prompts begin. A single sign-off session covering this document is the recommended workflow.
