/**
 * Canonical "Super Admin" gate for the React frontend.
 *
 * A Super Admin is any user with ``is_staff`` OR ``is_superuser`` set on the
 * JWT/me payload. Both flags mean the user can bypass org-level RBAC: see
 * org admin views, access cross-tenant template management, etc.
 *
 * Backend counterpart: ``bunk_logs.core.permissions.is_super_admin``.
 *
 * Returns ``false`` for ``null`` / ``undefined`` / missing flag objects, so
 * call sites can use ``isSuperAdmin(user)`` unconditionally.
 */
export default function isSuperAdmin(user) {
  return Boolean(user?.is_staff || user?.is_superuser);
}
