# Supervision Relationship

> Implementation reference for Step 7_3. Canonical product spec:
> [`docs/user_stories/00_cross_cutting/supervision_relationship.md`](../../../docs/user_stories/00_cross_cutting/supervision_relationship.md).

A single `core.Supervision` model governs the four supervision patterns
BunkLogs needs. Encoding them once keeps the audit and visibility story
uniform across summer camp (UH / Camper Care / LT) and the religious-school
program type (TBE Director / Madrich cohort).

## The four patterns

| # | Pattern | `target_type` | Fields populated |
|---|---|---|---|
| 1 | **UH → Counselor** (Story 10) | `MEMBERSHIP` | `target_membership` |
| 2 | **Camper Care → Caseload Bunk** (Story 18) | `BUNK` | `target_bunk` (AssignmentGroup, group_type=`bunk`) |
| 3 | **LT → team-by-role** (Story 45) | `ROLE_IN_PROGRAM` | `target_role` + `target_program` |
| 4 | **Director → Madrich cohort** (Story 64) | `ROLE_IN_PROGRAM` | `target_role=madrich` + `target_program` (religious-school program) |

Co-supervision is the common case, not the exception: many supervisors can
share the same target, and we model this as multiple `Supervision` rows that
agree on the target side.

## Model: `core.Supervision`

| Field | Type | Notes |
|---|---|---|
| `supervisor_membership` | FK Membership | Must hold `supervisor`, `program_lead`, or `admin` capability. |
| `target_type` | enum (`membership` / `role_in_program` / `bunk`) | Drives which target field is required. |
| `target_membership` | FK Membership, nullable | Required when `target_type=membership`. |
| `target_role` | CharField, blank | Required (must be a `Membership.ROLES` value) when `target_type=role_in_program`. |
| `target_program` | FK Program, nullable | Required with `target_role`. |
| `target_bunk` | FK AssignmentGroup, nullable | Required when `target_type=bunk`. Must have `group_type='bunk'`. |
| `start_date` | DateField | Required. Backdated supervision is permitted but never reattributes history (Admin Story 56 dec. 4). |
| `end_date` | DateField, nullable | Open-ended supervision when null. `end_date >= start_date` enforced by a `CheckConstraint`. |
| `is_active(today=None)` | computed | True iff `start_date <= today and (end_date is null or end_date >= today)`. |

### Validators (`Supervision.clean()`)

- Supervisor capability check (see table above).
- Target fields must match `target_type`; cross-wiring (e.g. setting
  `target_bunk` on a `membership` target) raises `ValidationError`.
- `target_role` must be a real `Membership.ROLES` value.
- `end_date >= start_date`.
- Cross-tenant guard: every leg (target Membership / Program / Bunk) must
  share the supervisor's organization.

## Manager + QuerySet helpers

`Supervision.objects` is the org-scoped manager (scopes via
`supervisor_membership__program__organization`). Use `Supervision.all_objects`
for cross-tenant administrative reads, migrations, and tests.

The four documented helpers all live on `SupervisionQuerySet` and accept
`today=` for deterministic testing:

| Helper | Returns | Use case |
|---|---|---|
| `.active(today=None)` | Supervision QuerySet | Base filter for the other helpers. |
| `.bunks_for_uh(uh_membership, *, today=None)` | AssignmentGroup QuerySet | UH dashboard ("which bunks do I see?"). Walks UH → Counselor Membership → Counselor Person → authored bunk AssignmentGroup. Counselor→Bunk is **not** a Supervision row — it's an `AssignmentGroupMembership(role_in_group='author')`. |
| `.caseload_campers(camper_care_membership, *, today=None)` | Person QuerySet | Camper Care caseload view. Walks active BUNK supervisions → AssignmentGroupMembership(subject) → Person. |
| `.team_members(supervisor_membership, target_role=None, *, today=None)` | Membership QuerySet | LT / Director dashboards: "everyone in this role I supervise". Pass `target_role` to narrow when the supervisor has multiple role scopes. |
| `.co_supervisors(supervision, *, today=None)` | Supervision QuerySet | Find the other active supervisors of the same target. Excludes `supervision` itself. Accepts a model instance or a dict with the target fields. |

