# API Consolidation Plan

## Background

The codebase has two parallel API trees:

- **`/api/`** — registered via `config/api_router.py` (mounted at `path("api/", include("config.api_router"))`)
- **`/api/v1/`** — registered via `bunk_logs/api/urls.py` (mounted at `path("api/v1/", include("bunk_logs.api.urls"))`)

Both trees import from the same viewset classes in `bunk_logs/api/views.py`, so there is no functional divergence — only URL-level duplication and naming inconsistency (`bunk-logs` vs `bunklogs`, etc.).

Additional top-level endpoints outside both trees live directly in `config/urls.py` (auth, schema, CSRF, Google OAuth).

**Target state**: all data endpoints live under `/api/v1/`. The `/api/` router retains only endpoints with no `/api/v1/` counterpart until those are individually migrated.

---

## Inventory

### Authentication & Session

| Endpoint path under `/api/` | Endpoint path under `/api/v1/` | View / function | Methods | Frontend? | External? | Recommendation |
|---|---|---|---|---|---|---|
| `api/auth/token/` | — | `CustomTokenObtainPairView` | POST | Yes (`Signin.jsx`) | No | KEEP; move to `api/v1/auth/token/` in a future PR |
| `api/auth/token/refresh/` | — | `TokenRefreshView` | POST | Yes (`api.js`) | No | KEEP; move to `api/v1/auth/token/refresh/` in a future PR |
| `api/auth/token/verify/` | — | `TokenVerifyView` | POST | No | No | KEEP with refresh migration |
| `api/auth-token/` | — | `obtain_auth_token` (DRF session token) | POST | No | No | DELETE — superseded by JWT; not called anywhere in the frontend |
| `api/auth/google/` | — | `google_login` | GET | Yes (`GoogleLoginButton.jsx`) | No | KEEP at current path (OAuth redirect URI is registered) |
| `api/auth/google/callback/` | — | `google_callback` | GET | No (server-side callback) | No | KEEP at current path |
| `api/auth/google/callback/token/` | — | `google_login_callback` | GET | No (server-side) | No | KEEP at current path |
| `api/get-csrf-token/` | — | `get_csrf_token` | GET | Yes (`api.js`) | No | KEEP; rename to `api/v1/csrf-token/` in a future PR |

### Users

| Endpoint path under `/api/` | Endpoint path under `/api/v1/` | View / function | Methods | Frontend? | External? | Recommendation |
|---|---|---|---|---|---|---|
| `api/users/` | `api/v1/users/` | `/api/`: `UserViewSet` (users/api/views); `/api/v1/`: `UserDetailsView` (ReadOnly) | GET, POST | No (neither path hit directly) | No | `/api/` version is richer (staff-filtered list). MIGRATE: expose `UserViewSet` under `/api/v1/users/` and delete `/api/users/`. The `/api/v1/users/` currently maps to the wrong class (`UserDetailsView` returns current user only). |
| `api/users/{id}/` | `api/v1/users/{id}/` | Same divergence as above | GET | No | No | MIGRATE (same as above) |
| `api/users/me/` | — | `UserViewSet.me` | GET | No (uses email lookup instead) | No | MIGRATE to `api/v1/users/me/` |
| `api/users/details/` | — | `UserDetailsView.list` | GET | No (superseded by email lookup) | No | DELETE — redundant; callers use `/api/v1/users/email/{email}/` |
| `api/users/email/{email}/` | `api/v1/users/email/{email}/` | `get_user_by_email` | GET | Yes (`UserInfo.jsx`, `BunkGrid.jsx`, `AuthContext.jsx`) | No | KEEP `/api/v1/` version; DELETE `/api/` duplicate |
| — | `api/v1/users/create/` | `UserCreate` (registration) | POST | Yes (`Signup.jsx`) | No | KEEP under `/api/v1/` |
| — | `api/v1/users/{user_id}` | `get_user_by_id` (no trailing slash) | GET | No | No | DELETE — missing trailing slash, no frontend caller; functionality covered by `/api/v1/users/email/{email}/` and `UserViewSet` |

### Bunks

