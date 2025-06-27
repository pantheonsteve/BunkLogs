import { useState, useEffect, useCallback } from 'react';

/**
 * Custom hook for fetching and managing camper care data with filtering support
 * @param {string} camperCareId - The camper care staff ID
 * @param {string} date - The date in YYYY-MM-DD format
 * @param {object} filters - Filter parameters object
 * @param {string} authToken - Authentication token
 * @returns {object} { data, loading, error, refetch }
 */
export const useCamperCareData = (camperCareId, date, filters = {}, authToken) => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const fetchData = useCallback(async () => {
    if (!camperCareId || !date || !authToken) {
      return;
    }

    setLoading(true);
    setError(null);

    console.log('[useCamperCareData] Fetching data with filters:', filters);

    try {
      // Build query parameters from filters
      const params = new URLSearchParams();
      
      // Add only non-empty filters
      Object.entries(filters).forEach(([key, value]) => {
        if (value !== '' && value != null && value !== undefined) {
          params.append(key, value);
        }
      });

      // Construct the API URL
      const baseUrl = `${process.env.REACT_APP_API_BASE_URL || '/api'}/campercare/${camperCareId}/${date}/`;
      const url = params.toString() ? `${baseUrl}?${params}` : baseUrl;

      const response = await fetch(url, {
        method: 'GET',
        headers: {
          'Authorization': `Token ${authToken}`,
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const result = await response.json();
      setData(result);
    } catch (err) {
      console.error('Error fetching camper care data:', err);
      setError(err);
    } finally {
      setLoading(false);
    }
  }, [camperCareId, date, JSON.stringify(filters), authToken]);

  // Refetch data when dependencies change
  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Manual refetch function
  const refetch = useCallback(() => {
    fetchData();
  }, [fetchData]);

  return {
    data,
    loading,
    error,
    refetch,
  };
};

export default useCamperCareData;
