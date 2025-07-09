import React from 'react';
import { Calendar, Users, FileText, Eye, ChevronLeft, ChevronRight, Download } from 'lucide-react';

// Helper function for score color
function getScoreColor(score) {
    if (score >= 4) return 'text-green-600 bg-green-50';
    if (score >= 2) return 'text-yellow-600 bg-yellow-50';
    return 'text-red-600 bg-red-50';
}

// Helper function for date formatting
function formatDisplayDate(date) {
    if (!date) return '';
    // Handle date strings properly to avoid timezone issues
    // If it's a string in YYYY-MM-DD format, parse it as local date
    if (typeof date === 'string' && date.match(/^\d{4}-\d{2}-\d{2}$/)) {
        const [year, month, day] = date.split('-').map(Number);
        const localDate = new Date(year, month - 1, day, 12, 0, 0, 0); // Set to noon local time
        return localDate.toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' });
    }
    return new Date(date).toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' });
}

const CounselorLogsGrid = ({
    date,
    loading,
    error,
    counselorLogs = [],
    viewLogDetails,
}) => {
    console.log('📊 CounselorLogsGrid received:', {
        date,
        loading,
        error,
        counselorLogsLength: counselorLogs?.length,
        hasViewLogDetails: typeof viewLogDetails === 'function'
    });

    // Ensure counselorLogs is always an array
    const logs = Array.isArray(counselorLogs) ? counselorLogs : [];
    
    if (logs.length > 0) {
        console.log('📊 Processing', logs.length, 'logs for rendering');
    }

    return (
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
            ) : !logs || logs.length === 0 ? (
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
                                Bunk Assignment
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
                        {logs.map((log) => {
                            // Ensure log has required fields
                            if (!log || !log.id) {
                                console.warn('⚠️ Invalid log data:', log);
                                return null;
                            }
                            
                            return (
                            <tr key={log.id} className="hover:bg-gray-50 dark:hover:bg-gray-700">
                                <td className="px-6 py-4 whitespace-nowrap">
                                    <div className="flex items-center">
                                        <div className="flex-shrink-0 h-10 w-10">
                                            <div className="h-10 w-10 rounded-full bg-gray-300 dark:bg-gray-600 flex items-center justify-center">
                                                <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                                                    {(log.counselor_first_name || '?')[0]}{(log.counselor_last_name || '?')[0]}
                                                </span>
                                            </div>
                                        </div>
                                        <div className="ml-4">
                                            <div className="text-sm font-medium text-gray-900 dark:text-white">
                                                {log.counselor_first_name || 'Unknown'} {log.counselor_last_name || 'User'}
                                            </div>
                                            <div className="text-sm text-gray-500 dark:text-gray-400">
                                                {log.counselor_email || 'No email'}
                                            </div>
                                        </div>
                                    </div>
                                </td>
                                <td className="px-6 py-4 whitespace-nowrap">
                                    <div className="text-sm text-gray-900 dark:text-white">
                                        {log.bunk_names || 'No bunk assignment'}
                                    </div>
                                    {log.bunk_assignments && log.bunk_assignments.length > 0 && (
                                        <div className="text-xs text-gray-500 dark:text-gray-400">
                                            {log.bunk_assignments.map((assignment, index) => (
                                                <div key={assignment.id}>
                                                    {assignment.unit_name && `${assignment.unit_name} Unit`}
                                                    {assignment.cabin_name && ` • ${assignment.cabin_name}`}
                                                </div>
                                            ))}
                                        </div>
                                    )}
                                </td>
                                <td className="px-6 py-4 whitespace-nowrap">
                                    <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${getScoreColor(log.day_quality_score || 0)}`}>
                                        {log.day_quality_score || 0}/5
                                    </span>
                                </td>
                                <td className="px-6 py-4 whitespace-nowrap">
                                    <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${getScoreColor(log.support_level_score || 0)}`}>
                                        {log.support_level_score || 0}/5
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
                                    {log.created_at ? new Date(log.created_at).toLocaleTimeString('en-US', { 
                                        hour: '2-digit', 
                                        minute: '2-digit' 
                                    }) : 'N/A'}
                                </td>
                                <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                                    {viewLogDetails ? (
                                        <button
                                            onClick={() => viewLogDetails(log)}
                                            className="text-blue-600 hover:text-blue-900 dark:text-blue-400 dark:hover:text-blue-300"
                                        >
                                            <Eye className="w-4 h-4" />
                                        </button>
                                    ) : (
                                        <span className="text-gray-400">-</span>
                                    )}
                                </td>
                            </tr>
                            );
                        })}
                    </tbody>
                </table>
            )}
        </div>
    </div>
    );
};

export default CounselorLogsGrid;