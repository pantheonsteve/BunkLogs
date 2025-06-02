import React, { useState, useEffect } from 'react';
import { useAuth } from '../auth/AuthContext';

import Sidebar from '../partials/Sidebar';
import Header from '../partials/Header';
import FilterButton from '../components/DropdownFilter';
import Datepicker from '../components/Datepicker';
import BunkGrid from '../partials/dashboard/BunkGrid';
import UserProfile from '../partials/dashboard/UserProfile';

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

              {/* Right: Actions */}
              <div className="grid grid-flow-col sm:auto-cols-max justify-start sm:justify-end gap-2">              
              </div>

            </div>
            <UserProfile user={userProfile} />
            {/* Bunk Cards */}
            <BunkGrid />
          </div>
        </main>

      </div>

    </div>
  );
}

export default Dashboard;