import React from 'react';
import Sidebar from '../partials/Sidebar';
import Header from '../partials/Header';

/**
 * Loading component for dashboards while authentication is completing
 */
function DashboardLoading({ sidebarOpen, setSidebarOpen, message = "Loading your dashboard..." }) {
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
                {message}
              </h1>
              <p className="text-gray-600 dark:text-gray-400 mt-2">
                Please wait while we set up your profile and load your data.
              </p>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}

export default DashboardLoading;
