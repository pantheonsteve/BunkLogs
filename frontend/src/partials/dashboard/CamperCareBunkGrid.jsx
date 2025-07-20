import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { useAuth } from '../../auth/AuthContext';
import api from '../../api';
import UnitHeadBunkCard from '../../components/bunklogs/UnitHeadBunkCard';
import CamperCareBunkLogItem from '../../components/bunklogs/CamperCareBunkLogItem';
import CamperCareFilters from '../../components/CamperCareFilters';
import { Loader2, AlertTriangle, Users, Home, Heart, UserCheck, Clock, Baby, AlertCircle, UserX, Filter, Search, X } from 'lucide-react';
import GenericAvatar from '../../images/avatar-generic.png';

function CamperCareBunkGrid({ selectedDate }) {
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);
  const [unitData, setUnitData] = useState(null);
  const [allCampers, setAllCampers] = useState([]);
  const [filteredCampers, setFilteredCampers] = useState([]);
  const [campersNeedingAttention, setCampersNeedingAttention] = useState([]);
  const [activeTab, setActiveTab] = useState('overview'); // 'overview', 'logs', 'attention'
  const [filters, setFilters] = useState({});
  const [showFilters, setShowFilters] = useState(false);
  const { user, isAuthenticated } = useAuth();

  // Search states
  const [searchQuery, setSearchQuery] = useState('');
  const [searchSuggestions, setSearchSuggestions] = useState([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [selectedSuggestionIndex, setSelectedSuggestionIndex] = useState(-1);
  const searchInputRef = useRef(null);
  const suggestionsRef = useRef(null);

  // Memoize filters to prevent unnecessary re-renders
  const memoizedFilters = useMemo(() => filters, [JSON.stringify(filters)]);

  // Apply search and filters when campers or filters change
  useEffect(() => {
    let filtered = [...allCampers];

    // Apply search filter first if there's a search query
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter(camper => 
        camper.first_name.toLowerCase().includes(query) ||
        camper.last_name.toLowerCase().includes(query) ||
        `${camper.first_name} ${camper.last_name}`.toLowerCase().includes(query)
      );
    }

    // Apply other filters (this logic would depend on what filters are available in CamperCareFilters)
    // For now, I'll add basic filtering structure that can be expanded
    Object.entries(memoizedFilters).forEach(([key, value]) => {
      if (value !== '' && value != null && value !== undefined) {
        // Add specific filter logic here based on the filter keys
        // This would need to be customized based on what filters are available
      }
    });

    setFilteredCampers(filtered);

    // Update campers needing attention based on filtered results
    const needingAttention = filtered.filter(camper => {
      if (camper.bunk_log) {
        return camper.bunk_log.request_camper_care_help ||
               camper.bunk_log.request_unit_head_help ||
               camper.bunk_log.not_on_camp;
      }
      return false;
    });
    setCampersNeedingAttention(needingAttention);
  }, [allCampers, memoizedFilters, searchQuery]);

  // Generate search suggestions based on input
  useEffect(() => {
    if (!searchQuery.trim()) {
      setSearchSuggestions([]);
      setShowSuggestions(false);
      return;
    }

    const query = searchQuery.toLowerCase();
    const suggestions = [];
    const seen = new Set();

    // Get unique camper names from all campers
    allCampers.forEach(camper => {
      const fullName = `${camper.first_name} ${camper.last_name}`;
      const key = `${camper.first_name.toLowerCase()}_${camper.last_name.toLowerCase()}`;
      
      if (!seen.has(key) && (
        camper.first_name.toLowerCase().includes(query) ||
        camper.last_name.toLowerCase().includes(query) ||
        fullName.toLowerCase().includes(query)
      )) {
        suggestions.push({
          fullName,
          firstName: camper.first_name,
          lastName: camper.last_name,
          camperId: camper.id,
          bunkName: camper.bunk_name,
          unitName: camper.unit_name
        });
        seen.add(key);
      }
    });

    // Sort suggestions by relevance (exact match first, then starts with, then contains)
    suggestions.sort((a, b) => {
      const aFull = a.fullName.toLowerCase();
      const bFull = b.fullName.toLowerCase();
      const aFirst = a.firstName.toLowerCase();
      const bFirst = b.firstName.toLowerCase();
      const aLast = a.lastName.toLowerCase();
      const bLast = b.lastName.toLowerCase();
      
      // Exact matches first
      if (aFull === query) return -1;
      if (bFull === query) return 1;
      if (aFirst === query || aLast === query) return -1;
      if (bFirst === query || bLast === query) return 1;
      
      // Starts with matches
      if (aFull.startsWith(query) && !bFull.startsWith(query)) return -1;
      if (bFull.startsWith(query) && !aFull.startsWith(query)) return 1;
      if (aFirst.startsWith(query) && !bFirst.startsWith(query)) return -1;
      if (bFirst.startsWith(query) && !aFirst.startsWith(query)) return 1;
      if (aLast.startsWith(query) && !bLast.startsWith(query)) return -1;
      if (bLast.startsWith(query) && !aLast.startsWith(query)) return 1;
      
      // Alphabetical order for remaining
      return aFull.localeCompare(bFull);
    });

    setSearchSuggestions(suggestions.slice(0, 10)); // Limit to 10 suggestions
    setShowSuggestions(suggestions.length > 0);
    setSelectedSuggestionIndex(-1);
  }, [searchQuery, allCampers]);

  // Handle search input changes
  const handleSearchChange = (e) => {
    setSearchQuery(e.target.value);
  };

  // Handle search input key events
  const handleSearchKeyDown = (e) => {
    if (!showSuggestions || searchSuggestions.length === 0) return;

    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault();
        setSelectedSuggestionIndex(prev => 
          prev < searchSuggestions.length - 1 ? prev + 1 : 0
        );
        break;
      case 'ArrowUp':
        e.preventDefault();
        setSelectedSuggestionIndex(prev => 
          prev > 0 ? prev - 1 : searchSuggestions.length - 1
        );
        break;
      case 'Enter':
        e.preventDefault();
        if (selectedSuggestionIndex >= 0) {
          selectSuggestion(searchSuggestions[selectedSuggestionIndex]);
        }
        break;
      case 'Escape':
        setShowSuggestions(false);
        setSelectedSuggestionIndex(-1);
        break;
    }
  };

  // Select a suggestion
  const selectSuggestion = (suggestion) => {
    setSearchQuery(suggestion.fullName);
    setShowSuggestions(false);
    setSelectedSuggestionIndex(-1);
    searchInputRef.current?.blur();
  };

  // Clear search
  const clearSearch = () => {
    setSearchQuery('');
    setShowSuggestions(false);
    setSelectedSuggestionIndex(-1);
  };

  // Handle clicking outside search suggestions
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (suggestionsRef.current && !suggestionsRef.current.contains(event.target) &&
          searchInputRef.current && !searchInputRef.current.contains(event.target)) {
        setShowSuggestions(false);
        setSelectedSuggestionIndex(-1);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Handle filter changes - MUST be declared before any conditional returns
  const handleFiltersChange = useCallback((newFilters) => {
    setFilters(newFilters);
  }, []);

  // Get all bunks for filter options
  const allBunks = unitData?.bunks || [];

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
        
        console.log(`[CamperCareBunkGrid] Fetching data for date: ${dateToUse}`, {
          filters: memoizedFilters,
          hasFilters: Object.values(memoizedFilters).some(v => v !== '' && v != null)
        });
        
        // Build query parameters from filters
        const params = new URLSearchParams();
        Object.entries(memoizedFilters).forEach(([key, value]) => {
          if (value !== '' && value != null && value !== undefined) {
            params.append(key, value);
          }
        });
        
        // Construct the API URL with filters
        const baseUrl = `/api/v1/campercare/${user.id}/${dateToUse}/`;
        const url = params.toString() ? `${baseUrl}?${params}` : baseUrl;
        
        const response = await api.get(url);
        console.log('[CamperCareBunkGrid] API response:', response.data);
        
        // The API returns an array of units, but camper care typically manages one unit
        const units = response.data;
        if (units && units.length > 0) {
          // Use the first unit (or combine multiple units if needed)
          const primaryUnit = units[0];
          
          // Collect all campers from all bunks across all units
          const allCampersArray = [];
          const campersNeedingAttentionArray = [];
          
          units.forEach(unit => {
            unit.bunks.forEach(bunk => {
              if (bunk.campers && bunk.campers.length > 0) {
                bunk.campers.forEach(camper => {
                  // Add bunk and unit context to camper data
                  const camperWithContext = {
                    ...camper,
                    bunk_name: bunk.cabin_name,
                    session_name: bunk.session_name,
                    unit_name: unit.name,
                    bunk_id: bunk.id
                  };
                  
                  allCampersArray.push(camperWithContext);
                  
                  // Check if camper needs attention
                  if (camper.bunk_log) {
                    const needsAttention = 
                      camper.bunk_log.request_camper_care_help ||
                      camper.bunk_log.request_unit_head_help ||
                      camper.bunk_log.not_on_camp;
                    
                    if (needsAttention) {
                      campersNeedingAttentionArray.push(camperWithContext);
                    }
                  }
                });
              }
            });
          });
          
          setAllCampers(allCampersArray);
          setFilteredCampers(allCampersArray); // Initialize filtered campers
          setCampersNeedingAttention(campersNeedingAttentionArray);
          
          // If there are multiple units, combine their bunks
          if (units.length > 1) {
            // Add unit_name to each bunk
            const allBunks = units.flatMap(unit =>
              (unit.bunks || []).map(bunk => ({ ...bunk, unit_name: unit.name }))
            );
            setUnitData({
              ...primaryUnit,
              name: units.length > 1 ? `${primaryUnit.name} (+${units.length - 1} more)` : primaryUnit.name,
              bunks: allBunks
            });
          } else {
            // Add unit_name to each bunk for single unit as well
            setUnitData({
              ...primaryUnit,
              bunks: (primaryUnit.bunks || []).map(bunk => ({ ...bunk, unit_name: primaryUnit.name }))
            });
          }
        } else {
          setUnitData({ name: 'No Units', bunks: [] });
          setAllCampers([]);
          setFilteredCampers([]); // Initialize filtered campers
          setCampersNeedingAttention([]);
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
  }, [user?.id, user?.role, selectedDate, memoizedFilters]);

  // Helper functions
  const getScoreBackgroundColor = (score) => {
    if (!score) return "bg-gray-100";
    
    const scoreNum = parseInt(score);
    if (scoreNum == 1) return 'bg-[#e86946]';
    if (scoreNum == 2) return 'bg-[#de8d6f]';
    if (scoreNum == 3) return 'bg-[#e5e825]';
    if (scoreNum == 4) return 'bg-[#90d258]';
    if (scoreNum == 5) return 'bg-[#18d128]';
    return "bg-red-100";
  };

  const getHelpRequestedIcon = (help_requested) => {
    if (help_requested === true) {
      return (
        <div className="flex items-center justify-center">
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="orange" className="size-6">
            <path d="M10.5 1.875a1.125 1.125 0 0 1 2.25 0v8.219c.517.162 1.02.382 1.5.659V3.375a1.125 1.125 0 0 1 2.25 0v10.937a4.505 4.505 0 0 0-3.25 2.373 8.963 8.963 0 0 1 4-.935A.75.75 0 0 0 18 15v-2.266a3.368 3.368 0 0 1 .988-2.37 1.125 1.125 0 0 1 1.591 1.59 1.118 1.118 0 0 0-.329.79v3.006h-.005a6 6 0 0 1-1.752 4.007l-1.736 1.736a6 6 0 0 1-4.242 1.757H10.5a7.5 7.5 0 0 1-7.5-7.5V6.375a1.125 1.125 0 0 1 2.25 0v5.519c.46-.452.965-.832 1.5-1.141V3.375a1.125 1.125 0 0 1 2.25 0v6.526c.495-.1.997-.151 1.5-.151V1.875Z" />
          </svg>
        </div>
      );
    }
    return null;
  };

  const getCampersWithLogs = () => {
    return filteredCampers.filter(camper => camper.bunk_log);
  };

  const getCampersNotOnCamp = () => {
    return filteredCampers.filter(camper => camper.bunk_log?.not_on_camp);
  };

  const getCampersRequestingCamperCare = () => {
    return filteredCampers.filter(camper => camper.bunk_log?.request_camper_care_help);
  };

  const getCampersRequestingUnitHeadHelp = () => {
    return filteredCampers.filter(camper => camper.bunk_log?.request_unit_head_help);
  };

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
        <div className="flex items-center justify-between">
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
          <button
            onClick={() => setShowFilters(!showFilters)}
            className="btn bg-white dark:bg-gray-800 border-gray-200 dark:border-gray-700/60 hover:border-gray-300 dark:hover:border-gray-600 text-gray-800 dark:text-gray-300"
          >
            <Filter className="w-4 h-4 mr-2" />
            Filters
          </button>
        </div>
      </div>

      {/* Search Bar */}
      <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-sm border border-gray-100 dark:border-gray-700 p-6">
        <div className="relative">
          <div className="flex items-center">
            <div className="relative flex-1 max-w-md">
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                <Search className="h-5 w-5 text-gray-400" />
              </div>
              <input
                ref={searchInputRef}
                type="text"
                placeholder="Search campers by name..."
                value={searchQuery}
                onChange={handleSearchChange}
                onKeyDown={handleSearchKeyDown}
                onFocus={() => searchQuery && setShowSuggestions(searchSuggestions.length > 0)}
                className="block w-full pl-10 pr-10 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400 focus:ring-2 focus:ring-rose-500 focus:border-transparent"
              />
              {searchQuery && (
                <div className="absolute inset-y-0 right-0 pr-3 flex items-center">
                  <button
                    onClick={clearSearch}
                    className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
                  >
                    <X className="h-4 w-4" />
                  </button>
                </div>
              )}
            </div>
            {searchQuery && (
              <div className="ml-4 text-sm text-gray-600 dark:text-gray-400">
                {filteredCampers.length} result{filteredCampers.length !== 1 ? 's' : ''} found
              </div>
            )}
          </div>

          {/* Search Suggestions Dropdown */}
          {showSuggestions && searchSuggestions.length > 0 && (
            <div 
              ref={suggestionsRef}
              className="absolute z-10 mt-1 w-full max-w-md bg-white dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-md shadow-lg max-h-60 overflow-y-auto"
            >
              {searchSuggestions.map((suggestion, index) => (
                <div
                  key={`${suggestion.camperId}-${suggestion.fullName}`}
                  onClick={() => selectSuggestion(suggestion)}
                  className={`px-4 py-3 cursor-pointer border-b border-gray-100 dark:border-gray-600 last:border-b-0 ${
                    index === selectedSuggestionIndex
                      ? 'bg-rose-50 dark:bg-rose-900/20 text-rose-900 dark:text-rose-100'
                      : 'hover:bg-gray-50 dark:hover:bg-gray-600 text-gray-900 dark:text-white'
                  }`}
                >
                  <div className="flex justify-between items-center">
                    <div>
                      <div className="font-medium">{suggestion.fullName}</div>
                      <div className="text-sm text-gray-500 dark:text-gray-400">
                        {suggestion.bunkName} • {suggestion.unitName} • ID: {suggestion.camperId}
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Filters Panel */}
      <CamperCareFilters
        onFiltersChange={handleFiltersChange}
        bunks={allBunks}
        initialFilters={filters}
        showFilters={showFilters}
        onToggleFilters={() => setShowFilters(!showFilters)}
      />

      {/* Navigation tabs */}
      <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-sm border border-gray-100 dark:border-gray-700">
        <div className="flex border-b border-gray-100 dark:border-gray-700">
          <button
            onClick={() => setActiveTab('overview')}
            className={`px-6 py-4 text-sm font-medium border-b-2 ${
              activeTab === 'overview'
                ? 'border-rose-500 text-rose-600 dark:text-rose-400'
                : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'
            }`}
          >
            Bunk Overview
          </button>
          <button
            onClick={() => setActiveTab('logs')}
            className={`px-6 py-4 text-sm font-medium border-b-2 ${
              activeTab === 'logs'
                ? 'border-rose-500 text-rose-600 dark:text-rose-400'
                : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'
            }`}
          >
            All Bunk Logs
          </button>
          <button
            onClick={() => setActiveTab('attention')}
            className={`px-6 py-4 text-sm font-medium border-b-2 ${
              activeTab === 'attention'
                ? 'border-rose-500 text-rose-600 dark:text-rose-400'
                : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'
            }`}
          >
            Needs Attention ({campersNeedingAttention.length})
          </button>
        </div>
      </div>

      {/* Stats overview */}
      <div className="grid grid-cols-2 lg:grid-cols-5 gap-4 mb-6">
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
              <Baby className="w-5 h-5 text-purple-600 dark:text-purple-400" />
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                {filteredCampers.length}
              </p>
              <p className="text-sm text-gray-600 dark:text-gray-400">
                {searchQuery ? 'Filtered' : 'Total'} Campers
                {searchQuery && ` (${allCampers.length} total)`}
              </p>
            </div>
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-100 dark:border-gray-700 p-4">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 bg-green-100 dark:bg-green-900/30 rounded-lg flex items-center justify-center">
              <UserCheck className="w-5 h-5 text-green-600 dark:text-green-400" />
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                {getCampersWithLogs().length}
              </p>
              <p className="text-sm text-gray-600 dark:text-gray-400">With Logs</p>
            </div>
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-100 dark:border-gray-700 p-4">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 bg-orange-100 dark:bg-orange-900/30 rounded-lg flex items-center justify-center">
              <AlertCircle className="w-5 h-5 text-orange-600 dark:text-orange-400" />
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                {campersNeedingAttention.length}
              </p>
              <p className="text-sm text-gray-600 dark:text-gray-400">Need Attention</p>
            </div>
          </div>
        </div>
      </div>

      {/* Tab content */}
      {activeTab === 'overview' && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {unitData.bunks.map((bunk) => (
            <UnitHeadBunkCard
              key={bunk.id}
              bunk={bunk}
              selectedDate={selectedDate}
            />
          ))}
        </div>
      )}

      {activeTab === 'logs' && (
        <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-sm border border-gray-100 dark:border-gray-700">
          <div className="p-6">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
              All Bunk Logs
            </h3>
            {getCampersWithLogs().length > 0 ? (
              <div className="overflow-x-auto">
                <table className="table-auto w-full">
                  <thead className="text-xs uppercase text-gray-400 dark:text-gray-500 bg-gray-50 dark:bg-gray-700/50">
                    <tr>
                      <th className="px-4 py-3 text-left font-semibold">Camper</th>
                      <th className="px-4 py-3 text-center font-semibold">Date</th>
                      <th className="px-4 py-3 text-center font-semibold">Social</th>
                      <th className="px-4 py-3 text-center font-semibold">Behavior</th>
                      <th className="px-4 py-3 text-center font-semibold">Participation</th>
                      <th className="px-4 py-3 text-center font-semibold">Care Help</th>
                      <th className="px-4 py-3 text-center font-semibold">Unit Help</th>
                      <th className="px-4 py-3 text-center font-semibold"></th>
                    </tr>
                  </thead>
                  {getCampersWithLogs().map((camper, index) => (
                    <CamperCareBunkLogItem
                      key={`${camper.id}-${index}`}
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
                      camper_care_help={camper.bunk_log.request_camper_care_help}
                      unit_head_help={camper.bunk_log.request_unit_head_help}
                      description={camper.bunk_log.description}
                      counselor_first_name={camper.bunk_log.counselor_first_name}
                      counselor_last_name={camper.bunk_log.counselor_last_name}
                    />
                  ))}
                </table>
              </div>
            ) : (
              <div className="text-center py-8">
                <Clock className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                <p className="text-gray-500 dark:text-gray-400">No bunk logs found for today</p>
              </div>
            )}
          </div>
        </div>
      )}

      {activeTab === 'attention' && (
        <div className="space-y-6">
          {/* Campers not on camp */}
          {getCampersNotOnCamp().length > 0 && (
            <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-sm border border-red-200 dark:border-red-800">
              <div className="p-6">
                <div className="flex items-center space-x-3 mb-4">
                  <div className="w-10 h-10 bg-red-100 dark:bg-red-900/30 rounded-lg flex items-center justify-center">
                    <UserX className="w-5 h-5 text-red-600 dark:text-red-400" />
                  </div>
                  <div>
                    <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                      Not On Camp ({getCampersNotOnCamp().length})
                    </h3>
                    <p className="text-sm text-gray-600 dark:text-gray-400">
                      Campers who are currently not on camp
                    </p>
                  </div>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {getCampersNotOnCamp().map((camper, index) => (
                    <div key={`not-on-camp-${camper.id}-${index}`} className="bg-red-50 dark:bg-red-900/20 rounded-lg p-4 border border-red-200 dark:border-red-800">
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
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* Campers requesting camper care help */}
          {getCampersRequestingCamperCare().length > 0 && (
            <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-sm border border-orange-200 dark:border-orange-800">
              <div className="p-6">
                <div className="flex items-center space-x-3 mb-4">
                  <div className="w-10 h-10 bg-orange-100 dark:bg-orange-900/30 rounded-lg flex items-center justify-center">
                    <Heart className="w-5 h-5 text-orange-600 dark:text-orange-400" />
                  </div>
                  <div>
                    <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                      Camper Care Help Requested ({getCampersRequestingCamperCare().length})
                    </h3>
                    <p className="text-sm text-gray-600 dark:text-gray-400">
                      Campers who need camper care attention
                    </p>
                  </div>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {getCampersRequestingCamperCare().map((camper, index) => {
                    // Build the date string in YYYY-MM-DD format
                    const dateStr = selectedDate
                      ? `${selectedDate.getFullYear()}-${String(selectedDate.getMonth() + 1).padStart(2, '0')}-${String(selectedDate.getDate()).padStart(2, '0')}`
                      : new Date().toISOString().split('T')[0];
                    // Build the URL to the camper's page for this date
                    const camperUrl = `/camper/${camper.id}/${dateStr}`;
                    return (
                      <a
                        key={`care-help-${camper.id}-${index}`}
                        href={camperUrl}
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
                                <span
                                  dangerouslySetInnerHTML={{ __html: camper.bunk_log.description }}
                                />
                              </p>
                            )}
                          </div>
                        </div>
                      </a>
                    );
                  })}
                </div>
              </div>
            </div>
          )}
          {getCampersRequestingUnitHeadHelp().length > 0 && (
            <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-sm border border-yellow-200 dark:border-yellow-800">
              <div className="p-6">
                <div className="flex items-center space-x-3 mb-4">
                  <div className="w-10 h-10 bg-yellow-100 dark:bg-yellow-900/30 rounded-lg flex items-center justify-center">
                    <UserCheck className="w-5 h-5 text-yellow-600 dark:text-yellow-400" />
                  </div>
                  <div>
                    <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                      Unit Head Help Requested ({getCampersRequestingUnitHeadHelp().length})
                    </h3>
                    <p className="text-sm text-gray-600 dark:text-gray-400">
                      Campers who need unit head attention
                    </p>
                  </div>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {getCampersRequestingUnitHeadHelp().map((camper, index) => {
                    // Build the date string in YYYY-MM-DD format
                    const dateStr = selectedDate
                      ? `${selectedDate.getFullYear()}-${String(selectedDate.getMonth() + 1).padStart(2, '0')}-${String(selectedDate.getDate()).padStart(2, '0')}`
                      : new Date().toISOString().split('T')[0];
                    // Build the URL to the camper's page for this date
                    const camperUrl = `/camper/${camper.id}/${dateStr}`;
                    return (
                      <a
                        key={`unit-help-${camper.id}-${index}`}
                        href={camperUrl}
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
                                <span
                                  dangerouslySetInnerHTML={{ __html: camper.bunk_log.description }}
                                />
                              </p>
                            )}
                          </div>
                        </div>
                      </a>
                    );
                  })}
                </div>
              </div>
            </div>
          )}

          {/* Show message if no campers need attention */}
          {campersNeedingAttention.length === 0 && (
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
      )}
    </div>
  );
}

export default CamperCareBunkGrid;
