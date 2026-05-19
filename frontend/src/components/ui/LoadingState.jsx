/**
 * Single-line loading indicator using the standard muted-gray treatment.
 *
 *   <LoadingState>Loading templates…</LoadingState>
 *
 * Use `inline` when the caller is already inside a section / table
 * cell and the surrounding wrapper provides spacing. Default rendering
 * adds `text-sm` plus the standard light/dark text colors so the
 * caller can drop it in directly.
 */
export default function LoadingState({ children, inline = false, ...rest }) {
  const className = inline
    ? 'text-gray-500 dark:text-gray-400'
    : 'text-sm text-gray-500 dark:text-gray-400';
  return (
    <p className={className} role="status" aria-live="polite" {...rest}>
      {children}
    </p>
  );
}
