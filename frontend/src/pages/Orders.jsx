import React, { useEffect, useState } from 'react';
import api from '../api';
import { useAuth } from '../auth/AuthContext';
import Sidebar from '../partials/Sidebar';
import Header from '../partials/Header';
import DeleteButton from '../partials/actions/DeleteButton';
import DateSelect from '../components/DateSelect';
import FilterButton from '../components/DropdownFilter';
import OrdersTable from '../partials/orders/OrdersTable';
import PaginationClassic from '../components/PaginationClassic';
import OrderFilters from '../components/OrderFilters';


function Orders() {

  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [selectedItems, setSelectedItems] = useState([]);
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [filters, setFilters] = useState({
    bunk: '',
    status: '',
    orderType: ''
  });
  const { isAuthenticated, token } = useAuth();

  const handleSelectedItems = (selectedItems) => {
    setSelectedItems([...selectedItems]);
  };

  const handleOrderUpdate = (orderId, newStatus, updatedOrder) => {
    // Update the local data state
    setData(prevData => 
      prevData.map(order => 
        order.id === parseInt(orderId) 
          ? { ...order, ...updatedOrder }
          : order
      )
    );
  };

  const handleFiltersChange = (newFilters) => {
    setFilters(newFilters);
    // Reset selected items when filters change
    setSelectedItems([]);
  };

  useEffect(() => {
    async function fetchOrders() {
      if (!isAuthenticated) {
        setError('Please log in to view orders');
        setLoading(false);
        return;
      }

      try {
        setLoading(true);
        setError(null);
        
        // Build query parameters based on filters
        const queryParams = new URLSearchParams();
        
        if (filters.bunk) {
          queryParams.append('bunk', filters.bunk);
        }
        if (filters.status) {
          queryParams.append('status', filters.status);
        }
        if (filters.orderType) {
          queryParams.append('order_type', filters.orderType);
        }
        
        const queryString = queryParams.toString();
        const url = `/api/orders/${queryString ? `?${queryString}` : ''}`;
        
        const response = await api.get(url);
        setData(response.data);
      } catch (error) {
        console.error('Error fetching orders:', error);
        if (error.response?.status === 401) {
          setError('Authentication required. Please log in again.');
        } else {
          setError('Failed to fetch orders. Please try again.');
        }
      } finally {
        setLoading(false);
      }
    }

    fetchOrders();
  }, [isAuthenticated, token, filters]);

  console.log('Orders data:', data);
  

  return (
    <div className="flex h-[100dvh] overflow-hidden">

      {/* Sidebar */}
      <Sidebar sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} />

      {/* Content area */}
      <div className="relative flex flex-col flex-1 overflow-y-auto overflow-x-hidden">

        {/*  Site header */}
        <Header sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} />

        <main className="grow">
          <div className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-[96rem] mx-auto">

            {/* Page header */}
            <div className="sm:flex sm:justify-between sm:items-center mb-8">

              {/* Left: Title */}
              <div className="mb-4 sm:mb-0">
                <h1 className="text-2xl md:text-3xl text-gray-800 dark:text-gray-100 font-bold">Orders</h1>
              </div>

              {/* Right: Actions */}
              <div className="grid grid-flow-col sm:auto-cols-max justify-start sm:justify-end gap-2">
              </div>

            </div>

            {/* Filters */}
            <div className="mb-6">
              <OrderFilters 
                filters={filters} 
                onFiltersChange={handleFiltersChange}
              />
            </div>

            {/* Error Display */}
            {error && (
              <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg">
                <div className="flex items-center">
                  <div className="flex-shrink-0">
                    <svg className="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
                      <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                    </svg>
                  </div>
                  <div className="ml-3">
                    <p className="text-sm text-red-700">{error}</p>
                  </div>
                </div>
              </div>
            )}

            {/* Loading State */}
            {loading && (
              <div className="flex justify-center items-center py-8">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900"></div>
                <span className="ml-2 text-gray-600">Loading orders...</span>
              </div>
            )}

            {/* Table */}
            {!loading && !error && <OrdersTable selectedItems={handleSelectedItems} data={data} onOrderUpdate={handleOrderUpdate} />}

            {/* Pagination */}
            {!loading && !error && (
              <div className="mt-8">
                <PaginationClassic />
              </div>
            )}

          </div>
        </main>

      </div>

    </div>
  );
}

export default Orders;