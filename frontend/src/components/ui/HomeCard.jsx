/**
 * Section card for the role homepages (Step 4_9).
 *
 * Wraps the `rounded-xl border ... bg-white dark:bg-gray-800 p-4` markup the
 * Madrich and Faculty dashboards already repeat inline, so the three new
 * homepages stay visually identical without copying class strings.
 *
 * Props:
 *   title: headline string, rendered as an h2 and used as the section's
 *          accessible name
 *   subtitle: optional line under the title
 *   badge: optional node rendered right-aligned in the header (status pill,
 *          UnreadDot, count)
 *   action: optional node rendered in the header below the badge row, e.g. a
 *           "View all →" link
 *   footer: optional node rendered under the body, for CTAs
 */
export default function HomeCard({
  title,
  subtitle,
  badge,
  action,
  footer,
  children,
  className = '',
  ...rest
}) {
  return (
    <section
      aria-label={title}
      className={`rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-4 ${className}`}
      {...rest}
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <h2 className="text-base font-semibold text-gray-900 dark:text-white">
            {title}
          </h2>
          {subtitle && (
            <p className="text-sm text-gray-500 dark:text-gray-400 mt-0.5">
              {subtitle}
            </p>
          )}
        </div>
        <div className="flex items-center gap-2 shrink-0">
          {badge}
          {action}
        </div>
      </div>
      {children && <div className="mt-3">{children}</div>}
      {footer && <div className="mt-3">{footer}</div>}
    </section>
  );
}
