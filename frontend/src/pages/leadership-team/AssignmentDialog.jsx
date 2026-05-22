/**
 * LT Assignment Dialog — Step 7_12, Story 52.
 *
 * Modal-style form for creating a TemplateAssignment. Caller controls
 * the open/close state; on success it calls ``onCreated(assignment)``.
 * Handles 409 conflicts inline by surfacing the conflict list and
 * collecting a ``conflict_resolution`` choice before retrying.
 */

import { useCallback, useState } from 'react';
import { createAssignment } from '../../api/leadershipTeam';
import { useAuth } from '../../auth/AuthContext';

const TARGET_TYPES = [
  { value: 'role', label: 'Role' },
  { value: 'individuals', label: 'Individuals' },
  { value: 'tag_group', label: 'Tag group' },
];

const ROLE_OPTIONS = [
  'counselor', 'junior_counselor', 'specialist', 'general_counselor',
  'unit_head', 'leadership_team', 'kitchen_staff', 'maintenance',
  'housekeeping', 'camper_care', 'health_center', 'madrich', 'faculty',
];

const CADENCE_OVERRIDES = ['', 'daily', 'weekly', 'biweekly', 'monthly', 'on_demand'];

const CONFLICT_CHOICES = [
  { value: 'replace', label: 'Replace existing (end prior assignment)' },
  { value: 'run_both', label: 'Run both' },
  { value: 'cancel', label: 'Cancel — keep prior, do not create' },
];

