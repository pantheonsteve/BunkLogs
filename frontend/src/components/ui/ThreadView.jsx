/**
 * Conversation on a single reflection answer or cohort post (Step 4_9 §2.3).
 *
 * Presentational: the caller owns fetching, posting, and resolving. The
 * backend decides who may post or resolve, and this only renders the
 * affordances it is told about via `thread.can_post` / `thread.can_resolve`.
 *
 * The subject's own messages are styled differently from a supervisor's
 * because the two read as different acts: one is the Madrich updating their
 * own entry, the other is a grown-up responding to it.
 */
import { useState } from 'react';
import { initialsFor } from '../../utils/initials';

const MAX_BODY = 10000;

function formatTimestamp(iso) {
  if (!iso) return '';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return '';
  return d.toLocaleString(undefined, {
    month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit',
  });
}

function Message({ message }) {
  const { author, body, is_self_update: isSelf, created_at: createdAt, edited_at: editedAt } = message;
  return (
    <li
      className={`rounded-lg border border-l-4 px-3 py-2 ${
        isSelf
          ? 'border-gray-200 dark:border-gray-700 border-l-gray-400 dark:border-l-gray-500 bg-gray-50 dark:bg-gray-700/40'
          : 'border-violet-200 dark:border-violet-800 border-l-violet-500 dark:border-l-violet-400 bg-violet-50 dark:bg-violet-900/20'
      }`}
      data-testid="thread-message"
      data-self-update={isSelf ? 'true' : 'false'}
    >
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className="flex items-center gap-2 min-w-0">
          <span
            className={`inline-flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-xs font-bold text-white ${
              isSelf ? 'bg-gray-500' : 'bg-violet-600'
            }`}
            aria-hidden="true"
          >
            {initialsFor(author?.display_name)}
          </span>
          <span className="text-sm font-semibold text-gray-900 dark:text-white truncate">
            {author?.display_name || 'Unknown'}
            {isSelf && (
              <span className="ml-2 text-xs font-medium text-gray-600 dark:text-gray-300">
                own update
              </span>
            )}
          </span>
        </span>
        <span className="text-xs text-gray-600 dark:text-gray-300">
          {formatTimestamp(createdAt)}
          {editedAt && ' · edited'}
        </span>
      </div>
      <p className="mt-1.5 text-sm text-gray-800 dark:text-gray-100 whitespace-pre-wrap">
        {body}
      </p>
    </li>
  );
}

export default function ThreadView({ thread, onPost, onResolve, busy = false }) {
  const [draft, setDraft] = useState('');
  const [error, setError] = useState(null);
  const [sending, setSending] = useState(false);

  if (!thread) return null;

  const messages = Array.isArray(thread.messages) ? thread.messages : [];
  const resolved = Boolean(thread.resolved_at);

  async function handleSubmit(event) {
    event.preventDefault();
    const body = draft.trim();
    if (!body) return;
    setSending(true);
    setError(null);
    try {
      await onPost(body);
      setDraft('');
    } catch {
      setError('Could not send. Please try again.');
    } finally {
      setSending(false);
    }
  }

  return (
    <div data-testid="thread-view">
      <div className="rounded-lg border border-indigo-100 dark:border-indigo-800/50 bg-indigo-50 dark:bg-indigo-900/20 p-3">
        <p className="text-xs font-semibold uppercase tracking-wide text-indigo-700 dark:text-indigo-300">
          {thread.field_label}
        </p>
        <p
          className="mt-1 text-sm text-indigo-900 dark:text-indigo-100 whitespace-pre-wrap"
          data-testid="thread-entry-body"
        >
          {thread.body || (
            <span className="italic text-indigo-700/70 dark:text-indigo-300/70">
              No longer in this reflection.
            </span>
          )}
        </p>
      </div>

      {resolved && (
        <p
          className="mt-3 rounded-lg bg-green-50 dark:bg-green-900/25 border border-green-200 dark:border-green-800 px-3 py-2 text-sm text-green-800 dark:text-green-200"
          data-testid="thread-resolved-notice"
        >
          Resolved {formatTimestamp(thread.resolved_at)}. This conversation is closed.
        </p>
      )}

      {messages.length > 0 ? (
        <ul className="mt-3 space-y-2">
          {messages.map((m) => <Message key={m.id} message={m} />)}
        </ul>
      ) : (
        <p className="mt-3 text-sm text-gray-600 dark:text-gray-300" data-testid="thread-empty">
          No replies yet.
        </p>
      )}

      {thread.can_post && !resolved && (
        <form onSubmit={handleSubmit} className="mt-3 space-y-2">
          <label htmlFor="thread-composer" className="sr-only">Write a reply</label>
          <textarea
            id="thread-composer"
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            rows={3}
            maxLength={MAX_BODY}
            placeholder="Write a reply…"
            data-testid="thread-composer"
            className="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900 px-3 py-2 text-sm text-gray-900 dark:text-gray-100 placeholder-gray-500 dark:placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-violet-500 focus:border-violet-500"
          />
          {error && <p className="text-xs text-red-600 dark:text-red-400" role="alert">{error}</p>}
          <div className="flex items-center justify-end gap-2">
            {thread.can_resolve && (
              <button
                type="button"
                onClick={onResolve}
                disabled={busy}
                data-testid="thread-resolve"
                className="px-4 py-2 text-sm font-medium rounded-lg border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors disabled:opacity-50"
              >
                Mark resolved
              </button>
            )}
            <button
              type="submit"
              disabled={sending || !draft.trim()}
              data-testid="thread-send"
              className="px-4 py-2 text-sm font-semibold text-white bg-violet-600 hover:bg-violet-700 rounded-lg shadow-sm transition-colors disabled:opacity-50"
            >
              {sending ? 'Sending…' : 'Reply'}
            </button>
          </div>
        </form>
      )}
    </div>
  );
}
