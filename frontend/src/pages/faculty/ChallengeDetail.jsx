/**
 * Faculty challenge detail — Step 4_8, MA7.
 *
 * Full author identity + status controls (Acknowledge / Resolve) +
 * reply composer. Resolved threads are read-only in Tier 1 (no admin
 * override reply — Director uses a faculty account or follows up
 * in person per the migration prompt).
 */

import { useCallback, useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import {
  fetchFacultyChallenge,
  replyToChallenge,
  updateChallengeStatus,
} from '../../api/facultyChallenges';
import { useAuth } from '../../auth/AuthContext';

const STATUS_STYLES = {
  open: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/40 dark:text-yellow-300',
  acknowledged: 'bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-300',
  resolved: 'bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-300',
};

function StatusBadge({ status }) {
  const cls = STATUS_STYLES[status] || 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300';
  const label = status ? status.charAt(0).toUpperCase() + status.slice(1) : 'Unknown';
  return (
    <span className={`shrink-0 text-xs font-medium px-2 py-0.5 rounded-full ${cls}`} data-testid="faculty-challenge-status">
      {label}
    </span>
  );
}

function flattenError(err, fallback) {
  const body = err?.response?.data;
  if (!body) return err?.message || fallback;
  if (typeof body === 'string') return body;
  if (typeof body.detail === 'string') return body.detail;
  return fallback;
}

export default function FacultyChallengeDetail() {
  const { challengeId } = useParams();
  const { orgSlug } = useAuth();

  const [challenge, setChallenge] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [replyBody, setReplyBody] = useState('');
  const [sending, setSending] = useState(false);
  const [updatingStatus, setUpdatingStatus] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await fetchFacultyChallenge(orgSlug, challengeId);
      setChallenge(data);
      setError(null);
    } catch {
      setError('Could not load this challenge.');
    } finally {
      setLoading(false);
    }
  }, [orgSlug, challengeId]);

  useEffect(() => {
    load();
  }, [load]);

  const handleReply = async (e) => {
    e.preventDefault();
    if (!replyBody.trim()) return;
    setSending(true);
    setError(null);
    try {
      const updated = await replyToChallenge(orgSlug, challengeId, replyBody.trim());
      setChallenge(updated);
      setReplyBody('');
    } catch (err) {
      setError(flattenError(err, 'Could not send this reply.'));
    } finally {
      setSending(false);
    }
  };

  const handleResolve = async () => {
    setUpdatingStatus(true);
    try {
      const updated = await updateChallengeStatus(orgSlug, challengeId, 'resolved');
      setChallenge(updated);
    } catch (err) {
      setError(flattenError(err, 'Could not update the status.'));
    } finally {
      setUpdatingStatus(false);
    }
  };

  const handleAcknowledge = async () => {
    setUpdatingStatus(true);
    try {
      const updated = await updateChallengeStatus(orgSlug, challengeId, 'acknowledged');
      setChallenge(updated);
    } catch (err) {
      setError(flattenError(err, 'Could not update the status.'));
    } finally {
      setUpdatingStatus(false);
    }
  };

  if (loading) {
    return (
      <div className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-[96rem] mx-auto" data-testid="faculty-challenge-detail-loading">
        <p className="text-gray-500 dark:text-gray-400">Loading…</p>
      </div>
    );
  }

  if (!challenge) {
    return (
      <div className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-[96rem] mx-auto" data-testid="faculty-challenge-detail-error">
        <p className="text-red-600 dark:text-red-400">{error || 'Challenge not found.'}</p>
      </div>
    );
  }

  const dateLabel = new Date(`${challenge.session_date}T00:00:00`).toLocaleDateString(undefined, {
    month: 'long',
    day: 'numeric',
    year: 'numeric',
  });
  const isResolved = challenge.status === 'resolved';

  return (
    <div className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-2xl mx-auto space-y-4">
      <div className="flex items-center justify-between gap-3">
        <span className="text-xs font-medium px-2 py-0.5 rounded-full bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300">
          {challenge.category_label}
        </span>
        <StatusBadge status={challenge.status} />
      </div>

      <div>
        <p className="text-sm text-gray-500 dark:text-gray-400" data-testid="faculty-challenge-detail-author">
          {challenge.author?.display_name} · {challenge.assignment_group?.name} · {dateLabel}
        </p>
        <p className="text-gray-900 dark:text-white mt-2 whitespace-pre-wrap" data-testid="faculty-challenge-detail-body">
          {challenge.body}
        </p>
      </div>

      {!isResolved && (
        <div className="flex gap-3">
          {challenge.status === 'open' && (
            <button
              type="button"
              onClick={handleAcknowledge}
              disabled={updatingStatus}
              className="rounded-lg border border-blue-300 dark:border-blue-700 text-blue-600 dark:text-blue-400 text-sm font-medium px-4 py-2 hover:bg-blue-50 dark:hover:bg-blue-900/20 transition-colors disabled:opacity-50"
              data-testid="faculty-challenge-acknowledge"
            >
              Acknowledge
            </button>
          )}
          <button
            type="button"
            onClick={handleResolve}
            disabled={updatingStatus}
            className="rounded-lg border border-green-300 dark:border-green-700 text-green-600 dark:text-green-400 text-sm font-medium px-4 py-2 hover:bg-green-50 dark:hover:bg-green-900/20 transition-colors disabled:opacity-50"
            data-testid="faculty-challenge-resolve"
          >
            Mark resolved
          </button>
        </div>
      )}

      <section aria-label="Responses" className="space-y-3">
        <h2 className="text-sm font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide">
          Responses
        </h2>
        {(challenge.responses || []).length === 0 ? (
          <p className="text-sm text-gray-500 dark:text-gray-400" data-testid="faculty-challenge-no-responses">
            No responses yet.
          </p>
        ) : (
          <ul className="space-y-3">
            {challenge.responses.map((r) => (
              <li
                key={r.id}
                className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-4"
                data-testid={`faculty-challenge-response-${r.id}`}
              >
                <p className="text-sm font-medium text-gray-900 dark:text-white">
                  {r.author?.display_name || r.author?.display}
                </p>
                <p className="text-gray-700 dark:text-gray-300 mt-1 whitespace-pre-wrap">{r.body}</p>
              </li>
            ))}
          </ul>
        )}
      </section>

      {error && (
        <p className="text-red-600 dark:text-red-400 text-sm" data-testid="faculty-challenge-detail-error-inline">
          {error}
        </p>
      )}

      {!isResolved && (
        <form onSubmit={handleReply} className="space-y-2">
          <label htmlFor="faculty-challenge-reply" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
            Reply
          </label>
          <textarea
            id="faculty-challenge-reply"
            value={replyBody}
            onChange={(e) => setReplyBody(e.target.value.slice(0, 2000))}
            rows={3}
            placeholder="Thanks — I'll address this next week."
            className="w-full rounded-lg border-gray-300 dark:border-gray-600 dark:bg-gray-700 text-sm"
            data-testid="faculty-challenge-reply-input"
          />
          <button
            type="submit"
            disabled={sending || !replyBody.trim()}
            className="rounded-lg bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white text-sm font-medium px-4 py-2 transition-colors"
            data-testid="faculty-challenge-reply-send"
          >
            {sending ? 'Sending…' : 'Send'}
          </button>
        </form>
      )}
    </div>
  );
}
