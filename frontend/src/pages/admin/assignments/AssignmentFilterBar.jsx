function partitionPrograms(programs) {
  const active = [];
  const ended = [];
  for (const p of programs) {
    if (p.is_active) active.push(p);
    else ended.push(p);
  }
  return { active, ended };
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
    </div>
  );
}
