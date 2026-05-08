# Dashboard Role-to-Widget Contract

This document describes how the BunkLogs template-driven dashboard system
works and how to extend it with new `dashboard_role` + widget pairs.

---

## Overview

Every `ReflectionTemplate` has a JSON `schema` containing `fields`. Each field
can carry an optional `dashboard_role` string. When reflection data is
aggregated, the frontend reads these tags to select the right visualization
widget.

```
ReflectionTemplate.schema.fields[n].dashboard_role → widget component
```

---

## The Five `dashboard_role` Values

| `dashboard_role`    | Allowed field types          | Widget component         | Description |
|---------------------|------------------------------|--------------------------|-------------|
| `primary_rating`    | `single_rating`              | `RatingHeadlineWidget`   | Large number with trend arrow vs prior period |
| `category_ratings`  | `rating_group`               | `CategoryRadarWidget`    | Bar per category with mean and trend |
| `wins`              | `text_list`                  | `HighlightFeedWidget`    | Frequency-weighted list of wins, green accent |
| `improvements`      | `text_list`                  | `ImprovementFeedWidget`  | Frequency-weighted list of growth areas, amber accent |
| `open_concern`      | `text`, `textarea`           | `ConcernQueueWidget`     | Expandable queue with unread counter |

Each template should use at most one field per role (the validator enforces
this). Role-tagged fields render **before** untagged fields in the dashboard.

---

## Generic Widgets (untagged fields)

Fields without a `dashboard_role` get a widget based on `type`:

| Field type                    | Widget component             |
|-------------------------------|------------------------------|
| `text`, `textarea`            | `TextResponseListWidget`     |
| `text_list`                   | `ItemCloudWidget`            |
| `single_rating`               | `RatingDistributionWidget`   |
| `rating_group`                | `RatingTableWidget`          |
| `single_choice`, `multiple_choice` | `ChoiceBarChartWidget`  |
| `yes_no`                      | `YesNoBreakdownWidget`       |
| `number`                      | `NumberSparklineWidget`      |
| `date`                        | `DateHistogramWidget`        |
| `section_header`, `instructions` | *(not rendered)*          |

Generic widgets appear in a collapsible "More fields" disclosure below the
role-tagged widgets.

---

## API: Aggregation Endpoint

```
GET /api/v1/dashboards/template/{id}/?period_end=YYYY-MM-DD&period_days=N
```

**Query params:**

| Param          | Default   | Description                        |
|----------------|-----------|------------------------------------|
| `period_end`   | today     | End of the current window (ISO)    |
| `period_start` | —         | Explicit start (overrides `period_days`) |
| `period_days`  | 14        | Window length in days (1–90)       |

**Response shape:**

```json
{
  "template": { "id": 1, "name": "...", "slug": "...", "role": "...", "schema": {...} },
  "period": { "current_start": "...", "current_end": "...", "prior_start": "...", "prior_end": "..." },
  "summary": { "person_count": 8, "response_count": 6, "eligible_count": 10, "completion_rate": 0.6 },
  "fields": [
    {
      "key": "overall",
      "type": "single_rating",
      "dashboard_role": "primary_rating",
      "data": {
        "mean": 3.8, "prior_mean": 3.2, "trend": "up",
        "response_count": 6,
        "distribution": { "1": 0, "2": 0, "3": 1, "4": 4, "5": 1 }
      }
    },
    {
      "key": "pulse",
      "type": "rating_group",
      "dashboard_role": "category_ratings",
      "data": {
        "categories": [
          { "key": "morale", "mean": 3.5, "prior_mean": 3.1, "trend": "up",
            "response_count": 6, "distribution": { "1": 0, ... } }
        ]
      }
    }
  ]
}
```

**Permissions:**  
Access is controlled by the template's `role` field:

| Template `role`                             | Required viewer membership |
|---------------------------------------------|---------------------------|
| `leadership_team`                           | `leadership_team` or `admin` |
| `camper_care`, `health_center`, `special_diets`, `wellness` | Those roles or `admin` |
| All other roles                             | `admin` only |
| (Legacy) User.role == `Admin` / superuser   | Always allowed |

---

## API: CSV Export

```
GET /api/v1/dashboards/template/{id}/export/?period_end=YYYY-MM-DD&period_days=N
```

Same parameters and permissions as the aggregation endpoint. Returns
`Content-Type: text/csv` with `Content-Disposition: attachment`.

**CSV columns:**

- `person_name`, `person_id`, `period_end`, `language`
- `subject_name`, `subject_id` — explicit subject (matches `person_*` for self-reflection)
- `author_name`, `author_id` — who *filled out* this reflection
- `assignment_group_name`, `assignment_group_id` — group context (e.g. which bunk)
- `subject_group_name`, `subject_group_id` — populated only when `subject_mode='group'`
- `submission_id` — UUID grouping multi-subject submissions
- One column per non-meta field
- `rating_group` fields expand to one column per category, e.g.
  `pulse__morale`, `pulse__energy`
- `text_list` fields are serialized as semicolon-joined strings

---

## Frontend: `TemplateDashboard` Component