| Endpoint path under `/api/` | Endpoint path under `/api/v1/` | View / function | Methods | Frontend? | External? | Recommendation |
|---|---|---|---|---|---|---|
| `api/bunks/` | `api/v1/bunks/` | `BunkViewSet` (same class) | GET, POST | No | No | KEEP `/api/v1/` version; DELETE `/api/` duplicate |
| `api/bunks/{id}/` | `api/v1/bunks/{id}/` | `BunkViewSet` (same class) | GET, PUT, PATCH, DELETE | No | No | KEEP `/api/v1/` version; DELETE `/api/` duplicate |
| — | `api/v1/bunk/{id}/` | `BunkViewSet.retrieve` (non-standard path) | GET | Yes (`BunkCard.jsx` calls `/api/v1/bunk/${bunk_id}`) | No | KEEP temporarily (active frontend caller); add to `/api/v1/bunks/{id}/` eventually and update `BunkCard.jsx` to use standard path, then DELETE |

### Units

| Endpoint path under `/api/` | Endpoint path under `/api/v1/` | View / function | Methods | Frontend? | External? | Recommendation |
|---|---|---|---|---|---|---|
| `api/units/` | `api/v1/units/` | `UnitViewSet` (same class) | GET, POST | No | No | KEEP `/api/v1/` version; DELETE `/api/` duplicate |
| `api/units/{id}/` | `api/v1/units/{id}/` | `UnitViewSet` (same class) | GET, PUT, PATCH, DELETE | No | No | KEEP `/api/v1/` version; DELETE `/api/` duplicate |
| `api/units/{id}/assign_staff/` | — | `UnitViewSet.assign_staff` | POST | No | No | MIGRATE to `/api/v1/units/{id}/assign_staff/` |
| `api/units/{id}/remove_staff/` | — | `UnitViewSet.remove_staff` | DELETE | No | No | MIGRATE to `/api/v1/units/{id}/remove_staff/` |

### Unit Staff Assignments

| Endpoint path under `/api/` | Endpoint path under `/api/v1/` | View / function | Methods | Frontend? | External? | Recommendation |
|---|---|---|---|---|---|---|
| `api/unit-staff-assignments/` | `api/v1/unit-staff-assignments/` | `UnitStaffAssignmentViewSet` (same class) | GET, POST | No | No | KEEP `/api/v1/` version; DELETE `/api/` duplicate |
| `api/unit-staff-assignments/{id}/` | `api/v1/unit-staff-assignments/{id}/` | `UnitStaffAssignmentViewSet` (same class) | GET, PUT, PATCH, DELETE | Yes — `/api/v1/unit-staff-assignments/${userId}/` (`api.js`, `BunkDashboard.jsx`) | No | KEEP `/api/v1/` version; DELETE `/api/` duplicate |

### Campers

| Endpoint path under `/api/` | Endpoint path under `/api/v1/` | View / function | Methods | Frontend? | External? | Recommendation |
|---|---|---|---|---|---|---|
| `api/campers/` | `api/v1/campers/` | `CamperViewSet` (same class) | GET, POST | No | No | KEEP `/api/v1/` version; DELETE `/api/` duplicate |
| `api/campers/{id}/` | `api/v1/campers/{id}/` | `CamperViewSet` (same class) | GET, PUT, PATCH, DELETE | No | No | KEEP `/api/v1/` version; DELETE `/api/` duplicate |
| `api/campers/{camper_id}/logs/` | `api/v1/campers/{camper_id}/logs/` | `CamperBunkLogViewSet` (same class) | GET | Yes — `/api/v1/campers/${camper_id}/logs` (`CamperDashboard.jsx`, note: no trailing slash in call site) | No | KEEP `/api/v1/` version; DELETE `/api/` duplicate |

### Camper Bunk Assignments

| Endpoint path under `/api/` | Endpoint path under `/api/v1/` | View / function | Methods | Frontend? | External? | Recommendation |
|---|---|---|---|---|---|---|
| `api/camper-bunk-assignments/` | `api/v1/camper-bunk-assignments/` | `CamperBunkAssignmentViewSet` (same class) | GET, POST | No | No | KEEP `/api/v1/` version; DELETE `/api/` duplicate |
| `api/camper-bunk-assignments/{id}/` | `api/v1/camper-bunk-assignments/{id}/` | `CamperBunkAssignmentViewSet` (same class) | GET, PUT, PATCH, DELETE | No | No | KEEP `/api/v1/` version; DELETE `/api/` duplicate |

