import { useState } from 'react';
import { Outlet } from 'react-router-dom';

import Header from '../partials/Header';
import Sidebar from '../partials/Sidebar';

/**
 * Shared layout for non-admin authenticated app routes (3.32
 * follow-up). Renders the same Sidebar + Header chrome AdminLayout
 * uses, then slots the matched child route into `<Outlet/>`.
 *
 * Why this exists: pages like /tasks, /reflect, /reflect/summary,
 * and /supervisor/coverage were originally built as mobile-first,
 * single-column views that mounted no chrome at all. After the 3.32
 * sidebar restructure the missing chrome became user-visible
 * ("My Tasks / File a Reflection / Coverage all make the sidebar
 * disappear"). Wrap those routes here so the navigation is always
 * in place when you click between admin, dashboards, supervise, and
 * task surfaces.
 *
 * Sibling of `AdminLayout`. We keep them separate so each can be
 * audited independently (AdminRoute gating sits on the admin tree;
 * AppLayout has no extra gates -- it inherits the per-route
 * ProtectedRoute wrappers in Router.jsx).
 *
 * The layout owns no width constraints. Child routes provide their
 * own `<main>` / content wrapper so a focused single-column page
 * (e.g. /reflect) and a full-width page can share this shell.
 */
export default function AppLayout() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} />
      <div
        data-testid="app-layout-scroll"
        className="relative flex flex-col flex-1 overflow-y-auto overflow-x-hidden bg-gray-50 dark:bg-gray-950"
      >
        <Header sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} />
        <Outlet />
      </div>
    </div>
  );
}
