# Visibility Model

Every piece of content in BunkLogs has an author, an intended audience, and optionally a sensitivity flag that narrows the audience. The author always sees their own content. The audience is role-based and configured per content type. Sensitivity, where supported, gates within the audience.

## Core principle

The visibility model is enforced **server-side at the data-fetch layer**, not client-side at render time. A role's API request returns only the content that role can see. Client-side filtering of a fully-populated payload is not acceptable: devtools-level access would leak content the role shouldn't have.

## Visibility table

| Content type | Author role | Default audience | Sensitive variant audience |
|---|---|---|---|
| Camper reflection | Counselor (any on bunk) | Counselors on bunk, UH, Camper Care (if in caseload), Leadership Team, Admin | n/a |
| Counselor self-reflection | Counselor | Counselor, UH, Leadership Team, Admin | n/a |
| Unit Head self-reflection | UH | UH, Leadership Team, Admin (UH-to-UH not visible to peers in Tier 1) | n/a |
| Camper Care note | Camper Care | Camper Care, Leadership Team, Admin | Camper Care, Health Center, Special Diets, Admin |
| Specialist note | Specialist | Counselor, UH, Camper Care, Leadership Team, Admin | Camper Care, Health Center, Special Diets, Admin |
| Specialist self-reflection | Specialist | Specialist (self), Leadership Team, Admin | n/a |
| Maintenance ticket note | Maintenance Staff | Maintenance team, Admin (team-only) OR Maintenance team + submitter + UH + LT + Admin (submitter-visible) | n/a |
| Kitchen Staff reflection | Kitchen Staff | Leadership Team (kitchen supervisor), Admin | n/a |
| Leadership Team self-reflection | LT | LT (peers), Admin | Admin only (when "Private" toggled) |
| Madrich reflection | Madrich | Director, TBE Admin | n/a |
| Admin self-reflection | Admin | Admin peers, platform support | Admin only (when "Private" toggled) |

## Three operational principles

These govern the UI everywhere the visibility model surfaces:

1. **The author always sees their own original content.** No role ever sees their own writing translated, paraphrased, or summarized back to them.

2. **The audience is always disclosed at write-time.** Every form for content that has a non-trivial audience displays the audience list before submission. The disclosure updates dynamically when the user toggles sensitivity, language, or other audience-affecting fields.

3. **Sensitive content's existence is acknowledged to non-audience viewers, but never the content itself.** A reader who cannot read a sensitive note sees a placeholder line: *"1 sensitive note (Camper Care)"*. They know it exists and who to ask about it. Silent invisibility erodes trust if it's later discovered.

## The `AudienceDisclosure` component

A shared frontend component implements the disclosure pattern. Inputs:

- `audience` — array of role labels appropriate to the current content type and any active modifiers (sensitivity, language)
- `contextHint` — optional short text providing context (e.g., "auto-translated from Spanish will be available")

Used by: Specialist note form (Story 26), Camper Care note form (Story 21), Maintenance team-or-submitter note form (Story 33), Kitchen Staff reflection form (Story 40), Madrich reflection form (Story 64), every other content form where audience is non-obvious.

## The sensitive-note placeholder pattern

When a reader's role lacks visibility to one or more sensitive notes attached to a subject (camper profile, etc.), the UI displays a count-only placeholder. The placeholder:

- States the count and the gating role: *"1 sensitive note (Camper Care)"*
- Does not link to or expand to anything
- Does not show authorship or timestamps
- Renders in the section where the note would otherwise appear, in-flow with non-sensitive content

## Admin's broad-read privilege

Admin sees all content in their org, including sensitive notes. When Admin acts on content (edits, closes, resolves) that would normally be another role's authority, an **explicit Admin override** affordance with a required reason note is required. The action is audit-logged as "Edited as Admin" per the audit trail spec.

## Out of scope for Tier 1

- Per-user content sharing (e.g., a Specialist sharing their note privately with another Specialist)
- Time-limited visibility (e.g., a Camper Care note visible to UH for 7 days then auto-restricted)
- Audience modification post-submission (a sensitive note cannot be "un-sensitived" later; a follow-up note handles corrections)
