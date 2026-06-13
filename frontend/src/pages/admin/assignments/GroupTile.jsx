import { useState } from 'react';
import AssignmentStatusPill from './AssignmentStatusPill';

function todayIso() {
  return new Date().toISOString().split('T')[0];
}

function prettyRole(role) {
  if (!role) return null;
  return role
    .split('_')
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(' ');
}

function RoleBadge({ role }) {
  const label = prettyRole(role);
  if (!label) return null;
  return (
    <span className="shrink-0 inline-flex items-center rounded-full bg-gray-100 dark:bg-gray-800 px-2 py-0.5 text-xs font-medium text-gray-700 dark:text-gray-300">
      {label}
    </span>
  );
}

function assignmentTitle(row) {
  if (row.kind === 'supervision') {
    const target = row.target_membership_name || row.target_name || 'Target';
    return `${row.supervisor_name || 'Supervisor'} → ${target}`;
  }
  return row.person_name || 'Person';
}

export default function GroupTile({
  title,
  subtitle,
  assignments,
  selectedAssignmentIds,
  onToggleAssignment,
  onToggleAllAssignments,
  onEndSelected,
  onAssignPerson,
  dimEnded = false,
  className = '',
}) {
  const [ending, setEnding] = useState(false);
  const [reason, setReason] = useState('');

  const activeRows = assignments.filter((r) => r.is_active);
  const allSelected = activeRows.length > 0
    && activeRows.every((r) => selectedAssignmentIds.has(r.id));

  const handleEnd = async () => {
    if (!reason.trim()) return;
    await onEndSelected(reason);
    setEnding(false);
    setReason('');
  };

  return (
    <section
      className={[
        'rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900/40 p-4 space-y-3 min-h-[20rem] flex flex-col',
        className,
      ].join(' ')}
      data-testid="assignment-group-tile"
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">{title}</h3>
          {subtitle && (
            <p className="text-sm text-gray-500 dark:text-gray-400">{subtitle}</p>
          )}
        </div>
        <div className="flex flex-wrap items-center gap-2 shrink-0">
          <button
            type="button"
            disabled={selectedAssignmentIds.size === 0 || ending}
            onClick={() => setEnding(true)}
            data-testid="unassign-btn"
            className="text-sm font-medium px-3 py-1.5 rounded-md border border-red-300 dark:border-red-700 text-red-700 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 disabled:opacity-50 disabled:hover:bg-transparent"
          >
            Unassign{selectedAssignmentIds.size > 0 ? ` (${selectedAssignmentIds.size})` : ''}
          </button>
          <button
            type="button"
            onClick={onAssignPerson}
            data-testid="assign-person-btn"
            className="text-sm font-medium text-indigo-600 dark:text-indigo-400 hover:underline"
          >
            Assign Person
          </button>
        </div>
      </div>

      {assignments.length === 0 ? (
        <p className="text-sm italic text-gray-500">No assignments in this view.</p>
      ) : (
        <>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => onToggleAllAssignments(!allSelected)}
              className="text-xs text-indigo-600 dark:text-indigo-400 hover:underline"
            >
              {allSelected ? 'Clear selection' : 'Select active'}
            </button>
          </div>
          <ul className="space-y-2 flex-1 overflow-y-auto max-h-96">
            {assignments.map((row) => {
              const faded = dimEnded && !row.is_active;
              return (
                <li
                  key={`${row.kind}-${row.id}`}
                  data-testid={`assignment-row-${row.kind}-${row.id}`}
                  className={[
                    'rounded-md border border-gray-200 dark:border-gray-700 p-2 text-sm',
                    faded ? 'opacity-60' : '',
                  ].join(' ')}
                >
                  <div className="flex items-start gap-2">
                    {row.is_active && (
                      <input
                        type="checkbox"
                        checked={selectedAssignmentIds.has(row.id)}
                        onChange={() => onToggleAssignment(row.id)}
                        className="mt-1"
                      />
                    )}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between gap-2">
                        <div className="flex items-center gap-2 min-w-0 flex-wrap">
                          <p className="font-medium truncate">{assignmentTitle(row)}</p>
                          {row.kind === 'supervision' ? (
                            <>
                              {row.supervisor_role && <RoleBadge role={row.supervisor_role} />}
                              {row.target_membership_role && (
                                <RoleBadge role={row.target_membership_role} />
                              )}
                            </>
                          ) : (
                            <RoleBadge role={row.membership_role} />
                          )}
                        </div>
                        <AssignmentStatusPill row={row} />
                      </div>
                      <p className="text-xs text-gray-500 dark:text-gray-400">
                        {row.start_date || '—'} → {row.end_date || 'open'}
                      </p>
                    </div>
                  </div>
                </li>
              );
            })}
          </ul>
        </>
      )}

      {ending && (
        <div className="flex gap-2 items-center border-t border-gray-100 dark:border-gray-800 pt-3">
          <input
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            placeholder="Reason for unassigning"
            className="text-sm rounded-md border border-gray-300 dark:border-gray-600 px-2 py-1 flex-1 bg-white dark:bg-gray-800"
          />
          <button
            type="button"
            disabled={!reason.trim()}
            onClick={handleEnd}
            className="text-xs px-3 py-1.5 rounded-md bg-red-600 text-white disabled:opacity-50"
          >
            Confirm unassign
          </button>
          <button
            type="button"
            onClick={() => { setEnding(false); setReason(''); }}
            className="text-xs text-gray-500 hover:underline"
          >
            Cancel
          </button>
        </div>
      )}
    </section>
  );
}

export { todayIso };
