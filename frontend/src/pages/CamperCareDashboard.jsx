import React, { useState, useEffect } from 'react';
import { useAuth } from '../auth/AuthContext';
import { Navigate, useParams, useNavigate } from 'react-router-dom';

import Sidebar from '../partials/Sidebar';
import Header from '../partials/Header';
import CamperCareBunkGrid from '../partials/dashboard/CamperCareBunkGrid';
import UserProfile from '../partials/dashboard/UserProfile';
import SingleDatePicker from '../components/ui/SingleDatePicker';
import CamperCareBunkLogsList from '../partials/dashboard/CamperCareBunkLogsList';
import CamperCareNeedsAttentionList from '../partials/dashboard/CamperCareNeedsAttentionList';

function CamperCareDashboard() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const { user, userProfile, isAuthenticated, loading } = useAuth();
  const { id, date } = useParams();
  const navigate = useNavigate();

  // Add redirect if no date parameter for date-aware routes
  useEffect(() => {
    if (id && (!date || date === 'undefined')) {
      const today = new Date();
      const year = today.getFullYear();
      const month = String(today.getMonth() + 1).padStart(2, '0');
      const day = String(today.getDate()).padStart(2, '0');
      const formattedDate = `${year}-${month}-${day}`;
      
      console.log(`[CamperCareDashboard] No date in URL, redirecting to today: ${formattedDate}`);
      navigate(`/campercare/${id}/${formattedDate}`, { replace: true });
      return;
    }
  }, [id, date, navigate]);

  // Initialize selectedDate state
  const [selectedDate, setSelectedDate] = useState(() => {
    if (!date) {
      return new Date(); // Default to today if no date is provided
    } else if (date && date !== 'undefined') {
      const [year, month, day] = date.split('-').map(Number);
      return new Date(year, month - 1, day);
    } else {
      return new Date();
    }
  });

  // Keep selectedDate in sync with URL parameter
  useEffect(() => {
    if (date) {
      const [year, month, day] = date.split('-').map(Number);
      const dateFromUrl = new Date(year, month - 1, day);
      setSelectedDate(dateFromUrl);
    }
  }, [date]);

  const handleDateChange = React.useCallback((newDate) => {
    if (!newDate || !new Date(newDate).getTime()) {
      console.log('[CamperCareDashboard] Invalid date provided to handleDateChange');
      return;
    }

    const year = newDate.getFullYear();
    const month = newDate.getMonth();
    const day = newDate.getDate();
    const standardizedDate = new Date(year, month, day);
    
    // Format date for URL: YYYY-MM-DD
    const formattedDate = `${year}-${String(month + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
    
    // Navigate to new URL with selected date
    if (id) {
      navigate(`/campercare/${id}/${formattedDate}`);
    }
    
    setSelectedDate(standardizedDate);
  }, [id, navigate]);

  // View state for sidebar navigation
  const [activeView, setActiveView] = useState('overview'); // 'overview', 'bunklogs', 'needsattention'

  // Redirect if not a Camper Care team member
  if (!loading && (!user || user.role !== 'Camper Care')) {
    return <Navigate to="/dashboard" replace />;
  }

  // Show loading state
  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gray-100 dark:bg-gray-900">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-rose-500 mx-auto"></div>
          <p className="mt-3 text-gray-700 dark:text-gray-300">Loading...</p>
        </div>
      </div>
    );
  }

  useEffect(() => {
    // Log user profile data when dashboard mounts
    console.log('Camper Care user profile in dashboard:', userProfile);
  }, [userProfile]);

  return (
    <div className="flex h-[100dvh] overflow-hidden">

      {/* Sidebar */}
      <Sidebar 
        sidebarOpen={sidebarOpen} 
        setSidebarOpen={setSidebarOpen} 
        extraLinks={[
          {
            label: 'My Bunk Logs',
            onClick: () => setActiveView('bunklogs'),
            active: activeView === 'bunklogs',
            role: 'Camper Care',
          },
          {
            label: 'Needs Attention',
            onClick: () => setActiveView('needsattention'),
            active: activeView === 'needsattention',
            role: 'Camper Care',
          },
        ]}
      />

      {/* Content area */}
      <div className="relative flex flex-col flex-1 overflow-y-auto overflow-x-hidden">

        {/*  Site header */}
        <Header sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} />

        <main className="grow">
          <div className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-[96rem] mx-auto">

            {/* Dashboard header */}
            <div className="mb-8">
              <div className="flex items-center space-x-3 mb-4">
                <div className="w-10 h-10 bg-rose-100 dark:bg-rose-900/30 rounded-xl flex items-center justify-center">
                  <svg className="w-6 h-6 text-rose-600 dark:text-rose-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" />
                  </svg>
                </div>
                <div>
                  <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100">
                    Camper Care Dashboard
                  </h1>
                  <p className="text-gray-600 dark:text-gray-400">
                    Monitor and support camper wellbeing
                  </p>
                </div>
              </div>

              {/* Date picker - only show for date-aware routes */}
              {id && date && (
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-4">
                    <SingleDatePicker 
                      date={selectedDate} 
                      setDate={handleDateChange}
                      className="w-auto"
                    />
                  </div>
                </div>
              )}
            </div>

            {/* User profile */}
            <UserProfile user={userProfile} />
            {/* Main content view */}
            {activeView === 'overview' && <CamperCareBunkGrid selectedDate={selectedDate} />}
            {activeView === 'bunklogs' && <CamperCareBunkLogsList selectedDate={selectedDate} />}
            {activeView === 'needsattention' && <CamperCareNeedsAttentionList selectedDate={selectedDate} />}
          </div>
        </main>

      </div>

    </div>
  );
}

export default CamperCareDashboard;
