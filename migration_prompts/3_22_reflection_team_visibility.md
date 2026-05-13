# Prompt 3.22 — Reflection.team_visibility (peer / supervisor split)

**Wave:** 3 (Crane Lake Summer 2026 Build) — Specialist private-notes flow
**Estimated time:** 4-5 hours
**Prerequisite:** Prompt 3.21 complete (Camper Care now on `supervisor` capability and the visibility module knows about unit-scoped supervisors).

**Use the context prompt at the top of `0_0_context_prompt.md` before this session.**

---

```
Add a per-reflection visibility toggle that lets an author keep a single reflection out of the peer feed while still surfacing it to supervisors. The driving use case: a domain specialist (counselor, kitchen lead, wellness aide) wants to log a sensitive observation about a camper that should reach the Unit Head and Camper Care lead, but NOT the rest of the bunk's counseling team. Today the visibility module gives peer authors of the same AssignmentGroup full read access to each other's reflections (path 4 in ``reflections_visible_to``); this prompt adds a clean opt-out without forking the data model.

CONTEXT:
Two visibility paths currently grant cross-author access:

- Path 4 (``_author_group_ids_with_descendants``) treats "direct author of the reflection's group" and "author of an ancestor group" as one set. We want to keep ancestor access (that's the supervisor pipe — unit head -> bunk; division head -> unit) and gate ONLY the direct-peer access on a new flag.
- Path 6 (``_wellness_q``) gives Health Center / Special Diets a cross-program shortcut to every wellness-umbrella template. A private reflection should ALSO opt out of this path; the author's intent is "supervisors only", not "any wellness specialist in the org".

Subject visibility (path 3) is intentionally NOT gated — if ``template.subject_visible=True``, the camper sees reflections about themselves regardless of who they're hidden from. Author and admin paths are also unchanged.

Tasks:

1. Add ``Reflection.team_visibility`` in ``backend/bunk_logs/core/models.py``:

       class TeamVisibility(models.TextChoices):
           TEAM = "team", "Visible to team"
           SUPERVISORS_ONLY = "supervisors_only", "Supervisors only"

       team_visibility = models.CharField(
           max_length=24,
           choices=TeamVisibility.choices,
           default=TeamVisibility.TEAM,
           db_index=True,
           help_text=(
               "Who else (besides author + admin + supervisors via ancestor groups "
               "or unit scope) can read this reflection. Default 'team' keeps peer "
               "authors in the loop; 'supervisors_only' hides it from same-group "
               "peers and from the wellness-template shortcut."
           ),
       )

   Migration: forward-only with ``default="team"`` so all existing rows get the inclusive default. The new index is fine to add inline since `Reflection` is small relative to a production camp (low thousands of rows per program).

2. Refactor ``backend/bunk_logs/core/permissions/visibility.py``:

   - Keep ``_author_group_ids_with_descendants(person)`` and the public ``author_group_ids_with_descendants`` alias unchanged (dashboards use it as a structural "groups in scope" primitive, not a row-level visibility gate).
   - Add a sibling helper ``_author_group_ids_split(person) -> tuple[set[int], set[int]]`` that returns ``(direct_ids, descendant_only_ids)`` where ``descendant_only_ids = author_group_ids_with_descendants(person) - direct_ids``. Same BFS over the parent map; just track the split.
   - In ``reflections_visible_to``, replace the single path 4 line with:

         direct_ids, descendant_ids = _author_group_ids_split(person)
         if direct_ids:
             parts.append(Q(
                 assignment_group_id__in=direct_ids,
                 team_visibility=Reflection.TeamVisibility.TEAM,
             ))
         if descendant_ids:
             parts.append(Q(assignment_group_id__in=descendant_ids))

   - In ``_wellness_q``, gate the wellness shortcut on team_visibility too:

         return Q(
             template__role__in=WELLNESS_TEMPLATE_ROLES,
             team_visibility=Reflection.TeamVisibility.TEAM,
         )

   - Update the docstring on ``reflections_visible_to`` so path 4 reads "Author in an ANCESTOR of the reflection's AssignmentGroup OR direct author of the group when ``team_visibility='team'``." and path 6 mentions the team_visibility gate. Path 5 (unit-scoped supervisor) and the admin / author / subject paths are unchanged.

3. Expose ``team_visibility`` on ``ReflectionSerializer`` (``backend/bunk_logs/api/reflections.py``):

   - Add to ``fields = [...]`` between ``language`` and ``submitted_at``.
   - Default behavior: writable on create + update. The existing ``has_object_permission`` already restricts mutation to author + subject, and the existing ``update()`` flow blocks edits after ``is_complete=True``, which is the right contract for the privacy flag too -- changing privacy on a completed log requires an admin to mark it incomplete first.
   - No new permission class is needed: the author is the only non-admin who can set this on create, and existing object-permission rules keep peers from PATCHing.

4. Backend tests:

   - ``backend/bunk_logs/core/permissions/test_visibility.py``: new ``TestPrivateReflection`` class with these cases (use the existing fixture helpers):
     a. ``test_peer_author_cannot_see_supervisors_only`` -- two counselors authoring in the same bunk; peer cannot see a reflection where ``team_visibility="supervisors_only"`` but CAN see the same reflection's twin in ``team_visibility="team"``.
     b. ``test_ancestor_author_sees_supervisors_only`` -- unit_head author of the parent unit sees both private and team reflections in a child bunk (their supervisor path is path 4-descendant, which is unchanged).
     c. ``test_unit_scoped_supervisor_sees_supervisors_only`` -- camper_care with ``assigned_unit_slugs=["pioneers"]`` sees a private reflection about a subject whose Membership.metadata.unit_slug="pioneers" (path 5 is unchanged).
     d. ``test_admin_sees_supervisors_only`` -- org admin sees every private reflection.
     e. ``test_subject_visible_overrides_supervisors_only`` -- if ``template.subject_visible=True`` and the reflection is about the user, they see it regardless of team_visibility.
     f. ``test_author_sees_own_supervisors_only`` -- author always sees their own (path 2 unchanged).
     g. ``test_wellness_viewer_does_not_see_private_camper_care_reflection`` -- nurse (health_center membership) sees a team-visibility camper-care reflection but NOT the same reflection marked supervisors_only. Pins the path 6 gate added above.
     h. ``test_query_count_unchanged`` -- extend the existing ``TestQueryCount`` regression so the descendant resolution still issues ``< 12`` queries with the new field referenced in the Q.

   - ``backend/bunk_logs/api/tests/test_reflection_api.py``: one test ``test_team_visibility_round_trip`` -- POST a reflection with ``team_visibility="supervisors_only"``, assert the GET payload returns the flag verbatim. One test ``test_team_visibility_defaults_to_team`` -- POST without the field, assert the persisted row has ``team_visibility="team"``.

5. Frontend (``frontend/src/pages/ReflectionFormPage.jsx``):

   - Add state ``teamVisibility`` defaulting to ``"team"``.
   - Render a compact radio / two-button toggle between the period inputs and the dynamic fields:
       Visible to:  [ My team ]  [ Supervisors only ]
     Match the language-toggle styling already in the header so the new control feels like a sibling of the existing affordances. Add a one-line helper text under the toggle when "Supervisors only" is active: "Hidden from peer authors. Unit Heads, Camper Care, and admins can still see this entry."
   - Include ``team_visibility: teamVisibility`` in the POST payload.
   - Persist the choice in the localStorage draft alongside ``answers`` (extend ``saveReflectionDraft`` / ``loadReflectionDraft`` -- the storage helper already stores arbitrary keys, just add ``teamVisibility`` to the draft object and restore it on mount).

6. Frontend tests (``frontend/src/pages/ReflectionFormPage.test.jsx``):

   - ``"defaults team_visibility to team in the submit payload"``: render the form, fill required fields, click submit, assert the ``postMock`` call had ``team_visibility: 'team'``.
   - ``"sends team_visibility=supervisors_only when toggled"``: same flow but click the Supervisors-only button first.
   - ``"renders the supervisors-only helper text when selected"``: visible only after the toggle.

7. Documentation:

   - Add a short subsection to ``docs/membership-role-vs-capability.md`` titled "Per-reflection visibility (team_visibility)" linking the model field, the visibility-module gating, and the form toggle. Call out the explicit non-changes: subject access, author access, admin access, and the unit-scoped supervisor path are all unaffected.

Acceptance criteria:
- A peer counselor cannot read a same-bunk reflection marked supervisors_only; the unit head, camper_care, and admin still can.
- A nurse (``role=health_center``) still sees team-visibility wellness reflections via the wellness shortcut but no longer sees supervisors_only wellness reflections.
- The subject of a reflection (with ``subject_visible=True``) still sees their own data even when marked supervisors_only.
- ``ReflectionSerializer`` round-trips the field; default is ``team`` when omitted.
- The reflection form ships with a default-team toggle and round-trips the user's choice to the server; the localStorage draft remembers the choice mid-edit.
- ``make test-backend`` and ``make test-frontend`` both green; ``TestQueryCount`` budget unchanged.

Out of scope:
- A template-level ``supports_privacy`` flag that hides the toggle for templates where the choice is meaningless (self-reflection templates etc.). The toggle is universal in this PR; a follow-up can gate the UI.
- Surfacing the privacy chip on the reflection list / detail pages so a supervisor can see "this entry was filed privately". That's UX polish, not a correctness requirement; comes after the data model lands.
- Audit logging of privacy-flag changes. The existing ``submitted_by`` / ``updated_at`` columns are enough for the v1 review trail.

Commit structure (single PR, ordered commits):
  1. feat(3_22_reflection_team_visibility): add Reflection.team_visibility field + migration
  2. refactor(3_22_reflection_team_visibility): split peer vs descendant author paths in reflections_visible_to + gate wellness shortcut
  3. test(3_22_reflection_team_visibility): TestPrivateReflection coverage + serializer round-trip
  4. feat(3_22_reflection_team_visibility): reflection-form privacy toggle + draft persistence
  5. docs(3_22_reflection_team_visibility): document the per-reflection visibility contract
```
