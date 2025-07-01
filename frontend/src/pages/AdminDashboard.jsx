import React, { useState, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { Calendar, Users, FileText, Eye, ChevronLeft, ChevronRight, Download } from 'lucide-react';

import Header from '../partials/Header';
import Sidebar from '../partials/Sidebar';
import SingleDatePicker from '../components/ui/SingleDatePicker';
import { useAuth } from '../auth/AuthContext';
import api from '../api';

function AdminDashboard() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const { user, loading: authLoading, isAuthenticating } = useAuth();
  const { date } = useParams();
  const navigate = useNavigate();
  
  // State management
  const [counselorLogs, setCounselorLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedDate, setSelectedDate] = useState(new Date());
  const [selectedLog, setSelectedLog] = useState(null);
  const [viewingDetails, setViewingDetails] = useState(false);

  // Parse and validate date from URL parameters
  useEffect(() => {
    if (date && date !== 'undefined') {
      try {
        const parsedDate = new Date(date + 'T00:00:00');
        if (!isNaN(parsedDate.getTime())) {
          setSelectedDate(parsedDate);
        }
      } catch (err) {
        console.error('Error parsing date from URL:', err);
      }
    }
  }, [date]);

  // Add redirect if no date parameter
  useEffect(() => {
    if (!date || date === 'undefined') {
      const today = new Date();
      const year = today.getFullYear();
      const month = String(today.getMonth() + 1).padStart(2, '0');
      const day = String(today.getDate()).padStart(2, '0');
      const formattedDate = `${year}-${month}-${day}`;
      
      navigate(`/admin-dashboard/${formattedDate}`, { replace: true });
      return;
    }
  }, [date, navigate]);

  // Fetch counselor logs for the selected date
  useEffect(() => {
    async function fetchCounselorLogs() {
      if (authLoading || isAuthenticating || !user?.id || !date) {
        console.log('⏳ Skipping data fetch - auth state:', { 
          authLoading, 
          isAuthenticating, 
          hasUserId: !!user?.id,
          hasDate: !!date
        });
        return;
      }
      
      try {
        console.log('📡 Fetching counselor logs for date:', date);
        setLoading(true);
        setError(null);
        
        // Get user's timezone
        const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
        console.log('🌍 User timezone:', timezone);
        
        const response = await api.get(`/api/v1/counselorlogs/${date}/`, {
          params: { timezone }
        });
        setCounselorLogs(response.data.results || []);
        console.log('✅ Counselor logs loaded:', response.data.results?.length || 0, 'items');
        
      } catch (err) {
        console.error('❌ Error fetching counselor logs:', err);
        setError('Failed to load counselor logs');
        setCounselorLogs([]);
      } finally {
        setLoading(false);
      }
    }
    
    fetchCounselorLogs();
  }, [user?.id, date, authLoading, isAuthenticating]);

  // Handle date change
  const handleDateChange = (newDate) => {
    const year = newDate.getFullYear();
    const month = String(newDate.getMonth() + 1).padStart(2, '0');
    const day = String(newDate.getDate()).padStart(2, '0');
    const formattedDate = `${year}-${month}-${day}`;
    
    navigate(`/admin-dashboard/${formattedDate}`);
  };

  // Navigate to previous/next day
  const navigateDate = (direction) => {
    const currentDate = new Date(selectedDate);
    const newDate = new Date(currentDate);
    newDate.setDate(currentDate.getDate() + (direction === 'next' ? 1 : -1));
    handleDateChange(newDate);
  };

  // View log details
  const viewLogDetails = (log) => {
    setSelectedLog(log);
    setViewingDetails(true);
  };

  // Export to CSV (placeholder for future implementation)
  const exportToCSV = () => {
    console.log('Export to CSV functionality to be implemented');
    // TODO: Implement CSV export
  };

  // Get quality score color
  const getScoreColor = (score) => {
    if (score >= 4) return 'text-green-600 bg-green-50';
    if (score >= 3) return 'text-yellow-600 bg-yellow-50';
    return 'text-red-600 bg-red-50';
  };

  // Format date for display
  const formatDisplayDate = (dateStr) => {
    // Parse as UTC to avoid timezone offset issues
    const [year, month, day] = dateStr.split('-');
    const date = new Date(Date.UTC(year, month - 1, day));
    return date.toLocaleDateString('en-US', { 
      weekday: 'long', 
      year: 'numeric', 
      month: 'long', 
      day: 'numeric',
      timeZone: 'UTC'
    });
  };

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
                  Loading Admin Dashboard...
                </h1>
                <p className="text-gray-600 dark:text-gray-400 mt-2">
                  Please wait while we load the counselor logs.
                </p>
              </div>
            </div>
          </main>
        </div>
      </div>
    );
  }

  // Redirect non-admin users
  if (user && user.role !== 'Admin') {
    return (
      <div className="flex h-screen overflow-hidden">
        <Sidebar sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} />
        <div className="relative flex flex-col flex-1 overflow-y-auto overflow-x-hidden">
          <Header sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} />
          <main className="grow">
            <div className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-9xl mx-auto">
              <div className="text-center">
                <div className="rounded-md bg-red-50 p-4">
                  <div className="flex">
                    <div className="ml-3">
                      <h3 className="text-sm font-medium text-red-800">
                        Access Denied
                      </h3>
                      <div className="mt-2 text-sm text-red-700">
                        <p>You do not have permission to access the Admin Dashboard.</p>
                      </div>
                    </div>
                  </div>
                </div>
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
        {/* Site header */}
        <Header sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} />

        <main className="grow">
          <div className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-9xl mx-auto">
            
            {/* Header */}
            <div className="sm:flex sm:justify-between sm:items-center mb-8">
              <div>
                <h1 className="text-2xl md:text-3xl text-gray-800 dark:text-gray-100 font-bold">
                  Admin Dashboard
                </h1>
                <p className="text-gray-600 dark:text-gray-400">
                  View and manage counselor logs across all staff
                </p>
              </div>
              
              {/* Actions */}
              <div className="grid grid-flow-col sm:auto-cols-max justify-start sm:justify-end gap-2">
                <button
                  onClick={exportToCSV}
                  className="btn bg-white dark:bg-gray-800 border-gray-200 dark:border-gray-700/60 hover:border-gray-300 dark:hover:border-gray-600 text-gray-800 dark:text-gray-300"
                >
                  <Download className="w-4 h-4 mr-2" />
                  Export CSV
                </button>
              </div>
            </div>

            {/* Date Navigation */}
            <div className="bg-white dark:bg-gray-800 shadow-sm rounded-xl p-6 mb-8">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-4">
                  <button
                    onClick={() => navigateDate('prev')}
                    className="p-2 rounded-lg border border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700"
                  >
                    <ChevronLeft className="w-4 h-4" />
                  </button>
                  
                  <div className="flex items-center space-x-3">
                    <Calendar className="w-5 h-5 text-gray-400" />
                    <SingleDatePicker date={selectedDate} setDate={handleDateChange} />
                  </div>
                  
                  <button
                    onClick={() => navigateDate('next')}
                    className="p-2 rounded-lg border border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700"
                  >
                    <ChevronRight className="w-4 h-4" />
                  </button>
                </div>
                
                <div className="text-sm text-gray-600 dark:text-gray-400">
                  {date && formatDisplayDate(date)}
                </div>
              </div>
            </div>

            {/* Stats Cards */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
              <div className="bg-white dark:bg-gray-800 shadow-sm rounded-xl p-6">
                <div className="flex items-center">
                  <div className="flex-shrink-0">
                    <Users className="w-8 h-8 text-blue-500" />
                  </div>
                  <div className="ml-4">
                    <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Total Logs</p>
                    <p className="text-2xl font-semibold text-gray-900 dark:text-white">
                      {counselorLogs.length}
                    </p>
                  </div>
                </div>
              </div>
              
              <div className="bg-white dark:bg-gray-800 shadow-sm rounded-xl p-6">
                <div className="flex items-center">
                  <div className="flex-shrink-0">
                    <FileText className="w-8 h-8 text-green-500" />
                  </div>
                  <div className="ml-4">
                    <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Avg. Quality Score</p>
                    <p className="text-2xl font-semibold text-gray-900 dark:text-white">
                      {counselorLogs.length > 0 
                        ? (counselorLogs.reduce((sum, log) => sum + log.day_quality_score, 0) / counselorLogs.length).toFixed(1)
                        : '--'
                      }
                    </p>
                  </div>
                </div>
              </div>
              
              <div className="bg-white dark:bg-gray-800 shadow-sm rounded-xl p-6">
                <div className="flex items-center">
                  <div className="flex-shrink-0">
                    <Users className="w-8 h-8 text-yellow-500" />
                  </div>
                  <div className="ml-4">
                    <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Support Needed</p>
                    <p className="text-2xl font-semibold text-gray-900 dark:text-white">
                      {counselorLogs.filter(log => log.staff_care_support_needed).length}
                    </p>
                  </div>
                </div>
              </div>
            </div>

            {/* Counselor Logs Table */}
            <div className="bg-white dark:bg-gray-800 shadow-sm rounded-xl">
              <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
                <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
                  Counselor Logs for {date && formatDisplayDate(date)}
                </h2>
              </div>
              
              <div className="overflow-x-auto">
                {loading ? (
                  <div className="flex items-center justify-center py-12">
                    <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-blue-500"></div>
                    <span className="ml-3 text-gray-600 dark:text-gray-400">Loading logs...</span>
                  </div>
                ) : error ? (
                  <div className="flex items-center justify-center py-12">
                    <div className="text-red-600 dark:text-red-400">{error}</div>
                  </div>
                ) : counselorLogs.length === 0 ? (
                  <div className="flex items-center justify-center py-12">
                    <div className="text-center">
                      <FileText className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                      <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
                        No logs found
                      </h3>
                      <p className="text-gray-600 dark:text-gray-400">
                        No counselor logs were submitted for this date.
                      </p>
                    </div>
                  </div>
                ) : (
                  <table className="w-full">
                    <thead className="bg-gray-50 dark:bg-gray-900">
                      <tr>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                          Counselor
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                          Quality Score
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                          Support Score
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                          Day Off
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                          Support Needed
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                          Submitted
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                          Actions
                        </th>
                      </tr>
                    </thead>
                    <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
                      {counselorLogs.map((log) => (
                        <tr key={log.id} className="hover:bg-gray-50 dark:hover:bg-gray-700">
                          <td className="px-6 py-4 whitespace-nowrap">
                            <div className="flex items-center">
                              <div className="flex-shrink-0 h-10 w-10">
                                <div className="h-10 w-10 rounded-full bg-gray-300 dark:bg-gray-600 flex items-center justify-center">
                                  <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                                    {log.counselor_first_name?.[0]}{log.counselor_last_name?.[0]}
                                  </span>
                                </div>
                              </div>
                              <div className="ml-4">
                                <div className="text-sm font-medium text-gray-900 dark:text-white">
                                  {log.counselor_first_name} {log.counselor_last_name}
                                </div>
                                <div className="text-sm text-gray-500 dark:text-gray-400">
                                  {log.counselor_email}
                                </div>
                              </div>
                            </div>
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap">
                            <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${getScoreColor(log.day_quality_score)}`}>
                              {log.day_quality_score}/5
                            </span>
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap">
                            <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${getScoreColor(log.support_level_score)}`}>
                              {log.support_level_score}/5
                            </span>
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap">
                            <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                              log.day_off ? 'text-blue-600 bg-blue-50' : 'text-gray-600 bg-gray-50'
                            }`}>
                              {log.day_off ? 'Yes' : 'No'}
                            </span>
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap">
                            <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                              log.staff_care_support_needed ? 'text-red-600 bg-red-50' : 'text-green-600 bg-green-50'
                            }`}>
                              {log.staff_care_support_needed ? 'Yes' : 'No'}
                            </span>
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                            {new Date(log.created_at).toLocaleTimeString('en-US', { 
                              hour: '2-digit', 
                              minute: '2-digit' 
                            })}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                            <button
                              onClick={() => viewLogDetails(log)}
                              className="text-blue-600 hover:text-blue-900 dark:text-blue-400 dark:hover:text-blue-300"
                            >
                              <Eye className="w-4 h-4" />
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </div>
            </div>

            {/* Detail Modal */}
            {viewingDetails && selectedLog && (
              <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
                <div className="bg-white dark:bg-gray-800 rounded-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
                  <div className="p-6">
                    <div className="flex items-center justify-between mb-6">
                      <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                        Counselor Log Details
                      </h3>
                      <button
                        onClick={() => setViewingDetails(false)}
                        className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
                      >
                        ✕
                      </button>
                    </div>
                    
                    <div className="space-y-6">
                      {/* Counselor Info */}
                      <div>
                        <h4 className="text-sm font-medium text-gray-900 dark:text-white mb-2">Counselor</h4>
                        <p className="text-sm text-gray-600 dark:text-gray-400">
                          {selectedLog.counselor_first_name} {selectedLog.counselor_last_name} ({selectedLog.counselor_email})
                        </p>
                      </div>
                      
                      {/* Scores */}
                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <h4 className="text-sm font-medium text-gray-900 dark:text-white mb-2">Day Quality Score</h4>
                          <span className={`inline-flex px-3 py-1 text-sm font-semibold rounded-full ${getScoreColor(selectedLog.day_quality_score)}`}>
                            {selectedLog.day_quality_score}/5
                          </span>
                        </div>
                        <div>
                          <h4 className="text-sm font-medium text-gray-900 dark:text-white mb-2">Support Level Score</h4>
                          <span className={`inline-flex px-3 py-1 text-sm font-semibold rounded-full ${getScoreColor(selectedLog.support_level_score)}`}>
                            {selectedLog.support_level_score}/5
                          </span>
                        </div>
                      </div>
                      
                      {/* Flags */}
                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <h4 className="text-sm font-medium text-gray-900 dark:text-white mb-2">Day Off</h4>
                          <span className={`inline-flex px-3 py-1 text-sm font-semibold rounded-full ${
                            selectedLog.day_off ? 'text-blue-600 bg-blue-50' : 'text-gray-600 bg-gray-50'
                          }`}>
                            {selectedLog.day_off ? 'Yes' : 'No'}
                          </span>
                        </div>
                        <div>
                          <h4 className="text-sm font-medium text-gray-900 dark:text-white mb-2">Support Needed</h4>
                          <span className={`inline-flex px-3 py-1 text-sm font-semibold rounded-full ${
                            selectedLog.staff_care_support_needed ? 'text-red-600 bg-red-50' : 'text-green-600 bg-green-50'
                          }`}>
                            {selectedLog.staff_care_support_needed ? 'Yes' : 'No'}
                          </span>
                        </div>
                      </div>
                      
                      {/* Elaboration */}
                      <div>
                        <h4 className="text-sm font-medium text-gray-900 dark:text-white mb-2">Day Elaboration</h4>
                        <div 
                          className="text-sm text-gray-600 dark:text-gray-400 bg-gray-50 dark:bg-gray-700 p-3 rounded-lg"
                          dangerouslySetInnerHTML={{ __html: selectedLog.elaboration }}
                        />
                      </div>
                      
                      {/* Values Reflection */}
                      <div>
                        <h4 className="text-sm font-medium text-gray-900 dark:text-white mb-2">Values Reflection</h4>
                        <div 
                          className="text-sm text-gray-600 dark:text-gray-400 bg-gray-50 dark:bg-gray-700 p-3 rounded-lg"
                          dangerouslySetInnerHTML={{ __html: selectedLog.values_reflection }}
                        />
                      </div>
                      
                      {/* Timestamps */}
                      <div className="grid grid-cols-2 gap-4 text-xs text-gray-500 dark:text-gray-400">
                        <div>
                          <span className="font-medium">Created:</span><br />
                          {new Date(selectedLog.created_at).toLocaleString()}
                        </div>
                        <div>
                          <span className="font-medium">Updated:</span><br />
                          {new Date(selectedLog.updated_at).toLocaleString()}
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            )}

          </div>
        </main>
      </div>
    </div>
  );
}

export default AdminDashboard;
