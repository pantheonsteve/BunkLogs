import React from 'react';
import api from '../../api';
import GenericAvatar from '../../images/avatar-generic.png';
import { useAuth } from '../../auth/AuthContext';
import { Heart, UserCheck } from 'lucide-react';

function CamperCareNeedsAttentionList({ selectedDate }) {
  const { user } = useAuth();
  const [campers, setCampers] = React.useState([]);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState(null);

  React.useEffect(() => {
    async function fetchCampers() {
      setLoading(true);
      setError(null);
      try {
        if (!user?.id) {
          setError('User not authenticated');
          setCampers([]);
          setLoading(false);
          return;
        }
        const year = selectedDate.getFullYear();
        const month = String(selectedDate.getMonth() + 1).padStart(2, '0');
        const day = String(selectedDate.getDate()).padStart(2, '0');
        const formattedDate = `${year}-${month}-${day}`;
        const response = await api.get(`/api/v1/campercare/${user.id}/${formattedDate}/`);
        const units = response.data;
        const allCampers = [];
        if (units && units.length > 0) {
          units.forEach(unit => {
            (unit.bunks || []).forEach(bunk => {
              (bunk.campers || []).forEach(camper => {
                if (camper.bunk_log) {
                  allCampers.push({
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
        setCampers(allCampers);
      } catch (err) {
        setError('Failed to load campers');
        setCampers([]);
      } finally {
        setLoading(false);
      }
    }
    if (selectedDate) fetchCampers();
  }, [selectedDate, user]);

  const getCampersRequestingCamperCare = () =>
    campers.filter(camper => camper.bunk_log?.request_camper_care_help);
  const getCampersRequestingUnitHeadHelp = () =>
    campers.filter(camper => camper.bunk_log?.request_unit_head_help);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-32">
        <div className="text-center">
          <div className="w-8 h-8 animate-spin border-4 border-rose-200 border-t-rose-600 rounded-full mx-auto mb-4" />
          <p className="text-sm text-gray-500 dark:text-gray-400">Loading campers needing attention...</p>
        </div>
      </div>
    );
  }
  if (error) {
    return (
      <div className="text-center text-red-600 dark:text-red-400 py-8">{error}</div>
    );
  }

  const dateStr = selectedDate
    ? `${selectedDate.getFullYear()}-${String(selectedDate.getMonth() + 1).padStart(2, '0')}-${String(selectedDate.getDate()).padStart(2, '0')}`
    : new Date().toISOString().split('T')[0];

  const campersCare = getCampersRequestingCamperCare();
  const campersUnit = getCampersRequestingUnitHeadHelp();

  return (
    <div className="space-y-6">
      <h2 className="text-xl font-bold mb-4">Needs Attention</h2>
      {campersCare.length > 0 && (
        <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-sm border border-orange-200 dark:border-orange-800">
          <div className="p-6">
            <div className="flex items-center space-x-3 mb-4">
              <div className="w-10 h-10 bg-orange-100 dark:bg-orange-900/30 rounded-lg flex items-center justify-center">
                <Heart className="w-5 h-5 text-orange-600 dark:text-orange-400" />
              </div>
              <div>
                <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                  Camper Care Help Requested ({campersCare.length})
                </h3>
                <p className="text-sm text-gray-600 dark:text-gray-400">
                  Campers who need camper care attention
                </p>
              </div>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {campersCare.map((camper, idx) => (
                <a
                  key={`care-help-${camper.id}-${idx}`}
                  href={`/camper/${camper.id}/${dateStr}`}
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
                          <span dangerouslySetInnerHTML={{ __html: camper.bunk_log.description }} />
                        </p>
                      )}
                    </div>
                  </div>
                </a>
              ))}
            </div>
          </div>
        </div>
      )}
      {campersUnit.length > 0 && (
        <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-sm border border-yellow-200 dark:border-yellow-800">
          <div className="p-6">
            <div className="flex items-center space-x-3 mb-4">
              <div className="w-10 h-10 bg-yellow-100 dark:bg-yellow-900/30 rounded-lg flex items-center justify-center">
                <UserCheck className="w-5 h-5 text-yellow-600 dark:text-yellow-400" />
              </div>
              <div>
                <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                  Unit Head Help Requested ({campersUnit.length})
                </h3>
                <p className="text-sm text-gray-600 dark:text-gray-400">
                  Campers who need unit head attention
                </p>
              </div>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {campersUnit.map((camper, idx) => (
                <a
                  key={`unit-help-${camper.id}-${idx}`}
                  href={`/camper/${camper.id}/${dateStr}`}
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
                          <span dangerouslySetInnerHTML={{ __html: camper.bunk_log.description }} />
                        </p>
                      )}
                    </div>
                  </div>
                </a>
              ))}
            </div>
          </div>
        </div>
      )}
      {campersCare.length === 0 && campersUnit.length === 0 && (
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
  );
}

export default CamperCareNeedsAttentionList;
