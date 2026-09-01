/**
 * Panel primitive for admin surfaces — the white bordered box that most
 * admin content sits in.
 *
 * `Card` is the shell, `CardHeader` the title strip with an optional
 * right-hand action slot, `CardBody` the padded content area. A card
 * built from all three matches the `bg-white … rounded-xl border` blob
 * that GroupList, GroupDetail and FieldKey were each repeating inline.
 */

export function CardHeader({ title, subtitle, action, className = '', children, ...rest }) {
  return (
    <div
      className={`flex items-start gap-3 px-[18px] py-4 border-b border-gray-100 dark:border-gray-800 ${className}`.trim()}
      {...rest}
    >
      <div className="min-w-0 flex-1">
        {title && (
          <h2 className="text-sm font-semibold text-gray-900 dark:text-white truncate">
            {title}
          </h2>
        )}
        {subtitle && (
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">{subtitle}</p>
        )}
        {children}
      </div>
      {action && <div className="shrink-0 flex items-center gap-2">{action}</div>}
    </div>
  );
}

export function CardBody({ className = '', children, ...rest }) {
  return (
    <div className={`p-4 ${className}`.trim()} {...rest}>
      {children}
    </div>
  );
}

export default function Card({ className = '', children, ...rest }) {
  return (
    <div
      className={`bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-xl shadow-sm ${className}`.trim()}
      {...rest}
    >
      {children}
    </div>
  );
}
