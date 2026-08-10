import { useState } from 'react';
import {
  DEV_KNOWN_ORGS,
  resolveOrganizationSlug,
  setDevOrgOverride,
} from '../utils/orgSlug';

/**
 * Dev-only floating widget to switch the tenant org slug at runtime, without
 * editing .env or restarting Vite. Persists the choice in localStorage (read
 * by resolveOrganizationSlug()) and clears auth state before reloading,
 * since a session tied to one org's Person 403s against another org's
 * API calls (see the login flicker/crash bug this was built to prevent).
 *
 * Never rendered outside `vite dev` -- import.meta.env.DEV is false in
 * production builds, so this can't ship to prod by accident.
 */
function DevOrgSwitcher() {
  const [open, setOpen] = useState(false);

  if (!import.meta.env.DEV) {
    return null;
  }

  const currentSlug = resolveOrganizationSlug();

  const handleSelect = (slug) => {
    setOpen(false);
    if (slug === currentSlug) {
      return;
    }
    setDevOrgOverride(slug);
    try {
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
      localStorage.removeItem('user_profile');
    } catch {
      // Ignore storage failures (e.g. private browsing).
    }
    window.location.href = '/signin';
  };

  return (
    // bottom-right: DevImpersonation ("Dev: view as user") owns bottom-left
    // and mounts later in the DOM, so it paints over anything sharing that corner.
    <div className="fixed bottom-4 right-4 z-50 font-mono text-xs select-none">
      {open && (
        <div className="mb-2 bg-gray-900 text-white rounded-lg shadow-lg py-2 min-w-[220px]">
          <div className="px-3 py-1 text-gray-400 uppercase tracking-wide text-[10px]">
            Dev: switch organization
          </div>
          {DEV_KNOWN_ORGS.map(({ slug, label }) => (
            <button
              key={slug}
              type="button"
              onClick={() => handleSelect(slug)}
              className={`block w-full text-left px-3 py-1.5 hover:bg-gray-700 ${
                slug === currentSlug ? 'text-violet-400 font-semibold' : 'text-white'
              }`}
            >
              {slug === currentSlug ? '✓ ' : '\u00A0\u00A0'}
              {label}
            </button>
          ))}
          <div className="px-3 pt-1.5 text-gray-500 text-[10px] max-w-[220px]">
            Switching logs you out — sessions are org-scoped.
          </div>
        </div>
      )}
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="bg-gray-900 text-white px-3 py-1.5 rounded-full shadow-lg hover:bg-gray-700"
        title="Dev: switch organization"
      >
        org: {currentSlug || 'none'}
      </button>
    </div>
  );
}

export default DevOrgSwitcher;
