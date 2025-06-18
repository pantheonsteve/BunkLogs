import React, { useState, useEffect } from 'react';
import { useAuth } from '../auth/AuthContext';
import { Navigate } from 'react-router-dom';

import Sidebar from '../partials/Sidebar';
import Header from '../partials/Header';
import UnitHeadBunkGrid from '../partials/dashboard/UnitHeadBunkGrid';
import UserProfile from '../partials/dashboard/UserProfile';

function UnitHeadDashboard() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const { user, userProfile, isAuthenticated, loading } = useAuth();

  // Redirect if not a Unit Head
  if (!loading && (!user || user.role !== 'Unit Head')) {
    return <Navigate to="/dashboard" replace />;
  }

  // Show loading state
  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gray-100 dark:bg-gray-900">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-emerald-500 mx-auto"></div>
          <p className="mt-3 text-gray-700 dark:text-gray-300">Loading...</p>
        </div>
      </div>
    );
  }

  useEffect(() => {
    // Log user profile data when dashboard mounts
    console.log('Unit Head user profile in dashboard:', userProfile);
  }, [userProfile]);

  return (
    <div className="flex h-[100dvh] overflow-hidden">

      {/* Sidebar */}
      <Sidebar sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} />

      {/* Content area */}
      <div className="relative flex flex-col flex-1 overflow-y-auto overflow-x-hidden">

        {/*  Site header */}
        <Header sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} />

        <main className="grow">
          <div className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-[96rem] mx-auto">

            {/* Dashboard header */}
            <div className="mb-8">
              <div className="flex items-center space-x-3 mb-4">
                <div className="w-10 h-10 bg-emerald-100 dark:bg-emerald-900/30 rounded-xl flex items-center justify-center">
                  <svg className="w-6 h-6 text-emerald-600 dark:text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
                  </svg>
                </div>
                <div>
                  <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100">
                    Unit Head Dashboard
                  </h1>
                  <p className="text-gray-600 dark:text-gray-400">
                    Manage your unit's bunks and staff
                  </p>
                </div>
              </div>
            </div>

            {/* User profile */}
            <UserProfile user={userProfile} />
            
            {/* Unit bunks grid */}
            <UnitHeadBunkGrid />
          </div>
        </main>

      </div>

    </div>
  );
}

export default UnitHeadDashboard;
