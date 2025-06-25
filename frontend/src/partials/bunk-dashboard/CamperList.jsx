import React, { useState, useEffect } from 'react';
import { Link, NavLink } from 'react-router-dom';
import api from '../../api';
import { CheckCircle, Clock, Filter, Loader2, AlertTriangle } from 'lucide-react';
import { useAuth } from '../../auth/AuthContext';

function CamperList({ bunk_id, date, openBunkModal, refreshTrigger, userRole }) {
    const { user } = useAuth();
    const [data, setData] = useState([]);
    const [error, setError] = useState(null);
    const [loading, setLoading] = useState(true);
    const [filterStatus, setFilterStatus] = useState('all'); // 'all', 'completed', 'pending'

    // Check if user can edit (only Counselors can open the modal)
    const canEdit = userRole === 'Counselor';

    useEffect(() => {
        const fetchData = async () => {
            try {
                setLoading(true);
                setError(null); // Clear any previous errors
                console.log(`[CamperList] Fetching data for bunk ${bunk_id}, date ${date}, refreshTrigger ${refreshTrigger}`);
                console.log(`[CamperList] User role: ${userRole}`);
                const response = await api.get(
                    `/api/v1/bunklogs/${bunk_id}/logs/${date}/`
                );
                console.log(`[CamperList] Data fetched:`, response.data.campers);
                console.log(`[CamperList] Response status:`, response.status);
                
                if (response.data && response.data.campers) {
                    setData(response.data.campers);
                    setError(null); // Ensure error is cleared on successful fetch
                    console.log(`[CamperList] Successfully set ${response.data.campers.length} campers`);
                } else {
                    console.warn(`[CamperList] No campers data in response:`, response.data);
                    setData([]);
                    setError(null); // Clear error even if no data
                }
            } catch (error) {
                console.error('Error fetching campers:', error);
                console.error('Error details:', error.response?.data || error.message);
                setError(`Error fetching campers: ${error.response?.data?.error || error.message}`);
                setData([]); // Clear data on error
            } finally {
                setLoading(false);
            }
        };
        
        // Don't fetch data for invalid/default dates
        if (bunk_id && date && date !== "2025-01-01") {
            fetchData();
        } else if (date === "2025-01-01") {
            console.warn(`[CamperList] Skipping fetch for default fallback date: ${date}`);
            setLoading(false);
            setError(null);
            setData([]);
        } else {
            console.warn(`[CamperList] Missing required props - bunk_id: ${bunk_id}, date: ${date}`);
            setLoading(false);
            setError(null);
            setData([]);
        }
    }, [bunk_id, date, refreshTrigger]);

    // Filter campers based on log status
    const filteredData = data.filter(camper => {
        if (filterStatus === 'completed') return camper.bunk_log;
        if (filterStatus === 'pending') return !camper.bunk_log;
        return true; // 'all'
    });

    // Get status counts for display
    const completedCount = data.filter(camper => camper.bunk_log).length;
    const pendingCount = data.filter(camper => !camper.bunk_log).length;

    // Debug logging (can be removed in production)
    if (process.env.NODE_ENV === 'development') {
        console.log(`[CamperList] Render - Total data: ${data.length}, Filtered: ${filteredData.length}, Filter: ${filterStatus}`);
        console.log(`[CamperList] Render - User role: ${userRole}, Can edit: ${canEdit}`);
    }

    // Loading state
    if (loading) {
        return (
            <div className="p-4">
                <div className="flex items-center justify-center py-8">
                    <Loader2 className="w-5 h-5 animate-spin text-gray-400" />
                    <span className="ml-2 text-sm text-gray-500">Loading campers...</span>
                </div>
            </div>
        );
    }

    // Error state - only show if there's actually an error and no data
    if (error && data.length === 0) {
        return (
            <div className="p-4">
                <div className="flex flex-col items-center justify-center py-8 text-red-500">
                    <AlertTriangle className="w-5 h-5 mb-2" />
                    <span className="text-sm font-medium">Failed to load</span>
                    <span className="text-xs text-gray-500 mt-1 text-center">{error}</span>
                </div>
            </div>
        );
    }

    // Helper: can the logged-in counselor open the modal for this camper?
    const canOpenBunkLog = (camper) => {
        if (userRole !== 'Counselor') return false;
        if (!camper.bunk_log) return true; // No log yet
        // Convert both values to strings to handle type mismatch (number vs string)
        const canOpen = String(camper.bunk_log.counselor) === String(user.id);
        return canOpen; // Only author can open
    };

    // Helper: should the row be grayed out?
    const isGrayedOut = (camper) => {
        if (!camper.bunk_log) return false;
        if (userRole !== 'Counselor') return false;
        // Convert both values to strings to handle type mismatch (number vs string)
        const shouldGray = String(camper.bunk_log.counselor) !== String(user.id);
        return shouldGray;
    };

    return (
        <div className="h-full flex flex-col">
            {/* Header with counts */}
            <div className="p-4 border-b border-gray-200 dark:border-gray-700">
                <div className="flex items-center justify-between mb-3">
                    <h3 className="font-small text-gray-900 dark:text-gray-100">Completed</h3>
                    <div className="text-sm text-gray-500">
                        {completedCount}/{data.length}
                    </div>
                </div>
                
                {/* Role-based access indicator */}
                {!canEdit && (
                    <div className="mb-3 p-2 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg">
                        <p className="text-xs text-blue-700 dark:text-blue-300 text-center">
                            👁️ View-only access
                        </p>
                    </div>
                )}
                
                {/* Simple filter tabs */}
                <div className="flex space-x-1 bg-gray-100 dark:bg-gray-800 rounded-lg p-1">
                    <button
                        onClick={() => setFilterStatus('all')}
                        className={`flex-1 px-2 py-1 text-xs font-medium rounded transition-colors ${
                            filterStatus === 'all' 
                                ? 'bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 shadow-sm' 
                                : 'text-gray-600 dark:text-gray-400'
                        }`}
                    >
                        All
                    </button>
                    <button
                        onClick={() => setFilterStatus('pending')}
                        className={`flex-1 px-2 py-1 text-xs font-medium rounded transition-colors ${
                            filterStatus === 'pending' 
                                ? 'bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 shadow-sm' 
                                : 'text-gray-600 dark:text-gray-400'
                        }`}
                    >
                        Pending
                    </button>
                    <button
                        onClick={() => setFilterStatus('completed')}
                        className={`flex-1 px-2 py-1 text-xs font-medium rounded transition-colors ${
                            filterStatus === 'completed' 
                                ? 'bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 shadow-sm' 
                                : 'text-gray-600 dark:text-gray-400'
                        }`}
                    >
                        Done
                    </button>
                </div>
            </div>

            {/* Camper list */}
            <div className="flex-1 overflow-y-auto p-2">
                <div className="space-y-1">
                    {filteredData.map((camper) => {
                        const canOpen = canOpenBunkLog(camper);
                        const shouldGrayOut = isGrayedOut(camper);
                        
                        return (
                        <button
                            key={camper.camper_id}
                            className={`w-full text-left px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-200 flex items-center justify-between group border border-gray-200 dark:border-gray-600
                                ${canOpen
                                    ? 'bg-gray-50 hover:bg-gray-100 text-gray-700 dark:bg-gray-800 dark:hover:bg-gray-700 dark:text-gray-300 cursor-pointer'
                                    : shouldGrayOut
                                        ? 'bg-gray-100 text-gray-400 dark:bg-gray-900 dark:text-gray-500 cursor-not-allowed opacity-60'
                                        : 'bg-gray-50 text-gray-700 dark:bg-gray-800 dark:text-gray-300 cursor-default'}
                            `}
                            onClick={(e) => {
                                e.stopPropagation();
                                if (canOpen) {
                                    openBunkModal(camper.camper_id, camper.bunk_assignment_id);
                                }
                            }}
                            title={canOpen ? (camper.bunk_log ? "Edit bunk log" : "Create bunk log") : shouldGrayOut ? "Another counselor's log (view only)" : "View only"}
                            disabled={!canOpen}
                        >
                            <span className="truncate">
                                {camper.camper_first_name} {camper.camper_last_name}
                            </span>
                            <div className="ml-2 flex-shrink-0">
                                {camper.bunk_log ? (
                                    <CheckCircle className="w-4 h-4 text-green-600 dark:text-green-500" />
                                ) : (
                                    <Clock className="w-4 h-4 text-red-500 dark:text-red-400" />
                                )}
                            </div>
                        </button>
                    )})}
                </div>
                
                {filteredData.length === 0 && (
                    <div className="text-center py-8 text-gray-500 dark:text-gray-400">
                        {data.length === 0 ? (
                            <div>
                                <p className="text-sm">No campers assigned to this bunk</p>
                                <p className="text-xs mt-1">Check the bunk assignments</p>
                            </div>
                        ) : (
                            <div>
                                <p className="text-sm">No campers match the current filter</p>
                                <p className="text-xs mt-1">Try changing the filter above</p>
                            </div>
                        )}
                    </div>
                )}
            </div>
        </div>
    );
}

export default CamperList;