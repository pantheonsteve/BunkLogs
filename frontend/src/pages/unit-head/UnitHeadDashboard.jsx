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

const HelpIcon = (props) => (
  <svg viewBox="0 0 20 20" fill="none" aria-hidden="true" {...props}>
    <circle cx="10" cy="10" r="7.25" stroke="currentColor" strokeWidth="1.5" />
    <circle cx="10" cy="10" r="2.5" stroke="currentColor" strokeWidth="1.5" />
    <path d="M10 2.75v2.75M10 14.5v2.75M2.75 10h2.75M14.5 10h2.75" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
  </svg>
);

const WarningIcon = (props) => (
  <svg viewBox="0 0 20 20" fill="none" aria-hidden="true" {...props}>
    <path d="M10 2.75 1.75 16.5h16.5L10 2.75Z" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round" />
    <path d="M10 8v3.25" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
    <circle cx="10" cy="13.75" r="0.85" fill="currentColor" />
  </svg>
);

const BusIcon = (props) => (
  <svg viewBox="0 0 20 20" fill="none" aria-hidden="true" {...props}>
    <rect x="3.25" y="3.25" width="13.5" height="11" rx="2" stroke="currentColor" strokeWidth="1.5" />
    <path d="M3.25 9.5h13.5" stroke="currentColor" strokeWidth="1.5" />
    <path d="M5.5 14.25v1.5M14.5 14.25v1.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
    <circle cx="6.25" cy="12" r="0.85" fill="currentColor" />
    <circle cx="13.75" cy="12" r="0.85" fill="currentColor" />
  </svg>
);

const BarsIcon = (props) => (
  <svg viewBox="0 0 20 20" fill="none" aria-hidden="true" {...props}>
    <path d="M4.5 11.5v4M10 7.5v8M15.5 9.5v6" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
  </svg>
);

const CheckIcon = (props) => (
  <svg viewBox="0 0 20 20" fill="currentColor" aria-hidden="true" {...props}>
    <path
      fillRule="evenodd"
      d="M10 18a8 8 0 1 0 0-16 8 8 0 0 0 0 16Zm3.7-9.3a1 1 0 0 0-1.4-1.4L9 10.58 7.7 9.3a1 1 0 0 0-1.4 1.4l2 2a1 1 0 0 0 1.4 0l4-4Z"
      clipRule="evenodd"
    />
  </svg>
);

const BADGE_META = {
  help_requested: {
    label: 'Help requested',
    className: 'bg-red-50 text-red-700 dark:bg-red-900/40 dark:text-red-200',
    Icon: HelpIcon,
  },
  bunk_concerns: {
    label: 'Bunk concerns',
    className: 'bg-amber-50 text-amber-700 dark:bg-amber-900/40 dark:text-amber-200',
    Icon: WarningIcon,
  },
  off_camp: {
    label: 'Off-camp',
    className: 'bg-blue-50 text-blue-700 dark:bg-blue-900/40 dark:text-blue-200',
    Icon: BusIcon,
  },
  low_completion: {
    label: 'Low completion',
    className: 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-100',
    Icon: BarsIcon,
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
        to={`/dashboards/group/${bunk.id}`}
        className="flex items-center gap-4 px-5 py-4 hover:bg-gray-50 dark:hover:bg-gray-800 rounded-xl"
      >
        <div className="w-28 shrink-0">
          <h3 className="font-semibold text-gray-900 dark:text-white truncate">
            {bunk.name}
          </h3>
          {bunk.unit_name && (
            <p className="text-sm text-gray-500 dark:text-gray-400 mt-0.5 truncate">
              {bunk.unit_name}
            </p>
          )}
        </div>

        <div className="min-w-0 flex-1">
          {bunk.counselor_names?.length > 0 && (
            <p className="text-sm text-gray-500 dark:text-gray-300 truncate">
              {bunk.counselor_names.join(' · ')}
            </p>
          )}
          {bunk.badges?.length > 0 && (
            <div className="flex flex-wrap gap-1.5 mt-2">
              {bunk.badges.map((badge) => {
                const meta = BADGE_META[badge] || {
                  label: badge,
                  className: 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-200',
                };
                const Icon = meta.Icon;
                return (
                  <span
                    key={badge}
                    data-testid={`uh-badge-${badge}`}
                    className={`inline-flex items-center gap-1 text-xs font-medium px-2.5 py-1 rounded-full ${meta.className}`}
                  >
                    {Icon && <Icon className="h-3.5 w-3.5" />}
                    {meta.label}
                  </span>
                );
              })}
            </div>
          )}
        </div>

        <div className="shrink-0 text-right">
          <p className="text-sm font-semibold text-gray-900 dark:text-white">
            {completion.submitted} of {completion.expected} submitted
          </p>
          {completion.off_camp > 0 && (
            <p className="text-xs text-gray-400 dark:text-gray-500 mt-0.5">
              {completion.off_camp} off-camp
            </p>
          )}
        </div>
      </Link>
    </li>
  );
}

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

  const bunks = data?.bunks ?? [];

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

      <section data-testid="uh-bunks">
        <div className="flex items-baseline justify-between mb-3">
          <h2 className="text-xl font-bold text-gray-900 dark:text-white">My bunks</h2>
          <span className="text-sm text-gray-500 dark:text-gray-400">
            {bunks.length} bunk{bunks.length === 1 ? '' : 's'}
          </span>
        </div>
        {bunks.length === 0 ? (
          <p className="text-sm text-gray-600 dark:text-gray-400">
            No supervised bunks yet. Once a Counselor is assigned to your supervision, their bunks will appear here.
          </p>
        ) : (
          <ul className="space-y-3">
            {bunks.map((bunk) => (
              <BunkRow key={bunk.id} bunk={bunk} />
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
