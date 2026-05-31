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
import { Flag, ClipboardList, Users, Heart } from 'lucide-react';
import { fetchCamperCareDashboard } from '../../api/camperCare';

const REFRESH_INTERVAL_MS = 60_000;

const BADGE_META = {
  cc_flagged: {
    label: 'Flagged',
    className: 'border border-rose-200 bg-rose-50 text-rose-700 dark:border-rose-900 dark:bg-rose-900/30 dark:text-rose-200',
  },
  cc_pending_order: {
    label: 'Pending order',
    className: 'border border-orange-200 bg-orange-50 text-orange-700 dark:border-orange-900 dark:bg-orange-900/30 dark:text-orange-200',
  },
  help_requested: {
    label: 'Help requested',
    className: 'border border-rose-200 bg-rose-50 text-rose-700 dark:border-rose-900 dark:bg-rose-900/30 dark:text-rose-200',
  },
  bunk_concerns: {
    label: 'Bunk concerns',
    className: 'border border-amber-200 bg-amber-50 text-amber-700 dark:border-amber-900 dark:bg-amber-900/30 dark:text-amber-200',
  },
  off_camp: {
    label: 'Off-camp',
    className: 'border border-blue-200 bg-blue-50 text-blue-700 dark:border-blue-900 dark:bg-blue-900/30 dark:text-blue-200',
  },
  low_completion: {
    label: 'Low completion',
    className: 'border border-gray-200 bg-gray-100 text-gray-600 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-200',
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
    <li data-testid={`cc-bunk-row-${bunk.id}`}>
      <Link
        to={`/dashboards/group/${bunk.id}`}
        data-testid={`cc-bunk-link-${bunk.id}`}
        className="block px-5 py-3 hover:bg-gray-50 dark:hover:bg-gray-800/60 transition-colors"
      >
        <div className="flex items-center justify-between gap-3">
          <div className="min-w-0">
            <h3 className="font-semibold text-gray-900 dark:text-white truncate">{bunk.name}</h3>
            {bunk.counselor_names?.length > 0 && (
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5 truncate">
                {bunk.counselor_names.join(', ')}
              </p>
            )}
          </div>
          <div className="flex items-center justify-end gap-3 shrink-0 flex-wrap">
            <span className="text-sm text-gray-700 dark:text-gray-300">
              {completion?.expected === 0 ? (
                <span className="text-gray-400 dark:text-gray-500">—</span>
              ) : (
                `${completion?.submitted ?? 0} of ${completion?.expected ?? 0} submitted`
              )}
            </span>
            {bunk.badges?.length > 0 && bunk.badges.map((b) => <Badge key={b} kind={b} />)}
          </div>
        </div>
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
    >
      <button
        type="button"
        onClick={onToggle}
        className="w-full flex items-center justify-between gap-3 px-5 py-3 text-left hover:bg-gray-50 dark:hover:bg-gray-800/40 transition-colors"
        aria-expanded={open}
        data-testid={`cc-unit-toggle-${unit.id ?? 'unassigned'}`}
      >
        <span className="flex items-center gap-3 min-w-0">
          <span
            aria-hidden="true"
            className="shrink-0 w-6 h-6 rounded-md border border-gray-300 dark:border-gray-600 flex items-center justify-center text-gray-500 dark:text-gray-300 text-base leading-none"
          >
            {open ? '−' : '+'}
          </span>
          <span className="font-semibold text-gray-900 dark:text-white truncate">{unit.name}</span>
        </span>
        <span className="text-xs text-gray-500 dark:text-gray-400 shrink-0 text-right">
          {unit.bunks.length} bunk{unit.bunks.length === 1 ? '' : 's'} ·{' '}
          <CompletionLabel completion={unit.completion} />
        </span>
      </button>
      {open && unit.bunks.length > 0 && (
        <ul className="border-t border-gray-100 dark:border-gray-800 divide-y divide-gray-100 dark:divide-gray-800 bg-gray-50/40 dark:bg-gray-800/20">
          {unit.bunks.map((b) => (
            <BunkRow key={b.id} bunk={b} />
          ))}
        </ul>
      )}
    </section>
  );
}

const WORKSPACE_ACCENTS = {
  red: {
    card: 'border-rose-200 dark:border-rose-900 bg-rose-50 dark:bg-rose-950/30',
    iconWrap: 'bg-rose-100 dark:bg-rose-900/40 text-rose-600 dark:text-rose-300',
    count: 'text-rose-600 dark:text-rose-300',
  },
  amber: {
    card: 'border-amber-200 dark:border-amber-900 bg-amber-50 dark:bg-amber-950/30',
    iconWrap: 'bg-amber-100 dark:bg-amber-900/40 text-amber-700 dark:text-amber-300',
    count: 'text-amber-700 dark:text-amber-300',
  },
};

