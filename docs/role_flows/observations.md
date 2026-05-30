# Observations — Converged Note System

**Step 7_23** | Supersedes: SubjectNote, core.Note (camper_care/specialist), notes.Note

## Overview

An **Observation** is the single converged entity for staff observations about
people. It collapses three previously-overlapping note concepts into one model
that is subject-anchored (one or more subjects), peer-taggable, threaded,
audience-captured for alerting, immutable-with-amendments, and access-controlled
by the supervisory hierarchy layered with an org-configurable sensitivity gate.

It lives in the `notes` app (`bunk_logs/notes/models.py`) alongside the legacy
notes-platform models it absorbs.

## Models

| Model | Role |
|---|---|
| `Observation` | Root record: org/program, author, body, sensitivity, context, language, amendment chain, source cross-ref. |
| `ObservationSubject` | Through table for the `subjects` M2M — the Persons an observation is about (≥1). |
| `ObservationRecipient` | Write-time captured recipients (keeps `option_key`); drives the inbox + tagged-recipient read leg. |
| `ObservationReply` | Threaded replies; no edit after creation. |
| `ObservationReadReceipt` | Per-person last-read watermark; drives the unread badge. |
| `ObservationArchive` | Per-user archive (through model for `archived_by`). |

`Observation` is org-scoped via `OrgScopedManager` (`objects`) with an
`all_objects` bypass for migrations/admin, exactly like the models it replaces.

## Read access model (permission layer, PR2)

```
readable = ( viewer is the author )
  OR ( viewer is an explicitly tagged recipient )
  OR ( viewer's role hierarchy covers ANY tagged subject )
INTERSECTED WITH ( viewer's capability clears Observation.sensitivity, per the org map )
```

The hierarchy leg reuses `subject_note_read.subject_note_read_q` /
`visibility.author_group_ids_with_descendants`; multi-subject means the read `Q`
ORs across the `subjects` M2M ("covers ANY tagged subject"). Author access never
expires (even after a role change). Cross-unit observations are allowed; a
sensitive one is still gated to sensitivity-cleared roles regardless of unit.

## Sensitivity gate

`Observation.sensitivity` is a small ordered enum mapped 1:1 from the legacy
SubjectNote visibility tiers:

| Sensitivity | Was (SubjectNote.visibility) |
|---|---|
| `normal` | `team` |
| `sensitive` | `supervisors_only` |
| `domain` | `domain_only` |
| `confidential` | `admin_only` |

The org map `Organization.settings["observations"]["view_by_capability"]`
(capability → set of viewable tiers) overlays a code default that mirrors
today's `NOTE_VIS_BY_CAP`, so behavior is unchanged until an org overrides it
(implemented in PR2):

| Capability | Tiers |
|---|---|
| `admin` | normal, sensitive, domain, confidential |
| `program_lead` | normal, sensitive, domain |
| `domain_specialist` | normal, sensitive, domain |
| `supervisor` | normal, sensitive |
| `participant` | (none) |

**Authoring-time gate:** when composing, the recipient candidate list is
filtered to people whose capability clears the selected sensitivity tier; the
POST endpoint re-validates server-side and rejects (400) any recipient who does
not clear the tier. Because of this gate, the tagged-recipient read leg can
never bypass sensitivity.

## Migration provenance (`migrate_observations`)

`python manage.py migrate_observations` (dry run by default; `--apply` to write)
converges the legacy sources. Each migrated Observation stores a provenance key
in `legacy_source` (`<app>.<model>:<pk>`), enforced by a partial unique
constraint, making the command idempotent.

| Source | Rule |
|---|---|
| `core.SubjectNote` (all) | 1:1 → Observation. `subject` → one `ObservationSubject`. `visibility` → `sensitivity` (table above). `is_sensitive=True` clamps to ≥ `sensitive`. Amendment chains preserved. No recipients. |
| `core.Note` (`camper_care`/`specialist`) | → Observation. `subject` → `ObservationSubject`. `note_type` → `context`. Sensitivity: camper_care `medical`/`family` → `domain`; else `sensitive` if `is_sensitive` else `normal`. No stored audience rows exist (computed at read time), so recipients are empty. `language` carried. |
| `notes.Note` WITH `camper_reference` | → Observation. `camper_reference` → `ObservationSubject`. `NoteAudienceCapture`/`NoteReply`/`NoteReadReceipt`/`NoteArchive` → Observation analogs. The thread `subject` title is **prepended to the body**. `sensitivity=normal`. `source_content_type`/`source_object_id` carried. |
| `notes.Note` WITHOUT `camper_reference` | **Exported** to `observations_retired_peer_notes.json`, **not migrated** (pure peer-to-peer notes are retired). |

**Left alone:** `core.Note` (`maintenance`), Camper Care Orders, Maintenance
Tickets, all Reflections — these are not observations.

Legacy tables are **not dropped** in this step; that happens in a later cleanup
prompt after a stable window.
