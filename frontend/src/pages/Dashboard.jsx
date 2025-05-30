import React, { useState, useEffect } from 'react';
import { useAuth } from '../auth/AuthContext';

import Sidebar from '../partials/Sidebar';
import Header from '../partials/Header';
import FilterButton from '../components/DropdownFilter';
import Datepicker from '../components/Datepicker';
import BunkGrid from '../partials/dashboard/BunkGrid';

function Dashboard() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const { userProfile, isAuthenticated } = useAuth();

  useEffect(() => {
    // Log user profile data when dashboard mounts
    console.log('User profile in dashboard:', userProfile);
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

            {/* Dashboard actions */}
            <div className="sm:flex sm:justify-between sm:items-center mb-8">

              {/* Left: Title */}
              <div className="mb-4 sm:mb-0">
                <h1 className="text-2xl md:text-3xl text-gray-800 dark:text-gray-100 font-bold">Dashboard</h1>
                {userProfile && (
                  <div className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                    Welcome, {userProfile.first_name || userProfile.email || 'User'} 
                    {userProfile.role && <span className="ml-2 px-2 py-1 bg-violet-100 text-violet-800 dark:bg-violet-800/30 dark:text-violet-400 rounded-full text-xs">{userProfile.role}</span>}
                  </div>
                )}
              </div>

              {/* Right: Actions */}
              <div className="grid grid-flow-col sm:auto-cols-max justify-start sm:justify-end gap-2">              
              </div>

            </div>

            {/* User Profile Summary Card */}
            {userProfile && (
              <div className="bg-white dark:bg-gray-800 shadow-lg rounded-sm border border-gray-200 dark:border-gray-700 mb-8">
                <div className="px-5 py-4">
                  <h2 className="font-semibold text-gray-800 dark:text-gray-100">User Profile</h2>
                  <div className="grid md:grid-cols-2 gap-4 mt-3">
                    <div>
                      <div className="text-sm text-gray-500 dark:text-gray-400">Name</div>
                      <div className="font-medium text-gray-800 dark:text-gray-100">
                        {userProfile.first_name || ''} {userProfile.last_name || ''}
                      </div>
                    </div>
                    <div>
                      <div className="text-sm text-gray-500 dark:text-gray-400">Email</div>
                      <div className="font-medium text-gray-800 dark:text-gray-100">{userProfile.email || 'Not available'}</div>
                    </div>
                    <div>
                      <div className="text-sm text-gray-500 dark:text-gray-400">Role</div>
                      <div className="font-medium text-gray-800 dark:text-gray-100">{userProfile.role || 'Not specified'}</div>
                    </div>
                    <div>
                      <div className="text-sm text-gray-500 dark:text-gray-400">User ID</div>
                      <div className="font-medium text-gray-800 dark:text-gray-100">{userProfile.id || 'Not available'}</div>
                    </div>
                  </div>
                </div>
              </div>
            )}
            {/* Bunk Cards */}
            <BunkGrid />
          </div>
        </main>

      </div>

    </div>
  );
}

export default Dashboard;