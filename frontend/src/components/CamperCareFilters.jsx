import React, { useState, useEffect, useRef, useCallback } from 'react';
import { X, Filter } from 'lucide-react';

const CamperCareFilters = ({ 
  onFiltersChange, 
  bunks = [], 
  initialFilters = {},
  showFilters = false,
  onToggleFilters,
  className = '' 
}) => {
  const [filters, setFilters] = useState({
    bunk_id: '',
    unit_head_help: '',
    camper_care_help: '',
    social_score_min: '',
    social_score_max: '',
    behavior_score_min: '',
    behavior_score_max: '',
    participation_score_min: '',
    participation_score_max: '',
    ...initialFilters
  });

  // Use ref to track if this is the initial render
  const isInitialRender = useRef(true);

  // Notify parent when filters change (but not on initial render)
  useEffect(() => {
    if (isInitialRender.current) {
      isInitialRender.current = false;
      return;
    }
    onFiltersChange(filters);
  }, [filters]);

  const updateFilter = useCallback((key, value) => {
    setFilters(prev => ({
      ...prev,
      [key]: value
    }));
  }, []);

  const clearFilters = useCallback(() => {
    const clearedFilters = Object.keys(filters).reduce((acc, key) => {
      acc[key] = '';
      return acc;
    }, {});
    setFilters(clearedFilters);
  }, [filters]);

  // Don't render anything if filters panel is not shown
  if (!showFilters) {
    return null;
  }

  return (
    <div className={`bg-white dark:bg-gray-800 shadow-sm rounded-xl p-6 mb-8 ${className}`}>
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-medium text-gray-900 dark:text-white">Filters</h3>
        <div className="flex space-x-2">
          <button
            onClick={clearFilters}
            className="text-sm text-gray-600 hover:text-gray-800 dark:text-gray-400 dark:hover:text-gray-200"
          >
            Clear All
          </button>
          <button
            onClick={onToggleFilters}
            className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Bunk Filter */}
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            Bunk
          </label>
          <select
            value={filters.bunk_id}
            onChange={(e) => updateFilter('bunk_id', e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
          >
            <option value="">All Bunks</option>
            {bunks.map((bunk) => (
              <option key={bunk.id} value={bunk.id.toString()}>
                {bunk.cabin_name} - {bunk.session_name}
              </option>
            ))}
          </select>
        </div>

        {/* Unit Head Help Filter */}
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            Unit Head Help
          </label>
          <select
            value={filters.unit_head_help}
            onChange={(e) => updateFilter('unit_head_help', e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
          >
            <option value="">All</option>
            <option value="true">Help Requested</option>
            <option value="false">No Help Requested</option>
          </select>
        </div>

        {/* Camper Care Help Filter */}
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            Camper Care Help
          </label>
          <select
            value={filters.camper_care_help}
            onChange={(e) => updateFilter('camper_care_help', e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
          >
            <option value="">All</option>
            <option value="true">Help Requested</option>
            <option value="false">No Help Requested</option>
          </select>
        </div>

        {/* Social Score Min Filter */}
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            Social Score (Min)
          </label>
          <select
            value={filters.social_score_min}
            onChange={(e) => updateFilter('social_score_min', e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
          >
            <option value="">Any</option>
            {[1, 2, 3, 4, 5].map(score => (
              <option key={score} value={score}>{score}+</option>
            ))}
          </select>
        </div>

        {/* Social Score Max Filter */}
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            Social Score (Max)
          </label>
          <select
            value={filters.social_score_max}
            onChange={(e) => updateFilter('social_score_max', e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
          >
            <option value="">Any</option>
            {[1, 2, 3, 4, 5].map(score => (
              <option key={score} value={score}>{score} or less</option>
            ))}
          </select>
        </div>

        {/* Behavior Score Min Filter */}
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            Behavior Score (Min)
          </label>
          <select
            value={filters.behavior_score_min}
            onChange={(e) => updateFilter('behavior_score_min', e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
          >
            <option value="">Any</option>
            {[1, 2, 3, 4, 5].map(score => (
              <option key={score} value={score}>{score}+</option>
            ))}
          </select>
        </div>

        {/* Behavior Score Max Filter */}
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            Behavior Score (Max)
          </label>
          <select
            value={filters.behavior_score_max}
            onChange={(e) => updateFilter('behavior_score_max', e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
          >
            <option value="">Any</option>
            {[1, 2, 3, 4, 5].map(score => (
              <option key={score} value={score}>{score} or less</option>
            ))}
          </select>
        </div>

        {/* Participation Score Min Filter */}
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            Participation Score (Min)
          </label>
          <select
            value={filters.participation_score_min}
            onChange={(e) => updateFilter('participation_score_min', e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
          >
            <option value="">Any</option>
            {[1, 2, 3, 4, 5].map(score => (
              <option key={score} value={score}>{score}+</option>
            ))}
          </select>
        </div>

        {/* Participation Score Max Filter */}
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            Participation Score (Max)
          </label>
          <select
            value={filters.participation_score_max}
            onChange={(e) => updateFilter('participation_score_max', e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
          >
            <option value="">Any</option>
            {[1, 2, 3, 4, 5].map(score => (
              <option key={score} value={score}>{score} or less</option>
            ))}
          </select>
        </div>
      </div>
    </div>
  );
};

export default CamperCareFilters;