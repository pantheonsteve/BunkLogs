import React, { useState, useEffect } from 'react';
import { useAuth } from '../../auth/AuthContext';
import { Link } from 'react-router-dom';
import { useNavigate, useLocation } from 'react-router-dom';
import api from '../../api';
import { Home, Users, Calendar, ArrowRight, Loader2 } from 'lucide-react';

// Import utilities
import { adjustColorOpacity, getCssVariable } from '../../utils/Utils';

// Today's date constant - uses current date
const TODAY = new Date();

function BunkCard({ cabin, session, bunk_id, counselors }) {
  const location = useLocation();
  const [error, setError] = useState(null);
  const { user, isAuthenticated, loading, logout } = useAuth();
  const navigate = useNavigate();
  const email = useAuth().user?.email;
  const [userData, setUserData] = useState(null);
  const [bunkData, setBunkData] = useState(null);
  const [isFetchingData, setIsFetchingData] = useState(false);
  const [fetchingUserData, setFetchingUserData] = useState(false);

  console.log(counselors);

  useEffect(() => {
    const fetchBunkData = async () => {
      if (bunk_id) {
        setIsFetchingData(true);
        try {
          const response = await api.get(`/api/v1/bunk/${bunk_id}`);
          console.log(response.data);
          setBunkData(response.data);
        } catch (err) {
          setError(err.response?.data?.message || 'Failed to fetch bunk data');
          console.error('Error fetching bunk data:', err);
        } finally {
          setIsFetchingData(false);
        }
      }
    };

    fetchBunkData();
  }, [bunk_id]);

  console.log('Bunk data:', bunkData);

  // Format today's date as YYYY-MM-DD for the URL
  const formattedDate = TODAY.toISOString().split('T')[0];

  // Loading state
  if (isFetchingData) {
    return (
      <div className="relative col-span-full xl:col-span-4 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700/60 shadow-sm rounded-2xl overflow-hidden">
        <div className="flex items-center justify-center h-64">
          <div className="text-center">
            <Loader2 className="w-8 h-8 animate-spin text-blue-600 mx-auto mb-2" />
            <p className="text-sm text-gray-500 dark:text-gray-400">Loading bunk data...</p>
          </div>
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="relative col-span-full xl:col-span-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800/50 shadow-sm rounded-2xl overflow-hidden">
        <div className="flex items-center justify-center h-64 p-6">
          <div className="text-center">
            <div className="w-12 h-12 bg-red-100 dark:bg-red-900/50 rounded-full flex items-center justify-center mx-auto mb-3">
              <Home className="w-6 h-6 text-red-600 dark:text-red-400" />
            </div>
            <p className="text-sm text-red-600 dark:text-red-400 font-medium">Error loading bunk</p>
            <p className="text-xs text-red-500 dark:text-red-500 mt-1">{error}</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <Link 
      to={`/bunk/${bunk_id}/${formattedDate}`} 
      className="group relative col-span-full xl:col-span-4 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700/60 shadow-sm hover:shadow-lg transition-all duration-300 rounded-2xl overflow-hidden hover:scale-[1.02] hover:-translate-y-1"
    >
      {/* Gradient header */}
      <div className="h-20 bg-gradient-to-r from-blue-500 via-purple-500 to-indigo-600 relative">
        <div className="absolute inset-0 bg-black/10"></div>
        {/* Decorative pattern */}
        <div className="absolute top-0 right-0 w-32 h-32 transform translate-x-16 -translate-y-16">
          <div className="w-full h-full rounded-full bg-white/10"></div>
        </div>
        <div className="absolute top-2 right-2 w-16 h-16 transform translate-x-8 -translate-y-8">
          <div className="w-full h-full rounded-full bg-white/5"></div>
        </div>
      </div>

      {/* Content */}
      <div className="relative px-6 pb-6 -mt-8">
        {/* Icon container */}
        <div className="flex justify-center mb-4">
          <div className="w-16 h-16 bg-white dark:bg-gray-800 rounded-2xl shadow-lg border border-gray-100 dark:border-gray-700 flex items-center justify-center group-hover:scale-110 transition-transform duration-300">
            <Home className="w-8 h-8 text-blue-600 dark:text-blue-400" />
          </div>
        </div>

        {/* Unit badge */}
        <div className="flex justify-center mb-3">
          {bunkData?.unit?.name && (
            <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300">
              <Users className="w-3 h-3 mr-1" />
              {bunkData.unit.name}
            </span>
          )}
        </div>

        {/* Cabin name */}
        <div className="text-center mb-4">
          <h2 className="text-xl font-bold text-gray-900 dark:text-gray-100 mb-2 group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors">
            {bunkData ? `${bunkData.cabin?.name || 'No Cabin'}` : `${cabin}`}
          </h2>
          <div className="w-12 h-1 bg-gradient-to-r from-blue-500 to-purple-500 rounded-full mx-auto"></div>
        </div>

        {/* Session info */}
        <div className="text-center mb-6">
          {bunkData?.session?.name && (
            <div className="inline-flex items-center px-4 py-2 rounded-lg bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800/30">
              <Calendar className="w-4 h-4 text-amber-600 dark:text-amber-400 mr-2" />
              <span className="text-sm font-medium text-amber-700 dark:text-amber-300">
                {bunkData.session.name}
              </span>
            </div>
          )}
        </div>

        {/* Counselor List */}
        <div className="text-center mb-6">
          <h3 className="text-sm font-semibold text-gray-800 dark:text-gray-200 mb-2 tracking-wide uppercase">
            Counselors
          </h3>
          {bunkData?.counselors && bunkData.counselors.length > 0 ? (
            <ul className="flex flex-wrap justify-center gap-2">
              {bunkData.counselors.map((counselor, index) => (
                <li
                  key={index}
                  className="inline-flex items-center px-3 py-1 rounded-full bg-blue-50 dark:bg-blue-900/30 text-blue-800 dark:text-blue-200 text-xs font-medium shadow-sm border border-blue-100 dark:border-blue-800"
                >
                  <Users className="w-3 h-3 mr-1" />
                  {(counselor.first_name || '') + ' ' + (counselor.last_name || '')}
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-gray-500 dark:text-gray-400">No counselors assigned</p>
          )}
        </div>
        {counselors && counselors.length > 0 && (
          <div className="text-center mb-4">
            <div className="text-sm text-gray-500 dark:text-gray-400">
              {counselors.length} counselor{counselors.length !== 1 ? 's' : ''}
            </div>
          </div>
        )}

        {/* Action indicator */}
        <div className="flex items-center justify-center">
          <div className="inline-flex items-center text-sm font-medium text-blue-600 dark:text-blue-400 group-hover:text-blue-700 dark:group-hover:text-blue-300 transition-colors">
            View Details
            <ArrowRight className="w-4 h-4 ml-1 group-hover:translate-x-1 transition-transform" />
          </div>
        </div>
      </div>

      {/* Hover overlay */}
      <div className="absolute inset-0 bg-gradient-to-r from-blue-600/5 to-purple-600/5 opacity-0 group-hover:opacity-100 transition-opacity duration-300 pointer-events-none"></div>
    </Link>
  );
}

export default BunkCard;