/**
 * Unit Head dashboard — Step 7_7, Story 10.
 *
 * Renders the supervised bunk list with attention badges + completion
 * + the UH's own "My reflection" section. Tapping a bunk row opens
 * the Bunk Dashboard (Story 11).
 *
 * Sort + badge styling mirror the backend's
 * `ATTENTION_BADGE_ORDER`: badged bunks rise to the top, ordered
 * help_requested -> bunk_concerns -> off_camp -> low_completion.
 */

import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { fetchUnitHeadDashboard } from '../../api/unitHead';

const REFRESH_INTERVAL_MS = 60_000;

const BADGE_META = {
  help_requested: {
    label: 'Help requested',
    className: 'bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-200',
  },
  bunk_concerns: {
    label: 'Bunk concerns',
    className: 'bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-200',
  },
  off_camp: {
    label: 'Off-camp',
    className: 'bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-200',
  },
  low_completion: {
    label: 'Low completion',
    className: 'bg-gray-200 text-gray-800 dark:bg-gray-700 dark:text-gray-100',
  },
};

function BunkRow({ bunk }) {
  const { completion } = bunk;
  return (
    <li
      data-testid={`uh-bunk-row-${bunk.id}`}
      data-bunk-id={bunk.id}
      className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 shadow-sm"
    >
      <Link
        to={`/dashboards/bunk/${bunk.id}`}
        className="block px-4 py-3 hover:bg-gray-50 dark:hover:bg-gray-800 rounded-xl"
      >
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <h3 className="font-semibold text-gray-900 dark:text-white truncate">
              {bunk.name}
            </h3>
            {bunk.unit_name && (
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                {bunk.unit_name}
              </p>
            )}
            {bunk.counselor_names?.length > 0 && (
              <p className="text-xs text-gray-600 dark:text-gray-300 mt-1 truncate">
                {bunk.counselor_names.join(' · ')}
              </p>
            )}
          </div>
          <div className="text-right shrink-0">
            <p className="text-sm font-medium text-gray-900 dark:text-white">
              {completion.submitted} of {completion.expected} submitted
            </p>
            {completion.off_camp > 0 && (
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                {completion.off_camp} off-camp
              </p>
            )}
          </div>
        </div>
        {bunk.badges?.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mt-2">
            {bunk.badges.map((badge) => {
              const meta = BADGE_META[badge] || {
                label: badge,
                className: 'bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-200',
              };
              return (
                <span
                  key={badge}
                  data-testid={`uh-badge-${badge}`}
                  className={`text-xs font-medium px-2 py-0.5 rounded-full ${meta.className}`}
                >
                  {meta.label}
                </span>
              );
            })}
          </div>
        )}
      </Link>
    </li>
  );
}

function SelfReflectionSection({ section, today }) {
  const state = section?.state ?? 'missing';
  const badge = (() => {
    if (state === 'complete') {
      return { label: 'Submitted', cls: 'bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-200' };
    }
    if (state === 'day_off') {
      return { label: 'Day off', cls: 'bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-200' };
    }
    return { label: 'Not yet', cls: 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-200' };
  })();

  return (
    <section
      data-testid="uh-self-reflection"
      data-state={state}
      className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 px-4 py-4 shadow-sm"
    >
      <div className="flex items-center justify-between gap-2 mb-2">
        <h2 className="text-base font-semibold text-gray-900 dark:text-white">My reflection</h2>
        <span
          className={`text-xs font-medium px-2 py-0.5 rounded-full ${badge.cls}`}
          data-testid="uh-self-reflection-state"
        >
          {badge.label}
        </span>
      </div>
      <p className="text-sm text-gray-700 dark:text-gray-300">
        {state === 'complete' && 'Your reflection for today is in.'}
        {state === 'day_off' && 'Marked as a day off — no further action needed.'}
        {state === 'missing' && `Today is ${today}. Submit your reflection so your team has it.`}
      </p>
      <div className="mt-3 flex items-center gap-3">
        <Link
          to="/unit-head/self-reflection"
          data-testid="uh-self-reflection-action"
          className="inline-flex items-center justify-center min-h-[44px] px-4 rounded-lg bg-blue-600 text-white text-sm font-medium hover:bg-blue-700"
        >
          {state === 'missing' ? 'Submit reflection' : 'Edit reflection'}
        </Link>
        <Link
          to="/unit-head/self-reflection/history"
          className="inline-flex items-center justify-center min-h-[44px] px-3 text-sm font-medium text-blue-700 dark:text-blue-300 hover:underline"
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

  const bunks = data?.bunks ?? [];

  return (
    <div data-testid="uh-dashboard" className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-[96rem] mx-auto space-y-4">
      <header className="mb-2">
        <h1 className="text-2xl font-semibold text-gray-900 dark:text-white">
          Unit Head
        </h1>
        <p className="text-sm text-gray-600 dark:text-gray-400">
          Today is {data?.today}
        </p>
        {refreshing && (
          <p className="text-xs text-gray-400 dark:text-gray-500 mt-0.5">Refreshing…</p>
        )}
      </header>

      <SelfReflectionSection section={data?.self_reflection} today={data?.today} />

      <section data-testid="uh-bunks">
        <div className="flex items-center justify-between mb-2">
          <h2 className="text-base font-semibold text-gray-900 dark:text-white">My bunks</h2>
          <span className="text-xs text-gray-500 dark:text-gray-400">
            {bunks.length} bunk{bunks.length === 1 ? '' : 's'}
          </span>
        </div>
        {bunks.length === 0 ? (
          <p className="text-sm text-gray-600 dark:text-gray-400">
            No supervised bunks yet. Once a Counselor is assigned to your supervision, their bunks will appear here.
          </p>
        ) : (
          <ul className="space-y-2">
            {bunks.map((bunk) => (
              <BunkRow key={bunk.id} bunk={bunk} />
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
