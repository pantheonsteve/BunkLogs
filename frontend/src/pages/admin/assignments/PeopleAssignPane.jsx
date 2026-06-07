import { useMemo } from 'react';

function prettyRole(role) {
  if (!role) return '';
  return role.split('_').map((w) => w.charAt(0).toUpperCase() + w.slice(1)).join(' ');
}

export default function PeopleAssignPane({
  people,
  selectedIds,
  onToggle,
  onToggleAll,
  disabledIds,
  startDate,
  endDate,
  onStartDateChange,
  onEndDateChange,
  onAssign,
  assigning,
  assignLabel = 'Assign selected',
  emptyMessage = 'No eligible people.',
  highlighted,
}) {
  const enabledPeople = useMemo(
    () => people.filter((p) => !disabledIds.has(p.id)),
    [people, disabledIds],
  );
  const allChecked = enabledPeople.length > 0
    && enabledPeople.every((p) => selectedIds.has(p.id));

  return (
    <aside
      className={[
        'rounded-xl border p-3 flex flex-col gap-3 min-h-[20rem]',
        highlighted
          ? 'border-indigo-400 ring-2 ring-indigo-200 dark:ring-indigo-800'
          : 'border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900/40',
      ].join(' ')}
      data-testid="people-assign-pane"
    >
      <div className="flex items-center justify-between gap-2">
        <h2 className="text-sm font-semibold text-gray-900 dark:text-white">
          People to assign
        </h2>
        {enabledPeople.length > 0 && (
          <button
            type="button"
            onClick={() => onToggleAll(!allChecked)}
            className="text-xs text-indigo-600 dark:text-indigo-400 hover:underline"
          >
            {allChecked ? 'Clear all' : 'Select all'}
          </button>
        )}
      </div>

      <div className="grid grid-cols-2 gap-2">
        <label className="text-xs font-medium text-gray-600 dark:text-gray-300">
          Start date
          <input
            type="date"
            value={startDate}
            onChange={(e) => onStartDateChange(e.target.value)}
            className="mt-1 w-full rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-2 py-1 text-sm"
          />
        </label>
        <label className="text-xs font-medium text-gray-600 dark:text-gray-300">
          End date (optional)
          <input
            type="date"
            value={endDate}
            onChange={(e) => onEndDateChange(e.target.value)}
            className="mt-1 w-full rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-2 py-1 text-sm"
          />
        </label>
      </div>

      <ul className="flex-1 overflow-y-auto space-y-1 max-h-80 pr-1">
        {people.length === 0 ? (
          <li className="text-sm italic text-gray-500">{emptyMessage}</li>
        ) : (
          people.map((person) => {
            const disabled = disabledIds.has(person.id);
            const checked = selectedIds.has(person.id);
            return (
              <li
                key={person.id}
                className={[
                  'flex items-start gap-2 rounded-md px-2 py-1.5 text-sm',
                  disabled ? 'opacity-50' : 'hover:bg-gray-50 dark:hover:bg-gray-800/60',
                ].join(' ')}
              >
                <input
                  type="checkbox"
                  checked={checked}
                  disabled={disabled}
                  onChange={() => onToggle(person.id)}
                  className="mt-0.5"
                  data-testid={`assign-person-${person.id}`}
                />
                <div className="min-w-0">
                  <p className="font-medium text-gray-900 dark:text-white truncate">
                    {person.full_name || `${person.first_name} ${person.last_name}`}
                  </p>
                  {person.roles?.length > 0 && (
                    <div className="flex flex-wrap gap-1 mt-0.5">
                      {person.roles.map((role) => (
                        <span
                          key={role}
                          className="text-[10px] uppercase tracking-wide rounded-full bg-gray-100 dark:bg-gray-800 px-1.5 py-0.5 text-gray-600 dark:text-gray-400"
                        >
                          {prettyRole(role)}
                        </span>
                      ))}
                    </div>
                  )}
                  {disabled && (
                    <p className="text-xs text-gray-500 mt-0.5">Already assigned</p>
                  )}
                </div>
              </li>
            );
          })
        )}
      </ul>

      <button
        type="button"
        disabled={assigning || selectedIds.size === 0}
        onClick={onAssign}
        data-testid="bulk-assign-submit"
        className="w-full rounded-md bg-indigo-600 text-white text-sm font-medium py-2 disabled:opacity-50 hover:bg-indigo-700"
      >
        {assigning ? 'Assigning…' : `${assignLabel} (${selectedIds.size})`}
      </button>
    </aside>
  );
}
