import React, { useState, useEffect, useCallback } from 'react';
import { Calendar, Users, AlertTriangle, TrendingUp, Loader2, Filter, Download, ChevronLeft, ChevronRight, X } from 'lucide-react';
import CamperCareFilters from './CamperCareFilters';
import { useCamperCareData } from '../hooks/useCamperCareData'; // Custom hook for API calls

const CamperCareDashboard = ({ 
  camperCareId, 
  authToken,
  className = '' 
}) => {
  const [selectedDate, setSelectedDate] = useState(
    new Date().toISOString().split('T')[0] // Today's date
  );
  const [filters, setFilters] = useState({});
  const [searchTerm, setSearchTerm] = useState('');
  const [showFilters, setShowFilters] = useState(false);

  // Custom hook for fetching camper care data
  const { 
    data: camperData, 
    loading, 
    error, 
    refetch 
  } = useCamperCareData(camperCareId, selectedDate, filters, authToken);

  // Filter campers by search term
  const filteredCamperData = React.useMemo(() => {
    if (!camperData || !searchTerm) return camperData;

    return camperData.map(unit => ({
      ...unit,
      bunks: unit.bunks.map(bunk => ({
        ...bunk,
        campers: bunk.campers.filter(camper => 
          `${camper.first_name} ${camper.last_name}`
            .toLowerCase()
            .includes(searchTerm.toLowerCase())
        )
      })).filter(bunk => bunk.campers.length > 0)
    })).filter(unit => unit.bunks.length > 0);
  }, [camperData, searchTerm]);

  // Calculate statistics
  const stats = React.useMemo(() => {
    if (!filteredCamperData) return { totalCampers: 0, totalBunks: 0, helpRequests: 0, averageScores: {} };

    let totalCampers = 0;
    let totalBunks = 0;
    let helpRequests = 0;
    let scores = { social: [], behavior: [], participation: [] };

    filteredCamperData.forEach(unit => {
      unit.bunks.forEach(bunk => {
        if (bunk.campers.length > 0) totalBunks++;
        
        bunk.campers.forEach(camper => {
          totalCampers++;
          
          if (camper.bunk_log) {
            const log = camper.bunk_log;
            if (log.request_unit_head_help || log.request_camper_care_help) {
              helpRequests++;
            }
            
            if (log.social_score) scores.social.push(log.social_score);
            if (log.behavior_score) scores.behavior.push(log.behavior_score);
            if (log.participation_score) scores.participation.push(log.participation_score);
          }
        });
      });
    });

    const calculateAverage = (arr) => arr.length > 0 ? (arr.reduce((a, b) => a + b, 0) / arr.length).toFixed(1) : '—';

    return {
      totalCampers,
      totalBunks,
      helpRequests,
      averageScores: {
        social: calculateAverage(scores.social),
        behavior: calculateAverage(scores.behavior),
        participation: calculateAverage(scores.participation)
      }
    };
  }, [filteredCamperData]);

  // Get all bunks for filter options
  const allBunks = React.useMemo(() => {
    if (!camperData) return [];
    return camperData.flatMap(unit => unit.bunks);
  }, [camperData]);

  const handleFiltersChange = useCallback((newFilters) => {
    setFilters(newFilters);
  }, []);

  const handleDateChange = (newDate) => {
    setSelectedDate(newDate);
  };

  const navigateDate = (direction) => {
    const currentDate = new Date(selectedDate);
    const newDate = new Date(currentDate);
    newDate.setDate(currentDate.getDate() + (direction === 'next' ? 1 : -1));
    const year = newDate.getFullYear();
    const month = String(newDate.getMonth() + 1).padStart(2, '0');
    const day = String(newDate.getDate()).padStart(2, '0');
    setSelectedDate(`${year}-${month}-${day}`);
  };

  const formatDisplayDate = (dateString) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', { 
      weekday: 'long', 
      year: 'numeric', 
      month: 'long', 
      day: 'numeric' 
    });
  };

  const exportToCSV = () => {
    console.log('Export to CSV functionality to be implemented');
    // TODO: Implement CSV export
  };

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
        <div className="bg-white dark:bg-gray-800 shadow-sm rounded-xl p-6">
          <div className="text-center text-red-600 dark:text-red-400">
            <AlertTriangle className="h-8 w-8 mx-auto mb-2" />
            <p>Error loading camper care data: {error.message}</p>
            <button
              onClick={() => refetch()}
              className="mt-4 px-4 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600"
            >
              Try Again
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={`min-h-screen bg-gray-50 dark:bg-gray-900 ${className}`}>
      <div className="max-w-7xl mx-auto py-8 px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="bg-white dark:bg-gray-800 shadow-sm rounded-xl p-6 mb-8">
          <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
            <div>
              <h1 className="text-3xl font-bold text-gray-900 dark:text-white">Camper Care Dashboard</h1>
              <p className="text-gray-600 dark:text-gray-400">
                Monitor and filter camper progress and support needs
              </p>
            </div>
            
            <div className="flex items-center gap-4">
              <button
                onClick={() => setShowFilters(!showFilters)}
                className="btn bg-white dark:bg-gray-800 border-gray-200 dark:border-gray-700/60 hover:border-gray-300 dark:hover:border-gray-600 text-gray-800 dark:text-gray-300"
              >
                <Filter className="w-4 h-4 mr-2" />
                Filters
              </button>
              <button
                onClick={exportToCSV}
                className="btn bg-white dark:bg-gray-800 border-gray-200 dark:border-gray-700/60 hover:border-gray-300 dark:hover:border-gray-600 text-gray-800 dark:text-gray-300"
                disabled={!filteredCamperData || filteredCamperData.length === 0}
              >
                <Download className="w-4 h-4 mr-2" />
                Export CSV
              </button>
            </div>
          </div>
        </div>

        {/* Date Navigation */}
        <div className="bg-white dark:bg-gray-800 shadow-sm rounded-xl p-6 mb-8">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <button
                onClick={() => navigateDate('prev')}
                className="p-2 rounded-lg border border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700"
              >
                <ChevronLeft className="w-4 h-4" />
              </button>
              
              <div className="flex items-center space-x-3">
                <Calendar className="w-5 h-5 text-gray-400" />
                <input
                  type="date"
                  value={selectedDate}
                  onChange={(e) => handleDateChange(e.target.value)}
                  className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                />
              </div>
              
              <button
                onClick={() => navigateDate('next')}
                className="p-2 rounded-lg border border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700"
              >
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
            
            <div className="flex items-center gap-4">
              <div className="text-sm text-gray-600 dark:text-gray-400">
                {formatDisplayDate(selectedDate)}
              </div>
              <button 
                onClick={() => refetch()}
                disabled={loading}
                className="px-4 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600 disabled:opacity-50"
              >
                {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Refresh'}
              </button>
            </div>
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

        {/* Statistics Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-6 mb-8">
          <StatCard
            title="Total Campers"
            value={stats.totalCampers}
            icon={<Users className="h-4 w-4" />}
            loading={loading}
          />
          <StatCard
            title="Active Bunks"
            value={stats.totalBunks}
            icon={<Users className="h-4 w-4" />}
            loading={loading}
          />
          <StatCard
            title="Help Requests"
            value={stats.helpRequests}
            icon={<AlertTriangle className="h-4 w-4" />}
            variant={stats.helpRequests > 0 ? "destructive" : "default"}
            loading={loading}
          />
          <StatCard
            title="Avg Social"
            value={stats.averageScores.social}
            icon={<TrendingUp className="h-4 w-4" />}
            loading={loading}
          />
          <StatCard
            title="Avg Behavior"
            value={stats.averageScores.behavior}
            icon={<TrendingUp className="h-4 w-4" />}
            loading={loading}
          />
        </div>

        {/* Search */}
        <div className="bg-white dark:bg-gray-800 shadow-sm rounded-xl p-6 mb-8">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Search Campers</h2>
            <div className="text-sm text-gray-500 dark:text-gray-400">
              {stats.totalCampers} results
            </div>
          </div>
          <input
            type="text"
            placeholder="Search by camper name..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
          />
        </div>

        {/* Camper Data Grid */}
        {loading ? (
          <div className="bg-white dark:bg-gray-800 shadow-sm rounded-xl p-6">
            <div className="flex items-center justify-center">
              <Loader2 className="h-8 w-8 animate-spin mr-2" />
              <span className="text-gray-600 dark:text-gray-400">Loading camper data...</span>
            </div>
          </div>
        ) : (
          <CamperDataGrid data={filteredCamperData} />
        )}
      </div>
    </div>
  );
};

