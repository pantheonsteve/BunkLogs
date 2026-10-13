/**
 * Madrich challenge detail — Step 4_8, MA7.
 *
 * Author identity follows the same redaction the list uses: the
 * backend only un-redacts when the viewer is the author, so
 * `!author.redacted` is the "is mine" signal for showing the
 * Withdraw button (no responses yet, still open).
 */

import { useCallback, useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { fetchChallenge, withdrawChallenge } from '../../api/madrichChallenges';
import { useAuth } from '../../auth/AuthContext';
import ChallengeDetailLayout from '../../components/ChallengeDetailLayout';
import Button from '../../components/ui/Button';

export default function MadrichChallengeDetail() {
  const { challengeId } = useParams();
  const { orgSlug } = useAuth();
  const navigate = useNavigate();

  const [challenge, setChallenge] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [withdrawing, setWithdrawing] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await fetchChallenge(orgSlug, challengeId);
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

  const handleWithdraw = async () => {
    setWithdrawing(true);
    try {
      await withdrawChallenge(orgSlug, challengeId);
      navigate('/madrich/challenges');
    } catch {
      setError('Could not withdraw this challenge.');
      setWithdrawing(false);
    }
  };

  if (loading) {
    return (
      <div className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-2xl mx-auto" data-testid="md-challenge-detail-loading">
        <p className="text-muted">Loading…</p>
      </div>
    );
  }

  if (error || !challenge) {
    return (
      <div className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-2xl mx-auto" data-testid="md-challenge-detail-error">
        <p className="text-red-600 dark:text-red-400">{error || 'Challenge not found.'}</p>
      </div>
    );
  }

  const isAuthor = !challenge.author?.redacted;
  const authorLabel = isAuthor
    ? 'You reported this'
    : `Submitted by ${challenge.author?.display || 'A Madrich'}`;
  const canWithdraw = isAuthor && challenge.status === 'open' && (challenge.responses || []).length === 0;
  const dateLabel = new Date(`${challenge.session_date}T00:00:00`).toLocaleDateString(undefined, {
    month: 'long',
    day: 'numeric',
    year: 'numeric',
  });

  return (
    <ChallengeDetailLayout
      backTo="/madrich/challenges"
      backLabel="Back to challenges"
      backTestId="md-challenge-detail-back"
      title={challenge.category_label}
      status={challenge.status}
      statusTestId="md-challenge-detail-status"
      meta={`${authorLabel} · ${dateLabel}`}
      metaTestId="md-challenge-detail-author"
      body={challenge.body}
      bodyTestId="md-challenge-detail-body"
      responsesLabel="Responses"
      responses={(challenge.responses || []).map((r) => ({
        id: r.id,
        author: r.author?.display_name || r.author?.display,
        body: r.body,
      }))}
      emptyResponsesTestId="md-challenge-no-responses"
      responseTestId={(id) => `md-challenge-response-${id}`}
      showDone
      doneTo="/madrich"
      doneTestId="md-challenge-done"
    >
      {canWithdraw && (
        <Button
          variant="danger"
          onClick={handleWithdraw}
          disabled={withdrawing}
          data-testid="md-challenge-withdraw"
        >
          {withdrawing ? 'Withdrawing…' : 'Withdraw challenge'}
        </Button>
      )}
    </ChallengeDetailLayout>
  );
}
