/**
 * One supervised Madrich, drilled in from the faculty roster — §5.2.
 *
 * Faculty see this person's threaded entries except anything routed to the
 * Director; the backend enforces that and returns 403 if the viewer does not
 * supervise them, which is surfaced as an explicit message rather than an
 * empty page.
 */
import { useCallback, useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { fetchFacultyRosterDetail } from '../../api/faculty';
import { useAuth } from '../../auth/AuthContext';
import CardSkeleton from '../../components/ui/CardSkeleton';
import EmptyState from '../../components/ui/EmptyState';
import HomeCard from '../../components/ui/HomeCard';
import UnreadDot from '../../components/ui/UnreadDot';

export default function FacultyRosterDetail() {
  const { personId } = useParams();
  const { orgSlug } = useAuth();
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      setData(await fetchFacultyRosterDetail(orgSlug, personId));
    } catch (err) {
      setError(
        err?.response?.status === 403
          ? 'You do not supervise this person.'
          : 'Could not load this Madrich.',
      );
    }
  }, [orgSlug, personId]);

  useEffect(() => { load(); }, [load]);

  if (error) {
    return (
      <div className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-3xl mx-auto" data-testid="fac-roster-detail-error">
        <Link to="/faculty" className="text-sm text-indigo-600 dark:text-indigo-400 hover:underline">
          ← Back to home
        </Link>
        <p className="mt-3 text-red-600 dark:text-red-400">{error}</p>
      </div>
    );
  }

  const entries = data?.entries || [];

  return (
    <div className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-3xl mx-auto space-y-4">
      <div>
        <Link to="/faculty" className="text-sm text-indigo-600 dark:text-indigo-400 hover:underline">
          ← Back to home
        </Link>
        <h1 className="mt-1 text-xl font-bold text-gray-900 dark:text-white">
          {data?.person?.display_name || '…'}
        </h1>
        {data?.reflection_state && (
          <p className="text-sm text-gray-500 dark:text-gray-400">
            This week:{' '}
            {data.reflection_state === 'complete' ? 'reflection submitted' : 'not submitted yet'}
          </p>
        )}
      </div>

      {!data ? (
        <CardSkeleton rows={5} data-testid="fac-roster-detail-loading" />
      ) : entries.length === 0 ? (
        <EmptyState title="No entries yet" data-testid="fac-roster-detail-empty">
          Entries appear here once this Madrich submits a reflection.
        </EmptyState>
      ) : (
        <HomeCard title="Their entries" data-testid="fac-roster-detail-entries">
          <ul className="space-y-2">
            {entries.map((entry) => (
              <li key={entry.id}>
                <Link
                  to={`/faculty/threads/${entry.id}`}
                  className="block rounded-lg border border-gray-200 dark:border-gray-700 px-3 py-2 hover:border-indigo-300 dark:hover:border-indigo-700"
                  data-testid={`fac-roster-entry-${entry.id}`}
                >
                  <div className="flex items-start justify-between gap-2">
                    <p className="text-xs text-gray-500 dark:text-gray-400">{entry.field_label}</p>
                    {entry.unread && <UnreadDot label="Unread" />}
                  </div>
                  <p className="mt-1 text-sm text-gray-900 dark:text-white">{entry.excerpt}</p>
                  <div className="mt-1 flex flex-wrap gap-2 text-xs text-gray-500 dark:text-gray-400">
                    {entry.message_count > 0 && (
                      <span>{entry.message_count} repl{entry.message_count === 1 ? 'y' : 'ies'}</span>
                    )}
                    {entry.resolved_at && <span>Resolved</span>}
                  </div>
                </Link>
              </li>
            ))}
          </ul>
        </HomeCard>
      )}
    </div>
  );
}
