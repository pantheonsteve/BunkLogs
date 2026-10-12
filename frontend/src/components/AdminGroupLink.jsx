/**
 * "Manage group" shortcut from a group dashboard to its admin screen.
 * Renders only for viewers the backend resolved as `admin`.
 */
import { Link } from 'react-router-dom';
import { Settings } from 'lucide-react';

export default function AdminGroupLink({ data, className = '' }) {
  const groupId = data?.header?.group?.id ?? data?.header?.bunk?.id;
  if (data?.role_context?.role !== 'admin' || !groupId) return null;
  return (
    <Link
      to={`/admin/groups/${groupId}`}
      data-testid="group-dashboard-admin-link"
      className={`inline-flex items-center gap-1.5 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900 px-3 py-1.5 text-xs font-semibold text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors ${className}`.trim()}
    >
      <Settings size={14} aria-hidden="true" />
      Manage group
    </Link>
  );
}
