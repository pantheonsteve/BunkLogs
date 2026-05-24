# Notes Audience Matrices

Per-role audience options for the Note composer (Story 66). v1 only specifies Counselor and Unit Head (per decision N4). Other roles are stubbed as "TBD when role flow is revised" so future role flow design pulls them in deliberately rather than backing into them.

## How to read this document

For each author role, the table below shows the audience options they can select from in the composer. Audience selections resolve at write-time to specific Person records and are captured in the audit trail (per Story 66 criterion 9).

Options are presented in the composer's audience picker grouped by relationship type (supervisors, peers, downstream). The composer dedupes — if a single Person matches multiple options, they appear once in the resolved audience.

---

## Counselor

| Option | Resolves to | Notes |
|---|---|---|
| My Unit Head | The UH for the counselor's currently-active bunk Membership | One Person in single-bunk case; multiple in cross-bunk coverage |
| Administration | All Admins of the counselor's organization with active Membership | Org-scoped |
| Co-counselors on this bunk | Other counselors with active Membership on the same bunk | Excludes the author |
| Co-counselors on a specific bunk | Other counselors on a bunk the author is or was a member of | Edge case: counselor moved mid-summer wants to message former bunkmates |
| A specific person | Autocomplete from the union of all options above | For 1:1 messaging without exposing the whole bunk |

## Unit Head

| Option | Resolves to | Notes |
|---|---|---|
| A specific counselor I supervise | Autocomplete from Counselors on bunks in this UH's unit | The most common UH-initiated path; used for Story 69 cross-references |
| All counselors on a specific bunk | Counselors with active Membership on the named bunk | For bunk-level heads-up messages |
| All counselors in my unit | All Counselors on all bunks in this UH's unit | Unit-level announcements; use sparingly per the platform's "low noise" ethos |
| Peer Unit Heads | Other UHs in the same Program | Subject to UH6 in decisions.md (UH-to-UH peer reflection visibility is no, but Notes is a different surface; UH-to-UH messaging is fine because the author chose the audience) |
| Leadership Team | All LT members of the Program | For LT escalation |
| Administration | All Admins of the org | For org-level escalation |
| A specific person | Autocomplete from the union of all options above | For 1:1 messaging |

---

## Other roles — TBD

The following roles are not in v1 (per decision N4). Their audience matrices will be specified when their role flows are revised:

- **Specialist** (Stories 24–29) — TBD. Likely includes: Counselors of the bunk for a referenced camper, the camper's UH, Camper Care, peer Specialists.
- **Camper Care** (Stories 18–23) — TBD. Likely includes: Counselors on bunks in caseload, UHs of those bunks, peer Camper Care, Health Center, Special Diets, LT, Admin.
- **Maintenance** (Stories 30–34) — TBD. Likely includes: peer Maintenance, original ticket submitters (when relevant), Admin.
- **Kitchen Staff** (Stories 35–40) — TBD. Likely includes: peer Kitchen, Kitchen supervisor (LT), Admin. May require Spanish/English handling per KS3.
- **Leadership Team** (Stories 45–53) — TBD. Likely includes: assigned UHs, peer LT, Admin, downward to any role they supervise via Supervision records.
- **Admin** (Stories 54–60) — TBD. Likely includes: any Person in the org. The broad-read privilege from the visibility model extends to broad-write for Notes.
- **Madrich** (Stories 61–65) — TBD. Likely includes: Director (TBE), Faculty. TBE Tier 1 may not include Notes at all; defer until TBE post-launch.

When a role is wired in, the audience matrix here is updated and the migration prompt that wires the role lands in `migration_prompts/`.

## Cross-cutting rules

These apply regardless of author role:

1. **Self-exclusion.** The composer always removes the author from the resolved audience. If an option's resolution would include the author (e.g., "Peer Unit Heads" for a UH), the author is excluded from the resolved list.
2. **Active Membership only.** Audience resolution considers only Persons with active Memberships matching the option's criteria at compose time. Persons whose Membership is end-dated before today are excluded.
3. **Org-scoping.** Audience resolution is always scoped to the author's organization. Cross-org Notes are not supported in any tier.
4. **Capture, don't dynamic-resolve.** The audience is captured at write-time (Story 66 criterion 9). If a counselor sends a note "to all counselors on Bunk Maple" and a new counselor is added to Bunk Maple tomorrow, the new counselor does NOT retroactively see the note. They are not in the captured audience. New conversations to them require a new note.
5. **Multi-program authors.** A Person with active Memberships in multiple Programs sees audience options scoped to whichever Program they're currently operating in (per the platform's existing Program-context model from migration prompts 2.x).

## Decisions

- N3 (`../00_cross_cutting/decisions.md`): Platform-primitive scope.
- N4: v1 limited to Counselor and Unit Head.
- UH6: UH-to-UH peer reflection not visible, but Notes audience is author-chosen, so UH-to-UH messaging is permitted.
