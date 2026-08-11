/**
 * Madrich (TBE) dashboard — Step 7_14, Stories 61 and 63.
 *
 * Three top-level sections (Story 61 criterion 3):
 *   1. Header — name, role label "Madrich", grade level, active program.
 *   2. My reflections — one card per template the Madrich currently owes
 *      (Story 63), each framed by its own cadence: "Week of [start]-[end]"
 *      for the recurring weekly 3-2-1, "Available to submit" for on-demand
 *      forms. An empty list is the nothing-assigned-yet state.
 *   3. History shortcut.
 *
 * No bunk lists, faculty submissions, peer-Madrich data, or camp-side
 * operational signal per Story 61 criterion 4. Per TBE Tier 1 scope:
 * English only, no LanguagePicker.
 */

import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { fetchDashboard } from '../../api/madrich';
import { useAuth } from '../../auth/AuthContext';

function formatPeriodLabel(cadence, periodStart, periodEnd) {
  if (cadence === 'on_demand') return 'Available to submit';
  if (!periodStart || !periodEnd) return '';
  const start = new Date(`${periodStart}T00:00:00`);
  const end = new Date(`${periodEnd}T00:00:00`);
  if (cadence === 'daily') {
    return start.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
  }
  if (cadence === 'monthly') {
    return start.toLocaleDateString(undefined, { month: 'long', year: 'numeric' });
  }
  const sameMonth = start.getMonth() === end.getMonth();
  const startLabel = start.toLocaleDateString(undefined, {
    month: 'short',
    day: 'numeric',
  });
  const endLabel = sameMonth
    ? end.toLocaleDateString(undefined, { day: 'numeric' })
    : end.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
  const range = `${startLabel}–${endLabel}`;
  return cadence === 'weekly' ? `Week of ${range}` : range;
}

function NoAssignmentsCard() {
  return (
    <section
      aria-label="My reflections"
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

function ReflectionStatusCard({ card }) {
  const {
    template_id, template_name, cadence, state, reflection_id, editable,
  } = card;
  const isComplete = state === 'complete';
  const title = template_name || 'My reflection';
  const periodLabel = formatPeriodLabel(cadence, card.period?.start, card.period?.end);

  const actionPath = editable && reflection_id
    ? `/madrich/reflection/${reflection_id}/edit`
    : `/madrich/reflection/new?template=${template_id}`;

  const statusLabel = isComplete
    ? (cadence === 'weekly' ? 'Submitted for this week' : 'Submitted')
    : 'Not yet submitted';
  const statusClass = isComplete
    ? 'bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-300'
    : 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/40 dark:text-yellow-300';
  const ctaLabel = isComplete ? 'Edit reflection' : 'Start reflection';

  return (
    <section
      aria-label={title}
      className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-4"
      data-testid="md-reflection-card"
    >
      <div className="flex items-center justify-between gap-3 mb-1">
        <h2 className="text-base font-semibold text-gray-900 dark:text-white">
          {title}
        </h2>
        <span
          className={`shrink-0 text-xs font-medium px-2 py-0.5 rounded-full ${statusClass}`}
          data-testid="md-reflection-status"
        >
          {statusLabel}
        </span>
      </div>
      {periodLabel && (
        <p
          className="text-sm text-gray-500 dark:text-gray-400 mb-3"
          data-testid="md-week-label"
        >
          {periodLabel}
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

  const { header, my_reflections, history_entry } = dashboard;
  const cards = Array.isArray(my_reflections) ? my_reflections : [];
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

      {cards.length === 0 ? (
        <NoAssignmentsCard />
      ) : (
        cards.map(card => (
          <ReflectionStatusCard key={card.template_id} card={card} />
        ))
      )}

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
