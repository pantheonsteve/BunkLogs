/**
 * Canonical "nothing here" panel for admin lists.
 *
 * Props:
 *   icon: optional lucide-react icon component (rendered at size=40
 *         with opacity-40 to match the existing GroupListPage style)
 *   title: headline string, required
 *   children: optional body / sub-headline content (can be a string,
 *             a <Link>, or any node)
 *   action: optional CTA node, rendered below the body
 *
 * Renders the standard `text-center py-12 text-gray-500
 * dark:text-gray-400` block.
 */
export default function EmptyState({ icon: Icon, title, children, action, ...rest }) {
  return (
    <div
      className="text-center py-12 text-gray-500 dark:text-gray-400"
      {...rest}
    >
      {Icon && (
        <Icon
          size={40}
          className="mx-auto mb-3 text-gray-400 dark:text-gray-600 opacity-40"
          aria-hidden="true"
        />
      )}
      {title && (
        <p className="text-sm text-gray-700 dark:text-gray-300 font-medium">
          {title}
        </p>
      )}
      {children && (
        <div className="mt-1 text-sm text-gray-500 dark:text-gray-400">
          {children}
        </div>
      )}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}
