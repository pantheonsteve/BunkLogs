import { useState } from 'react';
import { Outlet } from 'react-router-dom';

import { AdminProgramProvider } from '../context/AdminProgramContext';
import Header from '../partials/Header';
import Sidebar from '../partials/Sidebar';
import useNavBadges from './useNavBadges';

/**
 * Shared layout for /admin/* routes. Renders Sidebar + Header + a
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
    <div className="flex h-full min-h-0 overflow-hidden">
      <Sidebar
        sidebarOpen={sidebarOpen}
        setSidebarOpen={setSidebarOpen}
        navBadges={navBadges}
      />
      <div
        data-testid="admin-layout-scroll"
        className="relative flex flex-col flex-1 overflow-y-auto overflow-x-hidden bg-ground"
      >
        <Header sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} />
        <Outlet />
      </div>
    </div>
  );
}
