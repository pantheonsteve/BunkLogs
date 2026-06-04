/**
 * Counselor home dashboard at `/counselor`.
 *
 * Renders viewer context, a date picker (defaults to org "today"), bunk
 * tiles for groups the counselor authors (with form-assignment progress),
 * self-reflection status, quick actions (requests + observations), and
 * the all-set banner when camper + self work is complete.
 */

import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import {
  CheckCircle,
  ClipboardList,
  ClipboardCheck,
  Home,
  MessageSquarePlus,
  Users,
  Wrench,
  HeartHandshake,
} from 'lucide-react';
import { fetchCounselorDashboard } from '../../api/counselor';

const REFRESH_INTERVAL_MS = 60_000;

const STATE_BADGE = {
  complete: {
    label: 'Done',
    className:
      'border border-green-200 dark:border-green-900 bg-green-50 text-green-700 dark:bg-green-900/30 dark:text-green-300',
  },
  in_progress: {
    label: 'In progress',
    className:
      'border border-amber-200 dark:border-amber-900 bg-amber-50 text-amber-800 dark:bg-amber-900/30 dark:text-amber-300',
  },
  none: {
    label: 'Not started',
    className:
      'border border-gray-200 dark:border-gray-700 bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-300',
  },
};

function formatDisplayDate(iso) {
  if (!iso) return '';
  const parsed = new Date(`${iso}T00:00:00`);
  if (Number.isNaN(parsed.getTime())) return iso;
  return parsed.toLocaleDateString(undefined, {
    weekday: 'long',
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  });
}

function titleCaseRole(role) {
  if (!role) return '';
  return role.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}

function AssignmentRow({ assignment }) {
  const badge = STATE_BADGE[assignment.state] || STATE_BADGE.none;
  return (
    <div
      className="rounded-lg border border-gray-100 dark:border-gray-800 bg-gray-50/80 dark:bg-gray-800/40 px-3 py-2.5"
      data-testid={`bunk-assignment-${assignment.template_id}`}
      data-state={assignment.state}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="text-sm font-medium text-gray-900 dark:text-white truncate">
            {assignment.template_name}
          </p>
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
            {assignment.due_label}
            {assignment.total > 0 && assignment.cadence === 'daily' ? (
              <span className="text-gray-400 dark:text-gray-500">
                {' '}
                · {assignment.covered}/{assignment.total}
              </span>
            ) : null}
          </p>
        </div>
        <span
          className={`shrink-0 text-[10px] font-semibold px-2 py-0.5 rounded-full ${badge.className}`}
        >
          {badge.label}
        </span>
      </div>
      {assignment.action_path ? (
        <Link
          to={assignment.action_path}
          className="mt-2 inline-flex items-center justify-center min-h-[36px] px-3 rounded-md bg-blue-600 text-white text-xs font-medium hover:bg-blue-700 transition-colors"
          data-testid={`bunk-assignment-action-${assignment.template_id}`}
        >
          {assignment.state === 'complete' ? 'Review' : 'Complete assignment'}
        </Link>
      ) : null}
    </div>
  );
}

