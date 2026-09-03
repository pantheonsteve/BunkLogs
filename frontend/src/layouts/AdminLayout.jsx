import { useEffect, useState } from 'react';
import { Outlet } from 'react-router-dom';

import { fetchAdminNavBadges } from '../api/admin';
import AdminTopBar from '../components/admin/AdminTopBar';
import { AdminProgramProvider, useAdminProgram } from '../context/AdminProgramContext';
import Sidebar from '../partials/Sidebar';

/**
 * Shared layout for /admin/* routes. Renders Sidebar + AdminTopBar + a
 * scrollable main, and slots the matched child route into `<Outlet/>`.
 *
 * Child routes provide their own `<main>` (or content wrapper) so each
 * page can pick its own padding and max-width. The layout intentionally
 * owns no width constraints -- it's chrome only.
 *
 * `AdminProgramProvider` wraps the whole shell, not just the content, so
 * the program in scope is chosen once and read by the sidebar badges as
 * well as every page -- rather than each page shipping its own selector
 * with its own default.
 *
 * The template builder lives at /admin/templates/:id (inside this
 * layout). Legacy /admin/templates/:id/edit redirects to that path.
 */
export default function AdminLayout() {
  return (
    <AdminProgramProvider>
      <AdminShell />
    </AdminProgramProvider>
  );
}

function AdminShell() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const navBadges = useNavBadges();

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar
        sidebarOpen={sidebarOpen}
        setSidebarOpen={setSidebarOpen}
        variant="v2"
        navBadges={navBadges}
      />
      <div
        data-testid="admin-layout-scroll"
        className="relative flex flex-col flex-1 overflow-y-auto overflow-x-hidden bg-gray-50 dark:bg-gray-950"
      >
        <AdminTopBar sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} />
        <Outlet />
      </div>
    </div>
  );
}

/**
 * Sidebar counts. Refetched when the program changes and left null on
 * failure, which renders no badge -- a stale or missing count must never
 * take the nav down with it.
 */
function useNavBadges() {
  const { programId, ready } = useAdminProgram();
  const [badges, setBadges] = useState(null);

  useEffect(() => {
    if (!ready) return undefined;
    let cancelled = false;
    fetchAdminNavBadges(programId ? { program: programId } : {})
      .then((data) => {
        if (cancelled) return;
        setBadges(data && {
          peopleNeverInvited: data.people_never_invited,
          groupsNeedingAttention: data.groups_needing_attention,
        });
      })
      .catch(() => {});
    return () => { cancelled = true; };
  }, [programId, ready]);

  return badges;
}
