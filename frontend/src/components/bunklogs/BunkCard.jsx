import React, { use } from 'react';
import { useState } from 'react';
import { useAuth } from '../../auth/AuthContext';
import { Link } from 'react-router-dom';
import { useNavigate } from 'react-router-dom';
import { useLocation } from 'react-router-dom';
import { useEffect } from 'react';
import axios from 'axios';

// Import utilities
import { adjustColorOpacity, getCssVariable } from '../../utils/Utils';

// Today's date constant - uses current date
const TODAY = new Date();

function BunkCard({ cabin, session, bunk_id, counselors}) {
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
          const response = await axios.get(`http://localhost:8000/api/v1/bunk/${bunk_id}`);
          console.log(response.data);
          setBunkData(response.data); // Store the response data in state
        } catch (err) {
          setError(err.response?.data?.message || 'Failed to fetch bunk data');
          console.error('Error fetching bunk data:', err);
        } finally {
          setIsFetchingData(false);
        }
      }
    }

    fetchBunkData();
  }, [bunk_id]);

  console.log('Bunk data:', bunkData);

  // Format today's date as YYYY-MM-DD for the URL
  const formattedDate = TODAY.toISOString().split('T')[0];

  return (
    <Link to={`/bunk/${bunk_id}/${formattedDate}`} className="relative col-span-full xl:col-span-4 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700/60 shadow-xs rounded-lg">
    <div className="flex flex-col col-span-full sm:col-span-6 xl:col-span-4 bg-white dark:bg-gray-800 shadow-xs rounded-xl">
      <div className="px-5 pt-2 pb-2">
        <div className="flex justify-between mb-1">
          <div className="text-xs font-semibold text-gray-400 dark:text-gray-500 uppercase">
            {bunkData && (
              <span className="text-blue-300">{bunkData.unit.name}</span>
            )}
          </div>
          <div className="text-xs font-semibold text-gray-400 dark:text-gray-500 uppercase">
            {bunkData && (
              <span className="text-yellow-300">{bunkData.session.name}</span>
            )}
          </div>
        </div>
        <header className="justify-between items-start mb-2 text-center">
          <h2 className="text-lg font-semibold text-gray-800 dark:text-gray-100 mb-2 text-center">
            {bunkData ? `${bunkData.cabin?.name || 'No Cabin'}` : `${cabin}`}
          </h2>
        </header>
        {isFetchingData ? (
          <div className="text-sm text-gray-500">Loading bunk data...</div>
        ) : (
          <>
            {bunkData && (
              <div className="space-y-2">
                {bunkData.counselors && bunkData.counselors.length > 0 && (
                  <div className="mt-2 text-center">
                    <div className="text-xs font-semibold text-gray-400 dark:text-gray-500 uppercase mb-1">Counselors</div>
                    {bunkData.counselors.map((counselor, index) => (
                      <div key={counselor.id} className="text-sm text-blue-400 dark:text-gray-300">
                        {counselor.first_name} {counselor.last_name}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
            {!bunkData && !error && (
              <>
                <div className="text-xs font-semibold text-gray-400 dark:text-gray-500 uppercase mb-1">Bunk ID</div>
                <div className="text-xs font-semibold text-gray-400 dark:text-gray-500 uppercase mb-1">{bunk_id}</div>
                <div className="text-xs font-semibold text-gray-400 dark:text-gray-500 uppercase mb-1">{counselors}</div>
              </>
            )}
            {error && (
              <div className="text-sm text-red-500">{error}</div>
            )}
          </>
        )}
      </div>
    </div>
    </Link>
  );
}

export default BunkCard;
