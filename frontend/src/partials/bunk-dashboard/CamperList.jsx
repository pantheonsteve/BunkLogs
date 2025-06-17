import React, { useState, useEffect } from 'react';
import { Link, NavLink } from 'react-router-dom';
import api from '../../api';
import { CheckCircle, Clock, Filter, Loader2, AlertTriangle } from 'lucide-react';

function CamperList({ bunk_id, date, openBunkModal, refreshTrigger }) {
    const [data, setData] = useState([]);
    const [error, setError] = useState(null);
    const [loading, setLoading] = useState(true);
    const [filterStatus, setFilterStatus] = useState('all'); // 'all', 'completed', 'pending'

    useEffect(() => {
        const fetchData = async () => {
            try {
                setLoading(true);
                const response = await api.get(
                    `/api/v1/bunklogs/${bunk_id}/logs/${date}/`
                );
                setData(response.data.campers);
            } catch (error) {
                console.error('Error fetching campers:', error);
                setError('Error fetching campers.');
            } finally {
                setLoading(false);
            }
        };
        fetchData();
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

    // Loading state
    if (loading) {
        return (
            <div className="p-4">
                <div className="flex items-center justify-center py-8">
                    <Loader2 className="w-5 h-5 animate-spin text-gray-400" />
                    <span className="ml-2 text-sm text-gray-500">Loading...</span>
                </div>
            </div>
        );
    }

    // Error state
    if (error) {
        return (
            <div className="p-4">
                <div className="flex items-center justify-center py-8 text-red-500">
                    <AlertTriangle className="w-5 h-5" />
                    <span className="ml-2 text-sm">Failed to load</span>
                </div>
            </div>
        );
    }

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
                    {filteredData.map((camper) => (
                        <button
                            key={camper.camper_id}
                            className="w-full text-left px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-200 flex items-center justify-between group bg-gray-50 hover:bg-gray-100 text-gray-700 dark:bg-gray-800 dark:hover:bg-gray-700 dark:text-gray-300 border border-gray-200 dark:border-gray-600"
                            onClick={(e) => {
                                e.stopPropagation();
                                openBunkModal(camper.camper_id, camper.bunk_assignment_id);
                            }}
                            title={camper.bunk_log ? "Edit bunk log" : "Create bunk log"}
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
                    ))}
                </div>
                
                {filteredData.length === 0 && (
                    <div className="text-center py-8 text-gray-500 dark:text-gray-400">
                        <p className="text-sm">No campers found</p>
                    </div>
                )}
            </div>
        </div>
    );
}

export default CamperList;