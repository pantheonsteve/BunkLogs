import React, { useState, useEffect } from 'react';
import { useAuth } from '../auth/AuthContext';
import { useNavigate } from 'react-router-dom';

import Sidebar from '../partials/Sidebar';
import Header from '../partials/Header';
import FilterButton from '../components/DropdownFilter';
import Datepicker from '../components/Datepicker';
import BunkGrid from '../partials/dashboard/BunkGrid';
import UserProfile from '../partials/dashboard/UserProfile';

function Dashboard() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const { userProfile, isAuthenticated, user, loading: authLoading, isAuthenticating } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    // Don't redirect if we're still loading auth state
    if (authLoading || isAuthenticating) {
      console.log('⏳ Waiting for auth to complete before redirecting...');
      return;
    }

    // Log user profile data when dashboard mounts
    console.log('📊 Dashboard mounted with user profile:', userProfile);
    console.log('👤 User object in dashboard:', user);
    
    // Redirect to role-specific dashboard if user has a specific role
    if (user && user.role) {
      console.log('🚀 Redirecting based on role:', user.role);
      switch (user.role) {
        case 'Unit Head':
          // Get today's date for the redirect
          const today = new Date();
          const year = today.getFullYear();
          const month = String(today.getMonth() + 1).padStart(2, '0');
          const day = String(today.getDate()).padStart(2, '0');
          const formattedDate = `${year}-${month}-${day}`;
          navigate(`/unithead/${user.id}/${formattedDate}`, { replace: true });
          return;
        case 'Camper Care':
          // Get today's date for the redirect
          const todayCare = new Date();
          const yearCare = todayCare.getFullYear();
          const monthCare = String(todayCare.getMonth() + 1).padStart(2, '0');
          const dayCare = String(todayCare.getDate()).padStart(2, '0');
          const formattedDateCare = `${yearCare}-${monthCare}-${dayCare}`;
          navigate(`/campercare/${user.id}/${formattedDateCare}`, { replace: true });
          return;
        case 'Counselor':
          // Redirect counselors to counselor dashboard with today's date
          const todayCounselor = new Date();
          const yearCounselor = todayCounselor.getFullYear();
          const monthCounselor = String(todayCounselor.getMonth() + 1).padStart(2, '0');
          const dayCounselor = String(todayCounselor.getDate()).padStart(2, '0');
          const formattedDateCounselor = `${yearCounselor}-${monthCounselor}-${dayCounselor}`;
          navigate(`/counselor-dashboard/${formattedDateCounselor}`, { replace: true });
          return;
        default:
          // Stay on general dashboard for other roles (Admin, etc.)
          console.log('📍 Staying on general dashboard for role:', user.role);
          break;
      }
    }
  }, [userProfile, user, navigate, authLoading, isAuthenticating]);

  // Show loading state while authentication is completing
  if (authLoading || isAuthenticating) {
    return (
      <div className="flex h-screen overflow-hidden">
        <Sidebar sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} />
        <div className="relative flex flex-col flex-1 overflow-y-auto overflow-x-hidden">
          <Header sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} />
          <main className="grow">
            <div className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-9xl mx-auto">
              <div className="text-center">
                <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-blue-500 mx-auto"></div>
                <h1 className="text-xl font-semibold text-gray-900 dark:text-white mt-4">
                  Setting up your dashboard...
                </h1>
                <p className="text-gray-600 dark:text-gray-400 mt-2">
                  Please wait while we load your profile and redirect you to the appropriate dashboard.
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