/**
 * Inline callout that states a consequence or offers the control that
 * resolves it — used above lists and inside confirmations.
 *
 * Empty states and warnings should carry their own fix, so `children`
 * is expected to include the action rather than telling the reader to
 * go somewhere else.
 */

const TONE_CLASSES = {
  info: 'bg-indigo-50 border-indigo-200 text-indigo-900 dark:bg-indigo-950/30 dark:border-indigo-800 dark:text-indigo-200',
  warn: 'bg-amber-50 border-amber-200 text-amber-900 dark:bg-amber-950/30 dark:border-amber-800 dark:text-amber-100',
  ok: 'bg-green-50 border-green-200 text-green-900 dark:bg-green-950/30 dark:border-green-800 dark:text-green-200',
  danger: 'bg-red-50 border-red-200 text-red-900 dark:bg-red-950/30 dark:border-red-800 dark:text-red-200',
};

export default function Note({ tone = 'info', title, className = '', children, ...rest }) {
  const toneCls = TONE_CLASSES[tone] || TONE_CLASSES.info;
  return (
    <div
      className={`rounded-lg border px-4 py-3 text-sm leading-relaxed ${toneCls} ${className}`.trim()}
      {...rest}
    >
      {title && <p className="font-semibold mb-1">{title}</p>}
      {children}
    </div>
  );
}
