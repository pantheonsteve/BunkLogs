/**
 * Faculty challenge inbox — Step 4_8, MA7.
 *
 * Faculty always see full author identity (semi-anonymity is
 * peer-Madrich only, per the MA7 table). Results are grouped by
 * classroom client-side since a faculty member can author more than
 * one classroom; the API itself only supports status/session-date
 * filters plus an optional `classroom` narrow.
 */

import { useCallback, useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { fetchFacultyChallenges } from '../../api/facultyChallenges';
import { useAuth } from '../../auth/AuthContext';

const STATUS_STYLES = {
  open: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/40 dark:text-yellow-300',
  acknowledged: 'bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-300',
  resolved: 'bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-300',
};

function StatusBadge({ status }) {
  const cls = STATUS_STYLES[status] || 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300';
  const label = status ? status.charAt(0).toUpperCase() + status.slice(1) : 'Unknown';
  return (
    <span className={`shrink-0 text-xs font-medium px-2 py-0.5 rounded-full ${cls}`}>
      {label}
    </span>
  );
}

function groupByClassroom(challenges) {
  const groups = new Map();
  for (const c of challenges) {
    const key = c.assignment_group?.id ?? 'unknown';
    if (!groups.has(key)) {
      groups.set(key, { name: c.assignment_group?.name || 'Classroom', items: [] });
    }
    groups.get(key).items.push(c);
  }
  return Array.from(groups.values());
}

function ChallengeRow({ challenge }) {
  const dateLabel = new Date(`${challenge.session_date}T00:00:00`).toLocaleDateString(undefined, {
    month: 'short',
    day: 'numeric',
  });
  return (
    <li>
      <Link
        to={`/faculty/challenges/${challenge.id}`}
        className="flex items-center justify-between gap-3 rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-4 hover:border-indigo-300 dark:hover:border-indigo-600 transition-colors"
        data-testid={`faculty-challenge-row-${challenge.id}`}
      >
        <div className="min-w-0">
          <p className="text-sm font-medium text-gray-900 dark:text-white truncate">
            {challenge.author?.display_name || challenge.author?.display}
          </p>
          <p className="text-sm text-gray-500 dark:text-gray-400 truncate">{challenge.body_preview}</p>
          <p className="text-xs text-gray-400 dark:text-gray-500 mt-1">
            {challenge.category_label} · {dateLabel}
          </p>
        </div>
        <StatusBadge status={challenge.status} />
      </Link>
    </li>
  );
}

export default function FacultyChallengeInbox() {
  const { orgSlug } = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();
  const status = searchParams.get('status') || '';
  const sessionDate = searchParams.get('session_date') || '';
  const classroomFilter = searchParams.get('classroom') || '';

  const [challenges, setChallenges] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await fetchFacultyChallenges(orgSlug, {
        status: status || undefined,
        sessionDate: sessionDate || undefined,
        classroom: classroomFilter || undefined,
      });
      setChallenges(data?.results || []);
      setError(null);
    } catch {
      setError('Could not load the challenge inbox.');
    } finally {
      setLoading(false);
    }
  }, [orgSlug, status, sessionDate, classroomFilter]);

  useEffect(() => {
    load();
  }, [load]);

  const setParam = (key, value) => {
    const next = new URLSearchParams(searchParams);
    if (value) next.set(key, value);
    else next.delete(key);
    setSearchParams(next, { replace: true });
  };

  const groups = groupByClassroom(challenges);

  return (
    <div className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-[96rem] mx-auto space-y-4">
      <div>
        <Link
          to="/faculty"
          className="text-sm text-indigo-600 dark:text-indigo-400 hover:underline"
          data-testid="faculty-challenge-inbox-back"
        >
          ← Back to home
        </Link>
        <h1 className="mt-1 text-xl font-bold text-gray-900 dark:text-white">Classroom challenges</h1>
      </div>

      <div className="flex flex-wrap gap-3">
        <select
          value={status}
          onChange={(e) => setParam('status', e.target.value)}
          className="rounded-lg border-gray-300 dark:border-gray-600 dark:bg-gray-700 text-sm"
          data-testid="faculty-challenge-status-filter"
        >
          <option value="">All statuses</option>
          <option value="open">Open</option>
          <option value="acknowledged">Acknowledged</option>
          <option value="resolved">Resolved</option>
        </select>
        <input
          type="date"
          value={sessionDate}
          onChange={(e) => setParam('session_date', e.target.value)}
          className="rounded-lg border-gray-300 dark:border-gray-600 dark:bg-gray-700 text-sm"
          data-testid="faculty-challenge-date-filter"
        />
      </div>

      {loading ? (
        <p className="text-gray-500 dark:text-gray-400" data-testid="faculty-challenge-loading">Loading…</p>
      ) : error ? (
        <p className="text-red-600 dark:text-red-400">{error}</p>
      ) : challenges.length === 0 ? (
        <div
          className="rounded-xl border border-dashed border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 p-4 text-sm text-gray-500 dark:text-gray-400"
          data-testid="faculty-challenge-empty"
        >
          No challenges match these filters.
        </div>
      ) : (
        groups.map((group) => (
          <section key={group.name} aria-label={group.name} className="space-y-2">
            {groups.length > 1 && (
              <h2 className="text-sm font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide">
                {group.name}
              </h2>
            )}
            <ul className="space-y-3">
              {group.items.map((c) => <ChallengeRow key={c.id} challenge={c} />)}
            </ul>
          </section>
        ))
      )}
    </div>
  );
}
