/**
 * Placeholder card for the role homepages while their sections load
 * (Step 4_9).
 *
 * The homepages compose several independently-fetched cards, so a single
 * page-level "Loading…" would blank the whole screen whenever one endpoint
 * is slow. Skeletons keep the layout stable instead.
 */
export default function CardSkeleton({ rows = 3, title = true, ...rest }) {
  return (
    <div
      className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-4"
      role="status"
      aria-label="Loading"
      {...rest}
    >
      {title && (
        <div className="h-4 w-40 rounded bg-gray-200 dark:bg-gray-700 animate-pulse" />
      )}
      <div className="mt-3 space-y-2">
        {Array.from({ length: rows }, (_, i) => (
          <div
            key={i}
            className="h-3 rounded bg-gray-100 dark:bg-gray-700/60 animate-pulse"
            style={{ width: `${100 - i * 12}%` }}
          />
        ))}
      </div>
    </div>
  );
}
