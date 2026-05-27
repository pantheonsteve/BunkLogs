/**
 * NoteThread — inline reply thread for any note type.
 *
 * Props:
 *   noteId          — numeric ID of the parent note (for lazy-fetch).
 *   initialReplies  — array already in the note payload (avoids extra round-trip).
 *   onFetch(noteId) — async fn that returns the replies array.
 *   onPost(noteId, body) — async fn that creates a reply and returns the new reply obj.
 *
 * Reply shape: { id, author_name, author_role, body, created_at }
 *
 * Behaviour:
 *   - Shows reply count link. Clicking expands the thread.
 *   - Loaded once (lazy) the first time the thread is expanded; subsequent
 *     posts are appended optimistically.
 *   - Reply composer collapsed by default, expands on "Reply" click.
 */

import { useCallback, useRef, useState } from 'react';

const ROLE_LABEL = {
  counselor: 'Counselor',
  unit_head: 'Unit Head',
  camper_care: 'Camper Care',
  specialist: 'Specialist',
  leadership_team: 'Leadership',
  admin: 'Admin',
  health_center: 'Health',
  special_diets: 'Special Diets',
  kitchen_staff: 'Kitchen',
  maintenance: 'Maintenance',
  madrich: 'Madrich',
  director: 'Director',
};

function ReplyRow({ reply }) {
  const date = reply.created_at
    ? new Date(reply.created_at).toLocaleString(undefined, {
        month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit',
      })
    : '';
  const roleLabel = ROLE_LABEL[reply.author_role] || reply.author_role || '';

  return (
    <li
      className="py-2 border-t border-gray-100 dark:border-gray-700 first:border-0"
      data-testid={`thread-reply-${reply.id}`}
    >
      <div className="flex items-center gap-2 flex-wrap mb-0.5">
        <span className="text-xs font-medium text-gray-800 dark:text-gray-200">
          {reply.author_name}
        </span>
        {roleLabel && (
          <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300">
            {roleLabel}
          </span>
        )}
        <span className="text-[10px] text-gray-400 dark:text-gray-500 ml-auto">{date}</span>
      </div>
      <p className="text-sm text-gray-700 dark:text-gray-300 whitespace-pre-wrap">{reply.body}</p>
    </li>
  );
}

function ReplyComposer({ onSubmit, onCancel, disabled }) {
  const [body, setBody] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');
  const textareaRef = useRef(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    const text = body.trim();
    if (!text) return;
    setSubmitting(true);
    setError('');
    try {
      await onSubmit(text);
      setBody('');
      onCancel();
    } catch (err) {
      setError(err?.response?.data?.body || err?.message || 'Could not post reply.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="mt-2 space-y-1.5" data-testid="thread-composer">
      <textarea
        ref={textareaRef}
        value={body}
        onChange={(e) => setBody(e.target.value)}
        rows={3}
        disabled={disabled || submitting}
        placeholder="Write a reply…"
        className="block w-full rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm focus:border-blue-500 focus:ring-2 focus:ring-blue-200 resize-none"
        data-testid="thread-reply-input"
      />
      {error && (
        <p role="alert" className="text-xs text-red-600 dark:text-red-400">{error}</p>
      )}
      <div className="flex items-center gap-2 justify-end">
        <button
          type="button"
          onClick={onCancel}
          disabled={submitting}
          className="text-xs text-gray-500 dark:text-gray-400 hover:underline"
        >
          Cancel
        </button>
        <button
          type="submit"
          disabled={!body.trim() || submitting}
          data-testid="thread-reply-submit"
          className="px-3 py-1 rounded-md bg-blue-600 text-white text-xs font-medium hover:bg-blue-700 disabled:opacity-50"
        >
          {submitting ? 'Posting…' : 'Post reply'}
        </button>
      </div>
    </form>
  );
}

export default function NoteThread({ noteId, initialReplies = [], onFetch, onPost }) {
  const [expanded, setExpanded] = useState(false);
  const [replies, setReplies] = useState(initialReplies);
  const [loaded, setLoaded] = useState(initialReplies.length > 0);
  const [loading, setLoading] = useState(false);
  const [composerOpen, setComposerOpen] = useState(false);

  const expand = useCallback(async () => {
    if (expanded) {
      setExpanded(false);
      return;
    }
    setExpanded(true);
    if (loaded) return;
    if (!onFetch) { setLoaded(true); return; }
    setLoading(true);
    try {
      const data = await onFetch(noteId);
      setReplies(data);
      setLoaded(true);
    } finally {
      setLoading(false);
    }
  }, [expanded, loaded, onFetch, noteId]);

  const handlePost = useCallback(async (body) => {
    const reply = await onPost(noteId, body);
    setReplies((prev) => [...prev, reply]);
  }, [onPost, noteId]);

  const count = replies.length;
  const label = count === 1 ? '1 reply' : `${count} ${count === 0 ? 'replies' : 'replies'}`;

  return (
    <div className="mt-2" data-testid={`note-thread-${noteId}`}>
      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={expand}
          className="text-xs text-blue-600 dark:text-blue-400 hover:underline"
          data-testid="thread-toggle"
        >
          {expanded ? 'Hide thread' : label}
        </button>
        {!composerOpen && (
          <button
            type="button"
            onClick={() => { setExpanded(true); setComposerOpen(true); }}
            className="text-xs text-gray-500 dark:text-gray-400 hover:text-blue-600 dark:hover:text-blue-400 hover:underline"
            data-testid="thread-reply-btn"
          >
            Reply
          </button>
        )}
      </div>

      {expanded && (
        <div className="mt-2 pl-3 border-l-2 border-gray-200 dark:border-gray-700">
          {loading && (
            <p className="text-xs text-gray-500 dark:text-gray-400 py-1">Loading…</p>
          )}
          {!loading && replies.length > 0 && (
            <ul className="space-y-0">
              {replies.map((r) => <ReplyRow key={r.id} reply={r} />)}
            </ul>
          )}
          {!loading && replies.length === 0 && !composerOpen && (
            <p className="text-xs text-gray-400 dark:text-gray-500 py-1">No replies yet.</p>
          )}
          {composerOpen ? (
            <ReplyComposer
              onSubmit={handlePost}
              onCancel={() => setComposerOpen(false)}
              disabled={loading}
            />
          ) : (
            <button
              type="button"
              onClick={() => setComposerOpen(true)}
              className="mt-2 text-xs text-gray-500 dark:text-gray-400 hover:text-blue-600 dark:hover:text-blue-400 hover:underline"
              data-testid="thread-open-composer"
            >
              + Write a reply
            </button>
          )}
        </div>
      )}
    </div>
  );
}
