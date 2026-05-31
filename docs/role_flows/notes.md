# Notes Platform — Role Flows

> **DEPRECATED (Step 7_23).** The notes platform has been converged into the
> single **Observations** system. Notes about a person (`camper_reference`) are
> migrated to Observations; pure peer-to-peer notes are retired. See
> [`observations.md`](observations.md). The endpoints below remain as shims
> until legacy callers are migrated and a later cleanup prompt removes them.

**Step 7_19** | Affects: Counselor, Unit Head

## Overview

The Notes platform is a cross-role communication primitive. Unlike Reflections (camper-scoped, template-driven), a Note is a direct message between staff members, optionally cross-referencing a camper concern or specialist observation.

## Counselor flows

### Compose a note

1. Click **Notes** in the sidebar → **Compose** button.
2. Select at least one audience option from the picker (e.g. "My Unit Head", "Co-counselors on this bunk").
3. Fill in subject and body. The draft is auto-saved every 30 seconds and on blur.
4. Click **Send Note**.

**Audience options available to a Counselor:**

| Option key | Description |
|---|---|
| `my_unit_head` | The UH who supervises this counselor |
| `co_counselors_on_bunk` | Co-counselors assigned to the same bunk |
| `specific_counselor` | Any single counselor in the same program (requires person picker) |

### Inbox / Sent / Archive

- **Inbox** — notes where the counselor appears in the audience capture. Sorted newest-first. Unread notes are highlighted.
- **Sent** — notes the counselor authored.
- **Archive** — notes the counselor has archived (soft-hide).

The sidebar badge shows the count of unread inbox notes; it polls every 60 seconds.

### Reply

Open a thread (`/notes/:noteId`), type in the reply box, and click **Reply**. All thread participants can see all replies.

### Archive a note

From the thread view, click **Archive**. The note moves to the Archive tab for the archiving user only (not global).

### Cross-reference path: from a Bunk concern

From a camper's subject dashboard → **Concerns** section → "Open as Note". This POSTs to `/api/v1/notes/from-bunk-concern/` and returns a pre-filled draft. The NoteComposer opens with subject, body excerpt, and audience pre-filled from the concern data.

The source reference badge on the composed note is **non-transitive**: the recipient sees that the note references a concern but cannot follow the link unless they already have access to that concern.

---

## Unit Head flows

### Compose a note

Same flow as Counselor. Additional audience options:

| Option key | Description |
|---|---|
| `all_counselors_in_unit` | All counselors the UH supervises (resolved via Supervision rows) |
| `specific_counselor` | A single counselor by name |

### Inbox / Sent / Archive

Same as Counselor. The UH can receive notes from counselors they supervise and can send to any counselor in their unit.

### Cross-reference path: from a Specialist note

From a specialist's note detail page → "Share with Unit Head". POSTs to `/api/v1/notes/from-specialist-note/`. Returns a draft pre-filled with the specialist's note summary. Same non-transitive access semantics apply.

---

## Read receipts

When a user opens a thread (`GET /api/v1/notes/:id/`) the backend automatically upserts a `NoteReadReceipt` record for them. This marks the note as read and decrements the sidebar unread count.

---

## Security / tenancy invariants

- All notes are scoped to `(organization, program)`. A user cannot see notes from another org or program, even if they have the same email.
- `viewer_or_403` enforces: the requesting user must have an active v1-enabled `Membership` in the same program as the note.
- Only thread participants (author + audience capture members) can see a thread; UHs do not automatically see counselors' notes just because they supervise them — only notes where they are an explicit audience member.
- Audience resolution happens at send time and is captured immutably in `NoteAudienceCapture`. If supervision relationships change later, existing notes are unaffected.

---

## API reference (summary)

| Method | URL | Purpose |
|---|---|---|
| `GET` | `/api/v1/notes/inbox/` | Paginated inbox |
| `GET` | `/api/v1/notes/sent/` | Paginated sent |
| `GET` | `/api/v1/notes/archive/` | Paginated archive |
| `GET` | `/api/v1/notes/unread-count/` | `{"count": N}` for sidebar badge |
| `GET` | `/api/v1/notes/audience-options/` | Available options for current user's role |
| `POST` | `/api/v1/notes/` | Create note (resolves audience server-side) |
| `GET` | `/api/v1/notes/:id/` | Thread detail (marks read) |
| `POST` | `/api/v1/notes/:id/replies/` | Add reply |
| `POST` | `/api/v1/notes/:id/archive/` | Archive for current user |
| `DELETE` | `/api/v1/notes/:id/archive/` | Unarchive for current user |
| `POST` | `/api/v1/notes/from-bunk-concern/` | Cross-reference draft from concern |
| `POST` | `/api/v1/notes/from-specialist-note/` | Cross-reference draft from specialist note |
