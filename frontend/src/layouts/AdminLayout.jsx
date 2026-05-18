import { useState } from 'react';
import { Outlet } from 'react-router-dom';

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
 * The TemplateEditorPage (/admin/templates/:id/edit) is wired up as a
 * sibling of this layout in Router.jsx, not as a child, because it's a
 * focused full-bleed editor with its own sticky in-page header. See the
 * prompt in `migration_prompts/3_28_admin_chrome_alignment.md`.
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
        <Outlet />
      </div>
    </div>
  );
}
