import React, { useState, useEffect } from 'react';
import { useAuth } from '../../auth/AuthContext';
import api from '../../api';
import UnitHeadBunkCard from '../../components/bunklogs/UnitHeadBunkCard';
import { Loader2, AlertTriangle, Users, Home, UserCheck, Heart, UserX, Clock, AlertCircle, Baby } from 'lucide-react';
import GenericAvatar from '../../images/avatar-generic.png';

function UnitHeadBunkGrid({ selectedDate }) {
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);
  const [unitData, setUnitData] = useState(null);
  const [allCampers, setAllCampers] = useState([]);
  const [campersNeedingAttention, setCampersNeedingAttention] = useState([]);
  const [activeTab, setActiveTab] = useState('overview');
  const { user, isAuthenticated } = useAuth();

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
        let dateToUse;
        if (selectedDate) {
          const year = selectedDate.getFullYear();
          const month = String(selectedDate.getMonth() + 1).padStart(2, '0');
          const day = String(selectedDate.getDate()).padStart(2, '0');
          dateToUse = `${year}-${month}-${day}`;
        } else {
          dateToUse = new Date().toISOString().split('T')[0];
        }
        
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
                    // Build the date string in YYYY-MM-DD format
                    const dateStr = selectedDate
                      ? `${selectedDate.getFullYear()}-${String(selectedDate.getMonth() + 1).padStart(2, '0')}-${String(selectedDate.getDate()).padStart(2, '0')}`
                      : new Date().toISOString().split('T')[0];
                    // Build the URL to the camper's page for this date
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
                    // Build the date string in YYYY-MM-DD format
                    const dateStr = selectedDate
                      ? `${selectedDate.getFullYear()}-${String(selectedDate.getMonth() + 1).padStart(2, '0')}-${String(selectedDate.getDate()).padStart(2, '0')}`
                      : new Date().toISOString().split('T')[0];
                    // Build the URL to the camper's page for this date
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
                    // Build the date string in YYYY-MM-DD format
                    const dateStr = selectedDate
                      ? `${selectedDate.getFullYear()}-${String(selectedDate.getMonth() + 1).padStart(2, '0')}-${String(selectedDate.getDate()).padStart(2, '0')}`
                      : new Date().toISOString().split('T')[0];
                    // Build the URL to the camper's page for this date
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
    </div>
  );
}

export default UnitHeadBunkGrid;
