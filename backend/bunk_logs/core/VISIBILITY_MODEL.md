# Visibility model (developer reference)

Product spec: [`docs/user_stories/00_cross_cutting/visibility_model.md`](../../../docs/user_stories/00_cross_cutting/visibility_model.md)

## Modules

| Module | Purpose |
|--------|---------|
| `bunk_logs.core.content_visibility` | Canonical visibility **table** — content types, default/sensitive audiences, write-time labels |
| `bunk_logs.core.permissions.visibility` | Reflection **query paths** (assignment groups, unit scope, wellness shortcut) |
| `bunk_logs.core.filters` | DRF `RoleVisibilityFilterBackend`, `reflections_visible_for_user()`, `notes_visible_to()` |

## API

### `content_visibility`

```python
from bunk_logs.core.content_visibility import (
    ContentType,
    audience_labels,
    audience_roles,
    viewer_can_read,
    reflection_content_type,
    note_content_type,
    gating_role_label,
)
```

- **`audience_roles(content_type, *, is_sensitive, is_private, maintenance_visibility)`** — `frozenset` of `Membership.role` keys allowed to read (author/admin bypass handled separately).
- **`audience_labels(...)`** — sorted human labels for `AudienceDisclosure`.
- **`viewer_can_read(viewer_roles, content_type, ...)`** — boolean gate for tests and note filtering.
- **`reflection_content_type(reflection)`** / **`note_content_type(note)`** — map instances to table rows.

### Queryset filtering

```python
from bunk_logs.core.filters import reflections_visible_for_user, notes_visible_to

qs = reflections_visible_for_user(request.user, Reflection.objects.all())
notes = notes_visible_to(request.user, Note.objects.filter(subject_id=camper_id))
```

`RoleVisibilityFilterBackend` is registered in `REST_FRAMEWORK["DEFAULT_FILTER_BACKENDS"]` and applies automatically to `Reflection` and `Note` viewsets.

### Frontend

- `frontend/src/components/AudienceDisclosure.jsx` — write-time audience list (`audience` prop = labels from `audience_labels()`).
- `frontend/src/components/SensitiveNotePlaceholder.jsx` — count-only placeholder for gated sensitive notes.

## Content types with `is_sensitive`

| Model | Field | When true |
|-------|-------|-----------|
| `Note` | `is_sensitive` | Camper Care / Specialist notes use sensitive-variant audience |
| `Reflection` | `is_sensitive` | Same table row when stored as a reflection |
| `Reflection` | `team_visibility=supervisors_only` | LT/Admin “Private” self-reflection (admin-only audience) |

## Enforcement rule

All filtering is **server-side**. Never rely on the client to hide rows that were returned in full from the API.
