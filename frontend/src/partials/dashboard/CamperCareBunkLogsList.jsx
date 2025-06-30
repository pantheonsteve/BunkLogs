import React from 'react';
import CamperCareBunkLogItem from '../../components/bunklogs/CamperCareBunkLogItem';
import api from '../../api';
import GenericAvatar from '../../images/avatar-generic.png';
import { useAuth } from '../../auth/AuthContext';

function CamperCareBunkLogsList({ selectedDate }) {
  const { user } = useAuth();
  const [bunkLogs, setBunkLogs] = React.useState([]);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState(null);
  const [sortConfig, setSortConfig] = React.useState({ key: null, direction: 'asc' });

  React.useEffect(() => {
    async function fetchBunkLogs() {
      setLoading(true);
      setError(null);
      try {
        if (!user?.id) {
          setError('User not authenticated');
          setBunkLogs([]);
          setLoading(false);
          return;
        }
        const year = selectedDate.getFullYear();
        const month = String(selectedDate.getMonth() + 1).padStart(2, '0');
        const day = String(selectedDate.getDate()).padStart(2, '0');
        const formattedDate = `${year}-${month}-${day}`;
        const response = await api.get(`/api/v1/campercare/${user.id}/${formattedDate}/`);
        const units = response.data;
        // Flatten all campers with a bunk_log
        const logs = [];
        if (units && units.length > 0) {
          units.forEach(unit => {
            (unit.bunks || []).forEach(bunk => {
              (bunk.campers || []).forEach(camper => {
                if (camper.bunk_log) {
                  logs.push({
                    ...camper,
                    bunk_name: bunk.cabin_name,
                    unit_name: unit.name,
                    bunk_id: bunk.id,
                    bunk_log: camper.bunk_log
                  });
                }
              });
            });
          });
        }
        setBunkLogs(logs);
      } catch (err) {
        setError('Failed to load bunk logs');
        setBunkLogs([]);
      } finally {
        setLoading(false);
      }
    }
    if (selectedDate) fetchBunkLogs();
  }, [selectedDate, user]);

  // Sorting logic
  const handleSort = (key) => {
    setSortConfig((prev) => {
      if (prev.key === key) {
        return { key, direction: prev.direction === 'asc' ? 'desc' : 'asc' };
      }
      return { key, direction: 'asc' };
    });
  };

  const sortedLogs = React.useMemo(() => {
    if (!sortConfig.key) return bunkLogs;
    const sorted = [...bunkLogs].sort((a, b) => {
      let aValue, bValue;
      switch (sortConfig.key) {
        case 'camper':
          aValue = `${a.first_name} ${a.last_name}`.toLowerCase();
          bValue = `${b.first_name} ${b.last_name}`.toLowerCase();
          break;
        case 'bunk_unit':
          aValue = `${a.bunk_name} ${a.unit_name}`.toLowerCase();
          bValue = `${b.bunk_name} ${b.unit_name}`.toLowerCase();
          break;
        case 'date':
          aValue = a.bunk_log.date;
          bValue = b.bunk_log.date;
          break;
        case 'social_score':
          aValue = Number(a.bunk_log.social_score) || 0;
          bValue = Number(b.bunk_log.social_score) || 0;
          break;
        case 'participation_score':
          aValue = Number(a.bunk_log.participation_score) || 0;
          bValue = Number(b.bunk_log.participation_score) || 0;
          break;
        case 'behavior_score':
          aValue = Number(a.bunk_log.behavior_score) || 0;
          bValue = Number(b.bunk_log.behavior_score) || 0;
          break;
        default:
          aValue = '';
          bValue = '';
      }
      if (aValue < bValue) return sortConfig.direction === 'asc' ? -1 : 1;
      if (aValue > bValue) return sortConfig.direction === 'asc' ? 1 : -1;
      return 0;
    });
    return sorted;
  }, [bunkLogs, sortConfig]);

  return (
    <div>
      <h2 className="text-xl font-bold mb-4">My Bunk Logs</h2>
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow p-6">
        {loading ? (
          <div className="flex items-center justify-center py-12">
            <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-blue-500"></div>
            <span className="ml-3 text-gray-600 dark:text-gray-400">Loading logs...</span>
          </div>
        ) : error ? (
          <div className="text-red-600 dark:text-red-400 text-center py-8">{error}</div>
        ) : sortedLogs.length === 0 ? (
          <div className="text-center py-8 text-gray-500 dark:text-gray-400">No bunk logs found for this date.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="table-auto w-full dark:text-gray-300 border border-gray-200 dark:border-gray-700">
              <colgroup>
                <col style={{ width: '16.6667%' }} /> {/* Name: 2/12 */}
                <col style={{ width: '8.3333%' }} /> {/* Bunk/Unit: 1/12 */}
                <col style={{ width: '8.3333%' }} /> {/* Date: 1/12 */}
                <col style={{ width: '8.3333%' }} /> {/* Social: 1/12 */}
                <col style={{ width: '8.3333%' }} /> {/* Participation: 1/12 */}
                <col style={{ width: '8.3333%' }} /> {/* Behavior: 1/12 */}
                <col style={{ width: '25%' }} /> {/* Description: 3/12 */}
              </colgroup>
              <thead className="text-xs uppercase text-gray-400 dark:text-gray-500 bg-gray-50 dark:bg-gray-700/50 rounded-xs">
                <tr>
                  <th className="px-2 first:pl-5 last:pr-5 py-3 border border-gray-300 dark:border-gray-700 cursor-pointer w-2/12" onClick={() => handleSort('camper')}>
                    Camper Name {sortConfig.key === 'camper' ? (sortConfig.direction === 'asc' ? '▲' : '▼') : ''}
                  </th>
                  <th className="px-2 first:pl-5 last:pr-5 py-3 border border-gray-300 dark:border-gray-700 cursor-pointer w-1/12" onClick={() => handleSort('bunk_unit')}>
                    Bunk / Unit {sortConfig.key === 'bunk_unit' ? (sortConfig.direction === 'asc' ? '▲' : '▼') : ''}
                  </th>
                  <th className="px-2 first:pl-5 last:pr-5 py-3 border border-gray-300 dark:border-gray-700 cursor-pointer w-1/12" onClick={() => handleSort('date')}>
                    Date {sortConfig.key === 'date' ? (sortConfig.direction === 'asc' ? '▲' : '▼') : ''}
                  </th>
                  <th className="px-2 first:pl-5 last:pr-5 py-3 border border-gray-300 dark:border-gray-700 cursor-pointer w-1/12" onClick={() => handleSort('social_score')}>
                    Social {sortConfig.key === 'social_score' ? (sortConfig.direction === 'asc' ? '▲' : '▼') : ''}
                  </th>
                  <th className="px-2 first:pl-5 last:pr-5 py-3 border border-gray-300 dark:border-gray-700 cursor-pointer w-1/12" onClick={() => handleSort('participation_score')}>
                    Participation {sortConfig.key === 'participation_score' ? (sortConfig.direction === 'asc' ? '▲' : '▼') : ''}
                  </th>
                  <th className="px-2 first:pl-5 last:pr-5 py-3 border border-gray-300 dark:border-gray-700 cursor-pointer w-1/12" onClick={() => handleSort('behavior_score')}>
                    Behavior {sortConfig.key === 'behavior_score' ? (sortConfig.direction === 'asc' ? '▲' : '▼') : ''}
                  </th>
                  <th className="px-2 first:pl-5 last:pr-5 py-3 border border-gray-300 dark:border-gray-700 w-3/12">Description</th>
                </tr>
              </thead>
              {/* Render each row using CamperCareBunkLogItem, which outputs <tbody> */}
              {sortedLogs.map((camper, idx) => (
                <CamperCareBunkLogItem
                  key={camper.id || idx}
                  id={camper.id}
                  camper_id={camper.id}
                  image={GenericAvatar}
                  camper_first_name={camper.first_name}
                  camper_last_name={camper.last_name}
                  bunk_name={camper.bunk_name}
                  unit_name={camper.unit_name}
                  date={camper.bunk_log.date}
                  social_score={camper.bunk_log.social_score}
                  behavior_score={camper.bunk_log.behavior_score}
                  participation_score={camper.bunk_log.participation_score}
                  description={camper.bunk_log.description}
                  counselor_first_name={camper.bunk_log.counselor_first_name}
                  counselor_last_name={camper.bunk_log.counselor_last_name}
                  // Optionally pass help flags if you want to show them
                  camper_care_help={camper.bunk_log.request_camper_care_help}
                  unit_head_help={camper.bunk_log.request_unit_head_help}
                />
              ))}
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

export default CamperCareBunkLogsList;
