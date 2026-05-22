import { useState } from 'react';
import api from '../../api';
import { useAuth } from '../../auth/AuthContext';
import isSuperAdmin from '../../utils/auth/isSuperAdmin';

/**
 * Step 7_13 — Story 59 criterion 8.
 *
 * Explicit "Edit as Admin" affordance for content the Admin doesn't
 * own. Opens a modal that requires a non-empty reason note, then
 * POSTs `/api/v1/admin/override-edit/` with the patch payload. The
 * backend writes an `override_edit` AuditEvent with the reason so the
 * action is reviewable from the audit trail.
 *
 * Props:
 *   contentType   "reflection" | "note" — anything else the backend
 *                 rejects; PR2/PR3 extend the supported types.
 *   contentId     PK of the row being overridden.
 *   patchBuilder  Optional function returning the patch object. When
 *                 omitted, the modal renders a JSON textarea so the
 *                 caller can plug in a richer editor later without a
 *                 component refactor (most callers should supply
 *                 `patchBuilder`).
 *   onSaved       Optional callback fired after a successful override
 *                 with the API response body.
 *   label         Button label override. Defaults to "Edit as Admin".
 */
export default function EditAsAdminButton({
  contentType,
  contentId,
  patchBuilder,
  onSaved,
  label = 'Edit as Admin',
  className = '',
}) {
  const { user } = useAuth();
  const isAdmin = isSuperAdmin(user) || user?.role?.toLowerCase() === 'admin';
  const [open, setOpen] = useState(false);
  const [reason, setReason] = useState('');
  const [rawPatch, setRawPatch] = useState('{}');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  if (!isAdmin) return null;

  const resetState = () => {
    setReason('');
    setRawPatch('{}');
    setError('');
    setSaving(false);
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError('');
    if (!reason.trim()) {
      setError('Reason is required.');
      return;
    }
    let patch;
    if (typeof patchBuilder === 'function') {
      try {
        patch = patchBuilder();
      } catch (err) {
        setError(err?.message || 'Failed to build patch.');
        return;
      }
    } else {
      try {
        patch = JSON.parse(rawPatch || '{}');
      } catch {
        setError('Patch must be valid JSON.');
        return;
      }
    }
    setSaving(true);
    try {
      const resp = await api.post('/api/v1/admin/override-edit/', {
        content_type: contentType,
        content_id: contentId,
        reason,
        patch,
      });
      if (typeof onSaved === 'function') {
        onSaved(resp?.data);
      }
      setOpen(false);
      resetState();
    } catch (err) {
      const detail = err?.response?.data?.detail || err?.message || 'Override failed.';
      setError(detail);
    } finally {
      setSaving(false);
    }
  };

  return (
    <>
      <button
        type="button"
        data-testid="edit-as-admin-button"
        onClick={() => setOpen(true)}
        className={`inline-flex items-center px-2.5 py-1 rounded-md text-xs font-medium border border-red-300 bg-red-50 text-red-800 hover:bg-red-100 dark:bg-red-900/20 dark:border-red-700 dark:text-red-100 ${className}`}
      >
        {label}
      </button>
      {open && (
        <div
          data-testid="edit-as-admin-modal"
          role="dialog"
          aria-modal="true"
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
          onClick={(e) => {
            if (e.target === e.currentTarget && !saving) {
              setOpen(false);
              resetState();
            }
          }}
        >
          <form
            onSubmit={handleSubmit}
            className="w-full max-w-md rounded-xl bg-white dark:bg-gray-900 p-5 shadow-lg border border-gray-200 dark:border-gray-700"
          >
            <h2 className="text-base font-semibold text-gray-900 dark:text-white mb-1">
              Edit as Admin
            </h2>
            <p className="text-sm text-gray-600 dark:text-gray-300 mb-3">
              This action is recorded in the audit trail with your reason.
            </p>
            <label className="block text-xs font-medium text-gray-700 dark:text-gray-200 mb-1" htmlFor="override-reason">
              Reason
              <span className="text-red-600 ml-0.5" aria-hidden>*</span>
            </label>
            <textarea
              id="override-reason"
              data-testid="edit-as-admin-reason"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              rows={3}
              aria-required="true"
              className="w-full rounded-md border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 p-2 text-sm"
            />
            {!patchBuilder && (
              <>
                <label className="block text-xs font-medium text-gray-700 dark:text-gray-200 mb-1 mt-3" htmlFor="override-patch">
                  Patch (JSON)
                </label>
                <textarea
                  id="override-patch"
                  data-testid="edit-as-admin-patch"
                  value={rawPatch}
                  onChange={(e) => setRawPatch(e.target.value)}
                  rows={5}
                  className="w-full rounded-md border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 p-2 text-sm font-mono"
                />
              </>
            )}
            {error && (
              <p
                data-testid="edit-as-admin-error"
                className="mt-2 text-sm text-red-700 dark:text-red-300"
              >
                {error}
              </p>
            )}
            <div className="mt-4 flex items-center justify-end gap-2">
              <button
                type="button"
                onClick={() => {
                  setOpen(false);
                  resetState();
                }}
                disabled={saving}
                className="text-sm text-gray-600 dark:text-gray-300 hover:underline"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={saving}
                data-testid="edit-as-admin-submit"
                className="inline-flex items-center px-3 py-1.5 rounded-md text-sm font-medium bg-red-600 text-white hover:bg-red-700 disabled:opacity-60"
              >
                {saving ? 'Saving…' : 'Override and save'}
              </button>
            </div>
          </form>
        </div>
      )}
    </>
  );
}
