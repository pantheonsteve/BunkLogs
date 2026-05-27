/**
 * LT Team Dashboard — Step 7_12, Story 46 + Story 48 toggle.
 *
 * Per-supervised-team page: submission status, flagged reflections,
 * member rows. Tapping a member row navigates to MemberReflection.
 * The date selector defaults to the current period; future dates are
 * rejected by the backend with 400.
 *
 * Story 48 c5/c6: aggregate-CSV download button hits the export URL on
 * the server.
 */

import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link, useParams, useSearchParams } from 'react-router-dom';
import {
  exportTeamAggregateUrl,
  fetchTeamDashboard,
} from '../../api/leadershipTeam';
import { useAuth } from '../../auth/AuthContext';

const STATUS_META = {
  submitted: {
    label: 'Submitted',
    className: 'bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-200',
  },
  day_off: {
    label: 'Day off',
    className: 'bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-200',
  },
  not_submitted: {
    label: 'Not submitted',
    className: 'bg-gray-200 text-gray-800 dark:bg-gray-700 dark:text-gray-100',
  },
};

const REASON_LABELS = {
  needs_attention: 'Needs attention',
  low_rating: 'Low rating',
};

function StatusPill({ status }) {
  const meta = STATUS_META[status] ?? STATUS_META.not_submitted;
  return (
    <span
      data-testid={`lt-status-${status}`}
      className={`text-xs font-medium px-2 py-0.5 rounded-full ${meta.className}`}
    >
      {meta.label}
    </span>
  );
}

