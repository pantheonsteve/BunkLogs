# Kitchen Staff Flow — Stories 37-44

## Story 37: Sign in and land on minimal reflection-focused dashboard

### Acceptance criteria

1. Sign-in per Story 1.
2. Post-login is Kitchen Staff dashboard, scoped to active Program and Membership.
3. Dashboard displays: **Header** (user name, role label "Kitchen Staff", active program), **My reflection** card (today's status, per Story 16 pattern using `kitchen_staff` template), **My reflections** entry (Story 41), **Language** selector in header showing current language (Story 38).
4. NO display of: bunk lists, roster summaries, flag aggregates, order workspaces, completion counts, operational signal from camper-facing roles.
5. All dashboard labels/buttons/status/role label render in preferred UI language per Story 38. Hebrew-preference users see English UI per Hebrew/RTL scope; preference captured in data model.
6. "Today" interpretation respects org rollover boundary.
7. First contentful paint under 2s on mid-tier Android 4G.

### Decisions

- KS2: Kitchen operational signal (mealtime schedule, allergy callouts) out of scope.

## Story 38: Set and persist preferred language

### Acceptance criteria

1. Language selector in dashboard header and Settings.
2. Selector lists supported content languages in own name: English, Español, עברית (Hebrew).
3. Selector indicates UI vs. content-only support: English/Español UI+content; עברית content only (UI English Tier 1).
4. Selection persists to Person record (existing field).
5. Preference applies to: UI rendering, reflection template fetch (Story 39), email reminders, AudienceDisclosure text (Story 40).
6. Changes take effect on next page load. In-progress drafts preserved.
7. First-time login: if no preference, infer from browser Accept-Language, present as default in one-time confirmation prompt: *"Continue in [language]? Change?"*
8. Admin can set preference at onboarding via Campminder import CSV (Story 9 of migration prompts).

### Decisions

- KS1: Hebrew/RTL content-only Tier 1; full UI Tier 2.

## Story 39: Receive reflection form in preferred language

### Acceptance criteria

1. Opening reflection form fetches active `kitchen_staff` template with localized prompts in preferred language.
2. Every template element renders in preferred language where translation exists: field prompts, rating scale labels, multiple-choice/single-choice options, help text.
3. Form-level UI (Save/Submit/Add another/AudienceDisclosure) renders in preferred UI language per Story 38 criterion 5.
4. Translation gap on a specific field: that field renders in English with small indicator *"(English only)"* near field label. Rest of form remains in preferred language.
5. Translation gaps on required fields do not block submission.
6. No mid-form language switch within session. Changing preference requires save + re-open; draft preserved.
7. Template versioning interacts with localization: new version published, prior versions retain their localizations. User sees version active for their reflection period.

### Decisions

- KS3: Template author maintains translations in builder (Story 51).

## Story 40: Submit reflection in preferred language

### Acceptance criteria

1. User writes free-text in preferred content language.
2. Reflection's `language` set to preferred content language at submission.
3. Server-side Celery task to translate free-text to English when language ≠ 'en'. Rating values, choice keys, structured fields not translated.
4. Translation task does NOT block submission response. User gets "Submitted" confirmation immediately.
5. Translation stored alongside original with metadata: source/target languages, model ID, timestamp.
6. Re-submission via edit (Story 41) re-triggers translation. Prior translations retained per audit policy (90 days, per KS4).
7. Translation failures don't block storage/visibility. Reflection saves in original; readers see "Translation unavailable — retry" per Story 44. Failures logged to Datadog.
8. User's own view shows original-language content always. Never sees own writing translated back.
9. LLM translation prompt per i18n layer spec.
10. AudienceDisclosure component on form: *"This reflection will be visible to: Leadership Team, your Kitchen supervisor, Admin. Original written in [language] will be available alongside the English translation."*

### Decisions

- KS4: 90-day translation audit retention.
- KS5: No live draft translation.

## Story 41: Edit today's reflection; view past read-only

### Acceptance criteria

1. Today's submitted reflection displays Edit affordance in dashboard card and detail.
2. Edit window: until rollover; locked after.
3. Edit opens form (Story 39) populated. Form renders in current preferred language, may differ from authorship language.
4. If preference changed since authorship: prompts in current preference, field contents in original. User can: continue editing in original language (Spanish content with English prompts), save and change preference back, or translate manually within field. System does NOT auto-translate existing content.
5. Save re-triggers translation per Story 40 criterion 6.
6. `language` field NOT changed on edit unless user explicitly changes it. Change requires confirmation: *"Switch this reflection's language to English? This will replace the original Spanish content."*
7. History view reverse-chronological. Each entry: date, language of authorship, preview line in original language, status.
8. Prior submissions read-only. Original-language always. No Edit affordance.
9. User's own history always in original language. Never auto-translated.

## Story 42: See UI in preferred language

### Acceptance criteria

1. All user-facing strings on Kitchen Staff screens via react-i18next in preferred UI language per Story 38.
2. Tier 1 UI translation scope:
   1. Kitchen Staff dashboard (Story 37) — full translation
   2. Language selector (Story 38) — full + native names
   3. Reflection form chrome (Save, Submit, navigation, validation, AudienceDisclosure)
   4. Reflection history view (Story 41)
   5. Sign-in error states (Story 1) where reachable for authenticated-but-misconfigured user
3. Outside Tier 1 scope: rest of app remains English-only. Kitchen Staff doesn't reach those surfaces.
4. Tier 1 supported UI languages: English, Spanish. Hebrew UI deferred (KS1).
5. Date, number, time-of-day formats follow locale conventions.
6. i18n system supports plural forms, gendered nouns, string interpolation.
7. CI warning on missing translation keys for supported languages. Warning, not block, in PR review.
8. Translation file edits via repo PR for Tier 1; translation management UI is Tier 2.

### Decisions

- KS6: react-i18next.

## Story 43: Auto-translate non-English reflections to English

### Acceptance criteria

1. Reflection submission with language ≠ 'en' enqueues Celery task `translate_reflection_to_english(reflection_id)`.
2. Task loads Reflection + template, extracts free-text values, constructs prompt per i18n spec, calls Anthropic API. Success: stores translated answers + metadata. Failure: logs to Datadog, retry per criterion 4.
3. Task async, doesn't block submission UX.
4. Retry: exponential backoff, 3 attempts (1 min, 5 min, 30 min). After 3 failures, marked permanently failed.
5. Re-translation on edit: cancels pending task, enqueues fresh. Prior translations retained.
6. Hard timeout 30s. Exceeded calls treated as failures per criterion 4.
7. Integration via existing API key infra. Datadog metrics: `bunklogs.translation.submitted/completed/failed/tokens_used`.
8. Cost projection: ~30 staff × ~150 words/day < $5/month at current Anthropic pricing. Budgeted in financial model API line.
9. Prompt and model ID recorded with each translation for auditable prompt changes.

### Decisions

- KS7: English-only translation target Tier 1.
- KS8: No translation confidence flagging.

## Story 44: Leadership/admin readers see translated English alongside original

### Acceptance criteria

1. Leadership-tier reader (LT, kitchen supervisor, Admin) opens Reflection with language ≠ 'en':
   1. English translation primary
   2. Original-language content in secondary section labeled with source ("Original (Spanish)"), collapsible, default collapsed
   3. Visible badge: *"Auto-translated from Spanish."*
2. Badge unambiguous about LLM translation, not author's original words.
3. Four translation states:
   1. **Translated** — completion; primary English, original available
   2. **Pending** — recent submission, translation in flight. Original primary with "Translating to English — refresh in a moment" notice and manual refresh
   3. **Failed (retryable)** — all retries failed. Original primary with "Translation unavailable — retry" action
   4. **Failed (terminal)** — multiple retry cycles failed. Original primary with "Translation could not be generated. Contact Admin"
4. Hebrew originals render RTL within content panel via browser bidi (dir="auto"), even when rest of page LTR English.
5. Leadership dashboard search/filter operates against English translation. Search "burnout" matches Spanish reflection translating to include "burnout."
6. Per-reader preference: *Translation first* (default) / *Original first*. Persists across sessions.
7. Visibility per consolidated model: Kitchen Staff reflections visible to LT, Admin, LT member(s) assigned as kitchen supervisor via Supervision relationship.
8. Edits reflected: edit shows latest translation against latest content, "Edited [time]" indicator.
