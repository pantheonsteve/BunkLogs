/**
 * ChoiceBarChartWidget — generic widget for single_choice/multiple_choice fields.
 */
export default function ChoiceBarChartWidget({ field, label }) {
  const choices = field?.data?.choices ?? [];
  const total = field?.data?.response_count ?? 0;
  const maxCount = choices.length > 0 ? choices[0].count : 1;

  return (
    <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900/40 p-5">
      <div className="flex items-center justify-between mb-3">
        <p className="text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">
          {label ?? field?.key}
        </p>
        <span className="text-xs text-gray-400 dark:text-gray-500">{total} response{total !== 1 ? 's' : ''}</span>
      </div>
      {choices.length === 0 ? (
        <p className="text-sm text-gray-400 dark:text-gray-500">No data yet.</p>
      ) : (
        <ul className="space-y-2">
          {choices.map((choice) => {
            const pct = maxCount > 0 ? (choice.count / maxCount) * 100 : 0;
            const pctOfTotal = total > 0 ? Math.round((choice.count / total) * 100) : 0;
            return (
              <li key={choice.option} className="flex items-center gap-2">
                <span className="w-32 shrink-0 text-sm text-gray-700 dark:text-gray-300 truncate">
                  {choice.option}
                </span>
                <div className="flex-1 h-2 rounded-full bg-gray-100 dark:bg-gray-800 overflow-hidden">
                  <div
                    className="h-full rounded-full bg-violet-500"
                    style={{ width: `${pct}%` }}
                  />
                </div>
                <span className="w-10 shrink-0 text-right text-xs tabular-nums text-gray-500 dark:text-gray-400">
                  {pctOfTotal}%
                </span>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
