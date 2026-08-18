# Reflection template schema (v1)

`ReflectionTemplate.schema` is a JSON object consumed by reflection UIs and APIs. All user-facing copy lives in objects keyed by [BCP 47](https://www.rfc-editor.org/rfc/rfc5646.html) language tags (e.g. `en`, `es`).

Validation is performed by `core/validators/template_schema.py::validate_template_schema(schema, languages)`.

---

## Top level

| Key      | Type  | Required | Description                       |
| -------- | ----- | -------- | --------------------------------- |
| `fields` | array | yes      | Ordered list of field definitions |

---

## Field object (common properties)

| Key              | Type   | Required | Description                                                                    |
| ---------------- | ------ | -------- | ------------------------------------------------------------------------------ |
| `key`            | string | yes      | Stable snake\_case identifier used in answer data and analytics                |
| `type`           | string | yes      | One of the supported types listed below                                        |
| `required`       | bool   | no       | Whether the answer is required. Default `true`. Ignored for meta field types.  |
| `dashboard_role` | string | no       | Dashboard aggregation hint; `null` (default) or one of the values below        |
| `thread_enabled` | bool   | no       | Default `false`. Give the answer a comment thread; see thread flags below      |
| `thread_scope`   | string | no       | `"field"` (default) or `"item"`. `"item"` is only valid on `text_list`          |
| `routes_to`      | string | no       | `null` (default), `"faculty"`, `"director"`, or `"both"`. Requires a thread    |
| `share_with_cohort` | bool | no      | Default `false`. Publish the answer to the cohort feed on submit               |
| `trend_key`      | string | no       | `rating_group` only. Stable trend series key; defaults to the field `key`      |

### Reserved keys

The following field keys are reserved and cannot be used: `id`, `created_at`, `updated_at`, `submitted_at`, `submitted_by`, `template`, `program`, `person`, `organization`.

### `dashboard_role` values

| Value              | Allowed on              | Meaning                                    |
| ------------------ | ----------------------- | ------------------------------------------ |
| `primary_rating`   | `single_rating`         | Single top-level score for dashboards      |
| `category_ratings` | `rating_group`          | Multi-category rating matrix               |
| `wins`             | `text_list`             | Positive observations ("three wins")       |
| `improvements`     | `text_list`             | Areas for growth                           |
| `open_concern`     | `text`, `textarea`      | Free-text flag for leadership review       |

### Thread, routing, and cohort flags

These flags turn an answer into a surface the role homepages render. They live inside the field object, so adding them to a template is a JSON edit rather than a migration. Unlike most optional keys, they are validated strictly: a misspelled flag would fail open and a routed question would never reach anyone's queue.

| Flag | Values | Effect |
| ---- | ------ | ------ |
| `thread_enabled` | bool, default `false` | The answer gets a comment thread and appears as an expandable entry on the author's homepage. Not valid on `section_header` or `instructions`. |
| `thread_scope` | `"field"` (default) or `"item"` | For `text_list`, whether each list item threads separately or the whole answer threads as one. `"item"` on any other type is an error. |
| `routes_to` | `null` (default), `"faculty"`, `"director"`, `"both"` | Places the entry in that role's response queue. Setting it without `thread_enabled` is an error. |
| `share_with_cohort` | bool, default `false` | Publishes a snapshot of the answer to the cohort feed on submit. An error on `rating_group` and `single_rating` — ratings stay private to the author and their supervisors. |
| `trend_key` | string | `rating_group` only. Stable key for the trend series so renaming a field does not break history. Defaults to the field `key`. |

`routes_to` is snapshotted onto the thread at submit time, so editing a template later does not retroactively reroute items that are already open.

Example:

```json
{
  "key": "question_or_concern",
  "type": "text",
  "prompts": { "en": "One question or concern for your Director" },
  "thread_enabled": true,
  "routes_to": "director"
}
```

---

## Supported field types

### Text input

#### `text`

Single-line text input.

| Property      | Type   | Required | Description                                  |
| ------------- | ------ | -------- | -------------------------------------------- |
| `prompts`     | object | yes      | `{lang: string}` — main question label       |
| `max_length`  | int    | no       | Maximum character count                      |
| `placeholder` | object | no       | `{lang: string}` — input placeholder text    |

#### `textarea`

Multi-line text area.

| Property      | Type   | Required | Description                               |
| ------------- | ------ | -------- | ----------------------------------------- |
| `prompts`     | object | yes      | `{lang: string}` — main question label    |
| `min_length`  | int    | no       | Minimum character count                   |
| `max_length`  | int    | no       | Maximum character count                   |
| `placeholder` | object | no       | `{lang: string}` — textarea placeholder   |

#### `text_list`

Repeated single-line text inputs (e.g. "List 3 wins").

| Property    | Type   | Required | Description                              |
| ----------- | ------ | -------- | ---------------------------------------- |
| `prompts`   | object | yes      | `{lang: string}` — main question label   |
| `min_items` | int    | no       | Minimum number of items                  |
| `max_items` | int    | no       | Maximum number of items                  |

---

### Choice

#### `single_choice`

Radio buttons — exactly one answer selected.

| Property  | Type   | Required | Description                                                   |
| --------- | ------ | -------- | ------------------------------------------------------------- |
| `prompts` | object | yes      | `{lang: string}` — main question label                        |
| `options` | array  | yes      | List of `{key, labels: {lang: string}}` objects               |

> **Backward compat:** `value` is accepted as an alias for `key` in option objects.

#### `multiple_choice`

Checkboxes — zero or more answers selected.

| Property          | Type   | Required | Description                                   |
| ----------------- | ------ | -------- | --------------------------------------------- |
| `prompts`         | object | yes      | `{lang: string}` — main question label        |
| `options`         | array  | yes      | List of `{key, labels: {lang: string}}`        |
| `min_selections`  | int    | no       | Minimum number of selections                  |
| `max_selections`  | int    | no       | Maximum number of selections                  |

#### `rating_group`

Matrix of category rows × rating-scale columns.

| Property      | Type   | Required | Description                                                             |
| ------------- | ------ | -------- | ----------------------------------------------------------------------- |
| `scale`       | array  | yes      | `[min, max]` numeric anchors, e.g. `[1, 4]`                            |
| `scale_labels`| object | yes      | `{lang: [string, …]}` — ordered column labels, one per scale step      |
| `categories`  | array  | yes      | List of `{key, labels: {lang: string}}` — one row per category          |

#### `single_rating`

One rating on a 1-M scale with no category breakdown.

| Property      | Type   | Required | Description                                                             |
| ------------- | ------ | -------- | ----------------------------------------------------------------------- |
| `scale`       | array  | yes      | `[min, max]` numeric anchors, e.g. `[1, 5]`                            |
| `scale_labels`| object | yes      | `{lang: [string, …]}` — ordered column labels, one per scale step      |

---

### Structured

#### `yes_no`

Binary yes/no question, optionally revealing a follow-up textarea.

| Property           | Type   | Required | Description                                                            |
| ------------------ | ------ | -------- | ---------------------------------------------------------------------- |
| `prompts`          | object | yes      | `{lang: string}` — main question label                                 |
| `follow_up_on`     | string | no       | `"yes"` or `"no"` — which answer reveals the follow-up                 |
| `follow_up_prompts`| object | no       | `{lang: string}` — label for the conditional follow-up textarea        |

Answer value: `"yes"`, `"no"`, `true`, or `false`.

#### `date`

Date picker.

| Property   | Type   | Required | Description                              |
| ---------- | ------ | -------- | ---------------------------------------- |
| `prompts`  | object | yes      | `{lang: string}` — main question label   |
| `min_date` | string | no       | ISO 8601 minimum selectable date         |
| `max_date` | string | no       | ISO 8601 maximum selectable date         |

Answer value: ISO 8601 date string.

#### `number`

Numeric input.

| Property  | Type   | Required | Description                              |
| --------- | ------ | -------- | ---------------------------------------- |
| `prompts` | object | yes      | `{lang: string}` — main question label   |
| `min`     | number | no       | Minimum allowed value                    |
| `max`     | number | no       | Maximum allowed value                    |
| `step`    | number | no       | Increment step                           |

Answer value: integer or float.

---

### Meta (rendered, not collected as answer data)

#### `section_header`

Heading block. Not included in submitted answers.

| Property  | Type   | Required | Description                              |
| --------- | ------ | -------- | ---------------------------------------- |
| `prompts` | object | yes      | `{lang: string}` — heading text          |

#### `instructions`

Explanatory text block. Not included in submitted answers.

| Property  | Type   | Required | Description                              |
| --------- | ------ | -------- | ---------------------------------------- |
| `prompts` | object | yes      | `{lang: string}` — instruction text      |

---

## Language coverage

Set `ReflectionTemplate.languages` to the codes you support (e.g. `["en", "es"]`). When `languages` is non-empty, `validate_template_schema` enforces that every field's locale data covers all declared language codes.

---

## Complete example (all field types, with `dashboard_role`)

```json
{
  "fields": [
    {
      "key": "intro",
      "type": "section_header",
      "prompts": {
        "en": "Weekly Reflection",
        "es": "Reflexión Semanal"
      }
    },
    {
      "key": "overall_score",
      "type": "single_rating",
      "dashboard_role": "primary_rating",
      "scale": [1, 5],
      "scale_labels": {
        "en": ["1 — Poor", "2", "3", "4", "5 — Excellent"],
        "es": ["1 — Pobre", "2", "3", "4", "5 — Excelente"]
      }
    },
    {
      "key": "category_ratings",
      "type": "rating_group",
      "dashboard_role": "category_ratings",
      "scale": [1, 4],
      "scale_labels": {
        "en": ["Unsatisfactory", "Needs Improvement", "Meets Expectations", "Exceeds Expectations"],
        "es": ["Insatisfactorio", "Necesita Mejorar", "Cumple Expectativas", "Excede Expectativas"]
      },
      "categories": [
        { "key": "punctuality", "labels": { "en": "Punctuality", "es": "Puntualidad" } },
        { "key": "teamwork",    "labels": { "en": "Teamwork",    "es": "Trabajo en equipo" } }
      ]
    },
    {
      "key": "wins",
      "type": "text_list",
      "dashboard_role": "wins",
      "min_items": 3,
      "max_items": 3,
      "prompts": {
        "en": "List 3 things you did well this week.",
        "es": "Lista 3 cosas que hiciste bien esta semana."
      }
    },
    {
      "key": "improvements",
      "type": "text_list",
      "dashboard_role": "improvements",
      "min_items": 2,
      "max_items": 2,
      "prompts": {
        "en": "List 2 areas you want to improve.",
        "es": "Lista 2 áreas que quieres mejorar."
      }
    },
    {
      "key": "open_concern",
      "type": "textarea",
      "dashboard_role": "open_concern",
      "required": false,
      "prompts": {
        "en": "Anything you'd like leadership to know?",
        "es": "¿Algo que le gustaría que el liderazgo supiera?"
      }
    },
    {
      "key": "attendance",
      "type": "yes_no",
      "prompts": { "en": "Were you present for all sessions?" },
      "follow_up_on": "no",
      "follow_up_prompts": { "en": "Please explain your absence." }
    },
    {
      "key": "session_date",
      "type": "date",
      "prompts": { "en": "Date of the session being reflected on" },
      "max_date": "2026-12-31"
    },
    {
      "key": "hours_worked",
      "type": "number",
      "prompts": { "en": "Hours worked this week" },
      "min": 0,
      "max": 80
    },
    {
      "key": "preferred_shift",
      "type": "single_choice",
      "prompts": { "en": "Preferred shift next week" },
      "options": [
        { "key": "morning", "labels": { "en": "Morning" } },
        { "key": "afternoon", "labels": { "en": "Afternoon" } },
        { "key": "evening", "labels": { "en": "Evening" } }
      ]
    },
    {
      "key": "training_completed",
      "type": "multiple_choice",
      "prompts": { "en": "Which trainings did you complete?" },
      "options": [
        { "key": "safety",    "labels": { "en": "Safety" } },
        { "key": "inclusion", "labels": { "en": "Inclusion" } },
        { "key": "cpr",       "labels": { "en": "CPR" } }
      ]
    },
    {
      "key": "highlight",
      "type": "textarea",
      "prompts": {
        "en": "What was your biggest highlight this week?",
        "es": "¿Cuál fue tu mayor logro esta semana?"
      }
    }
  ]
}
```
