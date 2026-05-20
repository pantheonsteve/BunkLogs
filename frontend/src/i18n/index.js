/**
 * Step 7_5 — react-i18next bootstrap.
 *
 * Three supported languages per the canonical i18n spec
 * (docs/user_stories/00_cross_cutting/i18n.md):
 * - `en` — full UI translation target
 * - `es` — Kitchen Staff dashboard + audience disclosure + common chrome (Tier 1)
 * - `he` — content language only; Hebrew label renders natively (עברית) in
 *   the language picker even though the surrounding UI stays English.
 *
 * Namespaces (initial):
 * - `common` — shared chrome (buttons, validation, errors)
 * - `kitchen_staff` — Story 37 dashboard (lands in Step 7_11; scaffolded now)
 * - `audience_disclosure` — Reflection privacy chip + audience copy
 *
 * Translation files live under `frontend/src/locales/<lang>/<namespace>.json`.
 * Add a key in `en/<ns>.json` first; the eslint i18next rule warns if it’s
 * missing from `es/<ns>.json` (Hebrew is intentionally allowed to lag —
 * Hebrew UI is Tier 2).
 */
import i18n from 'i18next';
import LanguageDetector from 'i18next-browser-languagedetector';
import { initReactI18next } from 'react-i18next';

import enCommon from '../locales/en/common.json';
import enKitchen from '../locales/en/kitchen_staff.json';
import enAudience from '../locales/en/audience_disclosure.json';
import esCommon from '../locales/es/common.json';
import esKitchen from '../locales/es/kitchen_staff.json';
import esAudience from '../locales/es/audience_disclosure.json';
import heCommon from '../locales/he/common.json';
import heKitchen from '../locales/he/kitchen_staff.json';
import heAudience from '../locales/he/audience_disclosure.json';

export const SUPPORTED_LANGUAGES = Object.freeze([
  { code: 'en', label: 'English', native: 'English', uiSupported: true },
  { code: 'es', label: 'Spanish', native: 'Español', uiSupported: true },
  { code: 'he', label: 'Hebrew', native: 'עברית', uiSupported: false },
]);

export const SUPPORTED_LANGUAGE_CODES = SUPPORTED_LANGUAGES.map((l) => l.code);

export const DEFAULT_NAMESPACES = ['common', 'kitchen_staff', 'audience_disclosure'];

export const resources = {
  en: { common: enCommon, kitchen_staff: enKitchen, audience_disclosure: enAudience },
  es: { common: esCommon, kitchen_staff: esKitchen, audience_disclosure: esAudience },
  he: { common: heCommon, kitchen_staff: heKitchen, audience_disclosure: heAudience },
};

export function isUiSupported(code) {
  const entry = SUPPORTED_LANGUAGES.find((l) => l.code === code);
  return Boolean(entry && entry.uiSupported);
}

let _initialized = false;

export default function initI18n({ lng } = {}) {
  if (_initialized) return i18n;
  i18n
    .use(LanguageDetector)
    .use(initReactI18next)
    .init({
      resources,
      lng,
      fallbackLng: 'en',
      supportedLngs: SUPPORTED_LANGUAGE_CODES,
      defaultNS: 'common',
      ns: DEFAULT_NAMESPACES,
      interpolation: { escapeValue: false },
      detection: {
        order: ['localStorage', 'navigator'],
        caches: ['localStorage'],
        lookupLocalStorage: 'bunklogs.lang',
      },
      returnEmptyString: false,
      load: 'languageOnly',
    });
  _initialized = true;
  return i18n;
}

export { i18n };
