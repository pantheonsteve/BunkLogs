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
 *   accent: optional colour name from `components/ui/accents` — adds a top
 *           rule so a grid of cards reads as distinct sections rather than
 *           one undifferentiated wall of white
 *   icon: optional lucide component rendered in an accent-tinted badge
 *   badge: optional node rendered right-aligned in the header (status pill,
 *          UnreadDot, count)
 *   action: optional node rendered in the header below the badge row, e.g. a
 *           "View all →" link
 *   footer: optional node rendered under the body, for CTAs
 */
import { accent as resolveAccent } from './accents';

export default function HomeCard({
  title,
  subtitle,
  accent,
  icon: Icon,
  badge,
  action,
  footer,
  children,
  className = '',
  ...rest
}) {
  const tone = accent ? resolveAccent(accent) : null;
  return (
    <section
      aria-label={title}
      className={`rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-4 shadow-sm ${
        tone ? `border-t-4 ${tone.bar}` : ''
      } ${className}`}
      {...rest}
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex items-start gap-3 min-w-0">
          {Icon && (
            <span
              className={`inline-flex items-center justify-center w-9 h-9 rounded-lg shrink-0 ${
                tone ? tone.chip : 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-200'
              }`}
            >
              <Icon size={18} aria-hidden="true" />
            </span>
          )}
          <div className="min-w-0">
            <h2 className="text-base font-semibold text-gray-900 dark:text-white">
              {title}
            </h2>
            {subtitle && (
              <p className="text-sm text-gray-600 dark:text-gray-300 mt-0.5">
                {subtitle}
              </p>
            )}
          </div>
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