// Statistics Card Component
const StatCard = ({ title, value, icon, variant = "default", loading }) => (
  <div className="bg-white dark:bg-gray-800 shadow-sm rounded-xl p-6">
    <div className="flex items-center">
      <div className="flex-shrink-0">
        <div className={`w-8 h-8 flex items-center justify-center rounded-lg ${
          variant === "destructive" ? "bg-red-100 text-red-600 dark:bg-red-900 dark:text-red-400" : 
          "bg-blue-100 text-blue-600 dark:bg-blue-900 dark:text-blue-400"
        }`}>
          {icon}
        </div>
      </div>
      <div className="ml-4">
        <p className="text-sm font-medium text-gray-600 dark:text-gray-400">{title}</p>
        <p className={`text-2xl font-semibold ${
          variant === "destructive" ? "text-red-600 dark:text-red-400" : "text-gray-900 dark:text-white"
        }`}>
          {loading ? "—" : value}
        </p>
      </div>
    </div>
  </div>
);

// Camper Data Grid Component
const CamperDataGrid = ({ data }) => {
  if (!data || data.length === 0) {
    return (
      <div className="bg-white dark:bg-gray-800 shadow-sm rounded-xl p-6">
        <div className="text-center text-gray-500 dark:text-gray-400">
          <Users className="h-8 w-8 mx-auto mb-2" />
          <p>No campers found matching the current filters.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {data.map(unit => (
        <div key={unit.id} className="bg-white dark:bg-gray-800 shadow-sm rounded-xl">
          <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2">
                <Users className="h-5 w-5" />
                {unit.name}
              </h3>
              <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-200">
                {unit.bunks.reduce((total, bunk) => total + bunk.campers.length, 0)} campers
              </span>
            </div>
          </div>
          <div className="p-6">
            <div className="space-y-4">
              {unit.bunks.map(bunk => (
                <BunkCard key={bunk.id} bunk={bunk} />
              ))}
            </div>
          </div>
        </div>
      ))}
    </div>
  );
};

// Individual Bunk Card Component
const BunkCard = ({ bunk }) => (
  <div className="border border-gray-200 dark:border-gray-700 rounded-lg border-l-4 border-l-blue-500">
    <div className="px-4 py-3 border-b border-gray-200 dark:border-gray-700">
      <div className="flex justify-between items-center">
        <h4 className="text-lg font-medium text-gray-900 dark:text-white">
          {bunk.cabin_name}
        </h4>
        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-200">
          {bunk.campers.length} campers
        </span>
      </div>
      <p className="text-sm text-gray-600 dark:text-gray-400">{bunk.session_name}</p>
    </div>
    <div className="p-4">
      <div className="space-y-3">
        {bunk.campers.map(camper => (
          <CamperRow key={camper.id} camper={camper} />
        ))}
      </div>
    </div>
  </div>
);

// Individual Camper Row Component
const CamperRow = ({ camper }) => {
  const log = camper.bunk_log;
  
  return (
    <div className="flex items-center justify-between p-3 border border-gray-200 dark:border-gray-700 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors">
      <div className="flex items-center gap-3">
        <div className="w-8 h-8 bg-blue-100 dark:bg-blue-900 rounded-full flex items-center justify-center">
          <span className="text-sm font-medium text-blue-600 dark:text-blue-400">
            {camper.first_name[0]}{camper.last_name[0]}
          </span>
        </div>
        <div>
          <p className="font-medium text-gray-900 dark:text-white">{camper.first_name} {camper.last_name}</p>
          {log && (
            <div className="flex items-center gap-2 mt-1">
              {log.request_unit_head_help && (
                <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200">
                  Unit Head Help
                </span>
              )}
              {log.request_camper_care_help && (
                <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200">
                  Camper Care Help
                </span>
              )}
            </div>
          )}
        </div>
      </div>
      
      {log && (
        <div className="flex items-center gap-2">
          <ScoreBadge label="S" score={log.social_score} />
          <ScoreBadge label="B" score={log.behavior_score} />
          <ScoreBadge label="P" score={log.participation_score} />
        </div>
      )}
    </div>
  );
};

// Score Badge Component
const ScoreBadge = ({ label, score }) => {
  if (!score) return null;
  
  const getVariant = (score) => {
    if (score >= 4) return "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200";
    if (score >= 3) return "bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200";
    return "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200";
  };
  
  return (
    <span className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-medium ${getVariant(score)}`}>
      {label}{score}
    </span>
  );
};

export default CamperCareDashboard;
