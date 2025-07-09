import React, { useState, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { Calendar, Users, FileText, Eye, ChevronLeft, ChevronRight, Download, Filter, X } from 'lucide-react';

import Header from '../partials/Header';
import Sidebar from '../partials/Sidebar';
import SingleDatePicker from '../components/ui/SingleDatePicker';
import AdminBunkLogItem from '../components/bunklogs/AdminBunkLogItem';
import { useAuth } from '../auth/AuthContext';
import api from '../api';

function AdminBunkLogs() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const { user, loading: authLoading, isAuthenticating } = useAuth();
  const { date } = useParams();
  const navigate = useNavigate();
  
  // State management
  const [bunkLogs, setBunkLogs] = useState([]);
  const [filteredLogs, setFilteredLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedDate, setSelectedDate] = useState(() => {
    // Initialize with today's date at noon local time
    const today = new Date();
    today.setHours(12, 0, 0, 0);
    return today;
  });
  const [selectedLog, setSelectedLog] = useState(null);
  const [viewingDetails, setViewingDetails] = useState(false);
  const [showFilters, setShowFilters] = useState(false);

  // Filter states
  const [filters, setFilters] = useState({
    bunk: '',
    unit: '',
    camperCareHelp: '',
    unitHeadHelp: '',
    notOnCamp: '',
    socialScore: '',
    participationScore: '',
    behavioralScore: ''
  });

  // Sorting state
  const [sortConfig, setSortConfig] = useState({ key: null, direction: 'asc' });

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
      
      navigate(`/admin-bunk-logs/${formattedDate}`, { replace: true });
      return;
    }
  }, [date, navigate]);

  // Fetch bunk logs for the selected date
  useEffect(() => {
    async function fetchBunkLogs() {
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
        console.log('📡 Fetching bunk logs for date:', date);
        setLoading(true);
        setError(null);
        
        const response = await api.get(`/api/v1/bunklogs/all/${date}/`);
        setBunkLogs(response.data.logs || []);
        console.log('✅ Bunk logs loaded:', response.data.logs?.length || 0, 'items');
        
      } catch (err) {
        console.error('❌ Error fetching bunk logs:', err);
        setError('Failed to load bunk logs');
        setBunkLogs([]);
      } finally {
        setLoading(false);
      }
    }
    
    fetchBunkLogs();
  }, [user?.id, date, authLoading, isAuthenticating]);

  // Apply filters when bunk logs or filters change
  useEffect(() => {
    let filtered = [...bunkLogs];

    if (filters.bunk) {
      filtered = filtered.filter(log => 
        log.bunk_name.toLowerCase().includes(filters.bunk.toLowerCase())
      );
    }

    if (filters.unit) {
      filtered = filtered.filter(log => 
        log.unit_name?.toLowerCase().includes(filters.unit.toLowerCase())
      );
    }

    if (filters.camperCareHelp !== '') {
      const needsHelp = filters.camperCareHelp === 'true';
      filtered = filtered.filter(log => log.camper_care_help_requested === needsHelp);
    }

    if (filters.unitHeadHelp !== '') {
      const needsHelp = filters.unitHeadHelp === 'true';
      filtered = filtered.filter(log => log.unit_head_help_requested === needsHelp);
    }

    if (filters.notOnCamp !== '') {
      const notOnCamp = filters.notOnCamp === 'true';
      filtered = filtered.filter(log => log.not_on_camp === notOnCamp);
    }

    if (filters.socialScore) {
      filtered = filtered.filter(log => log.social_score === parseInt(filters.socialScore));
    }

    if (filters.participationScore) {
      filtered = filtered.filter(log => log.participation_score === parseInt(filters.participationScore));
    }

    if (filters.behavioralScore) {
      filtered = filtered.filter(log => log.behavioral_score === parseInt(filters.behavioralScore));
    }

    setFilteredLogs(filtered);
  }, [bunkLogs, filters]);

  // Handle date change
  const handleDateChange = (newDate) => {
    const year = newDate.getFullYear();
    const month = String(newDate.getMonth() + 1).padStart(2, '0');
    const day = String(newDate.getDate()).padStart(2, '0');
    const formattedDate = `${year}-${month}-${day}`;
    
    navigate(`/admin-bunk-logs/${formattedDate}`);
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

  // Clear all filters
  const clearFilters = () => {
    setFilters({
      bunk: '',
      unit: '',
      camperCareHelp: '',
      unitHeadHelp: '',
      notOnCamp: '',
      socialScore: '',
      participationScore: '',
      behavioralScore: ''
    });
  };

  // Export to CSV
  const exportToCSV = () => {
    if (filteredLogs.length === 0) return;

    const headers = [
      'Date',
      'Camper Name',
      'Bunk',
      'Unit',
      'Social Score',
      'Participation Score', 
      'Behavioral Score',
      'Not On Camp',
      'Counselor',
      'Unit Head Help',
      'Camper Care Help',
      'Description',
      'Created At'
    ];

    const csvData = filteredLogs.map(log => [
      log.date,
      `${log.camper_first_name} ${log.camper_last_name}`,
      log.bunk_name,
      log.unit_name || '',
      log.social_score,
      log.participation_score,
      log.behavioral_score,
      log.not_on_camp ? 'Yes' : 'No',
      `${log.reporting_counselor_first_name || ''} ${log.reporting_counselor_last_name || ''}`.trim(),
      log.unit_head_help_requested ? 'Yes' : 'No',
      log.camper_care_help_requested ? 'Yes' : 'No',
      log.description?.replace(/<[^>]*>/g, '') || '', // Strip HTML
      log.created_at
    ]);

    const csvContent = [headers, ...csvData]
      .map(row => row.map(field => `"${field}"`).join(','))
      .join('\n');

    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `bunk-logs-${date}.csv`;
    a.click();
    window.URL.revokeObjectURL(url);
  };

  // Get score color - matches AdminBunkLogItem styling
  const getScoreColor = (score) => {
    if (!score) return "text-gray-600 bg-gray-100";
    
    const scoreNum = parseInt(score);
    if (scoreNum == 1) return 'text-white bg-[#e86946]';
    if (scoreNum == 2) return 'text-white bg-[#de8d6f]';
    if (scoreNum == 3) return 'text-black bg-[#e5e825]';
    if (scoreNum == 4) return 'text-white bg-[#90d258]';
    if (scoreNum == 5) return 'text-white bg-[#18d128]';
    return "text-white bg-red-100";
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
                  Loading Admin Bunk Logs...
                </h1>
                <p className="text-gray-600 dark:text-gray-400 mt-2">
                  Please wait while we load the bunk logs.
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
                        <p>You do not have permission to access the Admin Bunk Logs.</p>
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

  // Get unique values for filter dropdowns
  const uniqueBunks = [...new Set(bunkLogs.map(log => log.bunk_name))].sort();
  const uniqueUnits = [...new Set(bunkLogs.map(log => log.unit_name).filter(Boolean))].sort();

  // Sorting handler
  const handleSort = (key) => {
    setSortConfig((prev) => {
      if (prev.key === key) {
        // Toggle direction
        return { key, direction: prev.direction === 'asc' ? 'desc' : 'asc' };
      }
      return { key, direction: 'asc' };
    });
  };

  // Apply sorting to filteredLogs
  const sortedLogs = React.useMemo(() => {
    if (!sortConfig.key) return filteredLogs;
    const sorted = [...filteredLogs].sort((a, b) => {
      let aValue, bValue;
      if (sortConfig.key === 'bunk') {
        aValue = a.bunk_name?.toLowerCase() || '';
        bValue = b.bunk_name?.toLowerCase() || '';
      } else if (sortConfig.key === 'lastName') {
        aValue = a.camper_last_name?.toLowerCase() || '';
        bValue = b.camper_last_name?.toLowerCase() || '';
      } else if (['social_score', 'behavioral_score', 'participation_score'].includes(sortConfig.key)) {
        aValue = Number(a[sortConfig.key]) || 0;
        bValue = Number(b[sortConfig.key]) || 0;
      } else {
        aValue = '';
        bValue = '';
      }
      if (aValue < bValue) return sortConfig.direction === 'asc' ? -1 : 1;
      if (aValue > bValue) return sortConfig.direction === 'asc' ? 1 : -1;
      return 0;
    });
    return sorted;
  }, [filteredLogs, sortConfig]);

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
                  Admin Bunk Logs
                </h1>
                <p className="text-gray-600 dark:text-gray-400">
                  View and filter bunk logs across all campers
                </p>
              </div>

              {/* Actions */}
              <div className="grid grid-flow-col sm:auto-cols-max justify-start sm:justify-end gap-2">
                <button
                  onClick={() => setShowFilters(!showFilters)}
                  className="btn bg-white dark:bg-gray-800 border-gray-200 dark:border-gray-700/60 hover:border-gray-300 dark:hover:border-gray-600 text-gray-800 dark:text-gray-300"
                >
                  <Filter className="w-4 h-4 mr-2" />
                  Filters
                </button>
                <button
                  onClick={exportToCSV}
                  className="btn bg-white dark:bg-gray-800 border-gray-200 dark:border-gray-700/60 hover:border-gray-300 dark:hover:border-gray-600 text-gray-800 dark:text-gray-300"
                  disabled={filteredLogs.length === 0}
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

            {/* Filters Panel */}
            {showFilters && (
              <div className="bg-white dark:bg-gray-800 shadow-sm rounded-xl p-6 mb-8">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-lg font-medium text-gray-900 dark:text-white">Filters</h3>
                  <div className="flex space-x-2">
                    <button
                      onClick={clearFilters}
                      className="text-sm text-gray-600 hover:text-gray-800 dark:text-gray-400 dark:hover:text-gray-200"
                    >
                      Clear All
                    </button>
                    <button
                      onClick={() => setShowFilters(false)}
                      className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
                    >
                      <X className="w-4 h-4" />
                    </button>
                  </div>
                </div>
                
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                  {/* Bunk Filter */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                      Bunk
                    </label>
                    <select
                      value={filters.bunk}
                      onChange={(e) => setFilters(prev => ({ ...prev, bunk: e.target.value }))}
                      className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                    >
                      <option value="">All Bunks</option>
                      {uniqueBunks.map(bunk => (
                        <option key={bunk} value={bunk}>{bunk}</option>
                      ))}
                    </select>
                  </div>

                  {/* Unit Filter */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                      Unit
                    </label>
                    <select
                      value={filters.unit}
                      onChange={(e) => setFilters(prev => ({ ...prev, unit: e.target.value }))}
                      className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                    >
                      <option value="">All Units</option>
                      {uniqueUnits.map(unit => (
                        <option key={unit} value={unit}>{unit}</option>
                      ))}
                    </select>
                  </div>

                  {/* Camper Care Help Filter */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                      Camper Care Help
                    </label>
                    <select
                      value={filters.camperCareHelp}
                      onChange={(e) => setFilters(prev => ({ ...prev, camperCareHelp: e.target.value }))}
                      className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                    >
                      <option value="">All</option>
                      <option value="true">Help Requested</option>
                      <option value="false">No Help Requested</option>
                    </select>
                  </div>

                  {/* Unit Head Help Filter */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                      Unit Head Help
                    </label>
                    <select
                      value={filters.unitHeadHelp}
                      onChange={(e) => setFilters(prev => ({ ...prev, unitHeadHelp: e.target.value }))}
                      className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                    >
                      <option value="">All</option>
                      <option value="true">Help Requested</option>
                      <option value="false">No Help Requested</option>
                    </select>
                  </div>

                  {/* Not On Camp Filter */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                      Not On Camp
                    </label>
                    <select
                      value={filters.notOnCamp}
                      onChange={(e) => setFilters(prev => ({ ...prev, notOnCamp: e.target.value }))}
                      className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                    >
                      <option value="">All</option>
                      <option value="true">Not On Camp</option>
                      <option value="false">On Camp</option>
                    </select>
                  </div>

                  {/* Social Score Filter */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                      Social Score
                    </label>
                    <select
                      value={filters.socialScore}
                      onChange={(e) => setFilters(prev => ({ ...prev, socialScore: e.target.value }))}
                      className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                    >
                      <option value="">All Scores</option>
                      {[1, 2, 3, 4, 5].map(score => (
                        <option key={score} value={score}>{score}</option>
                      ))}
                    </select>
                  </div>

                  {/* Participation Score Filter */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                      Participation Score
                    </label>
                    <select
                      value={filters.participationScore}
                      onChange={(e) => setFilters(prev => ({ ...prev, participationScore: e.target.value }))}
                      className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                    >
                      <option value="">All Scores</option>
                      {[1, 2, 3, 4, 5].map(score => (
                        <option key={score} value={score}>{score}</option>
                      ))}
                    </select>
                  </div>

                  {/* Behavioral Score Filter */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                      Behavioral Score
                    </label>
                    <select
                      value={filters.behavioralScore}
                      onChange={(e) => setFilters(prev => ({ ...prev, behavioralScore: e.target.value }))}
                      className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                    >
                      <option value="">All Scores</option>
                      {[1, 2, 3, 4, 5].map(score => (
                        <option key={score} value={score}>{score}</option>
                      ))}
                    </select>
                  </div>
                </div>
              </div>
            )}

            {/* Stats Cards */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
              <div className="bg-white dark:bg-gray-800 shadow-sm rounded-xl p-6">
                <div className="flex items-center">
                  <div className="flex-shrink-0">
                    <Users className="w-8 h-8 text-blue-500" />
                  </div>
                  <div className="ml-4">
                    <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Total Logs</p>
                    <p className="text-2xl font-semibold text-gray-900 dark:text-white">
                      {filteredLogs.length}
                    </p>
                  </div>
                </div>
              </div>
              
              <div className="bg-white dark:bg-gray-800 shadow-sm rounded-xl p-6 cursor-pointer border-2 transition-all duration-150 "
                onClick={() => setFilters(prev => ({ ...prev, camperCareHelp: prev.camperCareHelp === 'true' ? '' : 'true' }))}
                style={{ borderColor: filters.camperCareHelp === 'true' ? '#ef4444' : 'transparent' }}
                title="Show only logs with Camper Care Help requested"
              >
                <div className="flex items-center">
                  <div className="flex-shrink-0">
                    <FileText className="w-8 h-8 text-red-500" />
                  </div>
                  <div className="ml-4">
                    <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Camper Care Help</p>
                    <p className="text-2xl font-semibold text-gray-900 dark:text-white">
                      {filteredLogs.filter(log => log.camper_care_help_requested).length}
                    </p>
                  </div>
                </div>
              </div>
              
              <div className="bg-white dark:bg-gray-800 shadow-sm rounded-xl p-6 cursor-pointer border-2 transition-all duration-150 "
                onClick={() => setFilters(prev => ({ ...prev, unitHeadHelp: prev.unitHeadHelp === 'true' ? '' : 'true' }))}
                style={{ borderColor: filters.unitHeadHelp === 'true' ? '#facc15' : 'transparent' }}
                title="Show only logs with Unit Head Help requested"
              >
                <div className="flex items-center">
                  <div className="flex-shrink-0">
                    <FileText className="w-8 h-8 text-yellow-500" />
                  </div>
                  <div className="ml-4">
                    <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Unit Head Help</p>
                    <p className="text-2xl font-semibold text-gray-900 dark:text-white">
                      {filteredLogs.filter(log => log.unit_head_help_requested).length}
                    </p>
                  </div>
                </div>
              </div>

              <div className="bg-white dark:bg-gray-800 shadow-sm rounded-xl p-6">
                <div className="flex items-center">
                  <div className="flex-shrink-0">
                    <Users className="w-8 h-8 text-gray-500" />
                  </div>
                  <div className="ml-4">
                    <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Not On Camp</p>
                    <p className="text-2xl font-semibold text-gray-900 dark:text-white">
                      {filteredLogs.filter(log => log.not_on_camp).length}
                    </p>
                  </div>
                </div>
              </div>
            </div>

            {/* Bunk Logs Table */}
            <div className="bg-white dark:bg-gray-800 shadow-sm rounded-xl">
              <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
                <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
                  Bunk Logs for {date && formatDisplayDate(date)} ({filteredLogs.length} records)
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
                ) : filteredLogs.length === 0 ? (
                  <div className="flex items-center justify-center py-12">
                    <div className="text-center">
                      <FileText className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                      <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
                        No logs found
                      </h3>
                      <p className="text-gray-600 dark:text-gray-400">
                        {bunkLogs.length === 0 
                          ? "No bunk logs were submitted for this date."
                          : "No logs match your current filters."
                        }
                      </p>
                    </div>
                  </div>
                ) : (
                  <div className="overflow-x-auto">
                    <div className="rounded-lg border border-gray-200 dark:border-gray-700/60">
                      <div className="overflow-x-auto w-full">
                        <table className="table-auto w-full dark:text-gray-300">
                          {/* Table header */}
                          <thead className="text-xs uppercase text-gray-400 dark:text-gray-500 bg-gray-50 dark:bg-gray-700/50 rounded-xs">
                            <tr>
                              <th className="w-2/12 p-2 border-b border-gray-200 dark:border-gray-700 cursor-pointer select-none" onClick={() => handleSort('lastName')}>
                                <div className="font-semibold text-left flex items-center gap-1">
                                  Camper Name
                                  {sortConfig.key === 'lastName' && (
                                    <span>{sortConfig.direction === 'asc' ? '▲' : '▼'}</span>
                                  )}
                                </div>
                              </th>
                              <th className="w-1/12 p-2 border-b border-gray-200 dark:border-gray-700 cursor-pointer select-none" onClick={() => handleSort('bunk')}>
                                <div className="font-semibold text-center flex items-center gap-1 justify-center">
                                  Bunk/Unit
                                  {sortConfig.key === 'bunk' && (
                                    <span>{sortConfig.direction === 'asc' ? '▲' : '▼'}</span>
                                  )}
                                </div>
                              </th>
                              <th className="w-1/12 p-2 border-b border-gray-200 dark:border-gray-700">
                                <div className="font-semibold text-center">Date</div>
                              </th>
                              <th className="w-1/12 p-2 border-b border-gray-200 dark:border-gray-700 cursor-pointer select-none" onClick={() => handleSort('social_score')}>
                                <div className="font-semibold text-center flex items-center gap-1 justify-center">
                                  Social
                                  {sortConfig.key === 'social_score' && (
                                    <span>{sortConfig.direction === 'asc' ? '▲' : '▼'}</span>
                                  )}
                                </div>
                              </th>
                              <th className="w-1/12 p-2 border-b border-gray-200 dark:border-gray-700 cursor-pointer select-none" onClick={() => handleSort('behavioral_score')}>
                                <div className="font-semibold text-center flex items-center gap-1 justify-center">
                                  Behavior
                                  {sortConfig.key === 'behavioral_score' && (
                                    <span>{sortConfig.direction === 'asc' ? '▲' : '▼'}</span>
                                  )}
                                </div>
                              </th>
                              <th className="w-1/12 p-2 border-b border-gray-200 dark:border-gray-700 cursor-pointer select-none" onClick={() => handleSort('participation_score')}>
                                <div className="font-semibold text-center flex items-center gap-1 justify-center">
                                  Participation
                                  {sortConfig.key === 'participation_score' && (
                                    <span>{sortConfig.direction === 'asc' ? '▲' : '▼'}</span>
                                  )}
                                </div>
                              </th>
                              <th className="w-3/12 p-2 border-b border-gray-200 dark:border-gray-700">
                                <div className="font-semibold text-center">Description</div>
                              </th>
                            </tr>
                          </thead>
                          {sortedLogs.map((log) => (
                            <AdminBunkLogItem
                              key={log.id}
                              log={log}
                              date={date}
                              onViewDetails={viewLogDetails}
                            />
                          ))}
                        </table>
                      </div>
                    </div>
                  </div>
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
                        Bunk Log Details
                      </h3>
                      <button
                        onClick={() => setViewingDetails(false)}
                        className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
                      >
                        ✕
                      </button>
                    </div>
                    
                    <div className="space-y-6">
                      {/* Camper Info */}
                      <div>
                        <h4 className="text-sm font-medium text-gray-900 dark:text-white mb-2">Camper</h4>
                        <p className="text-sm text-gray-600 dark:text-gray-400">
                          {selectedLog.camper_first_name} {selectedLog.camper_last_name} (ID: {selectedLog.camper_id})
                        </p>
                      </div>

                      {/* Bunk Info */}
                      <div>
                        <h4 className="text-sm font-medium text-gray-900 dark:text-white mb-2">Bunk & Unit</h4>
                        <p className="text-sm text-gray-600 dark:text-gray-400">
                          {selectedLog.bunk_name} {selectedLog.unit_name && `- ${selectedLog.unit_name}`}
                        </p>
                      </div>
                      
                      {/* Scores */}
                      <div className="grid grid-cols-3 gap-4">
                        <div>
                          <h4 className="text-sm font-medium text-gray-900 dark:text-white mb-2">Social Score</h4>
                          <span className={`inline-flex px-3 py-1 text-sm font-semibold rounded-full ${getScoreColor(selectedLog.social_score)}`}>
                            {selectedLog.social_score}/5
                          </span>
                        </div>
                        <div>
                          <h4 className="text-sm font-medium text-gray-900 dark:text-white mb-2">Participation Score</h4>
                          <span className={`inline-flex px-3 py-1 text-sm font-semibold rounded-full ${getScoreColor(selectedLog.participation_score)}`}>
                            {selectedLog.participation_score}/5
                          </span>
                        </div>
                        <div>
                          <h4 className="text-sm font-medium text-gray-900 dark:text-white mb-2">Behavioral Score</h4>
                          <span className={`inline-flex px-3 py-1 text-sm font-semibold rounded-full ${getScoreColor(selectedLog.behavioral_score)}`}>
                            {selectedLog.behavioral_score}/5
                          </span>
                        </div>
                      </div>
                      
                      {/* Status Flags */}
                      <div className="grid grid-cols-3 gap-4">
                        <div>
                          <h4 className="text-sm font-medium text-gray-900 dark:text-white mb-2">Not On Camp</h4>
                          <span className={`inline-flex px-3 py-1 text-sm font-semibold rounded-full ${
                            selectedLog.not_on_camp ? 'text-gray-600 bg-gray-50' : 'text-green-600 bg-green-50'
                          }`}>
                            {selectedLog.not_on_camp ? 'Yes' : 'No'}
                          </span>
                        </div>
                        <div>
                          <h4 className="text-sm font-medium text-gray-900 dark:text-white mb-2">Camper Care Help</h4>
                          <span className={`inline-flex px-3 py-1 text-sm font-semibold rounded-full ${
                            selectedLog.camper_care_help_requested ? 'text-red-600 bg-red-50' : 'text-green-600 bg-green-50'
                          }`}>
                            {selectedLog.camper_care_help_requested ? 'Yes' : 'No'}
                          </span>
                        </div>
                        <div>
                          <h4 className="text-sm font-medium text-gray-900 dark:text-white mb-2">Unit Head Help</h4>
                          <span className={`inline-flex px-3 py-1 text-sm font-semibold rounded-full ${
                            selectedLog.unit_head_help_requested ? 'text-yellow-600 bg-yellow-50' : 'text-green-600 bg-green-50'
                          }`}>
                            {selectedLog.unit_head_help_requested ? 'Yes' : 'No'}
                          </span>
                        </div>
                      </div>
                      
                      {/* Description */}
                      {selectedLog.description && (
                        <div>
                          <h4 className="text-sm font-medium text-gray-900 dark:text-white mb-2">Description</h4>
                          <div 
                            className="text-sm text-gray-600 dark:text-gray-400 bg-gray-50 dark:bg-gray-700 p-3 rounded-lg"
                            dangerouslySetInnerHTML={{ __html: selectedLog.description }}
                          />
                        </div>
                      )}

                      {/* Counselor Info */}
                      {selectedLog.reporting_counselor_first_name && (
                        <div>
                          <h4 className="text-sm font-medium text-gray-900 dark:text-white mb-2">Reporting Counselor</h4>
                          <p className="text-sm text-gray-600 dark:text-gray-400">
                            {selectedLog.reporting_counselor_first_name} {selectedLog.reporting_counselor_last_name}
                            {selectedLog.reporting_counselor_email && ` (${selectedLog.reporting_counselor_email})`}
                          </p>
                        </div>
                      )}
                      
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

export default AdminBunkLogs;
