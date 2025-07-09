import React, { useState, useEffect } from 'react';
import { useAuth } from '../../auth/AuthContext';
import api from '../../api';
import UnitHeadBunkCard from '../../components/bunklogs/UnitHeadBunkCard';
import CounselorLogsGrid from '../admin-dashboard/CounselorLogsGrid';
import { Loader2, AlertTriangle, Users, Home, UserCheck, Heart, UserX, Clock, AlertCircle, Baby } from 'lucide-react';
import GenericAvatar from '../../images/avatar-generic.png';

function UnitHeadBunkGrid({ selectedDate }) {
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);
  const [counselorLogsLoading, setCounselorLogsLoading] = useState(false);
  const [counselorLogsError, setCounselorLogsError] = useState(null);
  const [unitData, setUnitData] = useState(null);
  const [allCampers, setAllCampers] = useState([]);
  const [counselorLogs, setCounselorLogs] = useState([]);
  const [campersNeedingAttention, setCampersNeedingAttention] = useState([]);
  const [activeTab, setActiveTab] = useState('overview');
  const [selectedLog, setSelectedLog] = useState(null);
  const [viewingDetails, setViewingDetails] = useState(false);
  const { user, isAuthenticated } = useAuth();

  // Helper function to format date consistently
  const formatDateString = (date) => {
    if (!date) {
      return new Date().toISOString().split('T')[0];
    }
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
  };

  useEffect(() => {
    const fetchUnitData = async () => {
      if (!user?.id || user?.role !== 'Unit Head') {
        setError('Access denied. Only Unit Heads can view this page.');
        setLoading(false);
        return;
      }

      try {
        setLoading(true);
        
        // Use selectedDate if provided, otherwise use today's date
        const dateToUse = formatDateString(selectedDate);
        
        const response = await api.get(`/api/v1/unithead/${user.id}/${dateToUse}/`);
        
        // The API returns an array of units, we need the first unit
        let data = null;
        if (Array.isArray(response.data) && response.data.length > 0) {
          data = response.data[0];
          
          // Collect all campers from all bunks for attention tracking
          const allCampersArray = [];
          const campersNeedingAttentionArray = [];
          
          if (data.bunks && data.bunks.length > 0) {
            data.bunks.forEach(bunk => {
              if (bunk.campers && bunk.campers.length > 0) {
                bunk.campers.forEach(camper => {
                  // Add bunk and unit context to camper data
                  const camperWithContext = {
                    ...camper,
                    bunk_name: bunk.cabin_name,
                    session_name: bunk.session_name,
                    unit_name: data.name,
                    bunk_id: bunk.id
                  };
                  
                  allCampersArray.push(camperWithContext);
                  
                  // Check if camper needs attention
                  if (camper.bunk_log) {
                    const needsAttention = 
                      camper.bunk_log.request_camper_care_help ||
                      camper.bunk_log.request_unit_head_help ||
                      camper.bunk_log.not_on_camp;
                    
                    if (needsAttention) {
                      campersNeedingAttentionArray.push(camperWithContext);
                    }
                  }
                });
              }
            });
          }
          
          setAllCampers(allCampersArray);
          setCampersNeedingAttention(campersNeedingAttentionArray);
        } else if (!Array.isArray(response.data)) {
          data = response.data;
        }
        
        setUnitData(data);
        setError(null);
      } catch (err) {
        setError(err.response?.data?.error || 'Failed to fetch unit data');
        console.error('Error fetching unit data:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchUnitData();
  }, [user?.id, user?.role, selectedDate]);

  // Fetch counselor logs for the selected date
  useEffect(() => {
    async function fetchCounselorLogs() {
      if (!user?.id) {
        console.log('⏳ Skipping counselor logs fetch - no user ID');
        return;
      }
      
      try {
        setCounselorLogsLoading(true);
        setCounselorLogsError(null);
        const dateToUse = formatDateString(selectedDate);
        console.log('📡 [UnitHead] Fetching counselor logs for date:', dateToUse);
        console.log('📡 [UnitHead] User info:', { id: user?.id, role: user?.role, email: user?.email });
        
        // Use the same endpoint as AdminDashboard with timezone support
        const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
        console.log('🌍 [UnitHead] User timezone:', timezone);
        
        const response = await api.get(`/api/v1/counselorlogs/${dateToUse}/`, {
          params: { timezone }
        });
        
        console.log('🔍 Counselor logs response:', response.data);
        console.log('🔍 Response status:', response.status);
        
        // Use the same response parsing as AdminDashboard
        const logs = response.data.results || [];
        
        setCounselorLogs(logs);
        console.log('✅ Counselor logs loaded:', logs.length, 'items');
        
      } catch (err) {
        console.error('❌ Error fetching counselor logs:', {
          message: err.message,
          response: err.response,
          status: err.response?.status,
          data: err.response?.data
        });
        
        // Provide more specific error messages
        let errorMessage = 'Failed to load counselor logs';
        if (err.response?.status === 404) {
          errorMessage = 'Counselor logs endpoint not found. Please check if the server is running.';
        } else if (err.response?.status === 403) {
          errorMessage = 'Access denied. You may not have permission to view counselor logs.';
        } else if (err.response) {
          errorMessage = `Server error (${err.response.status}): ${err.response.data?.detail || err.response.statusText}`;
        } else if (err.request) {
          errorMessage = 'Network error: Unable to reach the server. Please check your connection and ensure the server is running.';
        } else {
          errorMessage = `Request error: ${err.message}`;
        }
        
        setCounselorLogsError(errorMessage);
        setCounselorLogs([]);
      } finally {
        setCounselorLogsLoading(false);
      }
    }
    
    fetchCounselorLogs();
  }, [user?.id, selectedDate]);

  // Helper functions
  const getCampersWithLogs = () => {
    return allCampers.filter(camper => camper.bunk_log);
  };

  const getCampersNotOnCamp = () => {
    return allCampers.filter(camper => camper.bunk_log?.not_on_camp);
  };

  const getCampersRequestingCamperCare = () => {
    return allCampers.filter(camper => camper.bunk_log?.request_camper_care_help);
  };

  const getCampersRequestingUnitHeadHelp = () => {
    return allCampers.filter(camper => camper.bunk_log?.request_unit_head_help);
  };

  // Handler for viewing counselor log details
  const viewLogDetails = (log) => {
    console.log('Viewing counselor log details:', log);
    setSelectedLog(log);
    setViewingDetails(true);
  };

  // Loading state
  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-64">
        <div className="text-center">
          <Loader2 className="w-8 h-8 animate-spin text-emerald-600 mx-auto mb-4" />
          <p className="text-sm text-gray-500 dark:text-gray-400">Loading your unit data...</p>
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="flex items-center justify-center min-h-64">
        <div className="text-center max-w-md mx-auto">
          <div className="w-16 h-16 bg-red-100 dark:bg-red-900/30 rounded-full flex items-center justify-center mx-auto mb-4">
            <AlertTriangle className="w-8 h-8 text-red-600 dark:text-red-400" />
          </div>
          <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-2">
            Unable to load unit data
          </h3>
          <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
            {error}
          </p>
          <button
            onClick={() => window.location.reload()}
            className="px-4 py-2 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 transition-colors text-sm font-medium"
          >
            Try Again
          </button>
        </div>
      </div>
    );
  }

  // No data state
  if (!unitData || !unitData.bunks || !Array.isArray(unitData.bunks) || unitData.bunks.length === 0) {
    return (
      <div className="flex items-center justify-center min-h-64">
        <div className="text-center max-w-md mx-auto">
          <div className="w-16 h-16 bg-gray-100 dark:bg-gray-800 rounded-full flex items-center justify-center mx-auto mb-4">
            <Home className="w-8 h-8 text-gray-400" />
          </div>
          <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-2">
            No bunks found
          </h3>
          <p className="text-sm text-gray-600 dark:text-gray-400">
            {!unitData ? 'No unit data available.' : 'There are no bunks assigned to your unit yet.'}
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Unit header */}
        <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-sm border border-gray-100 dark:border-gray-700 p-6">
          <div className="flex items-center space-x-4">
            <div className="w-12 h-12 bg-emerald-100 dark:bg-emerald-900/30 rounded-xl flex items-center justify-center">
          <Users className="w-6 h-6 text-emerald-600 dark:text-emerald-400" />
            </div>
            <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
            {unitData.name}
          </h1>
          <p className="text-gray-600 dark:text-gray-400">
            {unitData.bunks.length} bunk{unitData.bunks.length !== 1 ? 's' : ''} in your unit
          </p>
            </div>
          </div>
        </div>

        {/* Navigation tabs */}
        <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-sm border border-gray-100 dark:border-gray-700">
          <div className="border-b border-gray-200 dark:border-gray-700">
            <button
          onClick={() => setActiveTab('overview')}
          className={`px-6 py-4 text-sm font-medium border-b-2 ${
            activeTab === 'overview'
              ? 'border-emerald-500 text-emerald-600 dark:text-emerald-400'
              : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'
          }`}
            >
          Unit Overview
            </button>
            <button
          onClick={() => setActiveTab('attention')}
          className={`px-6 py-4 text-sm font-medium border-b-2 ${
            activeTab === 'attention'
              ? 'border-emerald-500 text-emerald-600 dark:text-emerald-400'
              : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'
          }`}
            >
          Needs Attention ({campersNeedingAttention.length})
            </button>
            <button
          onClick={() => setActiveTab('counselorLogs')}
          className={`px-6 py-4 text-sm font-medium border-b-2 ${
            activeTab === 'counselorLogs'
              ? 'border-emerald-500 text-emerald-600 dark:text-emerald-400'
              : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'
          }`}
            >
          Counselor Logs
            </button>
          </div>

          {/* Stats overview */}
        <div className="grid grid-cols-1 sm:grid-cols-4 gap-4 p-6">
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-100 dark:border-gray-700 p-4">
            <div className="flex items-center space-x-3">
              <div className="w-10 h-10 bg-emerald-100 dark:bg-emerald-900/30 rounded-lg flex items-center justify-center">
                <Home className="w-5 h-5 text-emerald-600 dark:text-emerald-400" />
              </div>
              <div>
                <p className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                  {unitData.bunks.length}
                </p>
                <p className="text-sm text-gray-600 dark:text-gray-400">Total Bunks</p>
              </div>
            </div>
          </div>

          <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-100 dark:border-gray-700 p-4">
            <div className="flex items-center space-x-3">
              <div className="w-10 h-10 bg-blue-100 dark:bg-blue-900/30 rounded-lg flex items-center justify-center">
                <Users className="w-5 h-5 text-blue-600 dark:text-blue-400" />
              </div>
              <div>
                <p className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                  {unitData.bunks.reduce((total, bunk) => total + (bunk.counselors?.length || 0), 0)}
                </p>
                <p className="text-sm text-gray-600 dark:text-gray-400">Total Staff</p>
              </div>
            </div>
          </div>

          <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-100 dark:border-gray-700 p-4">
            <div className="flex items-center space-x-3">
              <div className="w-10 h-10 bg-purple-100 dark:bg-purple-900/30 rounded-lg flex items-center justify-center">
                <Baby className="w-5 h-5 text-purple-600 dark:text-purple-400" />
              </div>
              <div>
                <p className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                  {unitData.bunks.reduce((total, bunk) => total + (bunk.campers?.length || 0), 0)}
                </p>
                <p className="text-sm text-gray-600 dark:text-gray-400">Total Campers</p>
              </div>
            </div>
          </div>

          <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-100 dark:border-gray-700 p-4">
            <div className="flex items-center space-x-3">
              <div className="w-10 h-10 bg-orange-100 dark:bg-orange-900/30 rounded-lg flex items-center justify-center">
                <AlertCircle className="w-5 h-5 text-orange-600 dark:text-orange-400" />
              </div>
              <div>
                <p className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                  {campersNeedingAttention.length}
                </p>
                <p className="text-sm text-gray-600 dark:text-gray-400">Need Attention</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Tab content */}
      {activeTab === 'overview' && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {unitData.bunks.map((bunk) => (
            <UnitHeadBunkCard
              key={bunk.id}
              bunk={bunk}
              selectedDate={selectedDate}
            />
          ))}
        </div>
      )}

      {activeTab === 'counselorLogs' && (
        <CounselorLogsGrid
          date={formatDateString(selectedDate)}
          loading={counselorLogsLoading}
          error={counselorLogsError}
          counselorLogs={counselorLogs}
          viewLogDetails={viewLogDetails}
        />
      )}

      {activeTab === 'attention' && (
        <div className="space-y-6">
          {/* Campers not on camp */}
          {getCampersNotOnCamp().length > 0 && (
            <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-sm border border-red-200 dark:border-red-800">
              <div className="p-6">
                <div className="flex items-center space-x-3 mb-4">
                  <div className="w-10 h-10 bg-red-100 dark:bg-red-900/30 rounded-lg flex items-center justify-center">
                    <UserX className="w-5 h-5 text-red-600 dark:text-red-400" />
                  </div>
                  <div>
                    <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                      Not On Camp ({getCampersNotOnCamp().length})
                    </h3>
                    <p className="text-sm text-gray-600 dark:text-gray-400">
                      Campers who are currently not on camp
                    </p>
                  </div>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {getCampersNotOnCamp().map((camper, index) => {
                    // Build the URL to the camper's page for this date
                    const dateStr = formatDateString(selectedDate);
                    const camperUrl = `/camper/${camper.id}/${dateStr}`;
                    return (
                      <a
                        key={`not-on-camp-${camper.id}-${index}`}
                        href={camperUrl}
                        className="block bg-red-50 dark:bg-red-900/20 rounded-lg p-4 border border-red-200 dark:border-red-800 hover:shadow-lg transition-shadow cursor-pointer"
                        tabIndex={0}
                      >
                        <div className="flex items-center space-x-3">
                          <img 
                            src={GenericAvatar} 
                            alt="Avatar" 
                            className="w-10 h-10 rounded-full"
                          />
                          <div className="flex-1">
                            <p className="font-medium text-gray-900 dark:text-gray-100">
                              {camper.first_name} {camper.last_name}
                            </p>
                            <p className="text-sm text-gray-600 dark:text-gray-400">
                              {camper.bunk_name} • {camper.unit_name}
                            </p>
                            {camper.bunk_log.description && (
                              <p className="text-xs text-gray-500 dark:text-gray-400 mt-1 line-clamp-2">
                                <span
                                  dangerouslySetInnerHTML={{ __html: camper.bunk_log.description }}
                                />
                              </p>
                            )}
                          </div>
                        </div>
                      </a>
                    );
                  })}
                </div>
              </div>
            </div>
          )}

          {/* Unit Head Help Requested */}
          {getCampersRequestingUnitHeadHelp().length > 0 && (
            <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-sm border border-yellow-200 dark:border-yellow-800">
              <div className="p-6">
                <div className="flex items-center space-x-3 mb-4">
                  <div className="w-10 h-10 bg-yellow-100 dark:bg-yellow-900/30 rounded-lg flex items-center justify-center">
                    <UserCheck className="w-5 h-5 text-yellow-600 dark:text-yellow-400" />
                  </div>
                  <div>
                    <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                      Unit Head Help Requested ({getCampersRequestingUnitHeadHelp().length})
                    </h3>
                    <p className="text-sm text-gray-600 dark:text-gray-400">
                      Campers who need unit head attention
                    </p>
                  </div>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {getCampersRequestingUnitHeadHelp().map((camper, index) => {
                    // Build the URL to the camper's page for this date
                    const dateStr = formatDateString(selectedDate);
                    const camperUrl = `/camper/${camper.id}/${dateStr}`;
                    return (
                      <a
                        key={`unit-help-${camper.id}-${index}`}
                        href={camperUrl}
                        className="block bg-yellow-50 dark:bg-yellow-900/20 rounded-lg p-4 border border-yellow-200 dark:border-yellow-800 hover:shadow-lg transition-shadow cursor-pointer"
                        tabIndex={0}
                      >
                        <div className="flex items-center space-x-3">
                          <img 
                            src={GenericAvatar} 
                            alt="Avatar" 
                            className="w-10 h-10 rounded-full"
                          />
                          <div className="flex-1">
                            <p className="font-medium text-gray-900 dark:text-gray-100">
                              {camper.first_name} {camper.last_name}
                            </p>
                            <p className="text-sm text-gray-600 dark:text-gray-400">
                              {camper.bunk_name} • {camper.unit_name}
                            </p>
                            {camper.bunk_log.description && (
                              <p className="text-xs text-gray-500 dark:text-gray-400 mt-1 line-clamp-2">
                                <span
                                  dangerouslySetInnerHTML={{ __html: camper.bunk_log.description }}
                                />
                              </p>
                            )}
                          </div>
                        </div>
                      </a>
                    );
                  })}
                </div>
              </div>
            </div>
          )}

          {/* Campers requesting camper care help */}
          {getCampersRequestingCamperCare().length > 0 && (
            <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-sm border border-orange-200 dark:border-orange-800">
              <div className="p-6">
                <div className="flex items-center space-x-3 mb-4">
                  <div className="w-10 h-10 bg-orange-100 dark:bg-orange-900/30 rounded-lg flex items-center justify-center">
                    <Heart className="w-5 h-5 text-orange-600 dark:text-orange-400" />
                  </div>
                  <div>
                    <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                      Camper Care Help Requested ({getCampersRequestingCamperCare().length})
                    </h3>
                    <p className="text-sm text-gray-600 dark:text-gray-400">
                      Campers who need camper care attention
                    </p>
                  </div>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {getCampersRequestingCamperCare().map((camper, index) => {
                    // Build the URL to the camper's page for this date
                    const dateStr = formatDateString(selectedDate);
                    const camperUrl = `/camper/${camper.id}/${dateStr}`;
                    return (
                      <a
                        key={`care-help-${camper.id}-${index}`}
                        href={camperUrl}
                        className="block bg-orange-50 dark:bg-orange-900/20 rounded-lg p-4 border border-orange-200 dark:border-orange-800 hover:shadow-lg transition-shadow cursor-pointer"
                        tabIndex={0}
                      >
                        <div className="flex items-center space-x-3">
                          <img 
                            src={GenericAvatar} 
                            alt="Avatar" 
                            className="w-10 h-10 rounded-full"
                          />
                          <div className="flex-1">
                            <p className="font-medium text-gray-900 dark:text-gray-100">
                              {camper.first_name} {camper.last_name}
                            </p>
                            <p className="text-sm text-gray-600 dark:text-gray-400">
                              {camper.bunk_name} • {camper.unit_name}
                            </p>
                            {camper.bunk_log.description && (
                              <p className="text-xs text-gray-500 dark:text-gray-400 mt-1 line-clamp-2">
                                <span
                                  dangerouslySetInnerHTML={{ __html: camper.bunk_log.description }}
                                />
                              </p>
                            )}
                          </div>
                        </div>
                      </a>
                    );
                  })}
                </div>
              </div>
            </div>
          )}

          {/* Show message if no campers need attention */}
          {campersNeedingAttention.length === 0 && (
            <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-sm border border-gray-100 dark:border-gray-700">
              <div className="p-8 text-center">
                <div className="w-16 h-16 bg-green-100 dark:bg-green-900/30 rounded-full flex items-center justify-center mx-auto mb-4">
                  <UserCheck className="w-8 h-8 text-green-600 dark:text-green-400" />
                </div>
                <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-2">
                  All Good!
                </h3>
                <p className="text-gray-600 dark:text-gray-400">
                  No campers currently need special attention.
                </p>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Counselor Log Detail Modal */}
      {viewingDetails && selectedLog && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
          <div className="bg-white dark:bg-gray-800 rounded-xl max-w-3xl w-full max-h-[90vh] overflow-y-auto">
            <div className="p-6">
              {/* Modal Header */}
              <div className="flex items-center justify-between mb-6">
                <h3 className="text-xl font-semibold text-gray-900 dark:text-white">
                  Counselor Log Details
                </h3>
                <button
                  onClick={() => setViewingDetails(false)}
                  className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 text-2xl font-bold w-8 h-8 flex items-center justify-center"
                >
                  ×
                </button>
              </div>
              
              <div className="space-y-6">
                {/* Counselor Info */}
                <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-4">
                  <h4 className="text-lg font-medium text-gray-900 dark:text-white mb-3">Counselor Information</h4>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Name</p>
                      <p className="text-lg text-gray-900 dark:text-white">
                        {selectedLog.counselor_first_name || 'Unknown'} {selectedLog.counselor_last_name || 'User'}
                      </p>
                    </div>
                    <div>
                      <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Email</p>
                      <p className="text-lg text-gray-900 dark:text-white">
                        {selectedLog.counselor_email || 'Not provided'}
                      </p>
                    </div>
                    <div>
                      <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Date</p>
                      <p className="text-lg text-gray-900 dark:text-white">
                        {selectedLog.date
                          ? (() => {
                              const [year, month, day] = selectedLog.date.split('-').map(Number);
                              const localDate = new Date(year, month - 1, day, 12, 0, 0, 0);
                              return localDate.toLocaleDateString('en-US', {
                                weekday: 'long',
                                year: 'numeric',
                                month: 'long',
                                day: 'numeric',
                              });
                            })()
                          : 'Unknown'}
                      </p>
                    </div>
                    <div>
                      <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Elaboration</p>
                      <div className="text-lg text-gray-900 dark:text-white prose dark:prose-invert max-w-none">
                        {selectedLog.elaboration ? (
                          <span
                            dangerouslySetInnerHTML={{ __html: selectedLog.elaboration }}
                          />
                        ) : (
                          <span>None</span>
                        )}
                      </div>
                    </div>
                    <div>
                      <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Submitted</p>
                      <p className="text-lg text-gray-900 dark:text-white">
                        {selectedLog.created_at
                          ? new Date(selectedLog.created_at).toLocaleString('en-US', {
                              month: 'short',
                              day: 'numeric',
                              hour: '2-digit',
                              minute: '2-digit',
                            })
                          : 'Unknown'}
                      </p>
                    </div>
                    {/* Values Reflection */}
                    {selectedLog.values_reflection && (
                      <div className="md:col-span-2">
                        <p className="text-sm font-medium text-gray-600 dark:text-gray-400 mb-1">Values Reflection</p>
                        <div className="text-lg text-gray-900 dark:text-white prose dark:prose-invert max-w-none">
                          <span
                            dangerouslySetInnerHTML={{ __html: selectedLog.values_reflection }}
                          />
                        </div>
                      </div>
                    )}
                  </div>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                  <div className="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-4 text-center">
                    <p className="text-sm font-medium text-blue-600 dark:text-blue-400">Day Quality Score</p>
                    <p className="text-3xl font-bold text-blue-700 dark:text-blue-300 mt-2">
                      {selectedLog.day_quality_score || 0}<span className="text-lg">/5</span>
                    </p>
                  </div>
                  <div className="bg-green-50 dark:bg-green-900/20 rounded-lg p-4 text-center">
                    <p className="text-sm font-medium text-green-600 dark:text-green-400">Support Level Score</p>
                    <p className="text-3xl font-bold text-green-700 dark:text-green-300 mt-2">
                      {selectedLog.support_level_score || 0}<span className="text-lg">/5</span>
                    </p>
                  </div>
                  <div className={`rounded-lg p-4 text-center ${
                    selectedLog.day_off 
                      ? 'bg-yellow-50 dark:bg-yellow-900/20' 
                      : 'bg-gray-50 dark:bg-gray-700'
                  }`}>
                    <p className={`text-sm font-medium ${
                      selectedLog.day_off 
                        ? 'text-yellow-600 dark:text-yellow-400' 
                        : 'text-gray-600 dark:text-gray-400'
                    }`}>Day Off</p>
                    <p className={`text-2xl font-bold mt-2 ${
                      selectedLog.day_off 
                        ? 'text-yellow-700 dark:text-yellow-300' 
                        : 'text-gray-700 dark:text-gray-300'
                    }`}>
                      {selectedLog.day_off ? 'Yes' : 'No'}
                    </p>
                  </div>
                  <div className={`rounded-lg p-4 text-center ${
                    selectedLog.staff_care_support_needed 
                      ? 'bg-red-50 dark:bg-red-900/20' 
                      : 'bg-gray-50 dark:bg-gray-700'
                  }`}>
                    <p className={`text-sm font-medium ${
                      selectedLog.staff_care_support_needed 
                        ? 'text-red-600 dark:text-red-400' 
                        : 'text-gray-600 dark:text-gray-400'
                    }`}>Support Needed</p>
                    <p className={`text-2xl font-bold mt-2 ${
                      selectedLog.staff_care_support_needed 
                        ? 'text-red-700 dark:text-red-300' 
                        : 'text-gray-700 dark:text-gray-300'
                    }`}>
                      {selectedLog.staff_care_support_needed ? 'Yes' : 'No'}
                    </p>
                  </div>
                </div>

                {/* Comments and Notes */}
                {(selectedLog.comments || selectedLog.notes || selectedLog.activities) && (
                  <div className="space-y-4">
                    {selectedLog.comments && (
                      <div>
                        <h4 className="text-lg font-medium text-gray-900 dark:text-white mb-2">Comments</h4>
                        <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-4">
                          <p className="text-gray-700 dark:text-gray-300 whitespace-pre-wrap">
                            {selectedLog.comments}
                          </p>
                        </div>
                      </div>
                    )}
                    
                    {selectedLog.notes && (
                      <div>
                        <h4 className="text-lg font-medium text-gray-900 dark:text-white mb-2">Notes</h4>
                        <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-4">
                          <p className="text-gray-700 dark:text-gray-300 whitespace-pre-wrap">
                            {selectedLog.notes}
                          </p>
                        </div>
                      </div>
                    )}
                    
                    {selectedLog.activities && (
                      <div>
                        <h4 className="text-lg font-medium text-gray-900 dark:text-white mb-2">Activities</h4>
                        <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-4">
                          <p className="text-gray-700 dark:text-gray-300 whitespace-pre-wrap">
                            {selectedLog.activities}
                          </p>
                        </div>
                      </div>
                    )}
                  </div>
                )}

                {/* Additional Details */}
                {(selectedLog.mood || selectedLog.behavior || selectedLog.participation) && (
                  <div>
                    <h4 className="text-lg font-medium text-gray-900 dark:text-white mb-3">Additional Details</h4>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                      {selectedLog.mood && (
                        <div className="bg-purple-50 dark:bg-purple-900/20 rounded-lg p-4">
                          <p className="text-sm font-medium text-purple-600 dark:text-purple-400">Mood</p>
                          <p className="text-lg text-purple-700 dark:text-purple-300 mt-1">
                            {selectedLog.mood}
                          </p>
                        </div>
                      )}
                      {selectedLog.behavior && (
                        <div className="bg-indigo-50 dark:bg-indigo-900/20 rounded-lg p-4">
                          <p className="text-sm font-medium text-indigo-600 dark:text-indigo-400">Behavior</p>
                          <p className="text-lg text-indigo-700 dark:text-indigo-300 mt-1">
                            {selectedLog.behavior}
                          </p>
                        </div>
                      )}
                      {selectedLog.participation && (
                        <div className="bg-teal-50 dark:bg-teal-900/20 rounded-lg p-4">
                          <p className="text-sm font-medium text-teal-600 dark:text-teal-400">Participation</p>
                          <p className="text-lg text-teal-700 dark:text-teal-300 mt-1">
                            {selectedLog.participation}
                          </p>
                        </div>
                      )}
                    </div>
                  </div>
                )}

                {/* Action Buttons */}
                <div className="flex justify-end space-x-3 pt-4 border-t border-gray-200 dark:border-gray-600">
                  <button
                    onClick={() => setViewingDetails(false)}
                    className="px-4 py-2 text-gray-700 dark:text-gray-300 bg-gray-200 dark:bg-gray-600 rounded-lg hover:bg-gray-300 dark:hover:bg-gray-500 transition-colors"
                  >
                    Close
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default UnitHeadBunkGrid;
