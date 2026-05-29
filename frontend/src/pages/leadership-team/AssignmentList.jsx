/**
 * AssignmentList — embedded "Form assignments" section in the LT template builder.
 *
 * Renders all TemplateAssignments for a published template. Shows status badges,
 * target name, date range, required chip, and per-status actions (Cancel for
 * scheduled, End today for active). Gated on status === 'published' in the parent.
 *
 * FA-E, Step 7_20 frontend.
 */

import { useCallback, useEffect, useState } from 'react';
import { cancelAssignment, listAssignments, patchAssignment } from '../../api/leadershipTeam';

// ─── Helpers ────────────────────────────────────────────────────────────────

function today() {
  return new Date().toISOString().slice(0, 10);
}

function dateRange(start, end) {
  if (!end) return `${start} → ongoing`;
  return `${start} → ${end}`;
}

function describeTarget(a) {
  if (a.target_type === 'assignment_group') {
    return a.assignment_group_name ?? `Group #${a.assignment_group}`;
  }
  if (a.target_type === 'role') {
    return `Role: ${a.target_payload?.role ?? '—'}`;
  }
  if (a.target_type === 'tag_group') {
    return `Tag: ${a.target_payload?.tag ?? '—'}`;
  }
  if (a.target_type === 'individuals') {
    const n = Array.isArray(a.target_payload?.membership_ids)
      ? a.target_payload.membership_ids.length
      : 0;
    return `Individuals (${n})`;
  }
  return a.target_type ?? '—';
}

// ─── Status badge ────────────────────────────────────────────────────────────

const STATUS_STYLES = {
  active: 'bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-300',
  scheduled: 'bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-300',
  ended: 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400',
  cancelled: 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400',
};

function StatusBadge({ status }) {
  return (
    <span
      className={`text-xs font-medium px-2 py-0.5 rounded-full ${STATUS_STYLES[status] ?? STATUS_STYLES.ended}`}
      data-testid={`assignment-status-${status}`}
    >
      {status}
    </span>
  );
}

// ─── Skeleton ────────────────────────────────────────────────────────────────

function Skeleton() {
  return (
    <div className="space-y-2 animate-pulse" data-testid="assignment-list-skeleton">
      {[0, 1, 2].map((i) => (
        <div key={i} className="h-14 rounded-md bg-gray-100 dark:bg-gray-700" />
      ))}
    </div>
  );
}

// ─── Single assignment row ───────────────────────────────────────────────────

function AssignmentRow({ assignment, onCancelled, onEnded }) {
  const [pending, setPending] = useState(false);

  const handleCancel = async () => {
    const ok = window.confirm('Cancel this assignment? This cannot be undone.');
    if (!ok) return;
    setPending(true);
    try {
      await onCancelled(assignment);
    } finally {
      setPending(false);
    }
  };

  const handleEndToday = async () => {
    const ok = window.confirm(
      `End assignment "${assignment.display_title}" today? Responses to date are kept.`,
    );
    if (!ok) return;
    setPending(true);
    try {
      await onEnded(assignment);
    } finally {
      setPending(false);
    }
  };

  const a = assignment;

  return (
    <li
      className="flex flex-wrap items-start justify-between gap-3 rounded-md border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 px-3 py-2.5 text-sm"
      data-testid={`assignment-row-${a.id}`}
    >
      <div className="flex-1 min-w-0 space-y-0.5">
        <div className="flex flex-wrap items-center gap-2">
          <span className="font-medium text-gray-900 dark:text-white truncate">
            {a.display_title || a.title || '—'}
          </span>
          <StatusBadge status={a.status} />
          <span
            className={`text-xs px-1.5 py-0.5 rounded ${
              a.is_required
                ? 'bg-indigo-50 text-indigo-700 dark:bg-indigo-900/40 dark:text-indigo-300'
                : 'bg-gray-100 text-gray-500 dark:bg-gray-700 dark:text-gray-400'
            }`}
            data-testid={`assignment-required-${a.id}`}
          >
            {a.is_required ? 'Required' : 'Optional'}
          </span>
        </div>
        <div className="text-xs text-gray-500 dark:text-gray-400">
          <span data-testid={`assignment-target-${a.id}`}>{describeTarget(a)}</span>
          <span className="mx-1.5">·</span>
          <span data-testid={`assignment-dates-${a.id}`}>{dateRange(a.start_date, a.end_date)}</span>
        </div>
      </div>
      <div className="flex gap-2 shrink-0 items-center">
        {a.status === 'scheduled' && (
          <button
            type="button"
            onClick={handleCancel}
            disabled={pending}
            className="text-xs rounded-md border border-red-300 dark:border-red-700 text-red-700 dark:text-red-300 px-2 py-1 hover:bg-red-50 dark:hover:bg-red-900/20 disabled:opacity-50"
            data-testid={`assignment-cancel-${a.id}`}
          >
            {pending ? 'Cancelling…' : 'Cancel'}
          </button>
        )}
        {a.status === 'active' && (
          <button
            type="button"
            onClick={handleEndToday}
            disabled={pending}
            className="text-xs rounded-md border border-amber-300 dark:border-amber-700 text-amber-700 dark:text-amber-300 px-2 py-1 hover:bg-amber-50 dark:hover:bg-amber-900/20 disabled:opacity-50"
            data-testid={`assignment-end-today-${a.id}`}
          >
            {pending ? 'Ending…' : 'End today'}
          </button>
        )}
      </div>
    </li>
  );
}

// ─── Main component ──────────────────────────────────────────────────────────

/**
 * @param {object} props
 * @param {number|string} props.templateId
 * @param {string} props.orgSlug
 * @param {number} props.refreshKey — increment to force a reload (e.g. after a new assignment)
 */
export default function AssignmentList({ templateId, orgSlug, refreshKey = 0 }) {
  const [assignments, setAssignments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    if (!templateId) return;
    setLoading(true);
    setError('');
    try {
      const data = await listAssignments(orgSlug, { template: templateId });
      setAssignments(data?.assignments ?? data?.results ?? []);
    } catch {
      setError('Failed to load assignments. Refresh the page to try again.');
    } finally {
      setLoading(false);
    }
  }, [orgSlug, templateId]);

  useEffect(() => { load(); }, [load, refreshKey]);

  const handleCancelled = async (assignment) => {
    await cancelAssignment(orgSlug, assignment.id);
    await load();
  };

  const handleEnded = async (assignment) => {
    await patchAssignment(orgSlug, assignment.id, { end_date: today() });
    await load();
  };

  return (
    <section
      className="rounded-xl border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900/40 p-4 space-y-3"
      aria-label="Form assignments"
      data-testid="assignment-list-section"
    >
      <h2 className="text-base font-semibold text-gray-900 dark:text-white">
        Form assignments
      </h2>

      {loading && <Skeleton />}

      {!loading && error && (
        <p
          className="text-sm text-red-600 dark:text-red-400"
          data-testid="assignment-list-error"
        >
          {error}
        </p>
      )}

      {!loading && !error && assignments.length === 0 && (
        <p
          className="text-sm text-gray-500 dark:text-gray-400 italic"
          data-testid="assignment-list-empty"
        >
          No assignments yet — click &quot;Assign form&quot; to make this form available to staff.
        </p>
      )}

      {!loading && !error && assignments.length > 0 && (
        <ul className="space-y-2" data-testid="assignment-list">
          {assignments.map((a) => (
            <AssignmentRow
              key={a.id}
              assignment={a}
              onCancelled={handleCancelled}
              onEnded={handleEnded}
            />
          ))}
        </ul>
      )}
    </section>
  );
}
