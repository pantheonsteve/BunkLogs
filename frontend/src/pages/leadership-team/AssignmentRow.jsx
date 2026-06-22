/**
 * Single TemplateAssignment row — shared by AssignmentList and ActivelyAssignedTab.
 */

import { useState } from 'react';

export function today() {
  return new Date().toISOString().slice(0, 10);
}

export function dateRange(start, end) {
  if (!end) return `${start} → ongoing`;
  return `${start} → ${end}`;
}

export function describeTarget(a) {
  if (a.target_type === 'assignment_group') {
    const name = a.assignment_group_name ?? `Group #${a.assignment_group}`;
    if (a.assignment_group_type) {
      return `${name} (${a.assignment_group_type.replace(/_/g, ' ')})`;
    }
    return name;
  }
  if (a.target_type === 'role') {
    return `Role: ${(a.target_payload?.role ?? '—').replace(/_/g, ' ')}`;
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

export function isAssignmentLive(assignment, todayStr = today()) {
  if (assignment.status === 'cancelled' || assignment.status === 'ended') return false;
  if (assignment.start_date > todayStr) return false;
  if (assignment.end_date && assignment.end_date < todayStr) return false;
  return true;
}

export function assignmentActions(assignment, { endWhenLive = false } = {}) {
  const canCancel = assignment.status === 'scheduled';
  const canEnd = assignment.status === 'active'
    || (endWhenLive && isAssignmentLive(assignment));
  return { canCancel, canEnd };
}

function formatCadence(cadence) {
  if (!cadence) return null;
  return cadence.replace(/_/g, ' ');
}

function assignmentMetaParts(a) {
  const parts = [];
  if (a.program_name) parts.push(a.program_name);
  if (typeof a.reflection_count === 'number') {
    parts.push(`${a.reflection_count} response${a.reflection_count === 1 ? '' : 's'}`);
  }
  const cadence = formatCadence(a.effective_cadence ?? a.template_cadence);
  if (cadence) parts.push(cadence);
  if (a.cadence_override && a.template_cadence && a.cadence_override !== a.template_cadence) {
    parts.push(`override: ${formatCadence(a.cadence_override)}`);
  }
  return parts;
}

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

export default function AssignmentRow({
  assignment,
  onCancelled,
  onEnded,
  variant = 'compact',
  endWhenLive = false,
}) {
  const [pending, setPending] = useState(false);
  const { canCancel, canEnd } = assignmentActions(assignment, { endWhenLive });
  const metaParts = variant === 'detailed' ? assignmentMetaParts(assignment) : [];

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
        {metaParts.length > 0 && (
          <p
            className="text-xs text-gray-500 dark:text-gray-400"
            data-testid={`assignment-meta-${a.id}`}
          >
            {metaParts.join(' · ')}
          </p>
        )}
      </div>
      <div className="flex gap-2 shrink-0 items-center flex-wrap justify-end">
        {canEnd && (
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
        {canCancel && (
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
      </div>
    </li>
  );
}
