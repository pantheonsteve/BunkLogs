import React, { useState, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { ArrowLeft, FileText, Users, AlertCircle } from 'lucide-react';

import Header from '../partials/Header';
import Sidebar from '../partials/Sidebar';
import { useAuth } from '../auth/AuthContext';
import api from '../api';

// Score color helper (matches CounselorLogsGrid)
function getScoreColor(score) {
  if (!score) return 'bg-gray-100 text-gray-800';
  switch (parseInt(score)) {
    case 1: return 'bg-[#e86946] text-white';
    case 2: return 'bg-[#de8d6f] text-white';
    case 3: return 'bg-[#e5e825] text-gray-900';
    case 4: return 'bg-[#90d258] text-gray-900';
    case 5: return 'bg-[#18d128] text-white';
    default: return 'bg-gray-100 text-gray-800';
  }
}

function formatDate(dateStr) {
  if (!dateStr) return '';
  const [year, month, day] = dateStr.split('-').map(Number);
  return new Date(year, month - 1, day, 12).toLocaleDateString('en-US', {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });
}

function RoleBadge({ role }) {
  return (
    <span className="inline-flex px-2 py-1 text-xs font-medium rounded-full bg-blue-50 text-blue-700 dark:bg-blue-900 dark:text-blue-200">
      {role}
    </span>
  );
}

function StaffMemberHistory() {
  const { staffId } = useParams();
  const navigate = useNavigate();
  const { user, loading: authLoading, isAuthenticating } = useAuth();

  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedLog, setSelectedLog] = useState(null);

  useEffect(() => {
    async function fetchHistory() {
      if (authLoading || isAuthenticating || !user?.id) return;

      if (!staffId || staffId === 'undefined') {
        setError('Invalid staff member — no ID provided.');
        setLoading(false);
        return;
      }

      try {
        setLoading(true);
        setError(null);
        const response = await api.get('/api/v1/counselorlogs/', {
          params: { staff_member: staffId },
        });
        setLogs(response.data.results || []);
      } catch (err) {
        console.error('Error fetching staff history:', err);
        const status = err?.response?.status;
        const detail = err?.response?.data?.detail || err?.response?.data?.error || err?.message;
        const msg = status
          ? `Failed to load staff reflection history (${status}${detail ? ': ' + detail : ''}).`
          : `Failed to load staff reflection history: ${detail || 'Network error'}`;
        setError(msg);
      } finally {
        setLoading(false);
      }
    }
    fetchHistory();
  }, [staffId, user?.id, authLoading, isAuthenticating]);

  // Derive staff member info from any log
  const staffInfo = logs.length > 0 ? {
    firstName: logs[0].staff_member_first_name,
    lastName: logs[0].staff_member_last_name,
    email: logs[0].staff_member_email,
    role: logs[0].staff_member_role,
    title: logs[0].staff_member_title,
  } : null;

  // Stats
  const totalLogs = logs.length;
  const avgQuality = totalLogs > 0
    ? (logs.reduce((s, l) => s + l.day_quality_score, 0) / totalLogs).toFixed(1)
    : '--';
  const supportCount = logs.filter(l => l.staff_care_support_needed).length;

  if (authLoading || isAuthenticating) {
    return (
      <div className="flex h-screen overflow-hidden">
        <Sidebar sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} />
        <div className="relative flex flex-col flex-1 overflow-y-auto overflow-x-hidden">
          <Header sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} />
          <main className="grow flex items-center justify-center">
            <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-blue-500" />
          </main>
        </div>
      </div>
    );
  }

  if (user && user.role !== 'Admin') {
    return (
      <div className="flex h-screen overflow-hidden">
        <Sidebar sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} />
        <div className="relative flex flex-col flex-1 overflow-y-auto overflow-x-hidden">
          <Header sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} />
          <main className="grow">
            <div className="px-4 sm:px-6 lg:px-8 py-8 max-w-9xl mx-auto">
              <div className="rounded-md bg-red-50 p-4">
                <p className="text-sm text-red-700">You do not have permission to view this page.</p>
              </div>
            </div>
          </main>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-[100dvh] overflow-hidden">
      <Sidebar sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} />

      <div className="relative flex flex-col flex-1 overflow-y-auto overflow-x-hidden">
        <Header sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} />

        <main className="grow">
          <div className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-9xl mx-auto">

            {/* Back button */}
            <button
              onClick={() => navigate(-1)}
              className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white mb-6"
            >
              <ArrowLeft className="w-4 h-4" />
              Back
            </button>

            {/* Staff member header card */}
            <div className="bg-white dark:bg-gray-800 shadow-sm rounded-xl p-6 mb-6">
              {loading ? (
                <div className="flex items-center gap-3">
                  <div className="animate-spin rounded-full h-6 w-6 border-t-2 border-b-2 border-blue-500" />
                  <span className="text-gray-500 dark:text-gray-400">Loading...</span>
                </div>
              ) : staffInfo ? (
                <div className="flex items-center gap-5">
                  <div className="h-16 w-16 rounded-full bg-blue-100 dark:bg-blue-900 flex items-center justify-center flex-shrink-0">
                    <span className="text-xl font-bold text-blue-700 dark:text-blue-300">
                      {staffInfo.firstName?.[0]}{staffInfo.lastName?.[0]}
                    </span>
                  </div>
                  <div>
                    <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
                      {staffInfo.firstName} {staffInfo.lastName}
                    </h1>
                    <div className="flex items-center gap-3 mt-1 flex-wrap">
                      <RoleBadge role={staffInfo.role} />
                      {staffInfo.title && (
                        <span className="text-sm text-gray-500 dark:text-gray-400">{staffInfo.title}</span>
                      )}
                      <span className="text-sm text-gray-400 dark:text-gray-500">{staffInfo.email}</span>
                    </div>
                  </div>
                </div>
              ) : !error ? (
                <p className="text-gray-500 dark:text-gray-400">No reflection history found for this staff member.</p>
              ) : null}
            </div>

            {/* Stats row */}
            {!loading && !error && totalLogs > 0 && (
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
                <div className="bg-white dark:bg-gray-800 shadow-sm rounded-xl p-5 flex items-center gap-4">
                  <FileText className="w-8 h-8 text-blue-500 flex-shrink-0" />
                  <div>
                    <p className="text-sm text-gray-500 dark:text-gray-400">Total Reflections</p>
                    <p className="text-2xl font-semibold text-gray-900 dark:text-white">{totalLogs}</p>
                  </div>
                </div>
                <div className="bg-white dark:bg-gray-800 shadow-sm rounded-xl p-5 flex items-center gap-4">
                  <Users className="w-8 h-8 text-green-500 flex-shrink-0" />
                  <div>
                    <p className="text-sm text-gray-500 dark:text-gray-400">Avg Quality Score</p>
                    <p className="text-2xl font-semibold text-gray-900 dark:text-white">{avgQuality}</p>
                  </div>
                </div>
                <div className="bg-white dark:bg-gray-800 shadow-sm rounded-xl p-5 flex items-center gap-4">
                  <AlertCircle className="w-8 h-8 text-yellow-500 flex-shrink-0" />
                  <div>
                    <p className="text-sm text-gray-500 dark:text-gray-400">Support Needed</p>
                    <p className="text-2xl font-semibold text-gray-900 dark:text-white">{supportCount}</p>
                  </div>
                </div>
              </div>
            )}

            {/* Reflection history table */}
            <div className="bg-white dark:bg-gray-800 shadow-sm rounded-xl">
              <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
                <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
                  Reflection History
                </h2>
              </div>

              <div className="overflow-x-auto">
                {loading ? (
                  <div className="flex items-center justify-center py-12 gap-3">
                    <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-blue-500" />
                    <span className="text-gray-500 dark:text-gray-400">Loading reflections...</span>
                  </div>
                ) : error ? (
                  <div className="flex items-center justify-center py-12">
                    <p className="text-red-600 dark:text-red-400">{error}</p>
                  </div>
                ) : logs.length === 0 ? (
                  <div className="flex flex-col items-center justify-center py-12 gap-3">
                    <FileText className="w-12 h-12 text-gray-300 dark:text-gray-600" />
                    <p className="text-gray-500 dark:text-gray-400">No reflections submitted yet.</p>
                  </div>
                ) : (
                  <table className="w-full">
                    <thead className="bg-gray-50 dark:bg-gray-900">
                      <tr>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Date</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Quality Score</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Support Score</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Day Off</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Support Needed</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">View</th>
                      </tr>
                    </thead>
                    <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
                      {logs.map(log => (
                        <tr
                          key={log.id}
                          className="hover:bg-gray-50 dark:hover:bg-gray-700 cursor-pointer"
                          onClick={() => setSelectedLog(log)}
                        >
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-white font-medium">
                            {formatDate(log.date)}
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
                          <td className="px-6 py-4 whitespace-nowrap">
                            <FileText className="w-4 h-4 text-blue-600 dark:text-blue-400" />
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </div>
            </div>

          </div>
        </main>
      </div>

      {/* Detail Modal */}
      {selectedLog && (
        <div
          className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50"
          onClick={() => setSelectedLog(null)}
        >
          <div
            className="bg-white dark:bg-gray-800 rounded-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto"
            onClick={e => e.stopPropagation()}
          >
            <div className="p-6">
              <div className="flex items-center justify-between mb-6">
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                  Reflection — {formatDate(selectedLog.date)}
                </h3>
                <button
                  onClick={() => setSelectedLog(null)}
                  className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 text-xl leading-none"
                >
                  ✕
                </button>
              </div>

              <div className="space-y-6">
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
                    dangerouslySetInnerHTML={{ __html: selectedLog.elaboration || '<em>No elaboration provided.</em>' }}
                  />
                </div>

                {/* Values Reflection */}
                <div>
                  <h4 className="text-sm font-medium text-gray-900 dark:text-white mb-2">Values Reflection</h4>
                  <div
                    className="text-sm text-gray-600 dark:text-gray-400 bg-gray-50 dark:bg-gray-700 p-3 rounded-lg"
                    dangerouslySetInnerHTML={{ __html: selectedLog.values_reflection || '<em>No reflection provided.</em>' }}
                  />
                </div>

                {/* Timestamps */}
                <div className="grid grid-cols-2 gap-4 text-xs text-gray-500 dark:text-gray-400">
                  <div>
                    <span className="font-medium">Submitted:</span><br />
                    {new Date(selectedLog.created_at).toLocaleString()}
                  </div>
                  <div>
                    <span className="font-medium">Last updated:</span><br />
                    {new Date(selectedLog.updated_at).toLocaleString()}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default StaffMemberHistory;
