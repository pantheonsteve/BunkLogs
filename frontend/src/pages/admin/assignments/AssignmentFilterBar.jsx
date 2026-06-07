function partitionPrograms(programs) {
  const active = [];
  const ended = [];
  for (const p of programs) {
    if (p.is_active) active.push(p);
    else ended.push(p);
  }
  return { active, ended };
}

function ProgramStatusBadge({ isActive }) {
  if (isActive) {
    return (
      <span className="inline-flex items-center rounded-full bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300 px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide">
        Active
      </span>
    );
  }
  return (
    <span className="inline-flex items-center rounded-full bg-gray-200 text-gray-600 dark:bg-gray-700 dark:text-gray-400 px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide">
      Ended
    </span>
  );
}

export default function AssignmentFilterBar({
  programs,
  programId,
  onProgramChange,
  status,
  onStatusChange,
  search,
  onSearchChange,
}) {
  const { active, ended } = partitionPrograms(programs);
  const selected = programs.find((p) => String(p.id) === String(programId));

  return (
    <div
      className="space-y-3 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900/40 p-3"
      data-testid="assignment-filter-bar"
    >
      <div className="flex flex-wrap items-end gap-3">
        <label className="text-xs font-medium text-gray-600 dark:text-gray-300">
          Program
          <select
            value={programId}
            onChange={(e) => onProgramChange(e.target.value)}
            className="mt-1 block rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-2 py-1.5 text-sm min-w-[14rem]"
            data-testid="assignment-program-select"
          >
            <option value="">All programs</option>
            {active.length > 0 && (
              <optgroup label="Active programs">
                {active.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name} (Active)
                  </option>
                ))}
              </optgroup>
            )}
            {ended.length > 0 && (
              <optgroup label="Ended programs">
                {ended.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name} (Ended)
                  </option>
                ))}
              </optgroup>
            )}
          </select>
        </label>
        <label className="text-xs font-medium text-gray-600 dark:text-gray-300">
          Assignment status
          <select
            value={status}
            onChange={(e) => onStatusChange(e.target.value)}
            className="mt-1 block rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-2 py-1.5 text-sm"
          >
            <option value="active">Active</option>
            <option value="ended">Ended</option>
            <option value="all">All</option>
          </select>
        </label>
        <label className="text-xs font-medium text-gray-600 dark:text-gray-300 flex-1 min-w-[12rem]">
          Search
          <input
            type="search"
            value={search}
            onChange={(e) => onSearchChange(e.target.value)}
            placeholder="Name or group…"
            className="mt-1 block w-full rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-2 py-1.5 text-sm"
          />
        </label>
      </div>

      {selected && (
        <p className="text-xs text-gray-600 dark:text-gray-400 flex items-center gap-2">
          <span>Filtering:</span>
          <span className="font-medium text-gray-900 dark:text-white">{selected.name}</span>
          <ProgramStatusBadge isActive={selected.is_active} />
        </p>
      )}

      {programs.length > 0 && (
        <div data-testid="assignment-program-chips">
          <p className="text-xs font-medium text-gray-500 dark:text-gray-400 mb-2">
            Programs in this organization
          </p>
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              onClick={() => onProgramChange('')}
              className={[
                'inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-medium transition-colors',
                !programId
                  ? 'border-indigo-500 bg-indigo-50 text-indigo-800 dark:bg-indigo-900/40 dark:text-indigo-200'
                  : 'border-gray-200 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800',
              ].join(' ')}
            >
              All programs
            </button>
            {programs.map((p) => {
              const isSelected = String(p.id) === String(programId);
              return (
                <button
                  key={p.id}
                  type="button"
                  data-testid={`assignment-program-chip-${p.id}`}
                  onClick={() => onProgramChange(String(p.id))}
                  className={[
                    'inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-medium transition-colors',
                    isSelected
                      ? 'border-indigo-500 bg-indigo-50 text-indigo-800 dark:bg-indigo-900/40 dark:text-indigo-200'
                      : 'border-gray-200 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800',
                  ].join(' ')}
                >
                  <span>{p.name}</span>
                  <ProgramStatusBadge isActive={p.is_active} />
                </button>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
