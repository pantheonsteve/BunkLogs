import { useAuth } from '../auth/AuthContext';

/**
 * Terminal landing page for authenticated users with no membership in
 * the organization this site serves (e.g. a TBE user on
 * clc.bunklogs.net). Replaces the old behavior of bouncing between
 * / -> /dashboard -> /admin/home in a redirect loop.
 */
function NoAccess() {
  const { user, logout } = useAuth();
  const orgs = Array.isArray(user?.organizations) ? user.organizations : [];

  return (
    <div className="flex items-center justify-center min-h-screen bg-gray-100 dark:bg-gray-900 px-4">
      <div className="max-w-md w-full bg-white dark:bg-gray-800 rounded-xl shadow p-8 text-center">
        <h1 className="text-xl font-semibold text-gray-800 dark:text-gray-100 mb-2">
          No access in this organization
        </h1>
        <p className="text-sm text-gray-600 dark:text-gray-400 mb-6">
          {user?.email ? `You're signed in as ${user.email}, but this account ` : 'This account '}
          doesn&apos;t have a role in the organization this site belongs to.
        </p>

        {orgs.length > 0 && (
          <div className="mb-6 text-left">
            <p className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Your organizations:
            </p>
            <ul className="space-y-2">
              {orgs.map((org) => (
                <li key={org.slug}>
                  <a
                    href={`https://${org.slug}.bunklogs.net/`}
                    className="block px-4 py-2 rounded-lg border border-gray-200 dark:border-gray-700 text-sm text-violet-600 dark:text-violet-400 hover:bg-gray-50 dark:hover:bg-gray-700/40"
                  >
                    {org.name || org.slug}
                    <span className="text-gray-400 dark:text-gray-500"> — {org.slug}.bunklogs.net</span>
                  </a>
                </li>
              ))}
            </ul>
          </div>
        )}

        <p className="text-sm text-gray-600 dark:text-gray-400 mb-6">
          If you believe this is a mistake, contact your program administrator.
        </p>

        <button
          type="button"
          onClick={logout}
          className="btn bg-gray-900 text-gray-100 hover:bg-gray-800 dark:bg-gray-100 dark:text-gray-800 dark:hover:bg-white"
        >
          Sign out
        </button>
      </div>
    </div>
  );
}

export default NoAccess;
