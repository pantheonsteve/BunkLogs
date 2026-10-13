/**
 * Faculty challenge detail — Step 4_8, MA7.
 *
 * Full author identity + status controls (Acknowledge / Resolve) +
 * reply composer. Resolved threads are read-only in Tier 1.
 */

import { useCallback, useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import {
  fetchFacultyChallenge,
  replyToChallenge,
  updateChallengeStatus,
} from '../../api/facultyChallenges';
import { useAuth } from '../../auth/AuthContext';
import ChallengeDetailLayout from '../../components/ChallengeDetailLayout';
import Button from '../../components/ui/Button';
import PageHeader from '../../components/ui/PageHeader';

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

  const handleStatus = async (status) => {
    setUpdatingStatus(true);
    try {
      const updated = await updateChallengeStatus(orgSlug, challengeId, status);
      setChallenge(updated);
    } catch (err) {
      setError(flattenError(err, 'Could not update the status.'));
    } finally {
      setUpdatingStatus(false);
    }
  };

  const back = {
    backTo: '/faculty/challenges',
    backLabel: 'Back to challenges',
    backTestId: 'faculty-challenge-detail-back',
  };

  if (loading || !challenge) {
    return (
      <div
        className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-2xl mx-auto"
        data-testid={loading ? 'faculty-challenge-detail-loading' : 'faculty-challenge-detail-error'}
      >
        <PageHeader title="Challenge" {...back} />
        <p className={loading ? 'text-muted' : 'text-red-600 dark:text-red-400'}>
          {loading ? 'Loading…' : (error || 'Challenge not found.')}
        </p>
      </div>
    );
  }

  const dateLabel = new Date(`${challenge.session_date}T00:00:00`).toLocaleDateString(undefined, {
    month: 'long',
    day: 'numeric',
    year: 'numeric',
  });
  const isResolved = challenge.status === 'resolved';
  const responses = challenge.responses || [];

  return (
    <ChallengeDetailLayout
      {...back}
      title={challenge.category_label}
      status={challenge.status}
      statusTestId="faculty-challenge-status"
      meta={`${challenge.author?.display_name || ''} · ${challenge.assignment_group?.name || ''} · ${dateLabel}`}
      metaTestId="faculty-challenge-detail-author"
      body={challenge.body}
      bodyTestId="faculty-challenge-detail-body"
      responses={responses.map((r) => ({
        id: r.id,
        author: r.author?.display_name || r.author?.display,
        body: r.body,
      }))}
      emptyResponsesTestId="faculty-challenge-no-responses"
      responseTestId={(id) => `faculty-challenge-response-${id}`}
      showDone={responses.length > 0}
      doneTo="/faculty/challenges"
      doneTestId="faculty-challenge-done"
    >
      {!isResolved && (
        <div className="flex gap-3">
          {challenge.status === 'open' && (
            <Button
              variant="secondary"
              onClick={() => handleStatus('acknowledged')}
              disabled={updatingStatus}
              data-testid="faculty-challenge-acknowledge"
            >
              Acknowledge
            </Button>
          )}
          <Button
            variant="secondary"
            onClick={() => handleStatus('resolved')}
            disabled={updatingStatus}
            data-testid="faculty-challenge-resolve"
          >
            Mark resolved
          </Button>
        </div>
      )}

      {error && (
        <p className="text-red-600 dark:text-red-400 text-sm" data-testid="faculty-challenge-detail-error-inline">
          {error}
        </p>
      )}

      {!isResolved && (
        <form onSubmit={handleReply} className="space-y-2">
          <label htmlFor="faculty-challenge-reply" className="block text-sm font-medium text-ink">
            Reply
          </label>
          <textarea
            id="faculty-challenge-reply"
            value={replyBody}
            onChange={(e) => setReplyBody(e.target.value.slice(0, 2000))}
            rows={3}
            placeholder="Thanks — I'll address this next week."
            className="w-full rounded-lg border-line bg-white dark:bg-gray-900 text-sm text-ink"
            data-testid="faculty-challenge-reply-input"
          />
          <Button
            type="submit"
            disabled={sending || !replyBody.trim()}
            data-testid="faculty-challenge-reply-send"
          >
            {sending ? 'Sending…' : 'Send'}
          </Button>
        </form>
      )}
    </ChallengeDetailLayout>
  );
}
