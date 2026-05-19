/**
 * Inline error panel with the standard red-50 / red-200 treatment we
 * use on admin list pages. Optional title for "Access restricted" /
 * "Failed to load" headlines; children render the body.
 */
export default function ErrorPanel({ title, children, ...rest }) {
  return (
    <div
      role="alert"
      className="rounded-lg bg-red-50 dark:bg-red-950/30 border border-red-200 dark:border-red-800 px-4 py-3 text-sm text-red-700 dark:text-red-300"
      {...rest}
    >
      {title && (
        <p className="font-medium mb-0.5 text-red-800 dark:text-red-200">
          {title}
        </p>
      )}
      {children}
    </div>
  );
}
