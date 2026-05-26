/**
 * NoteListItem — shared row component for Inbox/Sent/Archive lists.
 * Shows: subject, author (inbox) or audience summary (sent), time, unread dot.
 */
import { Link } from 'react-router-dom';

function timeAgo(iso) {
  if (!iso) return '';
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  if (days === 1) return 'yesterday';
  return `${days}d ago`;
}

export default function NoteListItem({ note, variant = 'inbox' }) {
  const { id, subject, author, audience_summary, last_activity_at, unread } = note;

  return (
    <Link
      to={`/notes/${id}`}
      className="flex items-start gap-3 px-4 py-3 hover:bg-gray-50 dark:hover:bg-gray-700/40 transition-colors border-b border-gray-100 dark:border-gray-700/50 last:border-0"
    >
      {/* Unread dot */}
      <div className="mt-1.5 shrink-0 w-2 h-2">
        {unread && (
          <span className="block w-2 h-2 rounded-full bg-violet-500" aria-label="unread" />
        )}
      </div>

      <div className="flex-1 min-w-0">
        <div className="flex items-center justify-between gap-2">
          <span
            className={`text-sm truncate ${unread ? 'font-semibold text-gray-900 dark:text-white' : 'font-medium text-gray-700 dark:text-gray-300'}`}
          >
            {subject}
          </span>
          <span className="text-xs text-gray-400 shrink-0">{timeAgo(last_activity_at)}</span>
        </div>
        <p className="text-xs text-gray-500 dark:text-gray-400 truncate mt-0.5">
          {variant === 'inbox'
            ? `From: ${author?.full_name ?? '—'}`
            : `To: ${audience_summary ?? '—'}`}
        </p>
      </div>
    </Link>
  );
}