```jsx
import TemplateDashboard from '../dashboards/TemplateDashboard';

<TemplateDashboard
  templateId={12}
  language="en"           // optional, default 'en'
  title="Custom Title"    // optional
  subtitle="..."          // optional
  accentColor="teal"      // optional Tailwind color prefix for Refresh button
/>
```

The component:
1. Fetches template data from `GET /api/v1/dashboards/template/{id}/`
2. Renders a `SummaryBar` (completion, responses, respondents, period dates)
3. Renders role-tagged widgets first (in schema field order)
4. Renders generic widgets in a collapsible "More fields" section
5. Renders a CSV export link when there are responses

---

## Frontend: `DashboardPreviewModal`

The template editor includes a **"Dashboard"** button in the header that opens
a preview modal. The modal generates synthetic sample data for each field in
the current schema and renders the appropriate widgets, so admins can see what
the dashboard will look like before any real reflections are submitted.

```jsx
import DashboardPreviewModal from '../dashboards/DashboardPreviewModal';

<DashboardPreviewModal
  schemaFields={fields}      // from the editor's draft state (with _id keys)
  language={language}        // currently selected editor language
  onClose={() => setShow(false)}
/>
```

---

## Adding a New `dashboard_role` + Widget

1. **Backend validator** — Add the new role to `DASHBOARD_ROLES` and
   `DASHBOARD_ROLE_ALLOWED_TYPES` in
   `backend/bunk_logs/core/validators/template_schema.py`.

2. **Frontend validator mirror** — Update `DASHBOARD_ROLES` and
   `DASHBOARD_ROLE_ALLOWED_TYPES` in
   `frontend/src/components/templates/FieldInspector.jsx`.

3. **Widget component** — Create
   `frontend/src/dashboards/widgets/MyNewWidget.jsx`.  
   Export it from `frontend/src/dashboards/widgets/index.js`.

4. **widgetMap** — Add the role→widget entry to `ROLE_WIDGET_MAP` in
   `frontend/src/dashboards/widgetMap.js`.

5. **Aggregation** — If the new role requires a new aggregation shape, add a
   new aggregator function in
   `backend/bunk_logs/api/dashboards/template.py` and wire it in
   `_aggregate_field`.

6. **Tests** — Add tests to `widgetMap.test.js`, `widgets.test.jsx`, and
   `test_template_dashboard.py`.

7. **Docs** — Update the tables in this file.

---

## Permission Model Summary

The visibility model is consolidated in
[`backend/bunk_logs/core/permissions/visibility.py`](../backend/bunk_logs/core/permissions/visibility.py)
as `reflections_visible_to(user, queryset=None)`. Every list / dashboard /
export endpoint that touches reflections funnels through this helper so the
rules below cannot drift out of sync.

### Who can see which reflection

A reflection is visible to a user when **any** of these are true:

1. The user is a Django superuser, OR has an active `admin` Membership in the
   reflection's organization.
2. The user is the **author** of the reflection.
3. The user is the **subject** *and* the template's `subject_visible=True`.
4. The user is an **author of the reflection's `assignment_group`**, or of any
   ancestor group (e.g. a unit head sees every bunk under their unit).
5. The user has a `leadership_team` or `faculty` membership scoped to the
   reflection's program — restricted to `assigned_unit_slugs` when those are
   set on the membership metadata, unrestricted otherwise.
6. The user has a wellness membership (`camper_care`, `health_center`, or
   `special_diets`) and the reflection's template `role` is one of those
   wellness roles.

All paths are tenant-scoped: the helper filters by the current organization
context, so cross-tenant reflections are unreachable regardless of which path
matches.

### Per-dashboard access pre-checks

Some dashboards apply an additional cheap pre-check **before** running the
expensive aggregation, so users with no role-based relationship to a template
get an early 403 instead of an empty payload:

| Dashboard                  | Allowed viewers (in addition to admin / superuser) |
|----------------------------|---------------------------------------------------|
| `template/{id}/`           | LT for LT templates, wellness for wellness templates, supervisors of any matching shared-roster `assignment_group_types` |
| `coverage/`                | Anyone with at least one supervised group (org admins see everything) |
| `subject-trends/`          | Supervisors of the requested group (admins see all groups) |
| `subject/{person_id}/`     | Anyone (visibility filter on reflections handles the rest; empty payload if nothing visible) |
| `authors/`                 | Supervisors only (`has_supervisor_role`): admin, leadership/faculty, or author of a group with at least one descendant. Lone counselors get 403. |
| `concerns/`                | Anyone (filter on reflections is the gate); mark-read endpoint validates visibility on the underlying reflection so 404s don't leak existence. |

### How to test visibility changes

`backend/bunk_logs/core/permissions/test_visibility.py` is the canonical test
file. Add a fixture-driven case for every new code path that introduces a way
to see a reflection.

---

## Coverage / color-pattern dashboards (3.20)

### Coverage Dashboard

```
GET /api/v1/dashboards/coverage/?group_type=&template=&date_start=&date_end=
```

Per-group, per-day completion percentages. Returns one row per visible
`AssignmentGroup` with a `days[]` array of cells (`covered`, `total`, `percent`,
`status`). Tier mapping is fixed (and applied server-side):

