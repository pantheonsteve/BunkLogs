# Supervision Relationship

The same primitive governs four supervision patterns:

- **UH → Counselor** (Story 10) — Unit Head supervises Counselors; bunks surface transitively via the Counselors assigned to them
- **Camper Care → Caseload** (Story 18) — Camper Care staff member's caseload of bunks (which transitively defines covered campers)
- **Leadership Team → Team** (Story 45) — Leadership Team member supervises a team-by-role (Kitchen Staff, Specialists, Housekeeping, etc.)
- **Director → Madrich cohort** (Story 64) — TBE Director supervises Madrichim; the same primitive as LT-Team applied to the religious school program type

## Data model

A single `Supervision` model with fields:

- `supervisor_membership` (FK to Membership) — the supervising role's Membership
- `target_type` (enum: `MEMBERSHIP`, `ROLE_IN_PROGRAM`, `BUNK`) — what's being supervised
- `target_membership` (FK to Membership, nullable) — for direct supervisor-supervisee
- `target_role` (CharField, nullable) — for "all kitchen_staff in this program"
- `target_program` (FK to Program, nullable) — scoping the role
- `target_bunk` (FK to Bunk, nullable) — for Camper Care caseload entries
- `start_date` (DateField, required)
- `end_date` (DateField, nullable) — open-ended assignment
- `is_active` (computed: start_date <= today and (end_date is null or end_date >= today))

## Application examples

**UH supervises Counselor Sarah:**
```
supervisor_membership: UH (Alice's UH Membership)
target_type: MEMBERSHIP
target_membership: Counselor (Sarah's Counselor Membership)
```

**Camper Care caseload: Alice covers Bunks 12, 13, 14:**
```
3 Supervision records, one per bunk:
  supervisor_membership: Camper Care (Alice)
  target_type: BUNK
  target_bunk: Bunk 12 (or 13, or 14)
```

**LT supervises all kitchen staff:**
```
supervisor_membership: LT (Alyson)
target_type: ROLE_IN_PROGRAM
target_role: kitchen_staff
target_program: Summer 2026
```

**Director supervises all Madrichim:**
```
supervisor_membership: Director (Rachel)
target_type: ROLE_IN_PROGRAM
target_role: madrich
target_program: TBE Religious School 2026-27
```

## Co-supervision

Multiple supervisors per target is supported and is the common case. A team or person can have one primary and one or more backup supervisors. The Supervision model is many-to-many at the application level; the database is many one-to-many records sharing the same target.

## Validation

- A supervisor must hold an appropriate Membership for the supervision type (a Counselor cannot supervise a UH; an Admin can supervise anything).
- The target must exist as a Membership/role/bunk at the time the Supervision is created.
- Start date cannot be after end date.
- Backdated supervision is permitted but does not retroactively reattribute historical content (per Admin Story 56 decision 4).

## Query helpers

The primitive supports common queries:

- "Which bunks does this UH supervise?" → transitive: UH → Counselors → Bunks
- "Which campers are in this Camper Care person's caseload?" → caseload Bunks → Campers in those Bunks
- "Which kitchen staff does this LT supervise?" → role-in-program scope
- "Is this LT a co-supervisor of this team?" → matching supervisor on shared target

## Configured by Admin

All Supervision records are configured via the Admin Assignments surface (Story 56). UH and LT can apply existing tags to their teams but cannot create or modify Supervision records.

## Audit trail

Creation, modification, and end-dating of Supervision records writes audit events per the audit trail spec. Visible to Admin in the audit view.
