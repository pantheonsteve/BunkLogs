import React, { useState, useEffect } from 'react';
import api from '../api';

function OrderFilters({ 
  onFiltersChange,
  filters = {
    bunk: '',
    status: '',
    orderType: ''
  }
}) {
  const [bunks, setBunks] = useState([]);
  const [orderTypes, setOrderTypes] = useState([]);
  const [loading, setLoading] = useState(true);

  // Status options based on the backend model
  const statusOptions = [
    { value: '', label: 'All Statuses' },
    { value: 'submitted', label: 'Submitted' },
    { value: 'pending', label: 'Pending' },
    { value: 'completed', label: 'Completed' },
    { value: 'cancelled', label: 'Cancelled' }
  ];

  useEffect(() => {
    const fetchFilterData = async () => {
      try {
        setLoading(true);
        
        // Fetch orders and order types in parallel
        const [ordersResponse, orderTypesResponse] = await Promise.all([
          api.get('/api/orders/'),
          api.get('/api/order-types/')
        ]);

        // Extract unique bunks from orders data
        const uniqueBunks = [];
        const bunkIds = new Set();
        
        (ordersResponse.data || []).forEach(order => {
          if (order.order_bunk && !bunkIds.has(order.order_bunk)) {
            bunkIds.add(order.order_bunk);
            uniqueBunks.push({
              id: order.order_bunk,
              name: order.order_bunk_name || `Bunk ${order.order_bunk}`
            });
          }
        });

        // Sort bunks by name for better UX
        uniqueBunks.sort((a, b) => a.name.localeCompare(b.name));

        setBunks(uniqueBunks);
        setOrderTypes(orderTypesResponse.data || []);
      } catch (error) {
        console.error('Error fetching filter data:', error);
        // Set empty arrays on error so the filters still render
        setBunks([]);
        setOrderTypes([]);
      } finally {
        setLoading(false);
      }
    };

    fetchFilterData();
  }, []);

  const handleFilterChange = (filterType, value) => {
    const newFilters = {
      ...filters,
      [filterType]: value
    };
    onFiltersChange(newFilters);
  };

  const clearAllFilters = () => {
    const clearedFilters = {
      bunk: '',
      status: '',
      orderType: ''
    };
    onFiltersChange(clearedFilters);
  };

  // Count active filters
  const activeFilterCount = Object.values(filters).filter(value => value !== '').length;

  if (loading) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4">
        <div className="animate-pulse flex items-center space-x-4">
          <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-16"></div>
          <div className="h-8 bg-gray-200 dark:bg-gray-700 rounded w-32"></div>
          <div className="h-8 bg-gray-200 dark:bg-gray-700 rounded w-32"></div>
          <div className="h-8 bg-gray-200 dark:bg-gray-700 rounded w-32"></div>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        {/* Filter Controls */}
        <div className="flex flex-col sm:flex-row gap-4">
          <div className="flex items-center space-x-2">
            <span className="text-sm font-medium text-gray-700 dark:text-gray-300">Filters:</span>
            {activeFilterCount > 0 && (
              <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200">
                {activeFilterCount} active
              </span>
            )}
          </div>

          {/* Bunk Filter */}
          <div className="flex flex-col">
            <label htmlFor="bunk-filter" className="sr-only">Filter by Bunk</label>
            <select
              id="bunk-filter"
              value={filters.bunk}
              onChange={(e) => handleFilterChange('bunk', e.target.value)}
              className="block w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="">All Bunks</option>
              {bunks.map(bunk => (
                <option key={bunk.id} value={bunk.id}>
                  {bunk.name}
                </option>
              ))}
            </select>
          </div>

          {/* Status Filter */}
          <div className="flex flex-col">
            <label htmlFor="status-filter" className="sr-only">Filter by Status</label>
            <select
              id="status-filter"
              value={filters.status}
              onChange={(e) => handleFilterChange('status', e.target.value)}
              className="block w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            >
              {statusOptions.map(option => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>

          {/* Order Type Filter */}
          <div className="flex flex-col">
            <label htmlFor="type-filter" className="sr-only">Filter by Order Type</label>
            <select
              id="type-filter"
              value={filters.orderType}
              onChange={(e) => handleFilterChange('orderType', e.target.value)}
              className="block w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="">All Types</option>
              {orderTypes.map(type => (
                <option key={type.id} value={type.id}>
                  {type.type_name}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Clear Filters Button */}
        {activeFilterCount > 0 && (
          <button
            onClick={clearAllFilters}
            className="inline-flex items-center px-3 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-md hover:bg-gray-200 dark:hover:bg-gray-600 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors duration-200"
          >
            <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
            Clear Filters
          </button>
        )}
      </div>
    </div>
  );
}

export default OrderFilters;
