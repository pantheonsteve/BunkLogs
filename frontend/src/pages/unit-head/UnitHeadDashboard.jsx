/**
 * Unit Head dashboard — Step 7_7, Story 10.
 *
 * Renders the UH's own "My reflection" section plus the shared
 * PerformanceDashboard (supervised bunk completion + score cards).
 */

import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import PerformanceDashboard from '../../dashboards/performance/PerformanceDashboard';
import { fetchUnitHeadDashboard } from '../../api/unitHead';

const REFRESH_INTERVAL_MS = 60_000;

function formatToday(iso) {
  if (!iso) return '';
  const parsed = new Date(`${iso}T00:00:00`);
  if (Number.isNaN(parsed.getTime())) return iso;
  return parsed.toLocaleDateString('en-US', {
    weekday: 'long',
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  });
}

const CheckIcon = (props) => (
  <svg viewBox="0 0 20 20" fill="currentColor" aria-hidden="true" {...props}>
    <path
      fillRule="evenodd"
      d="M10 18a8 8 0 1 0 0-16 8 8 0 0 0 0 16Zm3.7-9.3a1 1 0 0 0-1.4-1.4L9 10.58 7.7 9.3a1 1 0 0 0-1.4 1.4l2 2a1 1 0 0 0 1.4 0l4-4Z"
      clipRule="evenodd"
    />
  </svg>
);

function SelfReflectionSection({ section, today }) {
  const state = section?.state ?? 'missing';
  const periodNoun = !section?.cadence || section.cadence === 'daily'
    ? 'today'
    : 'this period';
  const badge = (() => {
    if (state === 'complete') {
      return {
        label: 'Submitted',
        cls: 'bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-200',
        Icon: CheckIcon,
      };
    }
    if (state === 'day_off') {
      return { label: 'Day off', cls: 'bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-200' };
    }
    return { label: 'Not yet', cls: 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-200' };
  })();
  const BadgeIcon = badge.Icon;

  return (
    <section
      data-testid="uh-self-reflection"
      data-state={state}
      className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 px-5 py-5 shadow-sm"
    >
      <div className="flex items-start justify-between gap-2">
        <div>
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">My reflection</h2>
          <p className="text-sm text-gray-500 dark:text-gray-300 mt-1">
            {state === 'complete' && `Your reflection for ${periodNoun} is in.`}
            {state === 'day_off' && 'Marked as a day off — no further action needed.'}
            {state === 'missing' && (
              periodNoun === 'today'
                ? `Today is ${today}. Submit your reflection so your team has it.`
                : 'Submit your reflection for this period so your team has it.'
            )}
          </p>
        </div>
        <span
          className={`inline-flex items-center gap-1 text-xs font-medium px-2.5 py-1 rounded-full shrink-0 ${badge.cls}`}
          data-testid="uh-self-reflection-state"
        >
          {BadgeIcon && <BadgeIcon className="h-3.5 w-3.5" />}
          {badge.label}
        </span>
      </div>
      <div className="mt-4 flex items-center gap-4">
        <Link
          to="/unit-head/self-reflection"
          data-testid="uh-self-reflection-action"
          className="inline-flex items-center justify-center min-h-[44px] px-5 rounded-lg bg-blue-600 text-white text-sm font-semibold hover:bg-blue-700"
        >
          {state === 'missing' ? 'Submit reflection' : 'Edit reflection'}
        </Link>
        <Link
          to="/unit-head/self-reflection/history"
          className="inline-flex items-center justify-center min-h-[44px] text-sm font-semibold text-blue-700 dark:text-blue-300 hover:underline"
        >
          View history
        </Link>
      </div>
    </section>
  );
}

export default function UnitHeadDashboard() {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const load = useCallback(async ({ silent = false } = {}) => {
    if (!silent) setLoading(true);
    if (silent) setRefreshing(true);
    try {
      const next = await fetchUnitHeadDashboard({ noCache: silent });
      setData(next);
      setError(null);
    } catch (err) {
      setError(err?.response?.data?.detail || err?.message || 'Failed to load dashboard.');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    const id = setInterval(() => load({ silent: true }), REFRESH_INTERVAL_MS);
    return () => clearInterval(id);
  }, [load]);

  if (loading && !data) {
    return (
      <div className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-[96rem] mx-auto">
        <p className="text-gray-600 dark:text-gray-400">Loading dashboard…</p>
      </div>
    );
  }

  if (error && !data) {
    return (
      <div className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-[96rem] mx-auto">
        <div
          role="alert"
          className="rounded-xl border border-amber-200 bg-amber-50 dark:border-amber-900 dark:bg-amber-900/30 px-4 py-3 text-sm text-amber-900 dark:text-amber-100"
        >
          {error}
        </div>
      </div>
    );
  }

  return (
    <div data-testid="uh-dashboard" className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-[96rem] mx-auto space-y-6">
      <header>
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
          Unit Head
        </h1>
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
          Today is {formatToday(data?.today)}
        </p>
        {refreshing && (
          <p className="text-xs text-gray-400 dark:text-gray-500 mt-0.5">Refreshing…</p>
        )}
      </header>

      <SelfReflectionSection section={data?.self_reflection} today={formatToday(data?.today)} />

      <PerformanceDashboard embedded />
    </div>
  );
}
