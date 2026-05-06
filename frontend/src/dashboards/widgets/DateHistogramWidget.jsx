/**
 * DateHistogramWidget — generic widget for untagged date fields.
 */
export default function DateHistogramWidget({ field, label }) {
  const data = field?.data ?? {};
  const values = data.values ?? [];
  const count = data.response_count ?? 0;

  return (
    <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900/40 p-5">
      <div className="flex items-center justify-between mb-3">
        <p className="text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">
          {label ?? field?.key}
        </p>
        <span className="text-xs text-gray-400 dark:text-gray-500">{count} response{count !== 1 ? 's' : ''}</span>
      </div>
      {values.length === 0 ? (
        <p className="text-sm text-gray-400 dark:text-gray-500">No dates submitted yet.</p>
      ) : (
        <ul className="space-y-1 max-h-40 overflow-y-auto">
          {values.slice(0, 20).map((v, i) => (
            <li key={`${v}-${i}`} className="text-sm text-gray-700 dark:text-gray-300 tabular-nums">{v}</li>
          ))}
        </ul>
      )}
    </div>
  );
}
