import { Minus, TrendingDown, TrendingUp } from 'lucide-react';

function TrendIcon({ label }) {
  if (label === 'up') return <TrendingUp className="inline h-5 w-5 text-emerald-500" aria-hidden />;
  if (label === 'down') return <TrendingDown className="inline h-5 w-5 text-rose-500" aria-hidden />;
  return <Minus className="inline h-5 w-5 text-gray-400" aria-hidden />;
}

/**
 * RatingHeadlineWidget — for dashboard_role: primary_rating (single_rating fields).
 * Displays a large number with trend arrow vs prior period.
 */
export default function RatingHeadlineWidget({ field, label }) {
  const data = field?.data ?? {};
  const mean = data.mean;
  const priorMean = data.prior_mean;
  const trend = data.trend ?? 'flat';
  const scale = field?.scale ?? [1, 5];
  const scaleMax = Array.isArray(scale) ? scale[scale.length - 1] : 5;

  return (
    <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900/40 p-5">
      <p className="text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400 mb-3">
        {label ?? field?.key}
      </p>
      <div className="flex items-end gap-3">
        <span className="text-5xl font-bold text-gray-900 dark:text-white tabular-nums">
          {mean != null ? mean.toFixed(1) : '—'}
        </span>
        <span className="text-lg text-gray-400 dark:text-gray-500 mb-1">/ {scaleMax}</span>
        <span className="mb-1">
          <TrendIcon label={trend} />
        </span>
      </div>
      {priorMean != null && (
        <p className="text-xs text-gray-500 dark:text-gray-400 mt-2">
          Prior period: {priorMean.toFixed(1)}
        </p>
      )}
      <p className="text-xs text-gray-400 dark:text-gray-500 mt-1">
        {data.response_count ?? 0} response{data.response_count !== 1 ? 's' : ''}
      </p>
    </div>
  );
}