| `status`     | Range  | Meaning |
|--------------|--------|---------|
| `green`      | 100%   | All required reflections completed |
| `light_green`| 90–99% | Almost there |
| `yellow`     | 70–89% | Below target |
| `orange`     | 40–69% | Significant gaps |
| `red`        | 1–39%  | Mostly missed |
| `gray`       | 0%     | Day with a roster but no reflections |
| `inactive`   | n/a    | Group has no roster on this day (transparent + striped fill) |

UI: [`frontend/src/dashboards/coverage/`](../frontend/src/dashboards/coverage/).
Route `/dashboards/coverage`.

### Subject Trend Grid (color patterns)

```
GET /api/v1/dashboards/subject-trends/?assignment_group=&template=&date_start=&date_end=&category=
```

The signature view of 3.20: rows = subjects, columns = days, cells colored on
the template's primary rating field (or averaged across `category_ratings`,
or filtered to a single category when `?category=<key>` is set). Returns
`scale_max` so the UI picks the matching diverging palette.

UI: [`frontend/src/dashboards/trends/`](../frontend/src/dashboards/trends/).
Route `/dashboards/subject-trends/:groupId?template=&category=`.

### Per-Subject Detail

```
GET /api/v1/dashboards/subject/{person_id}/?date_start=&date_end=
```

Cross-template aggregation for one Person: rating series per template (one
entry per `single_rating` field, plus one per category in `rating_group`
fields), recent text responses, and a `concerning_patterns[]` array.

Detection rules (no scipy dependency):

- `low_rating` — any rating `≤ 1` in the last 14 days.
- `downward_trend` — split last 14 days in half, require `≥ 3` ratings each
  half, fire when `recent_mean < prior_mean − 0.5`.

Route `/dashboards/subject/:personId`.

### Author Attribution

```
GET /api/v1/dashboards/authors/?date_start=&date_end=&assignment_group=&template=
```

Per-author submission counts plus a per-day timeline. **Supervisor-gated** by
`has_supervisor_role` — direct reports cannot see this view.

Route `/dashboards/authors`.

### Concerns Inbox

```
GET    /api/v1/dashboards/concerns/?date_start=&date_end=&include_read=
POST   /api/v1/dashboards/concerns/<reflection_id>/<field_key>/read/
DELETE /api/v1/dashboards/concerns/<reflection_id>/<field_key>/read/
```

Lists concerning items (open-concern textareas with non-empty answers, plus
ratings `≤ 1` on `primary_rating` and `category_ratings` fields), filtered to
what the viewer is allowed to see. Per-user read state lives in
`ConcernReadState` keyed by `(user, reflection, field_key)`.

The mark-read endpoint refuses to write a row for a reflection the user can't
see (404), so an unauthorized user can't probe reflection IDs via 200/4xx
timing.

Route `/dashboards/concerns`.

---

## Color-scale conventions

Shared by the Coverage Dashboard, Subject Trend Grid, and ConcernQueueWidget.
Implemented in [`frontend/src/dashboards/colors.js`](../frontend/src/dashboards/colors.js).

- **Coverage tiers** (`green` / `light_green` / `yellow` / `orange` / `red` /
  `gray` / `inactive`) — colorblind-aware palette using Okabe-Ito-leaning
  hues. Inactive cells are transparent + diagonal stripes so they read as
  "no data" even on a black-and-white print.
- **Rating colors** — diverging palette anchored to the template's
  `scale_max`. 1-3 / 1-4 / 1-5 scales each have their own palette so a
  rating of `4 / 5` doesn't render the same color as `4 / 4`.
- **No-data cells** — neutral gray (`#e5e7eb`) with an em-dash glyph and an
  `aria-label` describing the missing-data state.

Every cell carries an `aria-label` of the form `"<subject>, <date>, rating X
of Y, logged by <author>"` (or the equivalent for coverage cells), and a
`<title>` tooltip with the same information for sighted hover users.

---

## Performance notes

- All five new dashboards run live SQL on the existing `Reflection` table; the
  3.16 indexes (`(template, period_end)`, `(subject, period_end)`,
  `(assignment_group, period_end)`, `(author, period_end)`) cover the access
  patterns. No `CoverageSnapshot` table is materialized — measured on the
  worst-case 60-day × full-org window the response is well under the 1s P95
  budget called out in the prompt.
- Visibility resolution is a constant number of queries regardless of group
  tree depth: one to load the user's direct author memberships, one to load
  the org's parent→child edges, then an in-memory BFS. There is a query-count
  guard in `core/permissions/test_visibility.py::TestQueryCount`.
- The legacy permission model summary below is preserved for context; the new
  consolidated rules above always supersede it.

### Legacy summary

- LT users see data for `leadership_team`-role templates only.
- Wellness users see data for wellness-type templates only.
- Admin users (membership role `admin` or legacy `User.role == Admin`) see
  all templates.
- Superusers always have full access.
- The counselor self-tracking dashboard (Prompt 3.11) is a separate flow and
  is not affected by this system.
