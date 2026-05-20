/**
 * LanguagePicker — Step 7_5 UI surface for `Person.preferred_language`.
 *
 * Renders the three supported languages (English, Spanish, Hebrew) from
 * `i18n/index.js#SUPPORTED_LANGUAGES`. Selecting one:
 *
 * 1. Calls `i18n.changeLanguage()` so the UI flips immediately.
 * 2. Persists the choice to `localStorage` (the i18next detector cache key
 *    `bunklogs.lang`).
 * 3. PATCHes `/api/v1/me/preferences/` so the choice follows the user
 *    across devices and feeds outbound email locale selection.
 *
 * Hebrew is intentionally labelled as "content language only" in the
 * dropdown — picking it does not give the user a Hebrew UI (we ship
 * English/Spanish UI in Tier 1). See `docs/user_stories/00_cross_cutting/i18n.md`.
 *
 * Accessibility: the `<select>` is fully keyboard / SR friendly. Status
 * messages live in an `aria-live="polite"` region so success / error
 * announcements don't move focus.
 */
import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';

import api from '../api';
import {
  SUPPORTED_LANGUAGES,
  SUPPORTED_LANGUAGE_CODES,
  isUiSupported,
} from '../i18n';

const STATUS = Object.freeze({
  IDLE: 'idle',
  SAVING: 'saving',
  SAVED: 'saved',
  ERROR: 'error',
});

function ensureSupported(code) {
  return SUPPORTED_LANGUAGE_CODES.includes(code) ? code : 'en';
}

export default function LanguagePicker({ className = '', onChange }) {
  const { t, i18n } = useTranslation('common');
  const [language, setLanguage] = useState(() => ensureSupported(i18n.resolvedLanguage || i18n.language));
  const [status, setStatus] = useState(STATUS.IDLE);
  const [errorMessage, setErrorMessage] = useState(null);

  // Pull the server-side preference once on mount so a fresh device picks
  // up the user's saved language. We do not block render on this — the
  // localStorage-detected language already drove first paint.
  useEffect(() => {
    let cancelled = false;
    api
      .get('/api/v1/me/preferences/')
      .then((res) => {
        if (cancelled) return;
        const next = ensureSupported(res?.data?.preferred_language);
        if (next && next !== i18n.resolvedLanguage) {
          setLanguage(next);
          i18n.changeLanguage(next);
        }
      })
      .catch(() => {
        // 404 = no Person row linked to the user; that's a valid state
        // (e.g. a brand-new staff account before roster import). Stay on
        // the localStorage-detected language.
      });
    return () => {
      cancelled = true;
    };
  }, [i18n]);

  async function handleSelect(event) {
    const next = ensureSupported(event.target.value);
    setLanguage(next);
    setStatus(STATUS.SAVING);
    setErrorMessage(null);

    try {
      await i18n.changeLanguage(next);
    } catch (err) {
      // i18next will only throw here if a namespace bundle is missing,
      // which would indicate a build problem rather than user error.
      console.error('i18n.changeLanguage failed', err);
    }

    try {
      await api.patch('/api/v1/me/preferences/', { preferred_language: next });
      setStatus(STATUS.SAVED);
      onChange?.(next);
    } catch (err) {
      // 404 means the user has no Person row — that's fine, the UI choice
      // still applied locally. Any other error surfaces a retry hint.
      if (err?.response?.status === 404) {
        setStatus(STATUS.SAVED);
        onChange?.(next);
        return;
      }
      console.error('Failed to persist preferred_language', err);
      setStatus(STATUS.ERROR);
      setErrorMessage(t('language.saveFailed'));
    }
  }

  return (
    <div className={`flex flex-col gap-1 ${className}`} data-testid="language-picker">
      <label className="text-sm font-medium text-gray-700 dark:text-gray-200" htmlFor="language-picker-select">
        {t('language.label')}
      </label>
      <select
        id="language-picker-select"
        className="rounded border border-gray-300 bg-white px-2 py-1 text-sm text-gray-900 focus:border-violet-500 focus:outline-none focus:ring-1 focus:ring-violet-500 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100"
        value={language}
        onChange={handleSelect}
        aria-label={t('language.ariaLabel')}
        aria-busy={status === STATUS.SAVING}
        data-testid="language-picker-select"
      >
        {SUPPORTED_LANGUAGES.map((lang) => (
          <option key={lang.code} value={lang.code}>
            {lang.native}
            {!isUiSupported(lang.code) ? ' — content only' : ''}
          </option>
        ))}
      </select>
      <span
        className="text-xs text-gray-500 dark:text-gray-400"
        role="status"
        aria-live="polite"
        data-testid="language-picker-status"
      >
        {status === STATUS.SAVING && t('language.saving')}
        {status === STATUS.SAVED && t('language.saved')}
        {status === STATUS.ERROR && (errorMessage || t('language.saveFailed'))}
      </span>
    </div>
  );
}