### Bunk Logs

| Endpoint path under `/api/` | Endpoint path under `/api/v1/` | View / function | Methods | Frontend? | External? | Recommendation |
|---|---|---|---|---|---|---|
| `api/bunk-logs/` | `api/v1/bunklogs/` | `BunkLogViewSet` (same class, different URL slug) | GET, POST | Yes — `/api/v1/bunklogs/` (`BunkLogForm.jsx` POST) | No | KEEP `/api/v1/` version; DELETE `/api/bunk-logs/` |
| `api/bunk-logs/{id}/` | `api/v1/bunklogs/{id}/` | `BunkLogViewSet` (same class) | GET, PUT, PATCH, DELETE | Yes — `/api/v1/bunklogs/${id}/` (`BunkLogForm.jsx` PUT) | No | KEEP `/api/v1/` version; DELETE `/api/bunk-logs/{id}/` |
| `api/bunklogs/{bunk_id}/logs/{date}/` | `api/v1/bunklogs/{bunk_id}/logs/{date}/` | `BunkLogsInfoByDateViewSet` (same class) | GET | Yes — `/api/v1/bunklogs/${bunk_id}/logs/${date}/` (`CamperList.jsx`, `BunkLogForm.jsx`) | No | KEEP `/api/v1/` version; DELETE `/api/` duplicate |
| `api/bunklogs/all/{date}/` | `api/v1/bunklogs/all/{date}/` | `BunkLogsAllByDateViewSet` (same class) | GET | Yes — `/api/v1/bunklogs/all/${date}/` (`AdminBunkLogs.jsx`) | No | KEEP `/api/v1/` version; DELETE `/api/` duplicate |

### Counselor / Staff Logs

| Endpoint path under `/api/` | Endpoint path under `/api/v1/` | View / function | Methods | Frontend? | External? | Recommendation |
|---|---|---|---|---|---|---|
| `api/counselor-logs/` | `api/v1/counselorlogs/` | `CounselorLogViewSet` (same class, different URL slug) | GET, POST | Yes — `/api/v1/counselorlogs/` (`CounselorDashboard.jsx`, `StaffMemberHistory.jsx`, `CounselorLogForm.jsx`) | No | KEEP `/api/v1/` version; DELETE `/api/counselor-logs/` |
| `api/counselor-logs/{id}/` | `api/v1/counselorlogs/{id}/` | `CounselorLogViewSet` (same class) | GET, PUT, PATCH, DELETE | Yes — `/api/v1/counselorlogs/${id}/` (`CounselorLogForm.jsx` PUT) | No | KEEP `/api/v1/` version; DELETE `/api/counselor-logs/{id}/` |
| — | `api/v1/counselorlogs/{date}/` | `CounselorLogViewSet.by_date` (@action) | GET | Yes — `/api/v1/counselorlogs/${date}/` (`UnitHeadBunkGrid.jsx`, `AdminDashboard.jsx`) | No | KEEP under `/api/v1/` |

### Unit Head & Camper Care Dashboard

| Endpoint path under `/api/` | Endpoint path under `/api/v1/` | View / function | Methods | Frontend? | External? | Recommendation |
|---|---|---|---|---|---|---|
| `api/unithead/{unithead_id}/{date}/` | `api/v1/unithead/{unithead_id}/{date}/` | `get_unit_head_bunks` (same function) | GET | Yes — `/api/v1/unithead/${user.id}/${date}/` (`UnitHeadBunkGrid.jsx`) | No | KEEP `/api/v1/` version; DELETE `/api/` duplicate |
| `api/campercare/{camper_care_id}/{date}/` | `api/v1/campercare/{camper_care_id}/{date}/` | `get_camper_care_bunks` (same function) | GET | Yes — `/api/v1/campercare/${user.id}/${date}/` (`CamperCareBunkLogsList.jsx`, `CamperCareNeedsAttentionList.jsx`, `CamperCareBunkGrid.jsx`) | No | KEEP `/api/v1/` version; DELETE `/api/` duplicate |

### CSV Import

