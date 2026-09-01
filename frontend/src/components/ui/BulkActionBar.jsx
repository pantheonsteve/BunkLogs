/**
 * Action strip that appears only once rows are selected.
 *
 * Checking a box should reveal what you can do with the selection, and
 * every action in here names its count — the bar renders nothing at
 * `count === 0` so no destructive control is ever clickable with an
 * empty selection.
 */
export default function BulkActionBar({ count, onClear, className = '', children, ...rest }) {
  if (!count) return null;
  return (
    <div
      className={`flex flex-wrap items-center gap-3 mb-4 px-4 py-2.5 rounded-lg bg-indigo-50 dark:bg-indigo-950/30 border border-indigo-200 dark:border-indigo-800 ${className}`.trim()}
      data-testid="bulk-action-bar"
      {...rest}
    >
      <span className="text-sm font-semibold text-indigo-700 dark:text-indigo-300">
        {count} selected
      </span>
      {children}
      <div className="flex-1" />
      {onClear && (
        <button
          type="button"
          onClick={onClear}
          className="text-sm font-medium text-indigo-700 dark:text-indigo-300 hover:underline"
        >
          Clear
        </button>
      )}
    </div>
  );
}
