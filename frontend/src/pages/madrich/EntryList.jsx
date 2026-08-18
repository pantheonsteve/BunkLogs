/**
 * Full history for one threaded field — Step 4_9 §4.3.
 *
 * The route carries the field key rather than a template id because the
 * homepage cards are schema-driven: whatever fields the template declares as
 * threaded get a card, and each card links here.
 */
import { useCallback, useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { fetchEntries } from '../../api/madrich';
import { useAuth } from '../../auth/AuthContext';
import CardSkeleton from '../../components/ui/CardSkeleton';
import EmptyState from '../../components/ui/EmptyState';
import UnreadDot from '../../components/ui/UnreadDot';

export default function MadrichEntryList() {
  const { fieldKey } = useParams();
  const { orgSlug } = useAuth();
  const [data, setData] = useState(null);
  const [page, setPage] = useState(1);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      setData(await fetchEntries(orgSlug, { fieldKey, page }));
    } catch {
      setError('Could not load entries.');
    }
  }, [orgSlug, fieldKey, page]);

  useEffect(() => { load(); }, [load]);

  if (error) {
    return (
      <div className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-[96rem] mx-auto" data-testid="md-entries-error">
        <p className="text-red-600 dark:text-red-400">{error}</p>
        <button onClick={load} className="mt-3 text-sm text-indigo-600 dark:text-indigo-400 underline">
          Retry
        </button>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-[96rem] mx-auto">
        <CardSkeleton rows={5} data-testid="md-entries-loading" />
      </div>
    );
  }

  const rows = data.results || [];

  return (
    <div className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-[96rem] mx-auto space-y-4">
      <div>
        <Link to="/madrich" className="text-sm text-indigo-600 dark:text-indigo-400 hover:underline">
          ← Back to home
        </Link>
        <h1 className="mt-1 text-xl font-bold text-gray-900 dark:text-white">{data.label}</h1>
      </div>

      {rows.length === 0 ? (
        <EmptyState title="Nothing here yet" data-testid="md-entries-empty">
          Entries appear here once you submit a reflection with this question answered.
        </EmptyState>
      ) : (
        <ul className="space-y-2" data-testid="md-entries-list">
          {rows.map((entry) => (
            <li key={entry.thread_id}>
              <Link
                to={`/madrich/threads/${entry.thread_id}`}
                className="block rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-4 hover:border-indigo-300 dark:hover:border-indigo-700"
                data-testid={`md-entry-${entry.thread_id}`}
              >
                <div className="flex items-start justify-between gap-2">
                  <p className="text-sm text-gray-900 dark:text-white">{entry.excerpt}</p>
                  {entry.unread && <UnreadDot label="Unread reply" />}
                </div>
                <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-gray-500 dark:text-gray-400">
                  <span>{entry.date}</span>
                  {entry.message_count > 0 && (
                    <span>{entry.message_count} repl{entry.message_count === 1 ? 'y' : 'ies'}</span>
                  )}
                  {entry.awaiting_reply && <span className="text-amber-700 dark:text-amber-400">No reply yet</span>}
                </div>
              </Link>
            </li>
          ))}
        </ul>
      )}

      {(data.next || data.previous) && (
        <div className="flex items-center justify-between">
          <button
            type="button"
            disabled={!data.previous}
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            className="text-sm text-indigo-600 dark:text-indigo-400 disabled:opacity-40"
          >
            ← Newer
          </button>
          <button
            type="button"
            disabled={!data.next}
            onClick={() => setPage((p) => p + 1)}
            className="text-sm text-indigo-600 dark:text-indigo-400 disabled:opacity-40"
          >
            Older →
          </button>
        </div>
      )}
    </div>
  );
}
