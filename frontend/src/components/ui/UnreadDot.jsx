/**
 * Unread marker for threads and cohort posts (Step 4_9).
 *
 * Renders nothing when there is nothing unread, so callers can drop it in
 * unconditionally. With a `count` it renders a pill; without one, a bare dot
 * matching the Observations inbox indicator.
 *
 * The visual is never the only signal — the label is always in the
 * accessible name, since a coloured dot alone is invisible to a screen
 * reader and indistinguishable to a colourblind user.
 */
export default function UnreadDot({ count, label, ...rest }) {
  const n = typeof count === 'number' ? count : null;
  if (n === 0) return null;
  if (n === null && !label) return null;

  if (n === null) {
    return (
      <span
        className="inline-block h-2 w-2 rounded-full bg-violet-600 dark:bg-violet-400"
        role="status"
        aria-label={label || 'Unread'}
        {...rest}
      />
    );
  }

  return (
    <span
      className="inline-flex items-center justify-center min-w-[1.25rem] px-1.5 h-5 rounded-full bg-violet-600 text-white text-xs font-semibold"
      role="status"
      aria-label={label || `${n} unread`}
      {...rest}
    >
      {n > 99 ? '99+' : n}
    </span>
  );
}
