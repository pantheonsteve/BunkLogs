/**
 * ItemCloudWidget — generic widget for untagged text_list fields.
 * Shows frequency-weighted item cloud/list.
 */
export default function ItemCloudWidget({ field, label }) {
  const items = field?.data?.items ?? [];
  const total = field?.data?.total_mentions ?? 0;
  const maxCount = items.length > 0 ? items[0].count : 1;

  function fontSize(count) {
    const pct = count / maxCount;
    if (pct > 0.8) return 'text-base font-semibold';
    if (pct > 0.5) return 'text-sm font-medium';
    return 'text-xs';
  }

  return (
    <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900/40 p-5">
      <div className="flex items-center justify-between mb-3">
        <p className="text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">
          {label ?? field?.key}
        </p>
        <span className="text-xs text-gray-400 dark:text-gray-500">{total} mentions</span>
      </div>
      {items.length === 0 ? (
        <p className="text-sm text-gray-400 dark:text-gray-500">No items submitted yet.</p>
      ) : (
        <div className="flex flex-wrap gap-2">
          {items.map((item) => (
            <span
              key={item.text}
              className={`px-2 py-1 rounded-full bg-indigo-50 dark:bg-indigo-900/30 text-indigo-700 dark:text-indigo-300 ${fontSize(item.count)}`}
              title={`${item.count} mention${item.count !== 1 ? 's' : ''}`}
            >
              {item.text}
              <span className="ml-1 opacity-60">×{item.count}</span>
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
