import React, { useState, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { Calendar, FileText, Plus, User, Clock, CheckCircle, Eye, Table } from 'lucide-react';

import Header from '../partials/Header';
import Sidebar from '../partials/Sidebar';
import SingleDatePicker from '../components/ui/SingleDatePicker';
import CounselorLogFormModal from '../components/modals/CounselorLogFormModal';
import CounselorLogForm from '../components/form/CounselorLogForm';
import { useAuth } from '../auth/AuthContext';
import api from '../api';

function CounselorDashboard() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const { user, loading: authLoading, isAuthenticating } = useAuth();
  const [counselorLogModalOpen, setCounselorLogModalOpen] = useState(false);
  const [viewLogModalOpen, setViewLogModalOpen] = useState(false);
  const [selectedLogForView, setSelectedLogForView] = useState(null);
  const [refreshTrigger, setRefreshTrigger] = useState(0);
  const { date } = useParams();
  const navigate = useNavigate();
  const [counselorLogs, setCounselorLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedDate, setSelectedDate] = useState(() => {
    // Initialize with today's date at noon local time
    const today = new Date();
    today.setHours(12, 0, 0, 0);
    return today;
  });
  const [showTableView, setShowTableView] = useState(false);

  // Debug modal state changes
  useEffect(() => {
    console.log('[CounselorDashboard] Modal state changed to:', counselorLogModalOpen);
  }, [counselorLogModalOpen]);

  // Parse and validate date from URL parameters
  useEffect(() => {
    if (date && date !== 'undefined') {
      try {
        // Parse date in a timezone-safe way
        const [year, month, day] = date.split('-').map(Number);
        const parsedDate = new Date(year, month - 1, day, 12, 0, 0, 0); // Set to noon local time
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
      
      navigate(`/counselor-dashboard/${formattedDate}`, { replace: true });
      return; // Exit early to avoid setting up the rest of the component
    }
  }, [date, navigate]);

  // For counselors, redirect future dates to today
  useEffect(() => {
    if (user?.role === 'Counselor' && date && date !== 'undefined') {
      const today = new Date();
      const selectedDate = new Date(date);
      
      // Check if the selected date is in the future
      if (selectedDate > today) {
        console.log('Counselor tried to access future date, redirecting to today');
        const year = today.getFullYear();
        const month = String(today.getMonth() + 1).padStart(2, '0');
        const day = String(today.getDate()).padStart(2, '0');
        const formattedDate = `${year}-${month}-${day}`;
        
        navigate(`/counselor-dashboard/${formattedDate}`, { replace: true });
        return;
      }
    }
  }, [date, user?.role, navigate]);

  // Fetch counselor logs data
  useEffect(() => {
    async function fetchCounselorLogs() {
      // Don't fetch if we're still authenticating or don't have a user ID
      if (authLoading || isAuthenticating || !user?.id) {
        console.log('⏳ Skipping data fetch - auth state:', { 
          authLoading, 
          isAuthenticating, 
          hasUserId: !!user?.id 
        });
        return;
      }
      
      try {
        console.log('📡 Fetching counselor logs for user:', user.id);
        setLoading(true);
        setError(null);
        
        const response = await api.get('/api/v1/counselorlogs/');
        setCounselorLogs(response.data.results || []);
        console.log('✅ Counselor logs loaded:', response.data.results?.length || 0, 'items');
        
      } catch (err) {
        console.error('❌ Error fetching counselor logs:', err);
        setError('Failed to load counselor logs');
      } finally {
        setLoading(false);
      }
    }
    
    fetchCounselorLogs();
  }, [user?.id, refreshTrigger, authLoading, isAuthenticating]);

  // Handle date change
  const handleDateChange = (newDate) => {
    // Don't navigate if modal is open (prevents modal from closing due to re-mount)
    if (counselorLogModalOpen) {
      return;
    }
    
    const year = newDate.getFullYear();
    const month = newDate.getMonth();
    const day = newDate.getDate();
    const standardizedDate = new Date(year, month, day);

    // Format date for URL: YYYY-MM-DD
    const formattedDate = `${year}-${String(month + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
    
    // Navigate to new URL with selected date
    navigate(`/counselor-dashboard/${formattedDate}`);
    
    // Update the selected date state
    setSelectedDate(standardizedDate);
  };

  const handleOpenCounselorLogModal = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setCounselorLogModalOpen(true);
  };

  const handleModalClose = (wasSubmitted) => {
    if(wasSubmitted) {
      // Trigger data refresh to show updated counselor logs
      setRefreshTrigger(prev => prev + 1);
    }
    setCounselorLogModalOpen(false);
  };

  const handleViewLogClick = (log) => {
    setSelectedLogForView(log);
    setViewLogModalOpen(true);
  };

  const handleViewModalClose = () => {
    setViewLogModalOpen(false);
    setSelectedLogForView(null);
  };

  // Helper function to strip HTML tags for table display
  const stripHtml = (html) => {
    if (!html) return '';
    const tmp = document.createElement("DIV");
    tmp.innerHTML = html;
    return tmp.textContent || tmp.innerText || "";
  };

  // Helper function to truncate text
  const truncateText = (text, maxLength = 50) => {
    if (!text) return '';
    const stripped = stripHtml(text);
    return stripped.length > maxLength ? stripped.substring(0, maxLength) + '...' : stripped;
  };

  // Score color coding (matching bunk logs color scheme)
  const getScoreColor = (score) => {
    if (!score) return 'bg-gray-100 text-gray-800';
    
    const scoreNum = parseInt(score);
    switch (scoreNum) {
      case 1: return 'bg-[#e86946] text-white';
      case 2: return 'bg-[#de8d6f] text-white';
      case 3: return 'bg-[#e5e825] text-gray-900';
      case 4: return 'bg-[#90d258] text-gray-900';
      case 5: return 'bg-[#18d128] text-white';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  // Format date to human readable format (e.g., "Mon June 23, 2025")
  const formatHumanDate = (dateString) => {
    if (!dateString) return '';
    try {
      const date = new Date(dateString);
      return date.toLocaleDateString('en-US', {
        weekday: 'short',
        year: 'numeric',
        month: 'long',
        day: 'numeric'
      });
    } catch (error) {
      return dateString;
    }
  };

  // Check user roles
  const isCounselor = user?.role === 'Counselor';

  // Show loading while authentication is completing
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
                  Loading your dashboard...
                </h1>
                <p className="text-gray-600 dark:text-gray-400 mt-2">
                  Please wait while we set up your profile.
                </p>
              </div>
            </div>
          </main>
        </div>
      </div>
    );
  }

  // Get formatted date for display and API calls
  const selected_date = selectedDate.toISOString().split('T')[0];

  // Find existing log for selected date
  const existingLogForDate = counselorLogs.find(log => log.date === selected_date);

  // Only allow counselors to access this page
  if (!isCounselor) {
    return (
      <div className="flex h-screen overflow-hidden">
        <Sidebar sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} />
        <div className="relative flex flex-col flex-1 overflow-y-auto overflow-x-hidden">
          <Header sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} />
          <main className="grow">
            <div className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-9xl mx-auto">
              <div className="text-center">
                <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-4">
                  Access Denied
                </h1>
                <p className="text-gray-600 dark:text-gray-400">
                  Only counselors can access the counselor dashboard.
                </p>
              </div>
            </div>
          </main>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-screen overflow-hidden">
      {/* Sidebar */}
      <Sidebar sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} />

      {/* Content area */}
      <div className="relative flex flex-col flex-1 overflow-y-auto overflow-x-hidden">
        {/* Site header */}
        <Header sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} />

        <main className="grow">
          <div className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-9xl mx-auto">
            
            {/* Page header */}
            <div className="sm:flex sm:justify-between sm:items-center mb-8">
              <div className="mb-4 sm:mb-0">
                <h1 className="text-2xl md:text-3xl text-gray-800 dark:text-gray-100 font-bold">
                  Counselor Dashboard
                </h1>
                <p className="text-sm text-gray-600 dark:text-gray-400">
                  Track your daily reflections and experiences
                </p>
              </div>

              {/* Action button */}
              <div className="grid grid-flow-col sm:auto-cols-max justify-start sm:justify-end gap-2">
                <button
                  onClick={handleOpenCounselorLogModal}
                  className="bg-blue-500 hover:bg-blue-600 text-white font-medium py-2 px-4 rounded-lg transition-colors duration-200 flex items-center space-x-2"
                >
                  <Plus className="w-4 h-4" />
                  <span>{existingLogForDate ? 'Edit' : 'Create'} Reflection</span>
                </button>
              </div>
            </div>

            {/* Date selector */}
            <div className="mb-6">
              <div className="flex items-center space-x-4">
                <div className="flex items-center space-x-2">
                  <Calendar className="w-5 h-5 text-gray-500" />
                  <span className="text-sm font-medium text-gray-700 dark:text-gray-300">Selected Date:</span>
                </div>
                <SingleDatePicker 
                  date={selectedDate}
                  setDate={handleDateChange}
                />
              </div>
            </div>

            {/* Main content */}
            <div className="space-y-6">
              
              {/* Current Day Log Status */}
              <div className="bg-white dark:bg-gray-800 shadow-sm rounded-xl p-6">
                <div className="flex items-center justify-between mb-4">
                  <h2 className="text-xl font-semibold text-gray-800 dark:text-white">
                    Today's Reflection Status
                  </h2>
                  <div className="text-sm text-gray-500 dark:text-gray-400">
                    {selected_date}
                  </div>
                </div>
                
                {existingLogForDate ? (
                  <div className="space-y-4">
                    <div className="flex items-center space-x-2 text-green-600 dark:text-green-400">
                      <CheckCircle className="w-5 h-5" />
                      <span className="font-medium">Reflection completed for this date</span>
                    </div>
                    
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">
                      <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-4">
                        <div className="text-sm text-gray-600 dark:text-gray-400 mb-2">Day Quality</div>
                        <div className={`inline-flex items-center justify-center px-3 py-1 rounded-lg text-2xl font-bold ${getScoreColor(existingLogForDate.day_quality_score)}`}>
                          {existingLogForDate.day_quality_score}/5
                        </div>
                      </div>
                      
                      <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-4">
                        <div className="text-sm text-gray-600 dark:text-gray-400 mb-2">Support Level</div>
                        <div className={`inline-flex items-center justify-center px-3 py-1 rounded-lg text-2xl font-bold ${getScoreColor(existingLogForDate.support_level_score)}`}>
                          {existingLogForDate.support_level_score}/5
                        </div>
                      </div>
                    </div>
                    
                    {existingLogForDate.day_off && (
                      <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-3">
                        <div className="text-blue-800 dark:text-blue-200 text-sm">
                          Day off marked for this date
                        </div>
                      </div>
                    )}
                    
                    {existingLogForDate.staff_care_support_needed && (
                      <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg p-3">
                        <div className="text-yellow-800 dark:text-yellow-200 text-sm">
                          Staff care support requested
                        </div>
                      </div>
                    )}
                    
                    {/* Elaboration Section */}
                    {!existingLogForDate.day_off && existingLogForDate.elaboration && (
                      <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-4">
                        <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                          Elaboration on your day
                        </h4>
                        <div 
                          className="text-sm text-gray-600 dark:text-gray-400 prose prose-sm max-w-none"
                          dangerouslySetInnerHTML={{ __html: existingLogForDate.elaboration }}
                        />
                      </div>
                    )}
                    
                    {/* Values Reflection Section */}
                    {!existingLogForDate.day_off && existingLogForDate.values_reflection && (
                      <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-4">
                        <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                          How the bunk exemplified our values
                        </h4>
                        <div 
                          className="text-sm text-gray-600 dark:text-gray-400 prose prose-sm max-w-none"
                          dangerouslySetInnerHTML={{ __html: existingLogForDate.values_reflection }}
                        />
                      </div>
                    )}
                    
                    <div className="flex space-x-3">
                      <button
                        onClick={handleOpenCounselorLogModal}
                        className="text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300 text-sm font-medium"
                      >
                        Edit Details →
                      </button>
                      <button
                        onClick={() => handleViewLogClick(existingLogForDate)}
                        className="text-green-600 hover:text-green-800 dark:text-green-400 dark:hover:text-green-300 text-sm font-medium flex items-center space-x-1"
                      >
                        <Eye className="w-4 h-4" />
                        <span>View Full Details</span>
                      </button>
                    </div>
                  </div>
                ) : (
                  <div className="space-y-4">
                    <div className="flex items-center space-x-2 text-gray-500 dark:text-gray-400">
                      <Clock className="w-5 h-5" />
                      <span>No reflection recorded for this date</span>
                    </div>
                    
                    <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-4 text-center">
                      <FileText className="w-8 h-8 text-gray-400 mx-auto mb-2" />
                      <div className="text-sm text-gray-600 dark:text-gray-400 mb-3">
                        Take a moment to reflect on your day and share your experiences.
                      </div>
                      <button
                        onClick={handleOpenCounselorLogModal}
                        className="bg-blue-500 hover:bg-blue-600 text-white font-medium py-2 px-4 rounded-lg transition-colors duration-200"
                      >
                        Create Reflection
                      </button>
                    </div>
                  </div>
                )}
              </div>

              {/* Table View Toggle and Recent Logs */}
              <div className="bg-white dark:bg-gray-800 shadow-sm rounded-xl p-6">
                <div className="flex items-center justify-between mb-4">
                  <h2 className="text-xl font-semibold text-gray-800 dark:text-white">
                    All Reflections
                  </h2>
                  <button
                    onClick={() => setShowTableView(!showTableView)}
                    className="flex items-center space-x-2 px-3 py-2 bg-gray-100 hover:bg-gray-200 dark:bg-gray-700 dark:hover:bg-gray-600 rounded-lg transition-colors"
                  >
                    <Table className="w-4 h-4" />
                    <span className="text-sm">{showTableView ? 'Show Cards' : 'Show Table'}</span>
                  </button>
                </div>
                
                {loading ? (
                  <div className="space-y-3">
                    {[1, 2, 3].map(i => (
                      <div key={i} className="animate-pulse">
                        <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-3/4 mb-2"></div>
                        <div className="h-3 bg-gray-200 dark:bg-gray-700 rounded w-1/2"></div>
                      </div>
                    ))}
                  </div>
                ) : error ? (
                  <div className="text-red-500 dark:text-red-400 text-sm">
                    {error}
                  </div>
                ) : counselorLogs.length === 0 ? (
                  <div className="text-gray-500 dark:text-gray-400 text-sm">
                    No reflections recorded yet.
                  </div>
                ) : showTableView ? (
                  // Table View
                  <div className="overflow-x-auto">
                    <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
                      <thead className="bg-gray-50 dark:bg-gray-700">
                        <tr>
                          <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                            Date
                          </th>
                          <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                            Day Off
                          </th>
                          <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                            Day Quality
                          </th>
                          <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                            Support Level
                          </th>
                          <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                            Support Needed
                          </th>
                          <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                            Elaboration
                          </th>
                          <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                            Values Reflection
                          </th>
                          <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                            Actions
                          </th>
                        </tr>
                      </thead>
                      <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
                        {counselorLogs.map(log => (
                          <tr 
                            key={log.id} 
                            className="hover:bg-gray-50 dark:hover:bg-gray-700 cursor-pointer"
                            onClick={() => handleViewLogClick(log)}
                          >
                            <td className="px-4 py-4 whitespace-nowrap text-sm font-medium text-gray-900 dark:text-white">
                              {formatHumanDate(log.date)}
                            </td>
                            <td className="px-4 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                              {log.day_off ? (
                                <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200">
                                  Yes
                                </span>
                              ) : (
                                <span className="text-gray-400">No</span>
                              )}
                            </td>
                            <td className="px-4 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                              {log.day_off ? (
                                <span className="text-gray-400">-</span>
                              ) : (
                                <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getScoreColor(log.day_quality_score)}`}>
                                  {log.day_quality_score}/5
                                </span>
                              )}
                            </td>
                            <td className="px-4 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                              {log.day_off ? (
                                <span className="text-gray-400">-</span>
                              ) : (
                                <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getScoreColor(log.support_level_score)}`}>
                                  {log.support_level_score}/5
                                </span>
                              )}
                            </td>
                            <td className="px-4 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                              {log.staff_care_support_needed ? (
                                <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200">
                                  Yes
                                </span>
                              ) : (
                                <span className="text-gray-400">No</span>
                              )}
                            </td>
                            <td className="px-4 py-4 text-sm text-gray-500 dark:text-gray-400 max-w-xs">
                              <div className="truncate" title={stripHtml(log.elaboration)}>
                                {truncateText(log.elaboration, 40)}
                              </div>
                            </td>
                            <td className="px-4 py-4 text-sm text-gray-500 dark:text-gray-400 max-w-xs">
                              <div className="truncate" title={stripHtml(log.values_reflection)}>
                                {truncateText(log.values_reflection, 40)}
                              </div>
                            </td>
                            <td className="px-4 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                              <button
                                onClick={(e) => {
                                  e.stopPropagation();
                                  handleViewLogClick(log);
                                }}
                                className="text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300"
                              >
                                <Eye className="w-4 h-4" />
                              </button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  // Card View
                  <div className="space-y-3">
                    {counselorLogs.map(log => (
                      <div
                        key={log.id}
                        className="border border-gray-200 dark:border-gray-700 rounded-lg p-3 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors cursor-pointer"
                        onClick={() => handleViewLogClick(log)}
                      >
                        <div className="flex justify-between items-start mb-1">
                          <div className="text-sm font-medium text-gray-900 dark:text-white">
                            {formatHumanDate(log.date)}
                          </div>
                          <div className="flex space-x-1">
                            {!log.day_off && (
                              <>
                                <span className={`text-xs px-2 py-1 rounded ${getScoreColor(log.day_quality_score)}`}>
                                  {log.day_quality_score}/5
                                </span>
                                <span className={`text-xs px-2 py-1 rounded ${getScoreColor(log.support_level_score)}`}>
                                  {log.support_level_score}/5
                                </span>
                              </>
                            )}
                          </div>
                        </div>
                        
                        {log.day_off && (
                          <div className="text-xs text-blue-600 dark:text-blue-400 mb-1">
                            Day off
                          </div>
                        )}
                        
                        {log.staff_care_support_needed && (
                          <div className="text-xs text-yellow-600 dark:text-yellow-400 mb-1">
                            Support requested
                          </div>
                        )}
                        
                        <div className="text-xs text-gray-500 dark:text-gray-400">
                          {new Date(log.created_at).toLocaleTimeString()}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
        </main>
      </div>

      {/* Counselor Log Modal */}
      {counselorLogModalOpen && (
          <CounselorLogFormModal 
            id="counselor-log-form"
            title={existingLogForDate ? "Edit Daily Reflection" : "Create Daily Reflection"}
            modalOpen={counselorLogModalOpen}
            setModalOpen={setCounselorLogModalOpen}
          >
            <CounselorLogForm 
              date={selected_date}
              existingLog={existingLogForDate}
              onClose={handleModalClose}
            />
          </CounselorLogFormModal>
        )}

      {/* View Log Modal */}
      {viewLogModalOpen && selectedLogForView && (
          <CounselorLogFormModal 
            id="view-counselor-log"
            title="View Daily Reflection"
            modalOpen={viewLogModalOpen}
            setModalOpen={setViewLogModalOpen}
          >
            <CounselorLogForm 
              date={selectedLogForView.date}
              existingLog={selectedLogForView}
              onClose={handleViewModalClose}
              viewOnly={true}
            />
          </CounselorLogFormModal>
        )}
    </div>
  );
}

export default CounselorDashboard;
