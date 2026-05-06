/**
 * RatingTableWidget — generic widget for untagged rating_group fields.
 * Rows = categories, summary of mean per category.
 */
export default function RatingTableWidget({ field, label }) {
  const categories = field?.data?.categories ?? [];

  return (
    <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900/40 p-5">
      <p className="text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400 mb-3">
        {label ?? field?.key}
      </p>
      {categories.length === 0 ? (
        <p className="text-sm text-gray-400 dark:text-gray-500">No data yet.</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead>
              <tr className="text-xs text-gray-500 dark:text-gray-400">
                <th className="text-left pb-2 font-medium">Category</th>
                <th className="text-right pb-2 font-medium">Mean</th>
                <th className="text-right pb-2 font-medium">Responses</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 dark:divide-gray-800">
              {categories.map((cat) => (
                <tr key={cat.key}>
                  <td className="py-1.5 text-gray-700 dark:text-gray-300 capitalize">{cat.key}</td>
                  <td className="py-1.5 text-right font-medium tabular-nums text-gray-900 dark:text-white">
                    {cat.mean != null ? cat.mean.toFixed(2) : '—'}
                  </td>
                  <td className="py-1.5 text-right tabular-nums text-gray-500 dark:text-gray-400">
                    {cat.response_count}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
