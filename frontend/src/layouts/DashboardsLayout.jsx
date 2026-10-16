import { useState } from 'react';
import { Outlet } from 'react-router-dom';

import { AdminProgramProvider } from '../context/AdminProgramContext';
import Header from '../partials/Header';
import Sidebar from '../partials/Sidebar';
import useNavBadges from './useNavBadges';

/**
 * Shared chrome for /dashboards/*. One sidebar (with the same nav badges
 * as /admin) so the Reflections item does not depend on which page
 * mounted it.
 */
export default function DashboardsLayout() {
  return (
    <AdminProgramProvider>
      <DashboardsShell />
    </AdminProgramProvider>
  );
}

function DashboardsShell() {
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
        data-testid="dashboards-layout-scroll"
        className="relative flex flex-col flex-1 overflow-y-auto overflow-x-hidden bg-ground"
      >
        <Header sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} />
        <Outlet />
      </div>
    </div>
  );
}
