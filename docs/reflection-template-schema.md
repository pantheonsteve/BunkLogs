# Reflection template schema

`ReflectionTemplate.schema` is a JSON object consumed by reflection UIs and APIs. All user-facing copy lives in objects keyed by [BCP 47](https://www.rfc-editor.org/rfc/rfc5646.html) language tags (e.g. `en`, `es`).

## Top level

| Key      | Type   | Required | Description                          |
| -------- | ------ | -------- | ------------------------------------ |
| `fields` | array  | yes      | Ordered list of field definitions    |

## Field object (common)

| Key      | Type   | Required | Description                                                |
| -------- | ------ | -------- | ---------------------------------------------------------- |
| `key`    | string | yes      | Stable identifier for responses and analytics              |
| `type`   | string | yes      | One of the supported types below                           |

Types **`text`**, **`textarea`**, **`text_list`**, **`multiple_choice`**, **`single_choice`** also require:

| Key       | Type   | Required | Description                                      |
| --------- | ------ | -------- | ------------------------------------------------ |
| `prompts` | object | yes      | Map of language code → primary prompt string     |

Type **`rating_group`** uses **`scale_labels`** and **`categories`** instead of `prompts` (see below).

Optional keys (ignored by structural validation but useful for UX): `required`, `min_items`, `max_items`, `placeholder`, `options`, etc.

## Supported `type` values

- `text` — single line
- `textarea` — multi line
- `text_list` — list of strings (e.g. “three wins”); use `min_items` / `max_items` in the field object when needed
- `multiple_choice` / `single_choice` — use `prompts` plus an `options` array (each option with localized `labels`) when you define choices in the UI layer
- `rating_group` — matrix of category rows × scale columns

## `rating_group`

| Key             | Type   | Required | Description                                                |
| --------------- | ------ | -------- | ---------------------------------------------------------- |
| `scale`         | array  | optional | e.g. `[1, 4]` numeric anchors                              |
| `scale_labels`  | object | yes      | Map language code → ordered list of column labels          |
| `categories`    | array  | yes      | Each item: `key` (string), `labels` (language → string)    |

## English-only example

```json
{
  "fields": [
    {
      "key": "highlight",
      "type": "textarea",
      "required": true,
      "prompts": {
        "en": "What was your biggest highlight this week?"
      }
    }
  ]
}
```

## Bilingual example (`en` + `es`)

```json
{
  "fields": [
    {
      "key": "wins",
      "type": "text_list",
      "min_items": 3,
      "max_items": 3,
      "required": true,
      "prompts": {
        "en": "List 3 things you did well this week.",
        "es": "Lista 3 cosas que hiciste bien esta semana."
      }
    },
    {
      "key": "ratings",
      "type": "rating_group",
      "scale": [1, 4],
      "scale_labels": {
        "en": ["Unsatisfactory", "Needs Improvement", "Meets Expectations", "Exceeds Expectations"],
        "es": ["Insatisfactorio", "Necesita Mejorar", "Cumple Expectativas", "Excede Expectativas"]
      },
      "categories": [
        {
          "key": "punctuality",
          "labels": {
            "en": "Reliability & Punctuality",
            "es": "Confiabilidad y Puntualidad"
          }
        }
      ]
    }
  ]
}
```

Set `ReflectionTemplate.languages` to the codes you ship (e.g. `["en", "es"]`) so clients know which locales to offer.
