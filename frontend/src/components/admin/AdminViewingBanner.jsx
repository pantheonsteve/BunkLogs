import { useAuth } from '../../auth/AuthContext';
import isSuperAdmin from '../../utils/auth/isSuperAdmin';

/**
 * Step 7_13 — Story 59 criterion 2.
 *
 * Renders a "Viewing as Admin — [role label]" header strip when an
 * Admin / Super Admin opens an operational role's dashboard or detail
 * view. Pass `roleLabel` for the role-specific copy ("Camper Care",
 * "Counselor", etc.); the banner stays out of the DOM for non-admin
 * viewers so callers can drop it anywhere without conditionals.
 *
 * Visual treatment is deliberately subtle (small amber chip) so it
 * doesn't interfere with the underlying role surface while still being
 * obvious enough that an Admin doesn't forget they're cross-viewing.
 */
export default function AdminViewingBanner({ roleLabel }) {
  const { user } = useAuth();
  const isAdmin = isSuperAdmin(user) || user?.role?.toLowerCase() === 'admin';
  if (!isAdmin) return null;
  return (
    <div
      data-testid="admin-viewing-banner"
      role="status"
      className="px-3 py-1.5 mb-3 inline-flex items-center gap-2 rounded-md border border-amber-300 bg-amber-50 text-amber-900 text-xs dark:bg-amber-900/30 dark:border-amber-700 dark:text-amber-100"
    >
      <span className="font-semibold uppercase tracking-wide">Viewing as Admin</span>
      {roleLabel ? <span>— {roleLabel}</span> : null}
    </div>
  );
}
