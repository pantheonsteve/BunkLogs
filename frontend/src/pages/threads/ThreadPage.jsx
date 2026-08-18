/**
 * One entry thread, for whoever can read it — Step 4_9.
 *
 * Registered under `/madrich`, `/faculty`, and `/admin` so each role keeps a
 * sensible back link, but the page itself is role-agnostic: the backend
 * decides what the viewer may read, post, and resolve, and this renders only
 * what it is granted.
 */
import { useCallback, useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { fetchThread, postThreadMessage, resolveThread } from '../../api/threads';
import { useAuth } from '../../auth/AuthContext';
import CardSkeleton from '../../components/ui/CardSkeleton';
import ThreadView from '../../components/ui/ThreadView';

export default function ThreadPage({ backTo = '/madrich', backLabel = 'Back to home' }) {
  const { threadId } = useParams();
  const { orgSlug } = useAuth();
  const [thread, setThread] = useState(null);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    setError(null);
    try {
      setThread(await fetchThread(orgSlug, threadId));
    } catch (err) {
      setError(
        err?.response?.status === 403 || err?.response?.status === 404
          ? 'This conversation is not available to you.'
          : 'Could not load this conversation.',
      );
    }
  }, [orgSlug, threadId]);

  useEffect(() => { load(); }, [load]);

  const handlePost = useCallback(async (body) => {
    await postThreadMessage(orgSlug, threadId, body);
    await load();
  }, [orgSlug, threadId, load]);

  const handleResolve = useCallback(async () => {
    setBusy(true);
    try {
      await resolveThread(orgSlug, threadId);
      await load();
    } finally {
      setBusy(false);
    }
  }, [orgSlug, threadId, load]);

  return (
    <div className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-3xl mx-auto space-y-4">
      <Link to={backTo} className="text-sm text-indigo-600 dark:text-indigo-400 hover:underline">
        ← {backLabel}
      </Link>

      {error && (
        <div data-testid="thread-error">
          <p className="text-red-600 dark:text-red-400">{error}</p>
        </div>
      )}

      {!error && !thread && <CardSkeleton rows={4} data-testid="thread-loading" />}

      {thread && (
        <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-4">
          <p className="text-sm text-gray-500 dark:text-gray-400">
            {thread.subject_person?.display_name}
          </p>
          <ThreadView
            thread={thread}
            onPost={handlePost}
            onResolve={handleResolve}
            busy={busy}
          />
        </div>
      )}
    </div>
  );
}