function BunkTile({ bunk }) {
  const complete =
    bunk.assignments?.length > 0
    && bunk.assignments.every((a) => a.state === 'complete');

  return (
    <article
      data-testid={`counselor-bunk-tile-${bunk.id}`}
      className={[
        'flex flex-col rounded-2xl border shadow-sm overflow-hidden transition-shadow hover:shadow-md',
        complete
          ? 'border-emerald-200 dark:border-emerald-800 bg-gradient-to-br from-emerald-50/80 to-white dark:from-emerald-950/30 dark:to-gray-900'
          : 'border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900',
      ].join(' ')}
    >
      <div className="h-1.5 bg-gradient-to-r from-emerald-500 via-blue-500 to-indigo-500" aria-hidden="true" />
      <div className="p-5 flex flex-col gap-4 flex-1">
        <div className="flex items-start gap-3">
          <div className="shrink-0 w-10 h-10 rounded-xl bg-white dark:bg-gray-800 border border-gray-100 dark:border-gray-700 shadow-sm flex items-center justify-center">
            <Home className="w-5 h-5 text-emerald-600 dark:text-emerald-400" aria-hidden="true" />
          </div>
          <div className="min-w-0 flex-1">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white truncate">
              {bunk.name}
            </h2>
            {bunk.unit_name ? (
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">{bunk.unit_name}</p>
            ) : null}
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1 flex items-center gap-1">
              <Users className="w-3 h-3" aria-hidden="true" />
              {bunk.camper_count} camper{bunk.camper_count === 1 ? '' : 's'}
              {bunk.off_camp_count > 0 ? (
                <span> · {bunk.off_camp_count} off-camp</span>
              ) : null}
            </p>
            {bunk.co_counselor_names?.length > 0 ? (
              <p className="text-xs text-gray-400 dark:text-gray-500 mt-1 truncate">
                Co-counselor{bunk.co_counselor_names.length === 1 ? '' : 's'}:{' '}
                {bunk.co_counselor_names.join(', ')}
              </p>
            ) : null}
          </div>
          {complete ? (
            <span className="shrink-0 text-[10px] font-bold uppercase tracking-wide text-emerald-700 dark:text-emerald-300 bg-emerald-100/90 dark:bg-emerald-900/50 px-2 py-1 rounded-full">
              Complete
            </span>
          ) : null}
        </div>

        {bunk.assignments?.length > 0 ? (
          <div className="space-y-2">
            {bunk.assignments.map((assignment) => (
              <AssignmentRow key={assignment.template_id} assignment={assignment} />
            ))}
          </div>
        ) : (
          <p className="text-sm text-gray-500 dark:text-gray-400">
            No form assignments for this bunk on the selected date.
          </p>
        )}

        <div className="mt-auto pt-1">
          <Link
            to={bunk.dashboard_path}
            className="text-sm font-medium text-blue-700 dark:text-blue-300 hover:underline"
            data-testid={`counselor-bunk-dashboard-${bunk.id}`}
          >
            Open bunk dashboard →
          </Link>
        </div>
      </div>
    </article>
  );
}

function SelfReflectionCard({ section, isToday, selectedDateLabel }) {
  const { state, submitted, is_day_off: isDayOff, template, reflection_id: reflectionId } =
    section || {};
  const badge = STATE_BADGE[state === 'complete' ? 'complete' : 'none'];

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
      <p>Day off recorded for {isToday ? 'today' : selectedDateLabel}.</p>
    ) : (
      <p>
        Your self-reflection is in for {isToday ? 'today' : selectedDateLabel}.
      </p>
    );
    actionLabel = 'Edit reflection';
    actionTo = reflectionId
      ? `/counselor/self-reflection/${reflectionId}/edit`
      : '/counselor/self-reflection';
  } else {
    summary = (
      <p>
        You haven&apos;t submitted your self-reflection for{' '}
        {isToday ? 'today' : selectedDateLabel} yet.
      </p>
    );
    actionLabel = 'Open self-reflection';
    actionTo = '/counselor/self-reflection';
  }

  return (
    <section
      data-testid="counselor-section-self"
      data-state={state}
      className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-5 shadow-sm"
    >
      <div className="flex items-start justify-between gap-2 mb-2">
        <h2 className="text-base font-semibold text-gray-900 dark:text-white">
          My self-reflection
        </h2>
        {template !== null ? (
          <span
            className={`shrink-0 text-xs font-semibold px-2 py-0.5 rounded-full ${badge.className}`}
            data-testid="counselor-section-self-state"
          >
            {badge.label}
          </span>
        ) : null}
      </div>
      <div className="text-sm text-gray-700 dark:text-gray-300">{summary}</div>
      {actionTo && template !== null ? (
        <div className="mt-4 flex flex-wrap items-center gap-3">
          <Link
            to={actionTo}
            data-testid="counselor-section-self-action"
            className="inline-flex items-center justify-center min-h-[44px] px-4 rounded-lg bg-blue-600 text-white text-sm font-medium hover:bg-blue-700 transition-colors"
          >
            {actionLabel}
          </Link>
          <Link
            to="/counselor/self-reflection/history"
            className="text-sm font-medium text-blue-700 dark:text-blue-300 hover:underline"
          >
            View history
          </Link>
        </div>
      ) : null}
    </section>
  );
}

