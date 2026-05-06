/**
 * NumberSparklineWidget — generic widget for untagged number fields.
 */
export default function NumberSparklineWidget({ field, label }) {
  const data = field?.data ?? {};
  return (
    <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900/40 p-5">
      <p className="text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400 mb-3">
        {label ?? field?.key}
      </p>
      {data.response_count === 0 ? (
        <p className="text-sm text-gray-400 dark:text-gray-500">No responses yet.</p>
      ) : (
        <div className="flex gap-6 flex-wrap">
          <div>
            <p className="text-xs text-gray-500 dark:text-gray-400">Mean</p>
            <p className="text-2xl font-bold tabular-nums text-gray-900 dark:text-white">
              {data.mean?.toFixed(1) ?? '—'}
            </p>
          </div>
          <div>
            <p className="text-xs text-gray-500 dark:text-gray-400">Min</p>
            <p className="text-2xl font-bold tabular-nums text-gray-900 dark:text-white">
              {data.min ?? '—'}
            </p>
          </div>
          <div>
            <p className="text-xs text-gray-500 dark:text-gray-400">Max</p>
            <p className="text-2xl font-bold tabular-nums text-gray-900 dark:text-white">
              {data.max ?? '—'}
            </p>
          </div>
          <div>
            <p className="text-xs text-gray-500 dark:text-gray-400">Responses</p>
            <p className="text-2xl font-bold tabular-nums text-gray-900 dark:text-white">
              {data.response_count}
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
