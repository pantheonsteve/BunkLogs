/**
 * ObservationThread — single observation thread with subjects, replies, and a
 * reply composer (Step 7_23). Route: /observations/:observationId.
 */
import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import RichText from '../../components/ui/RichText';
import {
  archiveObservation,
  fetchObservationThread,
  replyToObservation,
} from '../../api/observations';

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

const SENSITIVITY_LABEL = {
  normal: 'Normal',
  sensitive: 'Sensitive',
  domain: 'Domain',
  confidential: 'Confidential',
};

export default function ObservationThread() {
  const { observationId } = useParams();
  const navigate = useNavigate();
  const [obs, setObs] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [replyBody, setReplyBody] = useState('');
  const [sending, setSending] = useState(false);
  const [replyError, setReplyError] = useState(null);
  const [archiving, setArchiving] = useState(false);

  useEffect(() => {
    setLoading(true);
    fetchObservationThread(observationId)
      .then(setObs)
      .catch((err) => {
        if (err.response?.status === 404) setError('Observation not found.');
        else setError('Failed to load observation.');
      })
      .finally(() => setLoading(false));
  }, [observationId]);

  async function handleReply(e) {
    e.preventDefault();
    if (!replyBody.trim()) return;
    setSending(true);
    setReplyError(null);
    try {
      const reply = await replyToObservation(observationId, replyBody.trim());
      setObs((prev) => ({ ...prev, replies: [...(prev.replies ?? []), reply] }));
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
      await archiveObservation(observationId);
      navigate('/observations');
    } catch {
      setArchiving(false);
    }
  }

  if (loading) {
    return <div className="flex h-screen items-center justify-center text-gray-400">Loading…</div>;
  }
  if (error) {
    return <div className="flex h-screen items-center justify-center text-red-500">{error}</div>;
  }

  return (
    <main className="grow">
      <div className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-3xl mx-auto">
        <button
          type="button"
          onClick={() => navigate('/observations')}
          className="mb-4 flex items-center gap-1 text-sm text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 transition-colors"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
          Back to Observations
        </button>

        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
          <div className="px-5 py-4 border-b border-gray-100 dark:border-gray-700">
            <div className="flex items-start justify-between gap-3">
              <div className="flex-1 min-w-0">
                <div className="flex flex-wrap items-center gap-2">
                  {(obs.subjects ?? []).map((s) => (
                    <span
                      key={s.id}
                      className="inline-flex rounded-full bg-indigo-50 dark:bg-indigo-900/20 px-2.5 py-0.5 text-xs font-medium text-indigo-800 dark:text-indigo-100"
                    >
                      {s.full_name}
                    </span>
                  ))}
                  <span className="inline-flex rounded-full bg-amber-50 dark:bg-amber-900/20 px-2.5 py-0.5 text-xs font-medium text-amber-800 dark:text-amber-200">
                    {SENSITIVITY_LABEL[obs.sensitivity] ?? obs.sensitivity}
                  </span>
                </div>
                <div className="flex items-center gap-3 mt-2 flex-wrap">
                  <span className="text-sm text-gray-600 dark:text-gray-400">
                    From <span className="font-medium">{obs.author?.full_name}</span>
                    <span className="text-xs ml-1 text-gray-400">({obs.author_role_at_write})</span>
                  </span>
                  <span className="text-xs text-gray-400">{timeAgo(obs.created_at)}</span>
                  {obs.context && (
                    <span className="text-xs text-gray-400">· {obs.context}</span>
                  )}
                </div>
              </div>
              <button
                type="button"
                onClick={handleArchive}
                disabled={archiving}
                className="text-xs text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 transition-colors disabled:opacity-50 shrink-0"
              >
                Archive
              </button>
            </div>
          </div>

          <div className="px-5 py-4 border-b border-gray-100 dark:border-gray-700">
            <RichText
              html={obs.body}
              className="text-sm text-gray-800 dark:text-gray-200 break-words [&_p]:mb-2 last:[&_p]:mb-0"
            />
          </div>

          {obs.replies && obs.replies.length > 0 && (
            <div className="divide-y divide-gray-100 dark:divide-gray-700">
              {obs.replies.map((reply) => (
                <div key={reply.id} className="px-5 py-4">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                      {reply.author?.full_name}
                    </span>
                    <span className="text-xs text-gray-400">({reply.author_role_at_write})</span>
                    <span className="text-xs text-gray-400 ml-auto">{timeAgo(reply.created_at)}</span>
                  </div>
                  <RichText
                    html={reply.body}
                    className="text-sm text-gray-800 dark:text-gray-200 break-words [&_p]:mb-2 last:[&_p]:mb-0"
                  />
                </div>
              ))}
            </div>
          )}

          <div className="px-5 py-4 border-t border-gray-100 dark:border-gray-700">
            <form onSubmit={handleReply} className="space-y-2">
              <textarea
                value={replyBody}
                onChange={(e) => setReplyBody(e.target.value)}
                rows={3}
                maxLength={10000}
                placeholder="Write a reply…"
                className="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm text-gray-900 dark:text-white placeholder-gray-400 focus:ring-2 focus:ring-violet-500 focus:border-transparent resize-none"
              />
              {replyError && <p className="text-xs text-red-500">{replyError}</p>}
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
  );
}
