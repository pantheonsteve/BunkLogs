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
   `backend/bunk_logs/api/template_dashboard.py` and wire it in
   `_aggregate_field`.

6. **Tests** — Add tests to `widgetMap.test.js`, `widgets.test.jsx`, and
   `test_template_dashboard.py`.

7. **Docs** — Update the tables in this file.

---

## Permission Model Summary

- LT users see data for `leadership_team`-role templates only.
- Wellness users see data for wellness-type templates only.
- Admin users (membership role `admin` or legacy `User.role == Admin`) see
  all templates.
- Superusers always have full access.
- The counselor self-tracking dashboard (Prompt 3.11) is a separate flow and
  is not affected by this system.
