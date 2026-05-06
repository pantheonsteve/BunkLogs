import { Minus, TrendingDown, TrendingUp } from 'lucide-react';

function TrendIcon({ label }) {
  if (label === 'up') return <TrendingUp className="inline h-3.5 w-3.5 text-emerald-500" aria-hidden />;
  if (label === 'down') return <TrendingDown className="inline h-3.5 w-3.5 text-rose-500" aria-hidden />;
  return <Minus className="inline h-3.5 w-3.5 text-gray-400" aria-hidden />;
}

/**
 * CategoryRadarWidget — for dashboard_role: category_ratings (rating_group fields).
 * Shows one row per category with mean, trend, and a mini bar.
 */
export default function CategoryRadarWidget({ field, label }) {
  const categories = field?.data?.categories ?? [];
  const scale = field?.scale ?? [1, 5];
  const scaleMax = Array.isArray(scale) ? scale[scale.length - 1] : 5;

  return (
    <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900/40 p-5">
      <p className="text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400 mb-4">
        {label ?? field?.key}
      </p>
      {categories.length === 0 ? (
        <p className="text-sm text-gray-400 dark:text-gray-500">No data yet.</p>
      ) : (
        <ul className="space-y-3">
          {categories.map((cat) => {
            const pct = cat.mean != null ? (cat.mean / scaleMax) * 100 : 0;
            return (
              <li key={cat.key} className="flex items-center gap-3">
                <span className="w-28 shrink-0 text-sm text-gray-700 dark:text-gray-300 capitalize truncate">
                  {cat.key}
                </span>
                <div className="flex-1 h-2.5 rounded-full bg-gray-100 dark:bg-gray-800 overflow-hidden">
                  <div
                    className="h-full rounded-full bg-indigo-500"
                    style={{ width: `${pct}%` }}
                  />
                </div>
                <span className="w-10 shrink-0 text-right text-sm font-semibold tabular-nums text-gray-800 dark:text-gray-200">
                  {cat.mean != null ? cat.mean.toFixed(1) : '—'}
                </span>
                <TrendIcon label={cat.trend} />
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
