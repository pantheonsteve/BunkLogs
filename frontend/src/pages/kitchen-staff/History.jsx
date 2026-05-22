/**
 * Kitchen Staff reflection history — Step 7_11, Story 41 criterion 7.
 *
 * Reverse-chronological list of all reflections. Each entry shows:
 * date, language of authorship, preview in original language, status.
 * Prior submissions are read-only (no Edit affordance).
 * Only today's submission is editable (criterion 1-2).
 *
 * User's own history always in original language (criterion 9).
 */

import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { fetchHistory } from '../../api/kitchenStaff';
import { useAuth } from '../../auth/AuthContext';

const LANGUAGE_NAMES = { en: 'English', es: 'Español', he: 'עברית' };

function HistoryRow({ row, t }) {
  const {
    date,
    submitted,
    is_day_off,
    reflection_id,
    language,
    submitted_at,
    preview,
    editable,
  } = row;

  const formattedDate = new Date(date + 'T00:00:00').toLocaleDateString(undefined, {
    weekday: 'short', month: 'short', day: 'numeric',
  });

  let statusLabel;
  let statusClass;
  if (is_day_off) {
    statusLabel = t('history.dayOff');
    statusClass = 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300';
  } else if (submitted) {
    statusLabel = t('history.submitted');
    statusClass = 'bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300';
  } else {
    statusLabel = t('history.notSubmitted');
    statusClass = 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400';
  }

  return (
    <li
      className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-4"
      data-testid="ks-history-row"
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-sm font-medium text-gray-900 dark:text-white">{formattedDate}</span>
            <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${statusClass}`}>
              {statusLabel}
            </span>
            {language && language !== 'en' && (
              <span className="text-xs text-gray-400 dark:text-gray-500">
                {LANGUAGE_NAMES[language] ?? language}
              </span>
            )}
          </div>
          {preview && (
            <p className="text-sm text-gray-600 dark:text-gray-400 truncate">{preview}</p>
          )}
        </div>
        {editable && reflection_id ? (
          <Link
            to={`/kitchen-staff/reflection/${reflection_id}/edit`}
            className="shrink-0 text-xs font-medium text-indigo-600 dark:text-indigo-400 hover:underline"
            data-testid="ks-edit-link"
          >
            {t('history.edit')}
          </Link>
        ) : submitted ? (
          <span className="shrink-0 text-xs text-gray-400 dark:text-gray-500">
            {t('history.readOnly')}
          </span>
        ) : null}
      </div>
    </li>
  );
}

export default function KitchenStaffHistory() {
  const { t } = useTranslation('kitchen_staff');
  const { orgSlug } = useAuth();

  const [history, setHistory] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [page, setPage] = useState(1);

  const load = useCallback(async (p = 1) => {
    setLoading(true);
    try {
      const data = await fetchHistory(orgSlug, { page: p });
      setHistory(data);
      setError(null);
    } catch {
      setError(t('history.loadFailed'));
    } finally {
      setLoading(false);
    }
  }, [orgSlug, t]);

  useEffect(() => {
    load(page);
  }, [load, page]);

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <div className="max-w-2xl mx-auto px-4 py-8">
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white" data-testid="ks-history-heading">
            {t('history.heading')}
          </h1>
          <Link
            to="/kitchen-staff"
            className="text-sm text-indigo-600 dark:text-indigo-400 hover:underline"
          >
            ← Dashboard
          </Link>
        </div>

        {error && (
          <div className="mb-4 p-3 rounded-lg bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-300 text-sm" data-testid="ks-history-error">
            {error}
          </div>
        )}

        {loading && !history ? (
          <p className="text-gray-500 dark:text-gray-400 text-sm" data-testid="ks-history-loading">
            {t('history.loading')}
          </p>
        ) : history?.results?.length === 0 ? (
          <p className="text-gray-500 dark:text-gray-400 text-sm" data-testid="ks-history-empty">
            {t('history.empty')}
          </p>
        ) : (
          <>
            <ul className="space-y-3" data-testid="ks-history-list">
              {(history?.results ?? []).map(row => (
                <HistoryRow key={row.date} row={row} t={t} />
              ))}
            </ul>

            {/* Pagination */}
            <div className="mt-6 flex gap-3 justify-center">
              {history?.previous && (
                <button
                  onClick={() => setPage(p => p - 1)}
                  className="text-sm text-indigo-600 dark:text-indigo-400 hover:underline"
                  disabled={loading}
                >
                  ← Previous
                </button>
              )}
              {history?.next && (
                <button
                  onClick={() => setPage(p => p + 1)}
                  className="text-sm text-indigo-600 dark:text-indigo-400 hover:underline"
                  disabled={loading}
                >
                  Next →
                </button>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
