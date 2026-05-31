/**
 * Counselor dashboard — Step 7_6d (Stories 2 + 9).
 *
 * Renders the three-section payload from
 * `GET /api/v1/counselor/dashboard/`:
 *
 *   1. Camper reflections — covered / total, off-camp count, deep link
 *      into the roster page.
 *   2. Self-reflection — submitted/missing state, day-off badge, edit
 *      link.
 *   3. Open requests — combined camper-care + maintenance count from
 *      the viewer + co-counselors (decision C4).
 *
 * "All set" banner appears when the first two sections are complete.
 * The Requests section never blocks all-set (Story 9 criterion 2).
 *
 * Layout: mobile-first single column (matches the approved mockup);
 * on desktop the three task cards lay out as an equal-height 3-up grid
 * in the shared dashboard design language (rounded-xl cards, shadow-sm,
 * uppercase context line + large date header) used by the Bunk/Unit
 * dashboards.
 *
 * Auto-refresh on a 60-second interval so co-counselor submissions
 * surface without a manual reload (matches dashboard cache TTL of 30s
 * with one round-trip of buffer).
 */

import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { CheckCircle } from 'lucide-react';
import { fetchCounselorDashboard } from '../../api/counselor';

const REFRESH_INTERVAL_MS = 60_000;

function SectionCard({ title, state, children, actionLabel, actionTo, dataTestid }) {
  const stateBadge = (() => {
    switch (state) {
      case 'complete':
        return { label: 'Done', className: 'border border-green-200 dark:border-green-900 bg-green-50 text-green-700 dark:bg-green-900/30 dark:text-green-300' };
      case 'in_progress':
        return { label: 'In progress', className: 'border border-amber-200 dark:border-amber-900 bg-amber-50 text-amber-800 dark:bg-amber-900/30 dark:text-amber-300' };
      case 'none':
      default:
        return { label: 'Not started', className: 'border border-gray-200 dark:border-gray-700 bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-300' };
    }
  })();

  return (
    <section
      data-testid={dataTestid}
      data-state={state}
      className="flex flex-col h-full rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-5 shadow-sm"
    >
      <div className="flex items-start justify-between gap-2 mb-2">
        <h2 className="text-base font-semibold text-gray-900 dark:text-white">{title}</h2>
        <span
          className={`shrink-0 text-xs font-semibold px-2 py-0.5 rounded-full ${stateBadge.className}`}
          data-testid={`${dataTestid}-state`}
        >
          {stateBadge.label}
        </span>
      </div>
      <div className="text-sm text-gray-700 dark:text-gray-300">{children}</div>
      {actionTo ? (
        <div className="mt-auto pt-4">
          <Link
            to={actionTo}
            data-testid={`${dataTestid}-action`}
            className="inline-flex items-center justify-center min-h-[44px] px-4 rounded-lg bg-blue-600 text-white text-sm font-medium hover:bg-blue-700 transition-colors"
          >
            {actionLabel}
          </Link>
        </div>
      ) : null}
    </section>
  );
}

function CamperSection({ section }) {
  const { covered = 0, total = 0, off_camp: offCamp = 0, state } = section || {};
  const remaining = Math.max(total - covered, 0);

  let summary;
  if (total === 0) {
    summary = (
      <p className="text-gray-600 dark:text-gray-400">
        No campers on roster today.
      </p>
    );
  } else if (state === 'complete') {
    summary = (
      <p>
        All <span className="font-medium">{total}</span> campers covered.
      </p>
    );
  } else {
    summary = (
      <p>
        <span className="font-medium">{remaining}</span> camper{remaining === 1 ? '' : 's'} still need{remaining === 1 ? 's' : ''} a reflection.
        {' '}
        <span className="text-gray-500 dark:text-gray-400">
          ({covered}/{total})
        </span>
      </p>
    );
  }

  return (
    <SectionCard
      title="Camper reflections"
      state={state}
      actionLabel={state === 'complete' ? 'Review' : 'Start reflections'}
      actionTo="/counselor/camper-reflections"
      dataTestid="counselor-section-campers"
    >
      {summary}
      {offCamp > 0 ? (
        <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
          {offCamp} camper{offCamp === 1 ? '' : 's'} off-camp today (not counted).
        </p>
      ) : null}
    </SectionCard>
  );
}

