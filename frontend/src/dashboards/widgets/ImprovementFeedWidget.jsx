/**
 * ImprovementFeedWidget — for dashboard_role: improvements (text_list fields).
 * Similar to HighlightFeedWidget but framed as growth areas.
 */
export default function ImprovementFeedWidget({ field, label }) {
  const items = field?.data?.items ?? [];
  const totalMentions = field?.data?.total_mentions ?? 0;
  const maxCount = items.length > 0 ? items[0].count : 1;

  return (
    <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900/40 p-5">
      <div className="flex items-center justify-between mb-3">
        <p className="text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">
          {label ?? field?.key}
        </p>
        <span className="text-xs text-gray-400 dark:text-gray-500">{totalMentions} mentions</span>
      </div>
      {items.length === 0 ? (
        <p className="text-sm text-gray-400 dark:text-gray-500">None submitted yet.</p>
      ) : (
        <ul className="space-y-2">
          {items.slice(0, 10).map((item) => {
            const pct = maxCount > 0 ? (item.count / maxCount) * 100 : 0;
            return (
              <li key={item.text} className="flex items-center gap-2">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between mb-0.5">
                    <span className="text-sm text-gray-800 dark:text-gray-200 truncate">{item.text}</span>
                    <span className="ml-2 shrink-0 text-xs text-amber-600 dark:text-amber-400 font-medium">
                      ×{item.count}
                    </span>
                  </div>
                  <div className="h-1 w-full rounded-full bg-gray-100 dark:bg-gray-800 overflow-hidden">
                    <div
                      className="h-full rounded-full bg-amber-500"
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
