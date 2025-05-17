import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { useAuth } from '../../auth/AuthContext';
import ErrorMessage from '../ErrorMessage';
import BunkTile from './BunkTile';
import LoadingSpinner from '../ui/LoadingSpinner';

const UserInfo = () => {
    const { user, isAuthenticated, loading, error, logout, setError } = useAuth();
    const navigate = useNavigate();
    const email = useAuth().user?.email;
    const [userData, setUserData] = useState(null);
    const [fetchingUserData, setFetchingUserData] = useState(false);
  
    // Fetch user data from API
    useEffect(() => {
      const fetchUserData = async () => {
        if (email) {
          setFetchingUserData(true);
          try {
            const response = await axios.get(`http://localhost:8000/api/v1/users/email/${email}`);
            setUserData(response.data);
          } catch (err) {
            setError(err.response?.data?.message || 'Failed to fetch user data');
            console.error('Error fetching user data:', err);
          } finally {
            setFetchingUserData(false);
          }
        }
      };
      
      fetchUserData();
    }, [email, setError]);

    // Redirect to signin if not authenticated
    useEffect(() => {
      if (!isAuthenticated && !loading) {
        navigate('/signin');
      }
    }, [isAuthenticated, loading, navigate]);

    useEffect(() => {
      const fetchSpecificUserData = async () => {
        if (isAuthenticated) {
          try {
            const response = await axios.get(`http://localhost:8000/api/v1/users/email/${email}`);
          } catch (err) {
            console.error('Error fetching specific user data:', err);
          }
        }
      };

      fetchSpecificUserData();
    }, [isAuthenticated]);
  
    if (loading || fetchingUserData) {
      return (
        <div style={{ 
          padding: '20px',
          maxWidth: '1200px',
          margin: '0 auto'
        }}>
            <LoadingSpinner />
          <p style={{ textAlign: 'center' }}>Loading dashboard...</p>
        </div>
      );
    }
  
    if (!isAuthenticated) {
      return null; // Will redirect via useEffect
    }
  
    return (
      <div style={{ 
        padding: '20px',
        maxWidth: '1200px',
        margin: '0 auto'
      }}>
  
        {error && (
          <ErrorMessage 
            message={error} 
            onDismiss={() => setError(null)} 
          />
        )}
        <div className="flex flex-col col-span-full bg-white dark:bg-gray-800 shadow-xs rounded-xl p-4">
            <div className="mb-4">
              {isAuthenticated && (
                <div className="flex items-center mb-2">
                  <div className="w-6 h-6 rounded-full shrink-0 bg-green-500 mr-3">
                    <svg className="w-6 h-6 fill-current text-white" viewBox="0 0 24 24">
                      <path d="M12 17a.833.833 0 01-.833-.833 3.333 3.333 0 00-3.334-3.334.833.833 0 110-1.666 3.333 3.333 0 003.334-3.334.833.833 0 111.666 0 3.333 3.333 0 003.334 3.334.833.833 0 110 1.666 3.333 3.333 0 00-3.334 3.334c0 .46-.373.833-.833.833z" />
                    </svg>
                  </div>
                  <h3 className="text-lg text-gray-800 dark:text-gray-100 font-semibold">User Info</h3>
                </div>
              )}
              <strong className="font-medium text-gray-800 dark:text-gray-100">{user?.name || user?.email} | Role: {userData?.role}</strong>
              {userData?.role === "Unit Head" && userData?.unit_name && (
                <div className="mt-4">
                  <h4 className="text-md text-gray-800 dark:text-gray-100 font-semibold">Unit: {userData.unit_name}</h4>
                  {userData.unit_bunks?.length > 0 ? (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-2">
                      {userData.unit_bunks.map((bunk) => (
                        <BunkTile key={bunk.id} cabin={bunk.cabin.name} session={bunk.session.name} bunk_id={bunk.id} counselors='{bunk?.counselors}'/>
                      ))}
                    </div>
                  ) : (
                    <div className="text-xs text-gray-500 dark:text-gray-400">No Bunks in Unit</div>
                  )}
                </div>
              )}
            </div>

            {console.log('User data:', userData)}
            
            {userData?.bunks ? (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {userData.bunks.map((bunk) => (
                  <BunkTile key={bunk.id} cabin={bunk.cabin} session={bunk.session} bunk_id={bunk.id} counselors='{bunk?.counselors}'/>
                ))}
              </div>
            ) : (
              <div className="text-xs text-gray-500 dark:text-gray-400">No Bunks Assigned</div>
            )}
        </div>
      </div>
    );
  };
  
  export default UserInfo;