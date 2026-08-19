/**
 * Breadcrumb-style "back to X" link for pages reached from a hub.
 *
 * Several dashboards are entered from Admin Home but render their own chrome
 * rather than a nested layout, so the only way back is the browser button.
 */
import { Link } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';

export default function BackLink({ to, label, className = '', ...rest }) {
  return (
    <Link
      to={to}
      className={`inline-flex items-center gap-1.5 text-sm font-medium text-indigo-700 dark:text-indigo-300 hover:text-indigo-900 dark:hover:text-indigo-100 hover:underline ${className}`}
      {...rest}
    >
      <ArrowLeft size={16} aria-hidden="true" />
      {label}
    </Link>
  );
}
