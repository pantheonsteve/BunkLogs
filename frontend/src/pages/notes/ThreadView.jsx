/**
 * ThreadView — single note thread with replies and reply composer (Story 68).
 *
 * Route: /notes/:noteId
 */
import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import api from '../../api';
import Header from '../../partials/Header';
import Sidebar from '../../partials/Sidebar';
import SourceReferenceIndicator from '../../components/notes/SourceReferenceIndicator';

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

function AudienceBadge({ audience }) {
  if (!audience || audience.length === 0) return null;
  const names = audience.slice(0, 3).map(a => a.person?.full_name).filter(Boolean);
  const extra = audience.length > 3 ? ` +${audience.length - 3} more` : '';
  return (
    <span className="text-xs text-gray-500 dark:text-gray-400">
      Sent to: {names.join(', ')}{extra}
    </span>
  );
}

function ReadSummary({ readSummary }) {
  if (!readSummary) return null;
  const { read_count, audience_count } = readSummary;
  return (
    <span className="text-xs text-gray-400">
      Read by {read_count}/{audience_count}
    </span>
  );
}

export default function ThreadView() {
  const { noteId } = useParams();
  const navigate = useNavigate();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [note, setNote] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [replyBody, setReplyBody] = useState('');
  const [sending, setSending] = useState(false);
  const [replyError, setReplyError] = useState(null);
  const [archiving, setArchiving] = useState(false);

  useEffect(() => {
    setLoading(true);
    api.get(`/api/v1/notes/${noteId}/`)
      .then(r => setNote(r.data))
      .catch(err => {
        if (err.response?.status === 404) {
          setError('Note not found.');
        } else if (err.response?.status === 403) {
          setError('You do not have access to this note.');
        } else {
          setError('Failed to load note.');
        }
      })
      .finally(() => setLoading(false));
  }, [noteId]);

  async function handleReply(e) {
    e.preventDefault();
    if (!replyBody.trim()) return;
    setSending(true);
    setReplyError(null);
    try {
      const r = await api.post(`/api/v1/notes/${noteId}/replies/`, { body: replyBody.trim() });
      setNote(prev => ({
        ...prev,
        replies: [...(prev.replies ?? []), r.data],
      }));
      setReplyBody('');
    } catch {
      setReplyError('Failed to send reply. Please try again.');
    } finally {
      setSending(false);
    }
  }

  async function handleArchive() {
    setArchiving(true);
    try {
      await api.post(`/api/v1/notes/${noteId}/archive/`);
      navigate('/notes');
    } catch {
      setArchiving(false);
    }
  }

  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center text-gray-400">Loading…</div>
    );
  }

  if (error) {
    return (
      <div className="flex h-screen items-center justify-center text-red-500">{error}</div>
    );
  }

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} />
      <div className="relative flex flex-col flex-1 overflow-y-auto overflow-x-hidden">
        <Header sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} />
        <main className="grow">
          <div className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-[96rem] mx-auto">
            {/* Back link */}
            <button
              type="button"
              onClick={() => navigate('/notes')}
              className="mb-4 flex items-center gap-1 text-sm text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 transition-colors"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
              </svg>
              Back to Notes
            </button>

            {/* Thread card */}
            <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
              {/* Header */}
              <div className="px-5 py-4 border-b border-gray-100 dark:border-gray-700">
                <div className="flex items-start justify-between gap-3">
                  <div className="flex-1 min-w-0">
                    <h1 className="text-lg font-semibold text-gray-900 dark:text-white truncate">
                      {note.subject}
                    </h1>
                    <div className="flex items-center gap-3 mt-1 flex-wrap">
                      <span className="text-sm text-gray-600 dark:text-gray-400">
                        From <span className="font-medium">{note.author?.full_name}</span>
                        <span className="text-xs ml-1 text-gray-400">({note.author_role_at_write})</span>
                      </span>
                      <span className="text-xs text-gray-400">{timeAgo(note.created_at)}</span>
                    </div>
                    <div className="mt-1">
                      <AudienceBadge audience={note.audience} />
                    </div>
                    {note.source_content_type && (
                      <div className="mt-2">
                        <SourceReferenceIndicator
                          sourceContentType={note.source_content_type}
                          sourceObjectId={note.source_object_id}
                        />
                      </div>
                    )}
                  </div>
                  <div className="flex flex-col items-end gap-1 shrink-0">
                    <ReadSummary readSummary={note.read_summary} />
                    <button
                      type="button"
                      onClick={handleArchive}
                      disabled={archiving}
                      className="text-xs text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 transition-colors disabled:opacity-50"
                    >
                      Archive
                    </button>
                  </div>
                </div>
              </div>

              {/* Original body */}
              <div className="px-5 py-4 text-sm text-gray-800 dark:text-gray-200 whitespace-pre-wrap border-b border-gray-100 dark:border-gray-700">
                {note.body}
              </div>

              {/* Replies */}
              {note.replies && note.replies.length > 0 && (
                <div className="divide-y divide-gray-100 dark:divide-gray-700">
                  {note.replies.map(reply => (
                    <div key={reply.id} className="px-5 py-4">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                          {reply.author?.full_name}
                        </span>
                        <span className="text-xs text-gray-400">({reply.author_role_at_write})</span>
                        <span className="text-xs text-gray-400 ml-auto">{timeAgo(reply.created_at)}</span>
                      </div>
                      <p className="text-sm text-gray-800 dark:text-gray-200 whitespace-pre-wrap">
                        {reply.body}
                      </p>
                    </div>
                  ))}
                </div>
              )}

              {/* Reply composer */}
              <div className="px-5 py-4 border-t border-gray-100 dark:border-gray-700">
                <form onSubmit={handleReply} className="space-y-2">
                  <textarea
                    value={replyBody}
                    onChange={e => setReplyBody(e.target.value)}
                    rows={3}
                    maxLength={10000}
                    placeholder="Write a reply…"
                    className="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm text-gray-900 dark:text-white placeholder-gray-400 focus:ring-2 focus:ring-violet-500 focus:border-transparent resize-none"
                  />
                  {replyError && (
                    <p className="text-xs text-red-500">{replyError}</p>
                  )}
                  <div className="flex justify-end">
                    <button
                      type="submit"
                      disabled={sending || !replyBody.trim()}
                      className="px-4 py-2 text-sm font-medium text-white bg-violet-600 hover:bg-violet-700 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                    >
                      {sending ? 'Sending…' : 'Reply'}
                    </button>
                  </div>
                </form>
              </div>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}
