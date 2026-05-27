import React, { useState, useEffect } from 'react';
import { useAuth } from '../auth/AuthContext';
import { useNavigate } from 'react-router-dom';

import Sidebar from '../partials/Sidebar';
import Header from '../partials/Header';
import BunkGrid from '../partials/dashboard/BunkGrid';
import UserProfile from '../partials/dashboard/UserProfile';

/**
 * Role-based landing page.
 *
 * Reads user.role (old-model string from JWT) and immediately redirects to the
 * appropriate new-model role dashboard. This component is reachable from the
 * Sidebar "Home" link, the / root, and the * catch-all. Old bookmarks that
 * land here will transparently forward to the new URL.
 *
 * Roles without a specific redirect fall through to the BunkGrid view, which
 * is also kept as the fallback for Admins / Super-Admins browsing the legacy UI.
 */

const ROLE_DESTINATIONS = {
  'Counselor':      '/counselor',
  'Unit Head':      '/unit-head',
  'Camper Care':    '/camper-care',
  'Leadership':     '/leadership-team',
  'Leadership Team': '/leadership-team',
  'Kitchen Staff':  '/kitchen-staff',
  'Specialist':     '/specialist',
  'Madrich':        '/madrich',
  'Maintenance':    '/maintenance',
};

function Dashboard() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const { userProfile, isAuthenticated, user, loading: authLoading, isAuthenticating } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    if (authLoading || isAuthenticating) return;

    const destination = user?.role ? ROLE_DESTINATIONS[user.role] : null;
    if (destination) {
      navigate(destination, { replace: true });
    }
  }, [user, navigate, authLoading, isAuthenticating]);

  if (authLoading || isAuthenticating) {
    return (
      <div className="flex h-screen overflow-hidden">
        <Sidebar sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} />
        <div className="relative flex flex-col flex-1 overflow-y-auto overflow-x-hidden">
          <Header sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} />
          <main className="grow">
            <div className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-[96rem] mx-auto">
              <div className="text-center">
                <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-blue-500 mx-auto" />
                <h1 className="text-xl font-semibold text-gray-900 dark:text-white mt-4">
                  Setting up your dashboard…
                </h1>
                <p className="text-gray-600 dark:text-gray-400 mt-2">
                  Please wait while we load your profile.
                </p>
              </div>
            </div>
          </main>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-[100dvh] overflow-hidden">
      <Sidebar sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} />
      <div className="relative flex flex-col flex-1 overflow-y-auto overflow-x-hidden">
        <Header sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} />
        <main className="grow">
          <div className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-[96rem] mx-auto">
            <UserProfile user={userProfile} />
            <BunkGrid />
          </div>
        </main>
      </div>
    </div>
  );
}

export default Dashboard;