function QuickActionButton({ to, icon: Icon, label, sublabel, testid, badge }) {
  return (
    <Link
      to={to}
      data-testid={testid}
      className="relative flex flex-col items-center justify-center gap-2 rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-4 shadow-sm hover:shadow-md hover:border-blue-200 dark:hover:border-blue-800 transition-all min-h-[108px] text-center"
    >
      {badge ? (
        <span className="absolute top-2 right-2 text-xs font-bold rounded-full bg-amber-100 text-amber-800 dark:bg-amber-900/50 dark:text-amber-200 px-2 py-0.5">
          {badge}
        </span>
      ) : null}
      <Icon className="w-6 h-6 text-blue-600 dark:text-blue-400" aria-hidden="true" />
      <span className="text-sm font-semibold text-gray-900 dark:text-white">{label}</span>
      {sublabel ? (
        <span className="text-[11px] text-gray-500 dark:text-gray-400 leading-tight">{sublabel}</span>
      ) : null}
    </Link>
  );
}

export default function CounselorMobileDashboard() {
  const [searchParams, setSearchParams] = useSearchParams();
  const dateParam = searchParams.get('date') || '';

  const [data, setData] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const load = useCallback(
    async ({ background = false } = {}) => {
      if (background) {
        setRefreshing(true);
      } else {
        setLoading(true);
      }
      setError('');
      try {
        const payload = await fetchCounselorDashboard({
          noCache: background,
          date: dateParam || undefined,
        });
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
    },
    [dateParam],
  );

  useEffect(() => {
    load();
  }, [load]);

  const isToday = data?.is_today ?? true;

  useEffect(() => {
    if (!data || !isToday) return undefined;
    const id = setInterval(() => {
      load({ background: true });
    }, REFRESH_INTERVAL_MS);
    return () => clearInterval(id);
  }, [data, isToday, load]);

  const selectedDateIso = data?.selected_date || dateParam || data?.today || '';
  const selectedDateLabel = useMemo(
    () => formatDisplayDate(selectedDateIso),
    [selectedDateIso],
  );

  const handleDateChange = (next) => {
    const params = new URLSearchParams(searchParams);
    if (next) params.set('date', next);
    else params.delete('date');
    setSearchParams(params, { replace: true });
  };

  const maxDate = data?.today || '';

  if (loading) {
    return (
      <div
        className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-[96rem] mx-auto"
        data-testid="counselor-dashboard-loading"
      >
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

  const { viewer, all_set: allSet, sections, program, bunks = [] } = data;
  const selfSection = sections?.self_reflection;
  const requestsSection = sections?.requests;
  const openCount = requestsSection?.open_count ?? 0;

  return (
    <div className="px-4 sm:px-6 lg:px-8 py-8 pb-24 w-full max-w-[80rem] mx-auto space-y-6">
      <header className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <p className="text-xs font-medium uppercase tracking-wide text-gray-500 dark:text-gray-400">
            {program?.name || 'Counselor home'}
          </p>
          <h1 className="text-2xl sm:text-3xl font-semibold text-gray-900 dark:text-white mt-0.5">
            {viewer?.full_name || viewer?.name || 'Welcome'}
          </h1>
          <p className="text-sm text-gray-600 dark:text-gray-300 mt-1">
            {titleCaseRole(viewer?.role)}
            {selectedDateLabel ? (
              <>
                {' '}
                · {isToday ? 'Today' : 'Viewing'}: {selectedDateLabel}
              </>
            ) : null}
          </p>
          {refreshing ? (
            <p
              className="text-xs text-gray-400 dark:text-gray-500 mt-1"
              data-testid="counselor-dashboard-refreshing"
            >
              Refreshing…
            </p>
          ) : null}
        </div>
        <label className="flex flex-col gap-1 text-sm text-gray-700 dark:text-gray-300 shrink-0">
          <span className="font-medium">Date</span>
          <input
            type="date"
            value={selectedDateIso}
            max={maxDate}
            onChange={(e) => handleDateChange(e.target.value)}
            className="rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm min-w-[11rem]"
            data-testid="counselor-date-picker"
          />
        </label>
      </header>

      {allSet && isToday ? (
        <div
          className="flex items-start gap-3 rounded-xl border border-green-200 bg-green-50 dark:bg-green-950/40 dark:border-green-800 px-4 py-3"
          data-testid="counselor-all-set"
          role="status"
        >
          <CheckCircle
            className="h-5 w-5 shrink-0 text-green-600 dark:text-green-400 mt-0.5"
            aria-hidden="true"
          />
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

      <section data-testid="counselor-bunks-section">
        <div className="flex items-baseline justify-between mb-3">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">My bunks</h2>
          <span className="text-sm text-gray-500 dark:text-gray-400">
            {bunks.length} bunk{bunks.length === 1 ? '' : 's'}
          </span>
        </div>
        {bunks.length === 0 ? (
          <p className="text-sm text-gray-600 dark:text-gray-400 rounded-xl border border-dashed border-gray-200 dark:border-gray-700 px-4 py-6 text-center">
            You&apos;re not assigned as an author on any bunk yet. Once your camp
            assigns you to a group, it will appear here.
          </p>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 sm:gap-5">
            {bunks.map((bunk) => (
              <BunkTile key={bunk.id} bunk={bunk} />
            ))}
          </div>
        )}
      </section>

      <SelfReflectionCard
        section={selfSection}
        isToday={isToday}
        selectedDateLabel={selectedDateLabel}
      />

      <section data-testid="counselor-work-links" className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <Link
          to="/tasks"
          data-testid="counselor-action-tasks"
          className="flex items-center gap-4 rounded-xl border border-indigo-200 dark:border-indigo-800 bg-gradient-to-r from-indigo-50/80 to-white dark:from-indigo-950/40 dark:to-gray-900 px-5 py-4 shadow-sm hover:shadow-md transition-all"
        >
          <ClipboardList className="w-8 h-8 text-indigo-600 dark:text-indigo-400 shrink-0" aria-hidden="true" />
          <div>
            <p className="text-base font-semibold text-gray-900 dark:text-white">My Tasks</p>
            <p className="text-sm text-gray-600 dark:text-gray-300">Today&apos;s reflection assignments</p>
          </div>
        </Link>
        <Link
          to="/my-reflections"
          data-testid="counselor-action-my-reflections"
          className="flex items-center gap-4 rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 px-5 py-4 shadow-sm hover:shadow-md hover:border-indigo-200 dark:hover:border-indigo-800 transition-all"
        >
          <ClipboardCheck className="w-8 h-8 text-emerald-600 dark:text-emerald-400 shrink-0" aria-hidden="true" />
          <div>
            <p className="text-base font-semibold text-gray-900 dark:text-white">My Reflections</p>
            <p className="text-sm text-gray-600 dark:text-gray-300">History and streaks</p>
          </div>
        </Link>
      </section>

      <section data-testid="counselor-quick-actions">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-3">
          Requests & observations
        </h2>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
          <QuickActionButton
            to="/counselor/requests/camper-care/new"
            icon={HeartHandshake}
            label="Camper care"
            sublabel="Submit a request"
            testid="counselor-action-camper-care"
          />
          <QuickActionButton
            to="/counselor/requests/maintenance/new"
            icon={Wrench}
            label="Maintenance"
            sublabel="Report an issue"
            testid="counselor-action-maintenance"
          />
          <QuickActionButton
            to="/counselor/requests"
            icon={ClipboardList}
            label="My requests"
            sublabel={openCount ? `${openCount} open` : 'View progress'}
            testid="counselor-action-requests"
            badge={openCount > 0 ? openCount : null}
          />
          <QuickActionButton
            to="/observations"
            icon={MessageSquarePlus}
            label="Observation"
            sublabel="Note about a camper"
            testid="counselor-action-observation"
          />
        </div>
      </section>
    </div>
  );
}
