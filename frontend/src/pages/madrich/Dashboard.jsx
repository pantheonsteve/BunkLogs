/**
 * Madrich (TBE) dashboard — Step 7_14, Story 61.
 *
 * Three top-level sections (criterion 3) with weekly cadence framing
 * per criterion 5:
 *   1. Header — name, role label "Madrich", grade level, active program.
 *   2. My reflection — current week card (Week of [start]-[end]) with
 *      "Not yet started" / "Submitted for this week" state.
 *   3. My reflections — history shortcut.
 *
 * No bunk lists, faculty submissions, peer-Madrich data, or camp-side
 * operational signal per criterion 4. Per TBE Tier 1 scope: English
 * only, no LanguagePicker.
 */

import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { fetchDashboard } from '../../api/madrich';
import { useAuth } from '../../auth/AuthContext';

function formatWeekRange(periodStart, periodEnd) {
  if (!periodStart || !periodEnd) return '';
  const start = new Date(`${periodStart}T00:00:00`);
  const end = new Date(`${periodEnd}T00:00:00`);
  const sameMonth = start.getMonth() === end.getMonth();
  const startLabel = start.toLocaleDateString(undefined, {
    month: 'short',
    day: 'numeric',
  });
  const endLabel = sameMonth
    ? end.toLocaleDateString(undefined, { day: 'numeric' })
    : end.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
  return `Week of ${startLabel}–${endLabel}`;
}

function ReflectionStatusCard({ myReflection, weekLabel }) {
  if (!myReflection) return null;
  const { state, reflection_id, editable } = myReflection;

  if (state === 'no_template') {
    return (
      <section
        aria-label="My reflection"
        className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-4"
        data-testid="md-reflection-card"
      >
        <h2 className="text-base font-semibold text-gray-900 dark:text-white mb-1">
          My reflection
        </h2>
        <p className="text-sm text-gray-500 dark:text-gray-400">
          No reflections currently assigned. Your Director will set this up shortly.
        </p>
      </section>
    );
  }

  const isComplete = state === 'complete';
  const actionPath = editable && reflection_id
    ? `/madrich/reflection/${reflection_id}/edit`
    : '/madrich/reflection/new';

  const statusLabel = isComplete ? 'Submitted for this week' : 'Not yet submitted';
  const statusClass = isComplete
    ? 'bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-300'
    : 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/40 dark:text-yellow-300';
  const ctaLabel = isComplete ? 'Edit reflection' : 'Start reflection';

  return (
    <section
      aria-label="My reflection"
      className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-4"
      data-testid="md-reflection-card"
    >
      <div className="flex items-center justify-between mb-1">
        <h2 className="text-base font-semibold text-gray-900 dark:text-white">
          My reflection
        </h2>
        <span
          className={`text-xs font-medium px-2 py-0.5 rounded-full ${statusClass}`}
          data-testid="md-reflection-status"
        >
          {statusLabel}
        </span>
      </div>
      {weekLabel && (
        <p
          className="text-sm text-gray-500 dark:text-gray-400 mb-3"
          data-testid="md-week-label"
        >
          {weekLabel}
        </p>
      )}
      <Link
        to={actionPath}
        className="mt-2 inline-block rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium px-4 py-2 transition-colors"
        data-testid="md-reflection-cta"
      >
        {ctaLabel}
      </Link>
    </section>
  );
}

export default function MadrichDashboard() {
  const { orgSlug } = useAuth();
  const [dashboard, setDashboard] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await fetchDashboard(orgSlug);
      setDashboard(data);
      setError(null);
    } catch {
      setError('Could not load dashboard.');
    } finally {
      setLoading(false);
    }
  }, [orgSlug]);

  useEffect(() => {
    load();
  }, [load]);

  if (loading) {
    return (
      <div className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-[96rem] mx-auto" data-testid="md-loading">
        <p className="text-gray-500 dark:text-gray-400">Loading…</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-[96rem] mx-auto" data-testid="md-error">
        <p className="text-red-600 dark:text-red-400">{error}</p>
        <button
          onClick={load}
          className="mt-3 text-sm text-indigo-600 dark:text-indigo-400 underline"
        >
          Retry
        </button>
      </div>
    );
  }

  const { header, my_reflection, history_entry, period } = dashboard;
  const weekLabel = formatWeekRange(period?.start, period?.end);
  const gradeLevel = header?.grade_level;

  return (
    <div className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-[96rem] mx-auto space-y-4">
      <div>
        <p className="text-sm text-gray-500 dark:text-gray-400">{header.program_name}</p>
        <h1 className="text-xl font-bold text-gray-900 dark:text-white">{header.name}</h1>
        <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
          Madrich{typeof gradeLevel === 'number' ? ` · Grade ${gradeLevel}` : ''}
        </p>
      </div>

      <ReflectionStatusCard myReflection={my_reflection} weekLabel={weekLabel} />

      <section
        aria-label="My reflections"
        className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-4"
        data-testid="md-history-section"
      >
        <div className="flex items-center justify-between">
          <h2 className="text-base font-semibold text-gray-900 dark:text-white">
            My reflections
          </h2>
          <Link
            to={history_entry?.url ?? '/madrich/history'}
            className="text-sm text-indigo-600 dark:text-indigo-400 hover:underline"
            data-testid="md-history-link"
          >
            View history →
          </Link>
        </div>
      </section>
    </div>
  );
}
