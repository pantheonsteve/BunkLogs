/**
 * Full routed-entry queue for faculty — Step 4_9 §5.1.
 *
 * Oldest first, same as the homepage card. Resolving happens inside a thread,
 * not from the list, so the reply and the close are one deliberate act.
 */
import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { fetchFacultyQueue } from '../../api/faculty';
import { useAuth } from '../../auth/AuthContext';
import CardSkeleton from '../../components/ui/CardSkeleton';
import EmptyState from '../../components/ui/EmptyState';
import { QueueRow } from './Dashboard';

export default function FacultyQueue() {
  const { orgSlug } = useAuth();
  const [data, setData] = useState(null);
  const [page, setPage] = useState(1);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      setData(await fetchFacultyQueue(orgSlug, { page }));
    } catch {
      setError('Could not load the queue.');
    }
  }, [orgSlug, page]);

  useEffect(() => { load(); }, [load]);

  if (error) {
    return (
      <div className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-[96rem] mx-auto" data-testid="fac-queue-error">
        <p className="text-red-600 dark:text-red-400">{error}</p>
        <button onClick={load} className="mt-3 text-sm text-indigo-600 dark:text-indigo-400 underline">
          Retry
        </button>
      </div>
    );
  }

  const items = data?.results || [];

  return (
    <div className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-3xl mx-auto space-y-4">
      <div>
        <Link to="/faculty" className="text-sm text-indigo-600 dark:text-indigo-400 hover:underline">
          ← Back to home
        </Link>
        <h1 className="mt-1 text-xl font-bold text-gray-900 dark:text-white">Waiting on you</h1>
        <p className="text-sm text-gray-500 dark:text-gray-400">
          Questions your Madrichim routed to faculty, oldest first.
        </p>
      </div>

      {!data ? (
        <CardSkeleton rows={5} data-testid="fac-queue-loading" />
      ) : items.length === 0 ? (
        <EmptyState title="Nothing waiting" data-testid="fac-queue-empty">
          Every routed question has a reply.
        </EmptyState>
      ) : (
        <ul className="space-y-2" data-testid="fac-queue-page-list">
          {items.map((item) => <QueueRow key={item.id} item={item} />)}
        </ul>
      )}

      {(data?.next || data?.previous) && (
        <div className="flex items-center justify-between">
          <button
            type="button"
            disabled={!data.previous}
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            className="text-sm text-indigo-600 dark:text-indigo-400 disabled:opacity-40"
          >
            ← Previous
          </button>
          <button
            type="button"
            disabled={!data.next}
            onClick={() => setPage((p) => p + 1)}
            className="text-sm text-indigo-600 dark:text-indigo-400 disabled:opacity-40"
          >
            Next →
          </button>
        </div>
      )}
    </div>
  );
}