function WorkspaceCard({ to, label, description, count, testid, accent = 'red', icon: Icon }) {
  const a = WORKSPACE_ACCENTS[accent] || WORKSPACE_ACCENTS.red;
  return (
    <Link
      to={to}
      data-testid={testid}
      className={`flex items-center justify-between gap-3 rounded-xl border px-4 py-4 shadow-sm hover:shadow-md transition-shadow ${a.card}`}
    >
      <span className="flex items-center gap-3 min-w-0">
        <span className={`shrink-0 w-10 h-10 rounded-xl flex items-center justify-center ${a.iconWrap}`}>
          {Icon && <Icon className="w-5 h-5" aria-hidden="true" />}
        </span>
        <span className="min-w-0">
          <span className="block font-semibold text-gray-900 dark:text-white">{label}</span>
          {description && (
            <span className="block text-sm text-gray-600 dark:text-gray-400 mt-0.5">{description}</span>
          )}
        </span>
      </span>
      {typeof count === 'number' && (
        <span
          data-testid={`${testid}-count`}
          className={`shrink-0 text-3xl font-bold leading-none ${a.count}`}
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
      <div className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-[80rem] mx-auto">
        <p className="text-gray-600 dark:text-gray-400">Loading dashboard…</p>
      </div>
    );
  }

  if (error && !data) {
    return (
      <div className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-[80rem] mx-auto">
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
    <div data-testid="cc-dashboard" className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-[80rem] mx-auto">

      {/* Hero header */}
      <div className="mb-8">
        <div className="flex items-center space-x-3 mb-4">
          <div className="w-12 h-12 bg-rose-100 dark:bg-rose-900/30 rounded-xl flex items-center justify-center shrink-0">
            <Heart className="w-7 h-7 text-rose-600 dark:text-rose-400" aria-hidden="true" />
          </div>
          <div>
            <h1 className="text-2xl sm:text-3xl font-bold text-gray-900 dark:text-gray-100">
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
          <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 px-4 py-2.5 shadow-sm">
            <label className="text-sm text-gray-700 dark:text-gray-200 flex items-center gap-2">
              <span className="font-medium">Date:</span>
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
            className="flex items-center gap-3 rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 px-4 py-2.5 text-sm text-gray-800 dark:text-gray-200 shadow-sm"
          >
            <span className="shrink-0 w-8 h-8 rounded-full bg-blue-50 dark:bg-blue-900/30 text-blue-600 dark:text-blue-300 flex items-center justify-center">
              <Users className="w-4 h-4" aria-hidden="true" />
            </span>
            <p>
              <span data-testid="cc-summary-submitted" className="font-semibold text-gray-900 dark:text-white">
                {summary.submitted ?? 0} of {summary.expected ?? 0}
              </span>{' '}
              reflections submitted across your caseload
            </p>
          </div>
        </div>
      </div>

      {/* Two-column content grid */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6 items-start">

        {/* Left — caseload tree (spans 2 of 3 columns on xl) */}
        <section
          data-testid="cc-caseload"
          className="xl:col-span-2 rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 shadow-sm overflow-hidden"
        >
          <div className="px-5 pt-5 pb-3">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">My caseload</h2>
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
              {units.length} unit{units.length === 1 ? '' : 's'} · Today is {data?.today}
            </p>
          </div>
          {units.length === 0 ? (
            <p className="px-5 pb-5 text-sm text-gray-600 dark:text-gray-400">
              No bunks on your caseload yet. Once a bunk is assigned to your supervision, it will appear here.
            </p>
          ) : (
            <div className="border-t border-gray-100 dark:border-gray-800 divide-y divide-gray-100 dark:divide-gray-800">
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
          <WorkspaceCard
            to="/camper-care/flags"
            label="Flagged campers"
            description="View and follow up on campers that need attention."
            count={summary.flag_count}
            testid="cc-workspace-flags"
            accent="red"
            icon={Flag}
          />
          <WorkspaceCard
            to="/camper-care/orders"
            label="Orders"
            description="Review and manage pending and completed orders."
            count={summary.order_count}
            testid="cc-workspace-orders"
            accent="amber"
            icon={ClipboardList}
          />

          <SelfReflectionCard section={data?.self_reflection} today={data?.today} />
        </aside>
      </div>
    </div>
  );
}
