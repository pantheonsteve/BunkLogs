# Step 7_3: Supervision Relationship Primitive

**Goal:** Implement the Supervision model that handles UH-Counselor, Camper Care-Caseload, LT-Team, and Director-Madrich supervision patterns.

**Canonical product spec:** `docs/user_stories/00_cross_cutting/supervision_relationship.md`

**Scope of this step:**

1. Backend: implement `core.Supervision` model per spec data model section. Fields: supervisor_membership FK, target_type enum (MEMBERSHIP/ROLE_IN_PROGRAM/BUNK), target_membership FK nullable, target_role CharField nullable, target_program FK nullable, target_bunk FK nullable, start_date, end_date nullable, computed `is_active`.
2. Backend: model-level validators per spec validation section: supervisor must hold appropriate Membership; target must exist at creation; start <= end.
3. Backend: query helpers as model managers/QuerySet methods:
   1. `Supervision.objects.bunks_for_uh(uh_membership)` → transitive: UH → Counselors → Bunks
   2. `Supervision.objects.caseload_campers(camper_care_membership)` → caseload Bunks → Campers
   3. `Supervision.objects.team_members(lt_membership, target_role)` → role-in-program scope
   4. `Supervision.objects.co_supervisors(target)` → matching supervisors on shared target
4. Backend: API endpoints for Admin (will be polished in Step 7_13):
   1. `GET /api/v1/supervisions/?supervisor_membership_id=<id>` — list a supervisor's relationships
   2. `POST /api/v1/supervisions/` — create
   3. `PATCH /api/v1/supervisions/<id>/` — modify (end-date only after creation per spec)
   4. `DELETE` not implemented; soft-end via end_date.
5. Backend: data migration. For each existing Counselor-Bunk assignment, JC-Bunk, GC-Bunk on the old model, do NOT create Supervision records (those are direct assignments, not supervisor-supervisee). Only create Supervision records when explicitly configured by Admin in Step 7_13's Assignments surface.
6. Backend: audit trail integration per Step 7_4. Supervision creation, modification, end-dating write audit events.
7. Frontend: implement `useSupervision` hook at `frontend/src/hooks/useSupervision.js` providing query results scoped to the requesting user's Memberships.
8. Frontend: no UI in this step — Assignments surface lands in Admin flow Step 7_13. This step is backend primitive only.
9. Tests:
   1. Backend: model tests for each supervision pattern.
   2. Backend: query helper tests with realistic scenarios.
   3. Backend: API tests including isolation (a UH cannot create their own Supervision; only Admin can).
   4. Backend: validator tests for invalid combinations.
10. Documentation: `bunk_logs/core/SUPERVISION.md` with the four supervision patterns documented.

**Out of scope:**

- The Admin Assignments UI (Step 7_13).
- Caseload-specific UI (Camper Care flow Step 7_8 reads from Supervision via query helpers but doesn't configure).

**Commit scope: `feat(7_3_supervision_relationship): ...`. PR title prefix: `7_3`.**