## HTTP API

All routes live under `/api/v1/`. Permission: `IsOrgAdminOrSuperuser`
(Super Admin via `is_staff` / `is_superuser`, or an active `admin`
Membership in the request org). UH, LT, and Camper Care **cannot** create
or modify Supervision rows -- they only read.

| Verb | Path | Body / Params | Returns |
|---|---|---|---|
| GET | `/supervisions/?supervisor_membership_id=<id>` | optional: `target_type`, `is_active=true\|false` | List of Supervisions in the requesting org |
| POST | `/supervisions/` | `{supervisor_membership, target_type, target_membership? | target_role+target_program? | target_bunk?, start_date, end_date?}` | 201 + serialized row |
| PATCH | `/supervisions/<id>/` | `{end_date}` (other fields rejected) | 200 + serialized row |
| DELETE | `/supervisions/<id>/` | — | 405 (soft-end via PATCH `end_date`) |

### Error contract

| HTTP | Cause | Body |
|---|---|---|
| 400 | Validator failure (capability, cross-wiring, cross-tenant, date) | `{<field>: "..."}` |
| 400 | PATCH includes a field other than `end_date` | `{<field>: "immutable after creation"}` |
| 400 | PATCH missing `end_date` | `{end_date: "PATCH must include end_date."}` |
| 403 | Not an org Admin / Super Admin, or no org context | DRF default |
| 405 | DELETE | `{detail: "Method 'DELETE' not allowed."}` |

## Audit trail integration

Every create / modify / end writes a `SupervisionEvent` row capturing the
actor + before/after snapshot. This is a forward-compatible stand-in for the
cross-cutting `AuditEvent` model landing in **Step 7_4**; the column shape
mirrors `AuditEvent` so the backfill is mechanical: copy rows over, point
new writes at the audit module, then drop this table.

Helper: `bunk_logs.core.models.record_supervision_event(...)`.

## Frontend

`frontend/src/hooks/useSupervision.js` is a thin wrapper around `GET
/api/v1/supervisions/`. Mutations are not exposed -- the Admin Assignments
surface (Step 7_13) wires create / PATCH separately.

```js
const { supervisions, isLoading, error, refetch } = useSupervision({
  supervisorMembershipId: 42,            // optional
  targetType: 'bunk',                     // optional
  isActive: true,                         // optional
});
```

`SUPERVISION_TARGET_TYPES` is exported for callers that need the enum
strings without hard-coding them.

## What this step does NOT do

- **No bulk-import migration.** Per Step 7_3 scope, we do **not** create
  Supervision records from existing Counselor-Bunk / JC-Bunk / GC-Bunk
  legacy assignments. Those are direct assignments (AssignmentGroupMembership
  with `role_in_group='author'`), not supervisor-supervisee relationships.
  Admin will configure real Supervision rows via the Assignments surface in
  Step 7_13.
- **No Admin UI.** Surface lives in Step 7_13.
- **No Caseload-specific UI.** Camper Care flow (Step 7_8) consumes
  `caseload_campers` via the query helper.

## Testing

- Unit + queryset tests: `backend/bunk_logs/core/test_supervision.py`
  cover every validator branch, the four query helpers (including the
  ended-supervision exclusion case), `is_active` boundary behaviour, and
  tenant isolation via the org-scoped manager.
- API tests: `backend/bunk_logs/api/tests/test_supervisions_api.py` cover
  Admin vs. UH authorization, the supervisor_membership_id filter, the
  end-date-only PATCH path (incl. event write), immutable-field PATCH
  rejection, missing-end_date PATCH rejection, DELETE 405, and tenant
  scoping.
- Frontend: `frontend/src/hooks/__tests__/useSupervision.test.jsx` covers
  the autoload path, filter parameter forwarding, manual refetch, and error
  surfacing.

Run via `make test-backend` and `make test-frontend`.
