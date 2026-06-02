/**
 * Leadership Team dashboard — Step 7_12, Story 45.
 *
 * Per-team cards (one per ROLE_IN_PROGRAM supervision the LT viewer
 * holds), a bunks-and-units summary entry, the LT's own self-reflection
 * card, and a templates-and-assignments preview.
 *
 * Each team card is rendered from the dashboard payload returned by the
 * backend; if the call fails altogether the page surfaces a retry CTA.
 * Card-level retry is unnecessary here because the backend batches
 * everything into a single request — keeps the surface simple.
 */

import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { fetchDashboard } from '../../api/leadershipTeam';
import { useAuth } from '../../auth/AuthContext';

const REFRESH_INTERVAL_MS = 60_000;

const BADGE_META = {
  low_completion: {
    label: 'Low completion',
    className: 'bg-gray-200 text-gray-800 dark:bg-gray-700 dark:text-gray-100',
  },
  concerning_ratings: {
    label: 'Concerning ratings',
    className: 'bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-200',
  },
  sensitive_content: {
    label: 'Sensitive notes',
    className: 'bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-200',
  },
};

function Badge({ kind }) {
  const meta = BADGE_META[kind] || {
    label: kind,
    className: 'bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-200',
  };
  return (
    <span
      data-testid={`lt-badge-${kind}`}
      className={`text-xs font-medium px-2 py-0.5 rounded-full ${meta.className}`}
    >
      {meta.label}
    </span>
  );
}

function TeamCard({ card }) {
  const { team_role, team_role_label, member_count, completion, co_supervisors, badges } = card;
  return (
    <li
      data-testid={`lt-team-card-${team_role}`}
      className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 shadow-sm"
    >
      <Link
        to={`/leadership-team/teams/${team_role}`}
        className="block px-4 py-3 hover:bg-gray-50 dark:hover:bg-gray-800 rounded-xl"
      >
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <h3 className="font-semibold text-gray-900 dark:text-white truncate">
              {team_role_label}
            </h3>
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
              {member_count} {member_count === 1 ? 'member' : 'members'}
            </p>
            {co_supervisors?.length > 0 && (
              <p className="text-xs text-gray-600 dark:text-gray-300 mt-1 truncate">
                with {co_supervisors.map((c) => c.person_name).join(', ')}
              </p>
            )}
          </div>
          <div className="text-right shrink-0">
            <p className="text-sm font-medium text-gray-900 dark:text-white">
              {completion.submitted} / {completion.expected}
            </p>
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">submitted today</p>
          </div>
        </div>
        {badges?.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mt-2">
            {badges.map((b) => (
              <Badge key={b} kind={b} />
            ))}
          </div>
        )}
      </Link>
    </li>
  );
}

function SelfReflectionCard({ self }) {
  if (!self || self.state === 'missing') {
    return (
      <section
        aria-label="My reflection"
        className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-4"
        data-testid="lt-self-card"
      >
        <h2 className="text-base font-semibold text-gray-900 dark:text-white mb-1">
          My reflection
        </h2>
        <p className="text-sm text-gray-500 dark:text-gray-400">
          No reflection template is configured for your role yet.
        </p>
      </section>
    );
  }
  const isComplete = self.state === 'complete' || self.state === 'day_off';
  const actionPath = self.reflection_id
    ? `/leadership-team/self-reflection/${self.reflection_id}/edit`
    : '/leadership-team/self-reflection';
  const statusColors = {
    complete: 'bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-300',
    day_off: 'bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-300',
    missing: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/40 dark:text-yellow-300',
  };
  return (
    <section
      aria-label="My reflection"
      className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-4"
      data-testid="lt-self-card"
    >
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-base font-semibold text-gray-900 dark:text-white">My reflection</h2>
        <span
          className={`text-xs font-medium px-2 py-0.5 rounded-full ${statusColors[self.state] ?? statusColors.missing}`}
        >
          {self.state.replace('_', ' ')}
        </span>
      </div>
      <p className="text-xs text-gray-500 dark:text-gray-400 mb-2">
        Period {self.period_start} → {self.period_end} ({self.cadence})
      </p>
      <Link
        to={actionPath}
        className="mt-2 inline-block rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium px-4 py-2 transition-colors"
        data-testid="lt-self-cta"
      >
        {isComplete ? 'Edit reflection' : 'Start reflection'}
      </Link>
    </section>
  );
}

function BunksUnitsCard({ summary }) {
  if (!summary) return null;
  return (
    <section
      aria-label="Bunks and units"
      className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-4"
      data-testid="lt-bunks-units-card"
    >
      <h2 className="text-base font-semibold text-gray-900 dark:text-white mb-2">
        Bunks &amp; units
      </h2>
      <div className="flex flex-wrap gap-4 text-sm text-gray-700 dark:text-gray-300">
        <span data-testid="lt-bu-units">{summary.unit_count} units</span>
        <span data-testid="lt-bu-bunks">{summary.bunk_count} bunks</span>
        <span data-testid="lt-bu-completion">
          {summary.completion.submitted}/{summary.completion.expected} bunk logs today
        </span>
      </div>
    </section>
  );
}

export default function LeadershipTeamDashboard() {
  const { orgSlug } = useAuth();
  const [dashboard, setDashboard] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    try {
      const data = await fetchDashboard(orgSlug);
      setDashboard(data);
      setError(null);
    } catch (err) {
      const status = err?.response?.status;
      if (status === 403) {
        setError('Your account does not have Leadership Team access.');
      } else {
        setError('Failed to load the Leadership Team dashboard.');
      }
    } finally {
      setLoading(false);
    }
  }, [orgSlug]);

  useEffect(() => {
    load();
    const id = setInterval(load, REFRESH_INTERVAL_MS);
    return () => clearInterval(id);
  }, [load]);

  if (loading) {
    return (
      <div className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-[96rem] mx-auto" data-testid="lt-loading">
        <p className="text-gray-500 dark:text-gray-400">Loading…</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-[96rem] mx-auto" data-testid="lt-error">
        <p className="text-red-600 dark:text-red-400">{error}</p>
        <button
          onClick={load}
          className="mt-3 text-sm text-indigo-600 dark:text-indigo-400 underline"
          type="button"
        >
          Retry
        </button>
      </div>
    );
  }

  const teams = dashboard?.teams ?? [];

  return (
    <div className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-[96rem] mx-auto space-y-4">
      <div>
        <h1 className="text-xl font-bold text-gray-900 dark:text-white">Leadership Team</h1>
        <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">{dashboard.today}</p>
      </div>

      <SelfReflectionCard self={dashboard.self_reflection} />

      <section aria-label="Supervised teams" data-testid="lt-teams-section">
        <h2 className="text-base font-semibold text-gray-900 dark:text-white mb-2">
          My teams
        </h2>
        {teams.length === 0 ? (
          <div
            className="rounded-xl border border-dashed border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 p-4 text-sm text-gray-500 dark:text-gray-400"
            data-testid="lt-teams-empty"
          >
            You don&apos;t currently supervise any role-based teams in this program.
          </div>
        ) : (
          <ul className="space-y-2" data-testid="lt-teams-list">
            {teams.map((card) => (
              <TeamCard key={card.team_role} card={card} />
            ))}
          </ul>
        )}
      </section>

      <BunksUnitsCard summary={dashboard.bunks_and_units} />
    </div>
  );
}
