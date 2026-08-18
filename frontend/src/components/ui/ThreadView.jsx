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
      className={`rounded-lg px-3 py-2 ${
        isSelf
          ? 'bg-gray-50 dark:bg-gray-700/40 border border-gray-200 dark:border-gray-700'
          : 'bg-violet-50 dark:bg-violet-900/20 border border-violet-200 dark:border-violet-800'
      }`}
      data-testid="thread-message"
      data-self-update={isSelf ? 'true' : 'false'}
    >
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <span className="text-sm font-medium text-gray-900 dark:text-white">
          {author?.display_name || 'Unknown'}
          {isSelf && (
            <span className="ml-2 text-xs font-normal text-gray-500 dark:text-gray-400">
              own update
            </span>
          )}
        </span>
        <span className="text-xs text-gray-500 dark:text-gray-400">
          {formatTimestamp(createdAt)}
          {editedAt && ' · edited'}
        </span>
      </div>
      <p className="mt-1 text-sm text-gray-700 dark:text-gray-300 whitespace-pre-wrap">
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
      <div className="rounded-lg border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900/40 p-3">
        <p className="text-xs font-medium uppercase tracking-wide text-gray-500 dark:text-gray-400">
          {thread.field_label}
        </p>
        <p
          className="mt-1 text-sm text-gray-900 dark:text-white whitespace-pre-wrap"
          data-testid="thread-entry-body"
        >
          {thread.body || <span className="italic text-gray-400">No longer in this reflection.</span>}
        </p>
        {thread.period && (
          <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
            Week ending {thread.period.end}
          </p>
        )}
      </div>

      {resolved && (
        <p
          className="mt-3 text-sm text-gray-500 dark:text-gray-400"
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
        <p className="mt-3 text-sm text-gray-500 dark:text-gray-400" data-testid="thread-empty">
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
            className="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm text-gray-900 dark:text-white placeholder-gray-400"
          />
          {error && <p className="text-xs text-red-500" role="alert">{error}</p>}
          <div className="flex items-center justify-end gap-2">
            {thread.can_resolve && (
              <button
                type="button"
                onClick={onResolve}
                disabled={busy}
                data-testid="thread-resolve"
                className="px-4 py-2 text-sm font-medium rounded-lg border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 disabled:opacity-50"
              >
                Mark resolved
              </button>
            )}
            <button
              type="submit"
              disabled={sending || !draft.trim()}
              data-testid="thread-send"
              className="px-4 py-2 text-sm font-medium text-white bg-violet-600 hover:bg-violet-700 rounded-lg disabled:opacity-50"
            >
              {sending ? 'Sending…' : 'Reply'}
            </button>
          </div>
        </form>
      )}
    </div>
  );
}
