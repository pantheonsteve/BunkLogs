import { Link } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';

/**
 * Title block at the top of an admin page: optional breadcrumb back-link,
 * heading, one-line description, and a right-aligned action slot.
 *
 * Standardises the spacing every admin page was setting by hand, and
 * keeps the back-link in one place so it reads the same on every screen.
 */
export default function PageHeader({
  title,
  subtitle,
  backTo,
  backLabel = 'Admin',
  actions,
  className = '',
  children,
  ...rest
}) {
  return (
    <header className={`mb-6 ${className}`.trim()} {...rest}>
      {backTo && (
        <Link
          to={backTo}
          className="inline-flex items-center gap-1 text-sm text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 mb-4"
        >
          <ArrowLeft size={14} aria-hidden="true" /> {backLabel}
        </Link>
      )}
      <div className="flex flex-wrap items-start gap-3">
        <div className="min-w-0 flex-1">
          <h1 className="text-[27px] tracking-tight font-bold text-gray-900 dark:text-white">
            {title}
          </h1>
          {subtitle && (
            <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">{subtitle}</p>
          )}
        </div>
        {actions && <div className="flex items-center gap-2 shrink-0">{actions}</div>}
      </div>
      {children}
    </header>
  );
}
