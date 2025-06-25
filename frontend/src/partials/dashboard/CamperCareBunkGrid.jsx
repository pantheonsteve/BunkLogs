import React, { useState, useEffect } from 'react';
import { useAuth } from '../../auth/AuthContext';
import api from '../../api';
import UnitHeadBunkCard from '../../components/bunklogs/UnitHeadBunkCard';
import { Loader2, AlertTriangle, Users, Home, Heart } from 'lucide-react';

function CamperCareBunkGrid({ selectedDate }) {
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);
  const [unitData, setUnitData] = useState(null);
  const { user, isAuthenticated } = useAuth();

  useEffect(() => {
    const fetchUnitData = async () => {
      if (!user?.id || user?.role !== 'Camper Care') {
        setError('Access denied. Only Camper Care team members can view this page.');
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
        
        console.log(`[CamperCareBunkGrid] Fetching data for date: ${dateToUse}`);
        const response = await api.get(`/api/v1/campercare/${user.id}/${dateToUse}/`);
        console.log('[CamperCareBunkGrid] API response:', response.data);
        
        // The API returns an array of units, but camper care typically manages one unit
        const units = response.data;
        if (units && units.length > 0) {
          // Use the first unit (or combine multiple units if needed)
          const primaryUnit = units[0];
          
          // If there are multiple units, combine their bunks
          if (units.length > 1) {
            const allBunks = units.flatMap(unit => unit.bunks || []);
            setUnitData({
              ...primaryUnit,
              name: units.length > 1 ? `${primaryUnit.name} (+${units.length - 1} more)` : primaryUnit.name,
              bunks: allBunks
            });
          } else {
            setUnitData(primaryUnit);
          }
        } else {
          setUnitData({ name: 'No Units', bunks: [] });
        }
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

  // Loading state
  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-64">
        <div className="text-center">
          <Loader2 className="w-8 h-8 animate-spin text-rose-600 mx-auto mb-4" />
          <p className="text-sm text-gray-500 dark:text-gray-400">Loading your assigned unit data...</p>
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
            className="px-4 py-2 bg-rose-600 text-white rounded-lg hover:bg-rose-700 transition-colors text-sm font-medium"
          >
            Try Again
          </button>
        </div>
      </div>
    );
  }

  // No data state
  if (!unitData || !unitData.bunks || unitData.bunks.length === 0) {
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
            There are no bunks assigned to your unit yet.
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
          <div className="w-12 h-12 bg-rose-100 dark:bg-rose-900/30 rounded-xl flex items-center justify-center">
            <Heart className="w-6 h-6 text-rose-600 dark:text-rose-400" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
              {unitData.name}
            </h1>
            <p className="text-gray-600 dark:text-gray-400">
              {unitData.bunks.length} bunk{unitData.bunks.length !== 1 ? 's' : ''} under your care
            </p>
          </div>
        </div>
      </div>

      {/* Stats overview */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-6">
        <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-100 dark:border-gray-700 p-4">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 bg-rose-100 dark:bg-rose-900/30 rounded-lg flex items-center justify-center">
              <Home className="w-5 h-5 text-rose-600 dark:text-rose-400" />
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
              <Heart className="w-5 h-5 text-purple-600 dark:text-purple-400" />
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                {unitData.bunks.reduce((total, bunk) => total + (bunk.campers?.length || 0), 0)}
              </p>
              <p className="text-sm text-gray-600 dark:text-gray-400">Total Campers</p>
            </div>
          </div>
        </div>
      </div>

      {/* Bunks grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {unitData.bunks.map((bunk) => (
          <UnitHeadBunkCard
            key={bunk.id}
            bunk={bunk}
            selectedDate={selectedDate}
          />
        ))}
      </div>
    </div>
  );
}

export default CamperCareBunkGrid;
