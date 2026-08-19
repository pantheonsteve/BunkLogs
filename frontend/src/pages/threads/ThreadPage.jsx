/**
 * One entry thread, for whoever can read it — Step 4_9.
 *
 * Registered under `/madrich`, `/faculty`, and `/admin` so each role keeps a
 * sensible back link, but the page itself is role-agnostic: the backend
 * decides what the viewer may read, post, and resolve, and this renders only
 * what it is granted.
 */
import { useCallback, useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { MessagesSquare } from 'lucide-react';
import { fetchThread, postThreadMessage, resolveThread } from '../../api/threads';
import { useAuth } from '../../auth/AuthContext';
import { accent } from '../../components/ui/accents';
import BackLink from '../../components/ui/BackLink';
import CardSkeleton from '../../components/ui/CardSkeleton';
import ErrorPanel from '../../components/ui/ErrorPanel';
import ThreadView from '../../components/ui/ThreadView';
import { initialsFor } from '../../utils/initials';

/** Period bounds arrive as plain `YYYY-MM-DD`, so parse as UTC to avoid a day slip. */
function formatPeriodEnd(iso) {
  const [y, m, d] = String(iso ?? '').split('-').map(Number);
  if (!y || !m || !d) return '';
  return new Date(Date.UTC(y, m - 1, d)).toLocaleDateString('en-US', {
    month: 'short', day: 'numeric', timeZone: 'UTC',
  });
}

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

  const subjectName = thread?.subject_person?.display_name;
  const periodEnd = formatPeriodEnd(thread?.period?.end);

  return (
    <div className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-3xl mx-auto space-y-4">
      <div>
        <BackLink to={backTo} label={backLabel} data-testid="thread-back" />
        <div className="mt-2 rounded-2xl bg-gradient-to-r from-violet-600 to-indigo-600 px-5 py-4 shadow-md">
          <div className="flex items-center gap-3">
            <span className="inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-white/20 text-sm font-bold text-white">
              {subjectName
                ? initialsFor(subjectName)
                : <MessagesSquare size={18} aria-hidden="true" />}
            </span>
            <div className="min-w-0">
              <h1 className="text-xl font-bold text-white truncate">
                {subjectName || 'Conversation'}
              </h1>
              <p className="text-sm text-violet-50">
                {periodEnd
                  ? `Week ending ${periodEnd}`
                  : 'One reflection entry and the replies on it.'}
              </p>
            </div>
          </div>
        </div>
      </div>

      {error && <ErrorPanel data-testid="thread-error">{error}</ErrorPanel>}

      {!error && !thread && <CardSkeleton rows={4} data-testid="thread-loading" />}

      {thread && (
        <section
          aria-label="Conversation"
          className={`rounded-xl border border-t-4 border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-4 shadow-sm ${accent('violet').bar}`}
        >
          <ThreadView
            thread={thread}
            onPost={handlePost}
            onResolve={handleResolve}
            busy={busy}
          />
        </section>
      )}
    </div>
  );
}
