import { useState } from 'react';
import {
  previewAdminPersonDelete,
  commitAdminPersonDelete,
} from '../../api/admin';

/**
 * Modal for permanently deleting a Person from the admin People page.
 */
export default function DeletePersonModal({ person, onClose, onCompleted }) {
  const [confirmDestructive, setConfirmDestructive] = useState(false);
  const [reason, setReason] = useState('');
  const [preview, setPreview] = useState(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewError, setPreviewError] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState('');

  const needsDestructiveConfirm = preview?.blockers?.some(
    (blocker) => blocker.includes('confirm_destructive'),
  );

  const handlePreview = async () => {
    setPreviewLoading(true);
    setPreviewError('');
    setPreview(null);
    try {
      const data = await previewAdminPersonDelete(person.id, {
        confirm_destructive: confirmDestructive,
      });
      setPreview(data);
      if (!data.ok) {
        setPreviewError('Resolve the blockers below before deleting.');
      }
    } catch (err) {
      const data = err?.response?.data;
      if (data?.person_id) {
        setPreview(data);
      }
      setPreviewError(data?.detail || 'Preview failed.');
    } finally {
      setPreviewLoading(false);
    }
  };

  const handleDelete = async () => {
    if (!reason.trim()) {
      setSubmitError('A reason is required.');
      return;
    }
    setSubmitting(true);
    setSubmitError('');
    try {
      const result = await commitAdminPersonDelete(person.id, {
        reason: reason.trim(),
        confirm_destructive: confirmDestructive,
      });
      onCompleted(result);
    } catch (err) {
      const data = err?.response?.data;
      if (data?.person_id) {
        setPreview(data);
      }
      setSubmitError(data?.detail || 'Delete failed.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div
      role="dialog"
      data-testid="delete-person-modal"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
      onClick={(e) => { if (e.target === e.currentTarget && !submitting) onClose(); }}
    >
      <div className="w-full max-w-lg max-h-[90vh] overflow-y-auto rounded-xl bg-white p-5 shadow-lg dark:bg-gray-900 space-y-4">
        <header>
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Delete person</h2>
          <p className="text-sm text-gray-500 mt-1">
            Permanently remove <strong>{person.full_name}</strong> (Person #{person.id}).
            Active memberships are deactivated first; linked content may be removed.
          </p>
        </header>

        {needsDestructiveConfirm && (
          <label
            className="flex items-start gap-2 rounded-md border border-amber-300 bg-amber-50 p-3 text-sm text-amber-950 dark:border-amber-700 dark:bg-amber-900/20 dark:text-amber-100"
          >
            <input
              type="checkbox"
              checked={confirmDestructive}
              onChange={(e) => setConfirmDestructive(e.target.checked)}
              data-testid="delete-confirm-destructive"
              className="mt-0.5"
            />
            <span>
              This person is the subject of reflections. Confirm destructive delete of that data.
            </span>
          </label>
        )}

        <label className="block text-xs font-medium text-gray-700 dark:text-gray-300">
          Reason (required)
          <input
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            data-testid="delete-person-reason"
            className="mt-1 block w-full rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 p-2 text-sm"
            placeholder="Why is this record being deleted?"
          />
        </label>

        <div className="flex items-center gap-2">
          <button
            type="button"
            data-testid="delete-person-preview"
            disabled={previewLoading}
            onClick={handlePreview}
            className="px-3 py-1.5 rounded-md text-sm border border-indigo-300 text-indigo-700 hover:bg-indigo-50 disabled:opacity-50"
          >
            {previewLoading ? 'Previewing…' : 'Preview delete'}
          </button>
        </div>

        {previewError && <p className="text-sm text-red-700">{previewError}</p>}
        {submitError && <p className="text-sm text-red-700">{submitError}</p>}

        {preview && (
          <section
            data-testid="delete-person-preview-results"
            className="rounded-md border border-gray-200 dark:border-gray-700 p-3 space-y-2 text-sm"
          >
            <p className="font-medium">
              Preview {preview.ok ? 'ready' : 'blocked'}
            </p>
            {(preview.blockers || []).map((blocker) => (
              <p key={blocker} className="text-xs text-red-700">{blocker}</p>
            ))}
            {(preview.actions || []).map((action) => (
              <p key={`${action.model}-${action.description}`} className="text-xs text-gray-600">
                [{action.model}] {action.description}
              </p>
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
            data-testid="delete-person-confirm"
            disabled={submitting || !preview?.ok || !reason.trim()}
            onClick={handleDelete}
            className="px-3 py-1.5 rounded-md text-sm bg-red-600 text-white disabled:opacity-50"
          >
            {submitting ? 'Deleting…' : 'Delete person'}
          </button>
        </div>
      </div>
    </div>
  );
}
