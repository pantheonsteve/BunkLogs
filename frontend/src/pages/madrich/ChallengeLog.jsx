/**
 * Madrich classroom challenge log — Step 4_8, MA7.
 *
 * Two tabs:
 *   - "Our classroom": peer-safe list for the selected classroom (author
 *     redacted to "A Madrich" unless it's the viewer's own submission).
 *   - "My reports": everything the viewer has personally submitted,
 *     across all their classrooms, never redacted.
 *
 * A classroom picker only renders when the Madrich belongs to more
 * than one classroom; single-classroom Madrichim skip straight to
 * the list.
 */

import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { fetchChallenges, fetchClassrooms } from '../../api/madrichChallenges';
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

function ChallengeCard({ challenge }) {
  const authorLabel = challenge.author?.redacted
    ? challenge.author.display
    : challenge.author?.display_name;
  const dateLabel = new Date(`${challenge.session_date}T00:00:00`).toLocaleDateString(undefined, {
    month: 'short',
    day: 'numeric',
  });

  return (
    <li>
      <Link
        to={`/madrich/challenges/${challenge.id}`}
        className="block rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-4 hover:border-indigo-300 dark:hover:border-indigo-600 transition-colors"
        data-testid={`md-challenge-card-${challenge.id}`}
      >
        <div className="flex items-center justify-between gap-3 mb-1">
          <span className="text-xs font-medium px-2 py-0.5 rounded-full bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300">
            {challenge.category_label}
          </span>
          <StatusBadge status={challenge.status} />
        </div>
        <p className="text-sm text-gray-900 dark:text-white mb-1">{challenge.body_preview}</p>
        <div className="flex items-center justify-between text-xs text-gray-500 dark:text-gray-400">
          <span>{authorLabel} · {dateLabel}</span>
          <span>
            {challenge.response_count} repl{challenge.response_count === 1 ? 'y' : 'ies'}
          </span>
        </div>
      </Link>
    </li>
  );
}

export default function MadrichChallengeLog() {
  const { orgSlug } = useAuth();
  const [classrooms, setClassrooms] = useState([]);
  const [selectedClassroom, setSelectedClassroom] = useState(null);
  const [tab, setTab] = useState('classroom');
  const [challenges, setChallenges] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let active = true;
    fetchClassrooms(orgSlug)
      .then((data) => {
        if (!active) return;
        const rooms = data?.classrooms || [];
        setClassrooms(rooms);
        if (rooms.length > 0) setSelectedClassroom(rooms[0].assignment_group_id);
      })
      .catch(() => {});
    return () => { active = false; };
  }, [orgSlug]);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const opts = tab === 'mine'
        ? { mine: true }
        : { classroom: selectedClassroom };
      const data = await fetchChallenges(orgSlug, opts);
      setChallenges(data?.results || []);
      setError(null);
    } catch {
      setError('Could not load challenges.');
    } finally {
      setLoading(false);
    }
  }, [orgSlug, tab, selectedClassroom]);

  useEffect(() => {
    if (tab === 'mine' || selectedClassroom) {
      load();
    }
  }, [load, tab, selectedClassroom]);

  const emptyMessage = tab === 'mine'
    ? "You haven't reported any challenges yet."
    : 'No challenges reported for this classroom yet.';

  return (
    <div className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-[96rem] mx-auto space-y-4">
      <div className="flex items-center justify-between gap-3">
        <h1 className="text-xl font-bold text-gray-900 dark:text-white">Classroom challenges</h1>
        <Link
          to="/madrich/challenges/new"
          className="rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium px-4 py-2 transition-colors"
          data-testid="md-challenge-log-new"
        >
          Report a challenge
        </Link>
      </div>

      {classrooms.length > 1 && tab === 'classroom' && (
        <select
          value={selectedClassroom ?? ''}
          onChange={(e) => setSelectedClassroom(Number(e.target.value))}
          className="rounded-lg border-gray-300 dark:border-gray-600 dark:bg-gray-700 text-sm"
          data-testid="md-challenge-classroom-select"
        >
          {classrooms.map((c) => (
            <option key={c.assignment_group_id} value={c.assignment_group_id}>
              {c.name}
            </option>
          ))}
        </select>
      )}

      <div className="flex gap-2 border-b border-gray-200 dark:border-gray-700" role="tablist">
        <button
          type="button"
          role="tab"
          aria-selected={tab === 'classroom'}
          onClick={() => setTab('classroom')}
          className={`px-3 py-2 text-sm font-medium border-b-2 -mb-px transition-colors ${
            tab === 'classroom'
              ? 'border-indigo-600 text-indigo-600 dark:text-indigo-400'
              : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'
          }`}
          data-testid="md-challenge-tab-classroom"
        >
          Our classroom
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={tab === 'mine'}
          onClick={() => setTab('mine')}
          className={`px-3 py-2 text-sm font-medium border-b-2 -mb-px transition-colors ${
            tab === 'mine'
              ? 'border-indigo-600 text-indigo-600 dark:text-indigo-400'
              : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'
          }`}
          data-testid="md-challenge-tab-mine"
        >
          My reports
        </button>
      </div>

      {loading ? (
        <p className="text-gray-500 dark:text-gray-400" data-testid="md-challenge-log-loading">Loading…</p>
      ) : error ? (
        <p className="text-red-600 dark:text-red-400">{error}</p>
      ) : challenges.length === 0 ? (
        <div
          className="rounded-xl border border-dashed border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 p-4 text-sm text-gray-500 dark:text-gray-400"
          data-testid="md-challenge-log-empty"
        >
          {emptyMessage}
        </div>
      ) : (
        <ul className="space-y-3">
          {challenges.map((c) => <ChallengeCard key={c.id} challenge={c} />)}
        </ul>
      )}
    </div>
  );
}
