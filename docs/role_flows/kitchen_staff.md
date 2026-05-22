# Kitchen Staff Flow — Step 7_11 (Stories 37-44)

## Overview

Kitchen Staff members submit a daily self-reflection in their preferred language (English, Spanish, or Hebrew). Non-English submissions are automatically translated to English for leadership readers via Anthropic Celery task. The UI renders in English or Spanish (Hebrew UI is Tier 2 / future).

## Invariants

- A Kitchen Staff viewer must have an active `kitchen_staff` Membership in the current org/program.
- Edit window: until rollover boundary (`get_today(org)`). Prior-day reflections are read-only.
- `reflection.language` is not changed on edit unless the user explicitly sends the `language` field (Story 41 criterion 6).
- Non-English submissions always enqueue `translate_reflection_to_english`; day-off submissions do not.
- Author always sees original-language content — never auto-translated back.
- Visibility: `SUPERVISORS_ONLY` — Kitchen Staff reflections visible to Leadership Team, Kitchen supervisor (via Supervision relationship), and Admin.

## Backend endpoints

| Method | Path | Story | Notes |
|--------|------|-------|-------|
| GET | `/api/v1/kitchen-staff/dashboard/` | 37 | Header, my_reflection state card, history entry |
| POST | `/api/v1/kitchen-staff/reflection/` | 40 | Create today's reflection; enqueues translation for non-English |
| PATCH | `/api/v1/kitchen-staff/reflection/<id>/` | 41 | Edit within rollover window |
| GET | `/api/v1/kitchen-staff/reflection/history/` | 41 | Paginated reverse-chronological history |

## Response shape — translation embed (Story 44)

All reflection endpoints include a `translation` key:

```json
{
  "translation": null                          // English submissions
  "translation": {
    "status": "pending",                       // recent non-English submission
    "source_language": "es",
    "target_language": "en",
    "translated_text": ""
  }
  "translation": {
    "status": "completed",
    "source_language": "es",
    "target_language": "en",
    "translated_text": "...",
    "model_id": "claude-sonnet-4-5"
  }
  "translation": {
    "status": "failed_retryable",              // retry via POST /api/v1/reflections/<id>/retry-translation/
    ...
  }
  "translation": {
    "status": "failed_terminal",
    ...
  }
}
```

## Translation pipeline

Uses the shared infrastructure from Step 7_5:

- `enqueue_translation_for_reflection(reflection)` — called after create/edit when `language ≠ 'en'` and not day-off.
- Task: `bunk_logs.core.translation.translate_reflection_to_english` — Anthropic API, 30s soft limit, 3 exponential retries.
- Manual retry endpoint: `POST /api/v1/reflections/<id>/retry-translation/`.
- Datadog metrics: `bunklogs.translation.submitted / completed / failed / tokens_used`.

## i18n

- UI languages: English (full), Spanish (full). Hebrew UI is Tier 2 (deferred per KS1).
- Locale namespace: `kitchen_staff` (files at `frontend/src/locales/en/kitchen_staff.json`, `es/`).
- Template prompts localized via `field.prompts[lang]` with English fallback + `(English only)` indicator.
- `LanguagePicker` component in dashboard header → `PATCH /api/v1/me/preferences/` persists `preferred_language` to `Person`.

## Frontend routes

| Path | Component | Purpose |
|------|-----------|---------|
| `/kitchen-staff` | `Dashboard.jsx` | Landing page after login |
| `/kitchen-staff/reflection/new` | `ReflectionForm.jsx` | Create today's reflection |
| `/kitchen-staff/reflection/:id/edit` | `ReflectionForm.jsx` | Edit within window |
| `/kitchen-staff/history` | `History.jsx` | Read-only history |

## Template resolution

Template resolved via `kitchen_staff_template(org, program)` which queries `ReflectionTemplate` with:
- `role="kitchen_staff"` OR `author_role_filter contains "kitchen_staff"`
- `subject_mode="self"`, `cadence="daily"`

Seeded by: `python manage.py seed_role_template --role kitchen_staff` (see `docs/clc-2026-templates.md`).
