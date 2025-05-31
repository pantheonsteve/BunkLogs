import React, { useState, useEffect } from 'react';
import { NavLink } from 'react-router-dom';
import { useAuth } from '../../auth/AuthContext';
import api from '../../api';

function OrdersList({ bunk_id, date }) {
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
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
  }, [bunk_id]);

  const getStatusColor = (status) => {
    switch (status?.toLowerCase()) {
      case 'submitted':
        return 'text-blue-600 bg-blue-50';
      case 'pending':
        return 'text-yellow-600 bg-yellow-50';
      case 'completed':
        return 'text-green-600 bg-green-50';
      case 'canceled':
        return 'text-red-600 bg-red-50';
      default:
        return 'text-gray-600 bg-gray-50';
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

  if (loading) {
    return (
      <div className="px-3 py-2">
        <div className="flex items-center justify-center">
          <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-gray-400"></div>
          <span className="ml-2 text-xs text-gray-500">Loading orders...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="px-3 py-2">
        <p className="text-xs text-red-500">{error}</p>
      </div>
    );
  }

  if (orders.length === 0) {
    return (
      <div className="px-3 py-2">
        <p className="text-xs text-gray-500">No orders found</p>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {orders.map((order) => (
        <div key={order.id} className="px-3 py-2 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
          <div className="flex items-start justify-between">
            <div className="flex-1 min-w-0">
              <NavLink
                to={canEditOrder(order) ? `/bunk/${bunk_id}/${date}/orders/${order.id}` : `/bunk/${bunk_id}/${date}/orders/${order.id}`}
                className="block group"
              >
                <div className="flex items-center space-x-2">
                  <h4 className="text-sm font-medium text-gray-900 dark:text-gray-100 truncate group-hover:text-blue-600 dark:group-hover:text-blue-400">
                    Order #{order.id}
                  </h4>
                  {canEditOrder(order) && (
                    <svg className="w-3 h-3 text-gray-400 group-hover:text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                    </svg>
                  )}
                </div>
                <p className="text-xs text-gray-600 dark:text-gray-400 truncate">
                  {order?.order_type_name || 'Unknown Type'}
                </p>
                <p className="text-xs text-gray-500 dark:text-gray-500">
                  {formatDate(order.order_date)}
                </p>
              </NavLink>
            </div>
          </div>
          <div className="mt-2">
            <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(order.order_status)}`}>
              {order.order_status_display || order.order_status}
            </span>
          </div>
        </div>
      ))}
    </div>
  );
}

export default OrdersList;