export default function AssignmentDialog({ template, onClose, onCreated }) {
  const { orgSlug } = useAuth();
  const [targetType, setTargetType] = useState('role');
  const [role, setRole] = useState(template?.role ?? 'counselor');
  const [membershipIds, setMembershipIds] = useState('');
  const [tag, setTag] = useState('');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [cadenceOverride, setCadenceOverride] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [conflicts, setConflicts] = useState([]);
  const [resolution, setResolution] = useState('');

  const buildPayload = useCallback(() => {
    const target_payload = (() => {
      if (targetType === 'role') return { role };
      if (targetType === 'individuals') {
        const ids = membershipIds
          .split(',')
          .map((s) => parseInt(s.trim(), 10))
          .filter((n) => Number.isFinite(n));
        return { membership_ids: ids };
      }
      return { tag };
    })();
    const body = {
      template: template?.id,
      target_type: targetType,
      target_payload,
      start_date: startDate,
    };
    if (endDate) body.end_date = endDate;
    if (cadenceOverride) body.cadence_override = cadenceOverride;
    return body;
  }, [targetType, role, membershipIds, tag, startDate, endDate, cadenceOverride, template]);

  const submit = async () => {
    setError('');
    if (!template?.id) { setError('Choose a template first.'); return; }
    if (!startDate) { setError('Start date is required.'); return; }
    if (targetType === 'role' && !role) { setError('Pick a role.'); return; }
    if (targetType === 'individuals' && !membershipIds.trim()) {
      setError('Enter at least one membership ID.');
      return;
    }
    if (targetType === 'tag_group' && !tag.trim()) {
      setError('Enter a tag.');
      return;
    }
    setSubmitting(true);
    try {
      const payload = buildPayload();
      if (conflicts.length > 0) {
        if (!resolution) {
          setError('Pick how to resolve the conflict.');
          setSubmitting(false);
          return;
        }
        payload.conflict_resolution = resolution;
      }
      const data = await createAssignment(orgSlug, payload);
      if (onCreated) onCreated(data);
      onClose?.();
    } catch (err) {
      const status = err?.response?.status;
      if (status === 409) {
        const body = err.response.data ?? {};
        setConflicts(body.conflicts ?? []);
        setError(body.detail ?? 'There is a conflicting assignment.');
        setResolution('');
      } else {
        const detail = err?.response?.data?.detail
          ?? err?.response?.data?.errors
          ?? 'Failed to create assignment.';
        setError(typeof detail === 'string' ? detail : JSON.stringify(detail));
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 bg-black/40 flex items-center justify-center px-4"
      data-testid="lt-assignment-dialog"
    >
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-lg max-w-lg w-full p-5 max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-base font-semibold text-gray-900 dark:text-white">
            Assign template
          </h2>
          <button
            type="button"
            onClick={onClose}
            className="text-sm text-gray-500 hover:text-gray-700"
            data-testid="lt-assignment-close"
          >
            ✕
          </button>
        </div>

        <p className="text-sm text-gray-600 dark:text-gray-300 mb-3">
          {template?.name} <span className="text-xs">v{template?.version}</span>
        </p>

        <div className="space-y-3">
          <div className="flex gap-2" role="tablist" data-testid="lt-assignment-target-tabs">
            {TARGET_TYPES.map((t) => (
              <button
                key={t.value}
                type="button"
                role="tab"
                aria-selected={targetType === t.value}
                onClick={() => setTargetType(t.value)}
                className={`text-sm px-3 py-1 rounded-md ${
                  targetType === t.value
                    ? 'bg-indigo-600 text-white'
                    : 'border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300'
                }`}
                data-testid={`lt-assignment-target-${t.value}`}
              >
                {t.label}
              </button>
            ))}
          </div>

          {targetType === 'role' && (
            <label className="block text-sm text-gray-700 dark:text-gray-300">
              Role
              <select
                value={role}
                onChange={(e) => setRole(e.target.value)}
                className="mt-1 w-full rounded-md border-gray-300 dark:border-gray-600 dark:bg-gray-700 text-sm"
                data-testid="lt-assignment-role"
              >
                {ROLE_OPTIONS.map((r) => <option key={r} value={r}>{r}</option>)}
              </select>
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                Membership in this role auto-includes future additions while the assignment is active.
              </p>
            </label>
          )}

          {targetType === 'individuals' && (
            <label className="block text-sm text-gray-700 dark:text-gray-300">
              Membership IDs (comma-separated)
              <input
                type="text"
                value={membershipIds}
                onChange={(e) => setMembershipIds(e.target.value)}
                placeholder="123, 456"
                className="mt-1 w-full rounded-md border-gray-300 dark:border-gray-600 dark:bg-gray-700 text-sm"
                data-testid="lt-assignment-individuals"
              />
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                Static snapshot — added members later need a new assignment.
              </p>
            </label>
          )}

          {targetType === 'tag_group' && (
            <label className="block text-sm text-gray-700 dark:text-gray-300">
              Membership tag
              <input
                type="text"
                value={tag}
                onChange={(e) => setTag(e.target.value)}
                placeholder="e.g. kitchen-lead"
                className="mt-1 w-full rounded-md border-gray-300 dark:border-gray-600 dark:bg-gray-700 text-sm"
                data-testid="lt-assignment-tag"
              />
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                Dynamic — any membership with this tag is included.
              </p>
            </label>
          )}

          <div className="flex gap-3">
            <label className="flex-1 text-sm text-gray-700 dark:text-gray-300">
              Start date
              <input
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                className="mt-1 w-full rounded-md border-gray-300 dark:border-gray-600 dark:bg-gray-700 text-sm"
                data-testid="lt-assignment-start"
              />
            </label>
            <label className="flex-1 text-sm text-gray-700 dark:text-gray-300">
              End date (optional)
              <input
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
                className="mt-1 w-full rounded-md border-gray-300 dark:border-gray-600 dark:bg-gray-700 text-sm"
                data-testid="lt-assignment-end"
              />
            </label>
          </div>

          <label className="block text-sm text-gray-700 dark:text-gray-300">
            Cadence override (optional)
            <select
              value={cadenceOverride}
              onChange={(e) => setCadenceOverride(e.target.value)}
              className="mt-1 w-full rounded-md border-gray-300 dark:border-gray-600 dark:bg-gray-700 text-sm"
              data-testid="lt-assignment-cadence"
            >
              {CADENCE_OVERRIDES.map((c) => (
                <option key={c} value={c}>{c || 'inherit from template'}</option>
              ))}
            </select>
          </label>

          {conflicts.length > 0 && (
            <div
              className="rounded-md border border-amber-300 dark:border-amber-700 bg-amber-50 dark:bg-amber-900/20 p-3 text-sm text-amber-900 dark:text-amber-200"
              data-testid="lt-assignment-conflicts"
            >
              <p className="font-medium mb-1">Conflicting assignments:</p>
              <ul className="list-disc list-inside text-xs space-y-0.5 mb-2">
                {conflicts.map((c) => (
                  <li key={c.id}>
                    #{c.id}: {c.start_date} – {c.end_date ?? '∞'} ({c.target_type})
                  </li>
                ))}
              </ul>
              <fieldset className="space-y-1" role="radiogroup">
                {CONFLICT_CHOICES.map((c) => (
                  <label key={c.value} className="flex items-center gap-2 text-sm">
                    <input
                      type="radio"
                      name="lt-conflict-resolution"
                      value={c.value}
                      checked={resolution === c.value}
                      onChange={() => setResolution(c.value)}
                      data-testid={`lt-conflict-${c.value}`}
                    />
                    {c.label}
                  </label>
                ))}
              </fieldset>
            </div>
          )}

          {error && (
            <p className="text-red-600 dark:text-red-400 text-sm" data-testid="lt-assignment-error">
              {error}
            </p>
          )}
        </div>

        <div className="flex justify-end gap-2 mt-4">
          <button
            type="button"
            onClick={onClose}
            className="text-sm rounded-md border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 px-3 py-1.5"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={submit}
            disabled={submitting}
            className="text-sm rounded-md bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white px-3 py-1.5"
            data-testid="lt-assignment-submit"
          >
            {submitting ? 'Creating…' : 'Create assignment'}
          </button>
        </div>
      </div>
    </div>
  );
}
