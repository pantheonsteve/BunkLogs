# Step 7_16: Cross-cutting Audit Review Pass

**Goal:** End-to-end QA on visibility model enforcement, edit windows, audit trail completeness, and Supervision query consistency across all role flows.

**Depends on:** Steps 7_1 through 7_15.

**Scope of this step:**

1. Backend: visibility audit. Write a test matrix covering every (content type × reader role × sensitivity flag) combination from the visibility table in `docs/user_stories/00_cross_cutting/visibility_model.md`. Run against all API endpoints. Fix any gaps.
2. Backend: edit window audit. Write tests for every edit-able content type confirming:
   1. Edit is permitted within the window
   2. Edit is rejected after the window with clear error
   3. Edit history is preserved
   4. Edit-history visibility matches the spec (Counselors don't see prior versions of co-counselor reflections; supervisors do)
3. Backend: audit trail completeness audit. For every API endpoint that modifies content or relationships, verify that an audit event is written with the correct event_type, actor, before/after states, and reason note when required.
4. Backend: Supervision query consistency. For every role's dashboard/data endpoint, verify the query uses the appropriate `Supervision.objects.*` helper rather than ad-hoc filtering. Refactor any ad-hoc queries to use the helpers.
5. Backend: cross-org isolation. Write tests confirming a user in Org A cannot access any content from Org B via any endpoint, regardless of URL manipulation, parameter injection, or other paths.
6. Backend: rate limiting on Anthropic API calls. Verify the translation pipeline cannot exceed configured limits under realistic load.
7. Frontend: empty states and error states audit. For every role's dashboards and workspaces, verify the empty state is meaningful (not an empty container) and the error states are clear (not silent failures).
8. Frontend: AudienceDisclosure presence audit. Confirm AudienceDisclosure is rendered on every form where audience is non-obvious (Specialist note, Camper Care note, Maintenance team-or-submitter note, Kitchen Staff reflection, Madrich reflection).
9. Frontend: SensitiveNotePlaceholder presence audit. Confirm the placeholder is rendered on every reader view of a camper profile where sensitive notes exist but the reader can't access them.
10. Documentation: produce `docs/audit_review_findings.md` documenting any gaps found and their resolutions.

**Commit scope: `chore(7_16_audit_review_pass): ...`. PR title prefix: `7_16`.**
