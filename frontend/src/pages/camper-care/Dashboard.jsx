/**
 * Camper Care dashboard — Step 7_8, Stories 18-19.
 *
 * Top-of-flow surface for Camper Care. Sections (top to bottom):
 *   1. Header — date picker + caseload-wide submitted-of-expected rollup
 *   2. Workspace entries — Flagged campers, Orders, My reflection
 *   3. Caseload tree — Units expand to Bunks with completion + attention badges
 *
 * Bunk rows link to the per-bunk Camper Care drill-down (Story 18
 * criterion 9). Tapping a bunk navigates to `/camper-care/bunks/<id>`
 * which reuses the shared BunkDashboard component, scoped to the CC
 * caseload by the backend.
 */

import { useCallback, useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { fetchCamperCareDashboard } from '../../api/camperCare';

const REFRESH_INTERVAL_MS = 60_000;

const BADGE_META = {
  cc_flagged: {
    label: 'Flagged',
    className: 'bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-200',
  },
  cc_pending_order: {
    label: 'Pending order',
    className: 'bg-orange-100 text-orange-800 dark:bg-orange-900/40 dark:text-orange-200',
  },
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

function Badge({ kind }) {
  const meta = BADGE_META[kind] || {
    label: kind,
    className: 'bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-200',
  };
  return (
    <span
      data-testid={`cc-badge-${kind}`}
      className={`text-xs font-medium px-2 py-0.5 rounded-full ${meta.className}`}
    >
      {meta.label}
    </span>
  );
}

function CompletionLabel({ completion }) {
  if (!completion) return null;
  if (completion.expected === 0 && completion.off_camp === 0) {
    return <span title="No expected submissions">—</span>;
  }
  if (completion.expected === 0 && completion.off_camp > 0) {
    return (
      <span title="All campers off-camp">
        — <span className="text-xs">({completion.off_camp} off-camp)</span>
      </span>
    );
  }
  return (
    <>
      {completion.submitted} of {completion.expected} submitted
      {completion.off_camp > 0 && (
        <span className="text-xs text-gray-500 dark:text-gray-400 ml-2">
          ({completion.off_camp} off-camp)
        </span>
      )}
    </>
  );
}

function BunkRow({ bunk }) {
  return (
    <li data-testid={`cc-bunk-row-${bunk.id}`}>
      <Link
        to={`/camper-care/bunks/${bunk.id}`}
        data-testid={`cc-bunk-link-${bunk.id}`}
        className="block rounded-lg border border-gray-100 dark:border-gray-800 bg-white dark:bg-gray-900 px-3 py-2 hover:border-blue-300 dark:hover:border-blue-700 hover:shadow-sm transition"
      >
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0">
            <p className="font-medium text-sm text-gray-900 dark:text-white truncate">{bunk.name}</p>
            {bunk.counselor_names?.length > 0 && (
              <p className="text-xs text-gray-500 dark:text-gray-400 truncate">
                {bunk.counselor_names.join(' · ')}
              </p>
            )}
          </div>
          <div className="text-xs text-right shrink-0 text-gray-700 dark:text-gray-200">
            <CompletionLabel completion={bunk.completion} />
          </div>
        </div>
        {bunk.badges?.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mt-2">
            {bunk.badges.map((b) => (
              <Badge key={b} kind={b} />
            ))}
          </div>
        )}
      </Link>
    </li>
  );
}

function UnitSection({ unit }) {
  const [open, setOpen] = useState(true);
  return (
    <section
      data-testid={`cc-unit-${unit.id ?? 'unassigned'}`}
      className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 shadow-sm"
    >
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center justify-between gap-2 px-4 py-3 text-left"
        aria-expanded={open}
      >
        <div className="min-w-0">
          <h3 className="font-semibold text-gray-900 dark:text-white">{unit.name}</h3>
          <p className="text-xs text-gray-500 dark:text-gray-400">
            {unit.bunks.length} bunk{unit.bunks.length === 1 ? '' : 's'} ·{' '}
            <CompletionLabel completion={unit.completion} />
          </p>
        </div>
        <span aria-hidden="true" className="text-gray-400 text-sm">{open ? '–' : '+'}</span>
      </button>
      {open && (
        <ul className="px-3 pb-3 space-y-2">
          {unit.bunks.map((b) => (
            <BunkRow key={b.id} bunk={b} />
          ))}
        </ul>
      )}
    </section>
  );
}

function WorkspaceCard({ to, label, count, testid, accent = 'blue' }) {
  const accents = {
    blue: 'border-blue-200 dark:border-blue-800 bg-blue-50 dark:bg-blue-900/30 text-blue-900 dark:text-blue-100',
    red: 'border-red-200 dark:border-red-800 bg-red-50 dark:bg-red-900/30 text-red-900 dark:text-red-100',
    amber: 'border-amber-200 dark:border-amber-800 bg-amber-50 dark:bg-amber-900/30 text-amber-900 dark:text-amber-100',
  };
  return (
    <Link
      to={to}
      data-testid={testid}
      className={`flex items-center justify-between rounded-xl border px-4 py-3 shadow-sm hover:shadow-md transition-shadow ${accents[accent]}`}
    >
      <span className="font-semibold">{label}</span>
      {typeof count === 'number' && count > 0 && (
        <span
          data-testid={`${testid}-count`}
          className="inline-flex items-center justify-center min-w-[1.5rem] h-6 px-2 rounded-full bg-white/70 dark:bg-black/30 text-sm font-semibold"
        >
          {count}
        </span>
      )}
    </Link>
  );
}

function SelfReflectionCard({ section, today }) {
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
  const editTo = (state === 'complete' || state === 'day_off') && section?.reflection_id
    ? `/camper-care/self-reflection/${section.reflection_id}/edit`
    : '/camper-care/self-reflection';
  const hasTemplate = Boolean(section?.template_id);

  return (
    <section
      data-testid="cc-self-reflection"
      data-state={state}
      className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 px-4 py-4 shadow-sm"
    >
      <div className="flex items-center justify-between gap-2 mb-2">
        <h2 className="text-base font-semibold text-gray-900 dark:text-white">My reflection</h2>
        <span
          className={`text-xs font-medium px-2 py-0.5 rounded-full ${badge.cls}`}
          data-testid="cc-self-reflection-state"
        >
          {badge.label}
        </span>
      </div>
      {hasTemplate ? (
        <>
          <p className="text-sm text-gray-700 dark:text-gray-300">
            {state === 'complete' && 'Your reflection for today is in.'}
            {state === 'day_off' && 'Marked as a day off — no further action needed.'}
            {state === 'missing' && `Today is ${today}. Submit your reflection so your team has it.`}
          </p>
          <div className="mt-3 flex items-center gap-3">
            <Link
              to={editTo}
              data-testid="cc-self-reflection-action"
              className="inline-flex items-center justify-center min-h-[44px] px-4 rounded-lg bg-blue-600 text-white text-sm font-medium hover:bg-blue-700"
            >
              {state === 'missing' ? 'Submit reflection' : 'Edit reflection'}
            </Link>
          </div>
        </>
      ) : (
        <p className="text-sm text-gray-500 dark:text-gray-400">
          No Camper Care self-reflection template configured for your program.
        </p>
      )}
    </section>
  );
}

export default function CamperCareDashboard() {
  const [searchParams, setSearchParams] = useSearchParams();
  const dateParam = searchParams.get('date') || '';
  const [data, setData] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const load = useCallback(async ({ silent = false } = {}) => {
    if (!silent) setLoading(true);
    if (silent) setRefreshing(true);
    try {
      const next = await fetchCamperCareDashboard({
        date: dateParam || undefined,
        noCache: silent,
      });
      setData(next);
      setError('');
    } catch (err) {
      const detail = err?.response?.data?.detail;
      setError(typeof detail === 'string' ? detail : err?.message || 'Failed to load dashboard.');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [dateParam]);

  useEffect(() => {
    load();
  }, [load]);

  const isToday = !dateParam || (data && dateParam === data.today);
  useEffect(() => {
    if (!isToday) return undefined;
    const id = setInterval(() => load({ silent: true }), REFRESH_INTERVAL_MS);
    return () => clearInterval(id);
  }, [isToday, load]);

  const handleDateChange = (next) => {
    const params = new URLSearchParams(searchParams);
    if (next) params.set('date', next);
    else params.delete('date');
    setSearchParams(params, { replace: true });
  };

  if (loading && !data) {
    return (
      <div className="px-4 py-6 max-w-lg mx-auto">
        <p className="text-gray-600 dark:text-gray-400">Loading dashboard…</p>
      </div>
    );
  }

  if (error && !data) {
    return (
      <div className="px-4 py-6 max-w-lg mx-auto">
        <div
          role="alert"
          className="rounded-xl border border-amber-200 bg-amber-50 dark:border-amber-900 dark:bg-amber-900/30 px-4 py-3 text-sm text-amber-900 dark:text-amber-100"
          data-testid="cc-dashboard-error"
        >
          {error}
        </div>
      </div>
    );
  }

  const units = data?.units ?? [];
  const summary = data?.summary ?? {};

  return (
    <div data-testid="cc-dashboard" className="px-4 py-6 pb-24 max-w-lg mx-auto space-y-4">
      <header className="space-y-2">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900 dark:text-white">Camper Care</h1>
          <p className="text-sm text-gray-600 dark:text-gray-400">
            Today is {data?.today}
            {refreshing && <span className="text-xs text-gray-400 ml-2">Refreshing…</span>}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <label className="text-sm text-gray-700 dark:text-gray-200 flex items-center gap-2">
            <span>Date:</span>
            <input
              type="date"
              value={dateParam || data?.date || ''}
              max={data?.today || undefined}
              onChange={(e) => handleDateChange(e.target.value)}
              data-testid="cc-dashboard-date"
              className="rounded border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 px-2 py-1 text-sm"
            />
          </label>
        </div>
        <div
          data-testid="cc-dashboard-summary"
          className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 px-4 py-3 text-sm text-gray-800 dark:text-gray-200 shadow-sm"
        >
          <span data-testid="cc-summary-submitted">
            {summary.submitted ?? 0} of {summary.expected ?? 0}
          </span>{' '}
          reflections submitted across your caseload
        </div>
      </header>

      <section className="grid grid-cols-1 gap-2" data-testid="cc-workspaces">
        <WorkspaceCard
          to="/camper-care/flags"
          label="Flagged campers"
          count={summary.flag_count}
          testid="cc-workspace-flags"
          accent="red"
        />
        <WorkspaceCard
          to="/camper-care/orders"
          label="Orders"
          count={summary.order_count}
          testid="cc-workspace-orders"
          accent="amber"
        />
      </section>

      <SelfReflectionCard section={data?.self_reflection} today={data?.today} />

      <section data-testid="cc-caseload">
        <div className="flex items-center justify-between mb-2">
          <h2 className="text-base font-semibold text-gray-900 dark:text-white">My caseload</h2>
          <span className="text-xs text-gray-500 dark:text-gray-400">
            {units.length} unit{units.length === 1 ? '' : 's'}
          </span>
        </div>
        {units.length === 0 ? (
          <p className="text-sm text-gray-600 dark:text-gray-400">
            No bunks on your caseload yet. Once a bunk is assigned to your supervision, it will appear here.
          </p>
        ) : (
          <div className="space-y-3">
            {units.map((u) => (
              <UnitSection key={u.id ?? 'unassigned'} unit={u} />
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
