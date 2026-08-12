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

const STATUS_STYLES = {
  open: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/40 dark:text-yellow-300',
  acknowledged: 'bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-300',
  resolved: 'bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-300',
};

function StatusBadge({ status }) {
  const cls = STATUS_STYLES[status] || 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300';
  const label = status ? status.charAt(0).toUpperCase() + status.slice(1) : 'Unknown';
  return (
    <span className={`shrink-0 text-xs font-medium px-2 py-0.5 rounded-full ${cls}`} data-testid="md-challenge-detail-status">
      {label}
    </span>
  );
}

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
      <div className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-[96rem] mx-auto" data-testid="md-challenge-detail-loading">
        <p className="text-gray-500 dark:text-gray-400">Loading…</p>
      </div>
    );
  }

  if (error || !challenge) {
    return (
      <div className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-[96rem] mx-auto" data-testid="md-challenge-detail-error">
        <p className="text-red-600 dark:text-red-400">{error || 'Challenge not found.'}</p>
      </div>
    );
  }

  const isAuthor = !challenge.author?.redacted;
  const authorLabel = isAuthor
    ? `You reported this`
    : `Submitted by ${challenge.author?.display || 'A Madrich'}`;
  const canWithdraw = isAuthor && challenge.status === 'open' && (challenge.responses || []).length === 0;
  const dateLabel = new Date(`${challenge.session_date}T00:00:00`).toLocaleDateString(undefined, {
    month: 'long',
    day: 'numeric',
    year: 'numeric',
  });

  return (
    <div className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-2xl mx-auto space-y-4">
      <div className="flex items-center justify-between gap-3">
        <span className="text-xs font-medium px-2 py-0.5 rounded-full bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300">
          {challenge.category_label}
        </span>
        <StatusBadge status={challenge.status} />
      </div>

      <div>
        <p className="text-sm text-gray-500 dark:text-gray-400" data-testid="md-challenge-detail-author">
          {authorLabel} · {dateLabel}
        </p>
        <p className="text-gray-900 dark:text-white mt-2 whitespace-pre-wrap" data-testid="md-challenge-detail-body">
          {challenge.body}
        </p>
      </div>

      {canWithdraw && (
        <button
          type="button"
          onClick={handleWithdraw}
          disabled={withdrawing}
          className="rounded-lg border border-red-300 dark:border-red-700 text-red-600 dark:text-red-400 text-sm font-medium px-4 py-2 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors disabled:opacity-50"
          data-testid="md-challenge-withdraw"
        >
          {withdrawing ? 'Withdrawing…' : 'Withdraw challenge'}
        </button>
      )}

      <section aria-label="Faculty responses" className="space-y-3">
        <h2 className="text-sm font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide">
          Responses
        </h2>
        {(challenge.responses || []).length === 0 ? (
          <p className="text-sm text-gray-500 dark:text-gray-400" data-testid="md-challenge-no-responses">
            No responses yet.
          </p>
        ) : (
          <ul className="space-y-3">
            {challenge.responses.map((r) => (
              <li
                key={r.id}
                className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-4"
                data-testid={`md-challenge-response-${r.id}`}
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
    </div>
  );
}