| Endpoint path under `/api/` | Endpoint path under `/api/v1/` | View / function | Methods | Frontend? | External? | Recommendation |
|---|---|---|---|---|---|---|
| — | — (not registered in either router) | `UnitStaffAssignmentCSVImportView` (defined but no URL) | POST | No | No | DELETE the class or register at `api/v1/unit-staff-assignments/import/` if needed |

### Orders

| Endpoint path under `/api/` | Endpoint path under `/api/v1/` | View / function | Methods | Frontend? | External? | Recommendation |
|---|---|---|---|---|---|---|
| `api/orders/` | — | `OrderViewSet` | GET, POST | Yes (`Orders.jsx`, `OrdersList.jsx`, `CreateOrderModal.jsx`) | No | MIGRATE to `/api/v1/orders/` and update frontend callers |
| `api/orders/{id}/` | — | `OrderViewSet` | GET, PUT, PATCH, DELETE | Yes (`OrderDetail.jsx`, `OrderEdit.jsx`, `BunkOrderDetail.jsx`, `BunkOrderEdit.jsx`, `StatusDropdown.jsx`) | No | MIGRATE to `/api/v1/orders/{id}/` and update frontend callers |
| `api/orders/statistics/` | — | `get_order_statistics` | GET | No | No | MIGRATE to `/api/v1/orders/statistics/` |
| `api/items/` | — | `ItemViewSet` | GET, POST | Yes (`OrderEdit.jsx` — `?order_type=…` filter) | No | MIGRATE to `/api/v1/items/` |
| `api/items/{id}/` | — | `ItemViewSet` | GET, PUT, PATCH, DELETE | No | No | MIGRATE to `/api/v1/items/{id}/` |
| `api/item-categories/` | — | `ItemCategoryViewSet` | GET, POST | No | No | MIGRATE to `/api/v1/item-categories/` |
| `api/item-categories/{id}/` | — | `ItemCategoryViewSet` | GET, PUT, PATCH, DELETE | No | No | MIGRATE to `/api/v1/item-categories/{id}/` |
| `api/order-types/` | — | `OrderTypeViewSet` | GET, POST | Yes (`OrderFilters.jsx`, `CreateOrderModal.jsx`, `OrderEdit.jsx`) | No | MIGRATE to `/api/v1/order-types/` |
| `api/order-types/{id}/` | — | `OrderTypeViewSet` | GET, PUT, PATCH, DELETE | No | No | MIGRATE to `/api/v1/order-types/{id}/` |
| `api/order-types/{id}/items/` | — | `get_items_for_order_type` | GET | Yes (`BunkOrderEdit.jsx`, `CreateOrderModal.jsx`) | No | MIGRATE to `/api/v1/order-types/{id}/items/` |

### Messaging

| Endpoint path under `/api/` | Endpoint path under `/api/v1/` | View / function | Methods | Frontend? | External? | Recommendation |
|---|---|---|---|---|---|---|
| `api/messaging/templates/` | — | `EmailTemplateViewSet` | GET, POST, PUT, PATCH, DELETE | Unknown | No | MIGRATE to `/api/v1/messaging/templates/` |
| `api/messaging/recipient-groups/` | — | `EmailRecipientGroupViewSet` | GET, POST, PUT, PATCH, DELETE | Unknown | No | MIGRATE to `/api/v1/messaging/recipient-groups/` |
| `api/messaging/recipients/` | — | `EmailRecipientViewSet` | GET, POST, PUT, PATCH, DELETE | Unknown | No | MIGRATE to `/api/v1/messaging/recipients/` |
| `api/messaging/schedules/` | — | `EmailScheduleViewSet` | GET, POST, PUT, PATCH, DELETE | Unknown | No | MIGRATE to `/api/v1/messaging/schedules/` |
| `api/messaging/logs/` | — | `EmailLogViewSet` | GET | Unknown | No | MIGRATE to `/api/v1/messaging/logs/` |
| `api/messaging/preview/` | — | `EmailPreviewViewSet` | GET, POST | Unknown | No | MIGRATE to `/api/v1/messaging/preview/` |

### Debug

