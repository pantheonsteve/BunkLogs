# Story 7: Submit a camper-care request

**As a Counselor, I want to request items from camper care so a camper gets what they need without me leaving the bunk.**

## Acceptance criteria

1. The dashboard's "Requests" section provides a clear entry point to submit a new request, with **Camper Care** and **Maintenance** as distinct paths.
2. The camper-care request form captures:
   1. **Camper** — required, dropdown of the user's bunk roster
   2. **Item** — required, autocomplete from a server-maintained list of common items (toothbrush, deodorant, sunscreen, etc.) with a free-text fallback labeled "Other"
   3. **Note** — optional free text
3. Submitted requests appear in the dashboard's "Requests" section with: type, camper, item, status (**Submitted** / **In Progress** / **Fulfilled** / **Unable to Fulfill**), and submission time.
4. The user sees their own requests AND co-counselors' requests on the same bunk (per C4). Co-counselor requests show the originating counselor's name on the row.
5. Tapping a request opens its detail view, including any status-change history and notes added by Camper Care staff per the visibility rules in `../00_cross_cutting/visibility_model.md`.
6. Network-tolerant submission: if connectivity drops mid-submission, the request queues locally and submits when reconnected, with a visible "pending" state on the row.

## Decisions

- C4: Co-counselors see each other's open camper-care requests with submitter name attached.
- C6: Admin maintains the curated item list per program (Story 58).
