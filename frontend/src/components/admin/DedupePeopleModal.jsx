import { useEffect, useMemo, useState } from 'react';
import {
  previewAdminPeopleDedupe,
  commitAdminPeopleDedupe,
} from '../../api/admin';

function classNames(...args) {
  return args.filter(Boolean).join(' ');
}

function campminderId(person) {
  return person?.external_ids?.campminder_id || '';
}

/**
 * Modal for merging duplicate Person records selected on the Admin People page.
 */
export default function DedupePeopleModal({
  selectedPeople,
  onClose,
  onCompleted,
}) {
  const people = useMemo(
    () => Array.from(selectedPeople.values()).filter(Boolean),
    [selectedPeople],
  );
  const [winnerId, setWinnerId] = useState(people[0]?.id ?? null);
  const [loserStrategies, setLoserStrategies] = useState({});
  const [forceUser, setForceUser] = useState(false);
  const [confirmDestructive, setConfirmDestructive] = useState(false);
  const [reason, setReason] = useState('');
  const [preview, setPreview] = useState(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewError, setPreviewError] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState('');

  useEffect(() => {
    const defaults = {};
    for (const person of people) {
      if (person.id !== winnerId) {
        defaults[person.id] = 'repoint';
      }
    }
    setLoserStrategies(defaults);
    setPreview(null);
    setPreviewError('');
    setSubmitError('');
  }, [winnerId, people]);

  const losers = people.filter((person) => person.id !== winnerId);

  const buildPayload = () => ({
    winner_id: winnerId,
    losers: losers.map((person) => ({
      person_id: person.id,
      strategy: loserStrategies[person.id] || 'repoint',
      force_user: forceUser,
    })),
    confirm_destructive: confirmDestructive,
    reason: reason.trim(),
  });

  const handlePreview = async () => {
    if (!winnerId || losers.length === 0) return;
    setPreviewLoading(true);
    setPreviewError('');
    setPreview(null);
    try {
      const data = await previewAdminPeopleDedupe({
        winner_id: winnerId,
        losers: losers.map((person) => ({
          person_id: person.id,
          strategy: loserStrategies[person.id] || 'repoint',
          force_user: forceUser,
        })),
        confirm_destructive: confirmDestructive,
      });
      setPreview(data);
      if (!data.ok) {
        setPreviewError('Resolve the blockers below before deduping.');
      }
    } catch (err) {
      const data = err?.response?.data;
      if (data?.plans) {
        setPreview(data);
      }
      setPreviewError(data?.detail || 'Preview failed.');
    } finally {
      setPreviewLoading(false);
    }
  };

  const handleApply = async () => {
    if (!reason.trim()) {
      setSubmitError('A reason is required.');
      return;
    }
    setSubmitting(true);
    setSubmitError('');
    try {
      const result = await commitAdminPeopleDedupe(buildPayload());
      onCompleted(result);
    } catch (err) {
      const data = err?.response?.data;
      if (data?.plans) {
        setPreview(data);
      }
      setSubmitError(data?.detail || 'Dedupe failed.');
    } finally {
      setSubmitting(false);
    }
  };

  const needsForceUser = preview?.plans?.some(
    (plan) => plan.blockers?.some((blocker) => blocker.includes('different Users')),
  );
  const needsDestructiveConfirm = preview?.plans?.some(
    (plan) => plan.blockers?.some((blocker) => blocker.includes('confirm_destructive')),
  );

  return (
    <div
      role="dialog"
      data-testid="dedupe-people-modal"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
      onClick={(e) => { if (e.target === e.currentTarget && !submitting) onClose(); }}
    >
      <div className="w-full max-w-3xl max-h-[90vh] overflow-y-auto rounded-xl bg-white p-5 shadow-lg dark:bg-gray-900 space-y-4">
        <header>
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Dedupe people</h2>
          <p className="text-sm text-gray-500 mt-1">
            Choose the canonical Person to keep, then decide how to handle each duplicate.
          </p>
        </header>

        <section>
          <h3 className="text-sm font-medium text-gray-900 dark:text-white mb-2">Keep this person</h3>
          <div className="space-y-2">
            {people.map((person) => (
              <label
                key={person.id}
                className={classNames(
                  'flex items-start gap-3 rounded-md border p-3 cursor-pointer',
                  winnerId === person.id
                    ? 'border-indigo-500 bg-indigo-50 dark:bg-indigo-900/20'
                    : 'border-gray-200 dark:border-gray-700',
                )}
              >
                <input
                  type="radio"
                  name="dedupe-winner"
                  data-testid={`dedupe-winner-${person.id}`}
                  checked={winnerId === person.id}
                  onChange={() => setWinnerId(person.id)}
                  className="mt-1"
                />
                <div className="min-w-0">
                  <p className="font-medium text-sm">{person.full_name}</p>
                  <p className="text-xs text-gray-500">{person.email || 'no email'}</p>
                  <p className="text-xs text-gray-500">
                    User: {person.has_user ? 'linked' : 'none'}
                    {campminderId(person) ? ` · Campminder ${campminderId(person)}` : ''}
                  </p>
                  <p className="text-xs text-gray-500">
                    Memberships: {(person.memberships || []).length}
                  </p>
                </div>
              </label>
            ))}
          </div>
        </section>

        {losers.length > 0 && (
          <section>
            <h3 className="text-sm font-medium text-gray-900 dark:text-white mb-2">
              Handle duplicates
            </h3>
            <div className="space-y-2">
              {losers.map((person) => (
                <div
                  key={person.id}
                  data-testid={`dedupe-loser-${person.id}`}
                  className="rounded-md border border-gray-200 dark:border-gray-700 p-3"
                >
                  <p className="font-medium text-sm">{person.full_name}</p>
                  <p className="text-xs text-gray-500 mb-2">{person.email || 'no email'}</p>
                  <label className="block text-xs font-medium text-gray-700 dark:text-gray-300">
                    Strategy
                    <select
                      value={loserStrategies[person.id] || 'repoint'}
                      onChange={(e) => setLoserStrategies({
                        ...loserStrategies,
                        [person.id]: e.target.value,
                      })}
                      className="mt-1 block w-full rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 p-2 text-sm"
                    >
                      <option value="repoint">Roll into winner</option>
                      <option value="discard">Discard duplicate</option>
                    </select>
                  </label>
                </div>
              ))}
            </div>
          </section>
        )}

        <div className="flex flex-wrap items-center gap-4">
          {needsForceUser && (
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={forceUser}
                onChange={(e) => setForceUser(e.target.checked)}
                data-testid="dedupe-force-user"
              />
              Keep winner&apos;s login (unlink duplicate users)
            </label>
          )}
          {needsDestructiveConfirm && (
            <label className="flex items-center gap-2 text-sm text-amber-800">
              <input
                type="checkbox"
                checked={confirmDestructive}
                onChange={(e) => setConfirmDestructive(e.target.checked)}
                data-testid="dedupe-confirm-destructive"
              />
              Confirm destructive delete of reflection subjects
            </label>
          )}
        </div>

        <label className="block text-xs font-medium text-gray-700 dark:text-gray-300">
          Reason (required)
          <input
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            data-testid="dedupe-reason"
            className="mt-1 block w-full rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 p-2 text-sm"
            placeholder="Why are these records being merged?"
          />
        </label>

        <div className="flex items-center gap-2">
          <button
            type="button"
            data-testid="dedupe-preview"
            disabled={previewLoading || !winnerId || losers.length === 0}
            onClick={handlePreview}
            className="px-3 py-1.5 rounded-md text-sm border border-indigo-300 text-indigo-700 hover:bg-indigo-50 disabled:opacity-50"
          >
            {previewLoading ? 'Previewing…' : 'Preview changes'}
          </button>
        </div>

        {previewError && <p className="text-sm text-red-700">{previewError}</p>}
        {submitError && <p className="text-sm text-red-700">{submitError}</p>}

        {preview?.plans?.length > 0 && (
          <section
            data-testid="dedupe-preview-results"
            className="rounded-md border border-gray-200 dark:border-gray-700 p-3 space-y-3"
          >
            <p className="text-sm font-medium">
              Preview {preview.ok ? 'ready' : 'blocked'}
            </p>
            {preview.plans.map((plan) => (
              <div key={plan.person_id || plan.loser_id} className="text-sm space-y-1">
                <p className="font-medium">
                  Person #{plan.person_id || plan.loser_id}
                  {' '}
                  ({plan.strategy || 'repoint'})
                </p>
                {(plan.blockers || []).map((blocker) => (
                  <p key={blocker} className="text-xs text-red-700">{blocker}</p>
                ))}
                {(plan.actions || []).map((action) => (
                  <p key={`${action.model}-${action.description}`} className="text-xs text-gray-600">
                    [{action.model}] {action.description}
                  </p>
                ))}
              </div>
            ))}
          </section>
        )}

        <div className="flex items-center justify-end gap-2 pt-1">
          <button
            type="button"
            onClick={onClose}
            disabled={submitting}
            className="text-sm text-gray-600 hover:underline disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            type="button"
            data-testid="dedupe-apply"
            disabled={
              submitting
              || !preview?.ok
              || !reason.trim()
              || losers.length === 0
            }
            onClick={handleApply}
            className="px-3 py-1.5 rounded-md text-sm bg-red-600 text-white disabled:opacity-50"
          >
            {submitting ? 'Deduping…' : 'Confirm dedupe'}
          </button>
        </div>
      </div>
    </div>
  );
}
