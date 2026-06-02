import { useState } from 'react';
import { Outlet } from 'react-router-dom';

import GlobalSearch from '../components/admin/GlobalSearch';
import Header from '../partials/Header';
import Sidebar from '../partials/Sidebar';

/**
 * Shared layout for /admin/* routes. Renders Sidebar + Header + a
 * scrollable main, and slots the matched child route into `<Outlet/>`.
 *
 * Child routes provide their own `<main>` (or content wrapper) so each
 * page can pick its own padding and max-width. The layout intentionally
 * owns no width constraints -- it's chrome only.
 *
 * The template builder lives at /admin/templates/:id (inside this
 * layout). Legacy /admin/templates/:id/edit redirects to that path.
 */
export default function AdminLayout() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} />
      <div
        data-testid="admin-layout-scroll"
        className="relative flex flex-col flex-1 overflow-y-auto overflow-x-hidden bg-gray-50 dark:bg-gray-950"
      >
        <Header sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} />
        {/* 7_13 PR3 — Admin global search (Story 60). Mounted at layout
            level so every /admin/* surface shares the affordance. */}
        <div className="px-4 sm:px-6 lg:px-8 pt-3 flex justify-end">
          <GlobalSearch />
        </div>
        <Outlet />
      </div>
    </div>
  );
}
