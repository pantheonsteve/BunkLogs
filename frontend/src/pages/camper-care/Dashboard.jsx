/**
 * Camper Care dashboard — Step 7_8, Stories 18-19.
 *
 * Top-of-flow surface for Camper Care. Sections (top to bottom):
 *   1. Header — date picker + caseload-wide submitted-of-expected rollup
 *   2. Workspace entries — Flagged campers, Orders, My reflection
 *   3. Caseload tree — Units expand to Bunks with completion + attention badges
 *
 * Bunk rows link to the per-bunk Camper Care drill-down (Story 18
 * criterion 9). Tapping a bunk navigates to `/dashboards/group/<id>`
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
  const { completion } = bunk;
  return (
    <li
      data-testid={`cc-bunk-row-${bunk.id}`}
      className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 shadow-sm"
    >
      <Link
        to={`/dashboards/group/${bunk.id}`}
        data-testid={`cc-bunk-link-${bunk.id}`}
        className="block px-4 py-3 hover:bg-gray-50 dark:hover:bg-gray-800 rounded-xl"
      >
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <h3 className="font-semibold text-gray-900 dark:text-white truncate">{bunk.name}</h3>
            {bunk.counselor_names?.length > 0 && (
              <p className="text-xs text-gray-600 dark:text-gray-300 mt-1 truncate">
                {bunk.counselor_names.join(' · ')}
              </p>
            )}
          </div>
          <div className="text-right shrink-0">
            <p className="text-sm font-medium text-gray-900 dark:text-white">
              {completion?.expected === 0 ? (
                <span className="text-gray-400 dark:text-gray-500">—</span>
              ) : (
                `${completion?.submitted ?? 0} of ${completion?.expected ?? 0} submitted`
              )}
            </p>
            {completion?.off_camp > 0 && (
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                {completion.off_camp} off-camp
              </p>
            )}
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

const UNIT_COLLAPSE_KEY = 'cc.dashboard.collapsedUnits';

function readCollapsedUnits() {
  try {
    const raw = window.sessionStorage.getItem(UNIT_COLLAPSE_KEY);
    if (!raw) return new Set();
    const parsed = JSON.parse(raw);
    return new Set(Array.isArray(parsed) ? parsed.map(String) : []);
  } catch {
    return new Set();
  }
}

function persistCollapsedUnits(setLike) {
  try {
    window.sessionStorage.setItem(
      UNIT_COLLAPSE_KEY, JSON.stringify(Array.from(setLike)),
    );
  } catch {
    /* sessionStorage unavailable (private mode etc.) — silently noop */
  }
}

function UnitSection({ unit, collapsed, onToggle }) {
  const open = !collapsed;
  return (
    <section
      data-testid={`cc-unit-${unit.id ?? 'unassigned'}`}
      data-collapsed={collapsed ? 'true' : 'false'}
      className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 shadow-sm"
    >
      <button
        type="button"
        onClick={onToggle}
        className="w-full flex items-center justify-between gap-2 px-4 py-3 text-left"
        aria-expanded={open}
        data-testid={`cc-unit-toggle-${unit.id ?? 'unassigned'}`}
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
  const [collapsedUnits, setCollapsedUnits] = useState(() => readCollapsedUnits());

  const toggleUnit = useCallback((unitId) => {
    setCollapsedUnits((prev) => {
      const key = String(unitId ?? 'unassigned');
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      persistCollapsedUnits(next);
      return next;
    });
  }, []);

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
    <div data-testid="cc-dashboard" className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-[96rem] mx-auto">

      {/* Hero header */}
      <div className="mb-8">
        <div className="flex items-center space-x-3 mb-4">
          <div className="w-10 h-10 bg-rose-100 dark:bg-rose-900/30 rounded-xl flex items-center justify-center shrink-0">
            <svg className="w-6 h-6 text-rose-600 dark:text-rose-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" />
            </svg>
          </div>
          <div>
            <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100">
              Camper Care Dashboard
            </h1>
            <p className="text-gray-600 dark:text-gray-400">
              Monitor and support camper wellbeing
              {refreshing && <span className="text-xs text-gray-400 ml-2">Refreshing…</span>}
            </p>
          </div>
        </div>

        {/* Date + summary row */}
        <div className="flex flex-wrap items-center gap-4">
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
          <div
            data-testid="cc-dashboard-summary"
            className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 px-4 py-2 text-sm text-gray-800 dark:text-gray-200 shadow-sm"
          >
            <span data-testid="cc-summary-submitted">
              {summary.submitted ?? 0} of {summary.expected ?? 0}
            </span>{' '}
            reflections submitted across your caseload
          </div>
        </div>
      </div>

      {/* Two-column content grid */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">

        {/* Left — caseload tree (spans 2 of 3 columns on xl) */}
        <section data-testid="cc-caseload" className="xl:col-span-2">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">My caseload</h2>
            <span className="text-xs text-gray-500 dark:text-gray-400">
              {units.length} unit{units.length === 1 ? '' : 's'} · Today is {data?.today}
            </span>
          </div>
          {units.length === 0 ? (
            <p className="text-sm text-gray-600 dark:text-gray-400">
              No bunks on your caseload yet. Once a bunk is assigned to your supervision, it will appear here.
            </p>
          ) : (
            <div className="space-y-3">
              {units.map((u) => {
                const key = String(u.id ?? 'unassigned');
                return (
                  <UnitSection
                    key={key}
                    unit={u}
                    collapsed={collapsedUnits.has(key)}
                    onToggle={() => toggleUnit(u.id)}
                  />
                );
              })}
            </div>
          )}
        </section>

        {/* Right — workspace cards + self-reflection */}
        <aside className="space-y-4">
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
        </aside>
      </div>
    </div>
  );
}