export default function LeadershipTeamTeamDashboard() {
  const { teamRole } = useParams();
  const [searchParams, setSearchParams] = useSearchParams();
  const { orgSlug } = useAuth();
  const dateParam = searchParams.get('date') || '';
  const filterStatus = searchParams.get('filter') || 'all';

  const [payload, setPayload] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await fetchTeamDashboard(orgSlug, teamRole, {
        date: dateParam || undefined,
      });
      setPayload(data);
      setError(null);
    } catch (err) {
      const status = err?.response?.status;
      if (status === 403) setError('You do not supervise this team.');
      else if (status === 404) setError('Unknown team role.');
      else setError('Failed to load the team dashboard.');
    } finally {
      setLoading(false);
    }
  }, [orgSlug, teamRole, dateParam]);

  useEffect(() => {
    load();
  }, [load]);

  const filteredMembers = useMemo(() => {
    const rows = payload?.members ?? [];
    if (filterStatus === 'all') return rows;
    return rows.filter((m) => m.status === filterStatus);
  }, [payload, filterStatus]);

  if (loading) {
    return (
      <div className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-[96rem] mx-auto" data-testid="lt-team-loading">
        <p className="text-gray-500 dark:text-gray-400">Loading…</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-[96rem] mx-auto" data-testid="lt-team-error">
        <p className="text-red-600 dark:text-red-400">{error}</p>
        <Link
          to="/leadership-team"
          className="mt-3 inline-block text-sm text-indigo-600 dark:text-indigo-400 underline"
        >
          Back to LT dashboard
        </Link>
      </div>
    );
  }

  const { header, submission_status, flagged } = payload;

  const onDateChange = (e) => {
    const value = e.target.value;
    const next = new URLSearchParams(searchParams);
    if (value) next.set('date', value);
    else next.delete('date');
    setSearchParams(next, { replace: true });
  };

  const onFilterChange = (value) => {
    const next = new URLSearchParams(searchParams);
    if (value === 'all') next.delete('filter');
    else next.set('filter', value);
    setSearchParams(next, { replace: true });
  };

  return (
    <div className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-[96rem] mx-auto space-y-4">
      <div>
        <Link
          to="/leadership-team"
          className="text-sm text-indigo-600 dark:text-indigo-400 hover:underline"
        >
          ← Back to LT dashboard
        </Link>
        <div className="flex items-start justify-between gap-3 mt-2">
          <div>
            <h1 className="text-xl font-bold text-gray-900 dark:text-white">
              {header.team_role_label}
            </h1>
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
              {header.program.name} · {header.member_count} members
            </p>
            {header.supervisors?.length > 0 && (
              <p className="text-xs text-gray-600 dark:text-gray-300 mt-1">
                Supervisors: {header.supervisors.map((s) => s.person_name).join(', ')}
              </p>
            )}
          </div>
          <a
            href={exportTeamAggregateUrl(teamRole)}
            className="rounded-lg border border-gray-300 dark:border-gray-600 text-sm font-medium px-3 py-1.5 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800"
            data-testid="lt-team-export"
          >
            Export CSV
          </a>
        </div>
        <div className="mt-3 flex flex-wrap items-center gap-3">
          <label className="text-sm text-gray-700 dark:text-gray-300">
            Date{' '}
            <input
              type="date"
              value={dateParam || header.date}
              onChange={onDateChange}
              max={header.date}
              className="ml-1 rounded-md border-gray-300 dark:border-gray-600 dark:bg-gray-700 text-sm"
              data-testid="lt-team-date"
            />
          </label>
          {header.period && (
            <span className="text-xs text-gray-500 dark:text-gray-400">
              Period {header.period.start} → {header.period.end} ({header.period.cadence})
            </span>
          )}
        </div>
      </div>
        <section
          aria-label="Submission status"
          className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-4"
          data-testid="lt-team-status"
        >
          <h2 className="text-base font-semibold text-gray-900 dark:text-white mb-2">
            Submission status
          </h2>
          <div className="flex flex-wrap gap-2">
            {['all', 'submitted', 'not_submitted', 'day_off'].map((s) => {
              const count = s === 'all'
                ? submission_status.total
                : (submission_status[s] ?? 0);
              const active = filterStatus === s;
              return (
                <button
                  key={s}
                  type="button"
                  onClick={() => onFilterChange(s)}
                  className={`text-xs px-2 py-1 rounded-full border ${
                    active
                      ? 'bg-indigo-600 text-white border-indigo-600'
                      : 'border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300'
                  }`}
                  data-testid={`lt-filter-${s}`}
                >
                  {s === 'all' ? 'All' : STATUS_META[s].label} ({count})
                </button>
              );
            })}
          </div>
        </section>

        {flagged?.length > 0 && (
          <section
            aria-label="Flagged reflections"
            className="rounded-xl border border-amber-300 dark:border-amber-700 bg-amber-50 dark:bg-amber-900/20 p-4"
            data-testid="lt-team-flagged"
          >
            <h2 className="text-base font-semibold text-gray-900 dark:text-white mb-2">
              Flagged reflections
            </h2>
            <ul className="space-y-2">
              {flagged.map((row) => (
                <li
                  key={row.reflection_id}
                  className="flex items-start justify-between gap-3"
                  data-testid={`lt-flagged-${row.reflection_id}`}
                >
                  <div className="min-w-0">
                    <p className="font-medium text-gray-900 dark:text-white text-sm">
                      {row.person_name}
                    </p>
                    {row.preview && (
                      <p className="text-xs text-gray-700 dark:text-gray-300 truncate mt-0.5">
                        {row.preview}
                      </p>
                    )}
                    <div className="flex flex-wrap gap-1 mt-1">
                      {row.reasons.map((r) => (
                        <span
                          key={r}
                          className="text-xs bg-amber-200 text-amber-900 dark:bg-amber-700 dark:text-amber-50 rounded-full px-2 py-0.5"
                        >
                          {REASON_LABELS[r] ?? r}
                        </span>
                      ))}
                    </div>
                  </div>
                  <Link
                    to={`/reflections/${row.reflection_id}`}
                    className="text-sm text-indigo-600 dark:text-indigo-400 hover:underline shrink-0"
                  >
                    Open →
                  </Link>
                </li>
              ))}
            </ul>
          </section>
        )}

        <section aria-label="Members" data-testid="lt-team-members">
          <h2 className="text-base font-semibold text-gray-900 dark:text-white mb-2">
            Members
          </h2>
          {filteredMembers.length === 0 ? (
            <div className="rounded-xl border border-dashed border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 p-4 text-sm text-gray-500 dark:text-gray-400">
              No members match this filter.
            </div>
          ) : (
            <ul className="space-y-2">
              {filteredMembers.map((m) => (
                <li
                  key={m.membership_id}
                  className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900"
                  data-testid={`lt-member-row-${m.membership_id}`}
                >
                  <Link
                    to={`/leadership-team/teams/${teamRole}/members/${m.membership_id}`}
                    className="block px-4 py-3 hover:bg-gray-50 dark:hover:bg-gray-800 rounded-xl"
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0">
                        <div className="flex items-center gap-2">
                          <p className="font-medium text-gray-900 dark:text-white truncate">
                            {m.person_name}
                          </p>
                          <StatusPill status={m.status} />
                        </div>
                        {m.preview && (
                          <p className="text-xs text-gray-600 dark:text-gray-300 mt-1 truncate">
                            {m.preview}
                          </p>
                        )}
                      </div>
                      {m.attention_marker_count > 0 && (
                        <span
                          className="shrink-0 text-xs font-medium bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-200 rounded-full px-2 py-0.5"
                          data-testid={`lt-marker-count-${m.membership_id}`}
                        >
                          {m.attention_marker_count} flag{m.attention_marker_count === 1 ? '' : 's'}
                        </span>
                      )}
                    </div>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </section>
    </div>
  );
}
