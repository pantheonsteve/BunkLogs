# Story 8: Submit a maintenance request with optional urgency and photo

**As a Counselor, I want to submit a maintenance request with a photo and an urgency level so the maintenance team can triage and arrive prepared.**

## Acceptance criteria

1. The maintenance request form captures:
   1. **Location** — required, defaults to the user's bunk; editable to other camp locations
   2. **Category** — required, from a fixed enum: *Clogged plumbing*, *Broken light*, *Pest / Insect*, *Leak*, *Other*
   3. **Description** — required free text
   4. **Photo** — optional, with both "Take photo" (camera) and "Choose photo" (library) options
   5. **Urgency** — required, from a fixed enum: *Low*, *Normal*, *Urgent*
2. Selecting **Urgent** requires a reason (free text, separate field, becomes required when urgency is Urgent).
3. The form's photo capture uses the device's native camera/library, not a web file picker.
4. Submission is network-tolerant per Story 7 criterion 6.
5. Submitted requests appear in the dashboard's "Requests" section alongside camper-care requests, in one combined list, with type visually distinguishable.
6. The user can view their submitted request including its photo (full-size on tap), the maintenance team's status changes, and any notes maintenance has left for the requester (per Maintenance Story 33's visibility rules).
7. The user cannot edit a maintenance request's original fields after submission, but can add follow-up photos or comments (per C5).

## Decisions

- C5: Counselors can add follow-up photos/comments to their own open tickets.
