# Step 7_5: Internationalization Foundation

**Goal:** Set up the three i18n layers — content language, UI translation, auto-translation — as platform primitives consumed by role flows.

**Canonical product spec:** `docs/user_stories/00_cross_cutting/i18n.md`

**Scope of this step:**

1. Backend: confirm `Reflection.language` and `Note.language` fields exist with allowed values `'en'`, `'es'`, `'he'`. Add migration if not.
2. Backend: implement `core.translation` Celery task `translate_reflection_to_english(reflection_id)` per i18n spec auto-translation section.
3. Backend: implement `core.translation.translate_content(text, source_language, target_language='en')` helper using Anthropic API. Configured via existing API key infrastructure.
4. Backend: implement `TranslationRecord` model storing translated content + metadata (source_language, target_language, model_id, timestamp, attempt_count, status: pending/completed/failed_retryable/failed_terminal). One-to-one with the translated content record (Reflection or Note).
5. Backend: retry policy via Celery's exponential backoff. After 3 failures, mark `failed_terminal` and surface to Story 44's UI states.
6. Backend: 30-second hard timeout via Celery soft_time_limit.
7. Backend: Datadog metrics emission: `bunklogs.translation.submitted`, `bunklogs.translation.completed`, `bunklogs.translation.failed`, `bunklogs.translation.tokens_used`. Use existing ddtrace integration.
8. Backend: re-translation on edit cancels pending task, enqueues fresh. Prior translation retained per 90-day retention.
9. Backend: GC task to remove translation records older than 90 days, run nightly via Celery Beat.
10. Backend: API surface for readers per Story 44:
    1. `GET /api/v1/reflections/<id>/` returns reflection content with embedded translation state when language ≠ 'en'.
    2. `POST /api/v1/reflections/<id>/retry-translation/` for Story 44's manual retry.
11. Frontend: set up `react-i18next` with translation file structure under `frontend/src/locales/{en,es,he}/{namespace}.json`. Initial namespaces: `common`, `kitchen_staff`, `audience_disclosure`.
12. Frontend: implement `LanguagePicker` component at `frontend/src/components/LanguagePicker.jsx`. Renders list of supported languages in native names. Updates user's Person.language_preference via PATCH and triggers UI re-render.
13. Frontend: implement `TranslationDisplay` component at `frontend/src/components/TranslationDisplay.jsx`. Renders translation states per Story 44 criterion 3:
    1. **Translated** — translation primary, original collapsible
    2. **Pending** — original primary with "Translating to English — refresh in a moment"
    3. **Failed (retryable)** — original primary with "Translation unavailable — retry" action
    4. **Failed (terminal)** — original primary with "Translation could not be generated. Contact Admin"
14. Frontend: implement reader preference for translation-first vs. original-first per Story 44 criterion 6. Stored on user profile.
15. CI: lint warning on missing translation keys for declared supported languages. Custom rule using `eslint-plugin-i18next`.
16. Tests:
    1. Backend: translate_content helper tests (mock Anthropic API).
    2. Backend: Celery task tests including retry behavior, timeout, GC.
    3. Backend: API integration tests for retry endpoint, translation state in reflection payloads.
    4. Frontend: Vitest tests for LanguagePicker, TranslationDisplay, language preference persistence.
17. Documentation: `bunk_logs/core/I18N.md` developer reference covering all three layers.

**Out of scope:**

- Specific Kitchen Staff dashboard / form UIs (Step 7_11).
- Template builder's per-language prompt editing (Step 7_12).
- Hebrew UI / RTL layout (Tier 2).

**Commit scope: `feat(7_5_i18n_foundation): ...`. PR title prefix: `7_5`.**