function SelfSection({ section }) {
  const { state, submitted, is_day_off: isDayOff, template, reflection_id: reflectionId } = section || {};
  let summary;
  let actionLabel;
  let actionTo;
  if (template === null) {
    summary = (
      <p className="text-gray-600 dark:text-gray-400">
        No self-reflection template is configured for your role.
      </p>
    );
  } else if (state === 'complete') {
    summary = isDayOff ? (
      <p>Day off recorded — nothing else to do here.</p>
    ) : (
      <p>Your self-reflection is in.</p>
    );
    if (reflectionId) {
      actionLabel = 'Edit';
      actionTo = `/counselor/self-reflection/${reflectionId}/edit`;
    }
  } else {
    summary = <p>You haven&apos;t submitted your self-reflection yet.</p>;
    actionLabel = 'Open self-reflection';
    actionTo = '/counselor/self-reflection';
  }

  return (
    <SectionCard
      title="My self-reflection"
      state={state}
      actionLabel={actionLabel}
      actionTo={actionTo}
      dataTestid="counselor-section-self"
    >
      {summary}
    </SectionCard>
  );
}

function RequestsSection({ section }) {
  const { open_count: openCount = 0, by_type: byType = {}, state } = section || {};
  const camperCare = byType.camper_care || 0;
  const maintenance = byType.maintenance || 0;

  const summary = openCount === 0 ? (
    <p className="text-gray-600 dark:text-gray-400">
      No open requests on your bunks right now.
    </p>
  ) : (
    <p>
      <span className="font-medium">{openCount}</span> open request{openCount === 1 ? '' : 's'} — {camperCare} camper care, {maintenance} maintenance.
    </p>
  );

  return (
    <SectionCard
      title="Open requests"
      state={state}
      actionLabel="View requests"
      actionTo="/counselor/requests"
      dataTestid="counselor-section-requests"
    >
      {summary}
    </SectionCard>
  );
}

export default function CounselorMobileDashboard() {
  const [data, setData] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const load = useCallback(async ({ background = false } = {}) => {
    if (background) {
      setRefreshing(true);
    } else {
      setLoading(true);
    }
    setError('');
    try {
      const payload = await fetchCounselorDashboard({ noCache: background });
      setData(payload);
    } catch (err) {
      const detail = err?.response?.data?.detail;
      const status = err?.response?.status;
      if (status === 403) {
        setError(typeof detail === 'string' ? detail : 'You do not have access to the counselor dashboard.');
      } else {
        setError(typeof detail === 'string' ? detail : 'Could not load your dashboard.');
      }
    } finally {
      if (background) {
        setRefreshing(false);
      } else {
        setLoading(false);
      }
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    if (!data) return undefined;
    const id = setInterval(() => {
      load({ background: true });
    }, REFRESH_INTERVAL_MS);
    return () => clearInterval(id);
  }, [data, load]);

  if (loading) {
    return (
      <div className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-[96rem] mx-auto" data-testid="counselor-dashboard-loading">
        <p className="text-gray-600 dark:text-gray-400">Loading your dashboard…</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-[96rem] mx-auto">
        <div
          className="rounded-lg border border-amber-200 bg-amber-50 dark:bg-amber-950/40 dark:border-amber-800 px-4 py-3 text-sm text-amber-900 dark:text-amber-100"
          role="alert"
          data-testid="counselor-dashboard-error"
        >
          {error}
        </div>
      </div>
    );
  }

  if (!data) return null;

  const { today, all_set: allSet, sections, program } = data;
  const camperSection = sections?.camper_reflections;
  const selfSection = sections?.self_reflection;
  const requestsSection = sections?.requests;

  return (
    <div className="px-4 sm:px-6 lg:px-8 py-8 pb-24 w-full max-w-[80rem] mx-auto space-y-5">
        <header>
          <p className="text-xs font-medium uppercase tracking-wide text-gray-500 dark:text-gray-400">
            {program?.name ? `${program.name} · ` : ''}Today
          </p>
          <h1 className="text-2xl sm:text-3xl font-semibold text-gray-900 dark:text-white">
            {today}
          </h1>
          {refreshing ? (
            <p
              className="text-xs text-gray-400 dark:text-gray-500 mt-1"
              data-testid="counselor-dashboard-refreshing"
            >
              Refreshing…
            </p>
          ) : null}
        </header>

        {allSet ? (
          <div
            className="flex items-start gap-3 rounded-xl border border-green-200 bg-green-50 dark:bg-green-950/40 dark:border-green-800 px-4 py-3"
            data-testid="counselor-all-set"
            role="status"
          >
            <CheckCircle className="h-5 w-5 shrink-0 text-green-600 dark:text-green-400 mt-0.5" aria-hidden="true" />
            <div>
              <p className="text-sm font-medium text-green-900 dark:text-green-100">
                You&apos;re all set for today — nice work.
              </p>
              <p className="text-xs text-green-800 dark:text-green-200 mt-1">
                Edits stay open until the day rolls over.
              </p>
            </div>
          </div>
        ) : null}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 sm:gap-5 items-stretch">
          <CamperSection section={camperSection} />
          <SelfSection section={selfSection} />
          <RequestsSection section={requestsSection} />
        </div>
    </div>
  );
}
