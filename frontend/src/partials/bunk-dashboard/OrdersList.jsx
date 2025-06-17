import React, { useState, useEffect } from 'react';
import { NavLink } from 'react-router-dom';
import { useAuth } from '../../auth/AuthContext';
import { Calendar, Clock, CheckCircle, XCircle, AlertCircle, Edit3, Loader2 } from 'lucide-react';
import api from '../../api';

function OrdersList({ bunk_id, date, refreshTrigger }) {
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [filterStatus, setFilterStatus] = useState('all'); // 'all', 'active', 'completed', 'canceled'
  const { user } = useAuth();

  // Check if user is a counselor
  const isCounselor = user?.role === 'Counselor';

  useEffect(() => {
    const fetchOrders = async () => {
      if (!bunk_id) {
        setLoading(false);
        return;
      }

      try {
        setLoading(true);
        setError(null);
        
        // Fetch orders for the specific bunk
        const response = await api.get(`/api/orders/?bunk=${bunk_id}`);
        
        // Sort orders by date in descending order (newest first)
        const sortedOrders = response.data.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
        setOrders(sortedOrders);
      } catch (error) {
        console.error('Error fetching orders:', error);
        setError('Failed to fetch orders');
      } finally {
        setLoading(false);
      }
    };

    fetchOrders();
  }, [bunk_id, refreshTrigger]);

  // Filter orders based on status
  const filteredOrders = orders.filter(order => {
    const status = order.order_status?.toLowerCase();
    if (filterStatus === 'active') return status === 'submitted' || status === 'pending';
    if (filterStatus === 'completed') return status === 'completed';
    if (filterStatus === 'canceled') return status === 'canceled';
    return true; // 'all'
  });

  // Get status counts for display
  const activeCount = orders.filter(order => {
    const status = order.order_status?.toLowerCase();
    return status === 'submitted' || status === 'pending';
  }).length;
  const completedCount = orders.filter(order => order.order_status?.toLowerCase() === 'completed').length;
  const canceledCount = orders.filter(order => order.order_status?.toLowerCase() === 'canceled').length;

  const getStatusColor = (status) => {
    switch (status?.toLowerCase()) {
      case 'submitted':
        return 'text-blue-600 bg-blue-50 border-blue-200';
      case 'pending':
        return 'text-amber-600 bg-amber-50 border-amber-200';
      case 'completed':
        return 'text-green-600 bg-green-50 border-green-200';
      case 'canceled':
        return 'text-red-600 bg-red-50 border-red-200';
      default:
        return 'text-gray-600 bg-gray-50 border-gray-200';
    }
  };

  const getStatusIcon = (status) => {
    switch (status?.toLowerCase()) {
      case 'submitted':
        return <Clock className="w-3 h-3" />;
      case 'pending':
        return <AlertCircle className="w-3 h-3" />;
      case 'completed':
        return <CheckCircle className="w-3 h-3" />;
      case 'canceled':
        return <XCircle className="w-3 h-3" />;
      default:
        return <Clock className="w-3 h-3" />;
    }
  };

  const canEditOrder = (order) => {
    return isCounselor && order.order_status?.toLowerCase() === 'submitted';
  };

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', { 
      month: 'short', 
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  // Loading state
  if (loading) {
    return (
      <div className="p-4">
        <div className="flex items-center justify-center py-8">
          <Loader2 className="w-5 h-5 animate-spin text-gray-400" />
          <span className="ml-2 text-sm text-gray-500">Loading...</span>
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="p-4">
        <div className="flex items-center justify-center py-8 text-red-500">
          <AlertCircle className="w-5 h-5" />
          <span className="ml-2 text-sm">Failed to load</span>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col">
      {/* Header with counts */}
      <div className="p-4 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-between mb-3">
          <h3 className="font-medium text-gray-900 dark:text-gray-100">Orders</h3>
          <div className="text-xs text-gray-500">
            {filteredOrders.length}/{orders.length}
          </div>
        </div>
        
        {/* Simple filter tabs */}
        <div className="flex space-x-1 bg-gray-100 dark:bg-gray-800 rounded-lg p-1">
          <button
            onClick={() => setFilterStatus('all')}
            className={`flex-1 px-2 py-1 text-xs font-medium rounded transition-colors ${
              filterStatus === 'all' 
                ? 'bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 shadow-sm' 
                : 'text-gray-600 dark:text-gray-400'
            }`}
          >
            All
          </button>
          <button
            onClick={() => setFilterStatus('active')}
            className={`flex-1 px-2 py-1 text-xs font-medium rounded transition-colors ${
              filterStatus === 'active' 
                ? 'bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 shadow-sm' 
                : 'text-gray-600 dark:text-gray-400'
            }`}
          >
            Active
          </button>
          <button
            onClick={() => setFilterStatus('completed')}
            className={`flex-1 px-2 py-1 text-xs font-medium rounded transition-colors ${
              filterStatus === 'completed' 
                ? 'bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 shadow-sm' 
                : 'text-gray-600 dark:text-gray-400'
            }`}
          >
            Done
          </button>
        </div>
      </div>

      {/* Orders list */}
      <div className="flex-1 overflow-y-auto p-2">
        <div className="space-y-2">
          {filteredOrders.map((order) => (
            <NavLink
              key={order.id}
              to={`/bunk/${bunk_id}/${date}/orders/${order.id}`}
              className="block group"
            >
              <div className="bg-gray-50 hover:bg-gray-100 dark:bg-gray-800 dark:hover:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-lg p-3 transition-all duration-200 hover:shadow-sm">
                {/* Header */}
                <div className="flex items-start justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <h4 className="text-sm font-semibold text-gray-900 dark:text-gray-100 group-hover:text-blue-600 dark:group-hover:text-blue-400">
                      Order #{order.id}
                    </h4>
                    {canEditOrder(order) && (
                      <Edit3 className="w-3 h-3 text-gray-400 group-hover:text-blue-600" />
                    )}
                  </div>
                  <span className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium border ${getStatusColor(order.order_status)}`}>
                    {getStatusIcon(order.order_status)}
                    {order.order_status_display || order.order_status}
                  </span>
                </div>

                {/* Order details */}
                <div className="space-y-1">
                  <p className="text-sm text-gray-700 dark:text-gray-300 font-medium">
                    {order?.order_type_name || 'Unknown Type'}
                  </p>
                  <div className="flex items-center gap-1 text-xs text-gray-500 dark:text-gray-400">
                    <Calendar className="w-3 h-3" />
                    {formatDate(order.order_date)}
                  </div>
                </div>
              </div>
            </NavLink>
          ))}
        </div>
        
        {filteredOrders.length === 0 && (
          <div className="text-center py-8 text-gray-500 dark:text-gray-400">
            <p className="text-sm">No orders found</p>
          </div>
        )}
      </div>
    </div>
  );
}

export default OrdersList;