| Endpoint path under `/api/` | Endpoint path under `/api/v1/` | View / function | Methods | Frontend? | External? | Recommendation |
|---|---|---|---|---|---|---|
| `api/debug/user-bunks/` | `api/v1/debug/user-bunks/` | `debug_user_bunks` (same function) | GET | No | No | DELETE both — debug-only, no active frontend caller |
| `api/debug/fix-social-apps/` | `api/v1/debug/fix-social-apps/` | `FixSocialAppsView` (same class) | GET, POST | No | No | DELETE both — one-time diagnostic, shouldn't be a permanent endpoint |
| — | `api/v1/debug/auth/` | `auth_debug_view` | GET | No | No | DELETE — debug-only |

### Schema & Meta

| Endpoint path under `/api/` | Endpoint path under `/api/v1/` | View / function | Methods | Frontend? | External? | Recommendation |
|---|---|---|---|---|---|---|
| `api/schema/` | — | `SpectacularAPIView` | GET | No | No | KEEP for dev tooling |
| `api/docs/` | — | `SpectacularSwaggerView` | GET | No | No | KEEP for dev tooling |
| `api/migration-status/` | — | `migration_views.migration_status` | GET | No (internal monitoring) | No | KEEP at current path |

---

## Summary by Recommendation

### KEEP under `/api/v1/` (already there, actively used)

- `api/v1/unit-staff-assignments/{id}/`
- `api/v1/bunklogs/`, `api/v1/bunklogs/{id}/`
- `api/v1/bunklogs/{bunk_id}/logs/{date}/`
- `api/v1/bunklogs/all/{date}/`
- `api/v1/counselorlogs/`, `api/v1/counselorlogs/{id}/`, `api/v1/counselorlogs/{date}/`
- `api/v1/unithead/{id}/{date}/`
- `api/v1/campercare/{id}/{date}/`
- `api/v1/users/email/{email}/`
- `api/v1/users/create/`
- `api/v1/campers/{id}/logs/`
- `api/v1/bunk/{id}/` (keep temporarily; normalise to `api/v1/bunks/{id}/` + update `BunkCard.jsx`)

### MIGRATE from `/api/` to `/api/v1/`

- All ordering endpoints: `orders/`, `items/`, `item-categories/`, `order-types/`, `order-types/{id}/items/`, `orders/statistics/`
- All messaging endpoints: `messaging/*`
- Unit actions: `units/{id}/assign_staff/`, `units/{id}/remove_staff/`
- Users list / me: `users/`, `users/{id}/`, `users/me/`
- Auth tokens: `auth/token/`, `auth/token/refresh/`, `auth/token/verify/`
- CSRF helper: `get-csrf-token/`

### DELETE

- `api/auth-token/` — DRF session token, superseded by JWT
- `api/users/details/` — redundant (email-based lookup preferred)
- `api/v1/users/{user_id}` — no trailing slash, no callers, duplicates email lookup
- All `/api/` duplicates once the matching `/api/v1/` endpoint is the sole registered path
- `api/debug/user-bunks/`, `api/v1/debug/user-bunks/`
- `api/debug/fix-social-apps/`, `api/v1/debug/fix-social-apps/`
- `api/v1/debug/auth/`

---

## Known Issues to Fix Alongside Migration

1. **`/api/v1/users/` maps to `UserDetailsView` (wrong class)** — should map to the richer `UserViewSet` from `bunk_logs/users/api/views.py`. Currently `/api/v1/users/` is a `ReadOnlyModelViewSet` that only returns the calling user; the `/api/` version returns the full staff-filtered list.

2. **`BunkCard.jsx` calls `/api/v1/bunk/${bunk_id}` (missing trailing slash)** — this succeeds only because Django's `APPEND_SLASH=True` issues a redirect. Should be normalised to `/api/v1/bunks/{id}/` once the standard router URL is confirmed to be live.

3. **`CamperDashboard.jsx` calls `/api/v1/campers/${camper_id}/logs` (missing trailing slash)** — same issue as above.

4. **`src/auth.jsx` contains dead API calls** — `/api/token/`, `/api/token/refresh/`, `/api/google/login/`, `/api/google/validate_token/` are not registered URLs and belong to an old auth flow. This file appears to be superseded by `AuthContext.jsx` + `api.js` and can likely be removed.

5. **`/api/auth/user/` referenced in `api.js:checkUserRole`** — this URL does not exist in the backend. Dead code; callers should use `/api/v1/users/email/{email}/` or `/_allauth/browser/v1/auth/session`.
