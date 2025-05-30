import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../auth/AuthContext';
import api from '../../api';

function BunkOrderEdit({ orderId, bunk_id, date }) {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [order, setOrder] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [updating, setUpdating] = useState(false);
  const [updateError, setUpdateError] = useState(null);
  const [availableItems, setAvailableItems] = useState([]);

  // Form state
  const [formData, setFormData] = useState({
    order_status: '',
    order_items: []
  });

  // Check user roles and permissions
  const isCounselor = user?.role === 'Counselor';
  const isAdminOrCamperCare = user?.role === 'Admin' || user?.role === 'Camper Care';
  const canEditStatus = isAdminOrCamperCare; // Only Admin and Camper Care can change status from submitted
  const canEdit = isAdminOrCamperCare || (isCounselor && order?.order_status === 'submitted');

  useEffect(() => {
    const fetchOrder = async () => {
      try {
        setLoading(true);
        setError(null);
        
        const response = await api.get(`/api/orders/${orderId}/`);
        
        const orderData = response.data;
        setOrder(orderData);
        
        // Initialize form data
        setFormData({
          order_status: orderData.order_status || '',
          order_items: orderData.order_items || []
        });

        // Fetch available items for this order type if it exists
        if (orderData.order_type) {
          try {
            const itemsResponse = await api.get(`/api/order-types/${orderData.order_type}/items/`);
            setAvailableItems(itemsResponse.data);
          } catch (itemsError) {
            console.error('Error fetching available items:', itemsError);
            // Don't fail the whole component if items can't be fetched
          }
        }
      } catch (error) {
        console.error('Error fetching order:', error);
        if (error.response?.status === 404) {
          setError('Order not found');
        } else if (error.response?.status === 403) {
          setError('You do not have permission to edit this order');
        } else {
          setError('Failed to fetch order details');
        }
      } finally {
        setLoading(false);
      }
    };

    if (orderId) {
      fetchOrder();
    }
  }, [orderId]);

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handleItemChange = (index, field, value) => {
    setFormData(prev => ({
      ...prev,
      order_items: prev.order_items.map((item, i) => 
        i === index ? { ...item, [field]: value } : item
      )
    }));
  };

  const addOrderItem = () => {
    setFormData(prev => ({
      ...prev,
      order_items: [...prev.order_items, {
        item: '', // Use item ID for new items
        item_name: '',
        item_description: '',
        item_quantity: 1
      }]
    }));
  };

  const removeOrderItem = (index) => {
    setFormData(prev => ({
      ...prev,
      order_items: prev.order_items.filter((_, i) => i !== index)
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    // Check permissions before submitting
    if (!canEdit && !isAdminOrCamperCare) {
      setUpdateError('You do not have permission to edit this order');
      return;
    }

    // For counselors, only allow editing if order is in submitted status
    if (isCounselor && !isAdminOrCamperCare && order?.order_status !== 'submitted') {
      setUpdateError('Only orders with "submitted" status can be edited by counselors');
      return;
    }

    // Status change validation
    if (formData.order_status !== order?.order_status) {
      if (order?.order_status === 'submitted' && !isAdminOrCamperCare) {
        setUpdateError('Only Camper Care and Admin users can change order status from "Submitted"');
        return;
      }
    }

    // Prepare the update data - include required fields from the original order
    const updateData = {
      order_status: formData.order_status,
      order_bunk: order.order_bunk, // Required field from the original order
      order_type: order.order_type, // Required field from the original order
      order_items: formData.order_items.map(item => ({
        id: item.id || undefined, // Include ID for existing items
        item: typeof item.item === 'object' ? item.item.id : item.item, // Handle both new and existing items
        item_quantity: item.item_quantity
      }))
    };

    try {
      setUpdating(true);
      setUpdateError(null);

      console.log('Sending update data:', updateData);

      const response = await api.put(`/api/orders/${orderId}/`, updateData);

      // Navigate back to order detail view
      navigate(`/bunk/${bunk_id}/${date}/orders/${orderId}`);
    } catch (error) {
      console.error('Error updating order:', error);
      console.error('Request data sent:', updateData);
      console.error('API response data:', error.response?.data);
      console.error('API response status:', error.response?.status);
      
      if (error.response?.data) {
        const errorData = error.response.data;
        if (typeof errorData === 'object') {
          const errorMessages = Object.entries(errorData)
            .map(([field, messages]) => `${field}: ${Array.isArray(messages) ? messages.join(', ') : messages}`)
            .join('\n');
          setUpdateError(errorMessages);
        } else {
          setUpdateError(errorData);
        }
      } else {
        setUpdateError('Failed to update order');
      }
    } finally {
      setUpdating(false);
    }
  };

  const handleBackClick = () => {
    navigate(`/bunk/${bunk_id}/${date}/orders/${orderId}`);
  };

  const handleCancelClick = () => {
    navigate(`/bunk/${bunk_id}/${date}`);
  };

  if (loading) {
    return (
      <div className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-9xl mx-auto">
        <div className="flex justify-center items-center py-8">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900"></div>
          <span className="ml-2 text-gray-600">Loading order...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-9xl mx-auto">
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-md p-4">
          <div className="flex">
            <div className="flex-shrink-0">
              <svg className="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
              </svg>
            </div>
            <div className="ml-3">
              <p className="text-sm text-red-800 dark:text-red-200">{error}</p>
            </div>
          </div>
        </div>
        <div className="mt-4">
          <button
            onClick={handleCancelClick}
            className="bg-gray-500 hover:bg-gray-600 text-white font-medium py-2 px-4 rounded-lg transition-colors duration-200"
          >
            ← Back to Bunk Dashboard
          </button>
        </div>
      </div>
    );
  }

  if (!canEdit && !isAdminOrCamperCare) {
    return (
      <div className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-9xl mx-auto">
        <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-md p-4">
          <p className="text-sm text-yellow-800 dark:text-yellow-200">
            You do not have permission to edit this order.
          </p>
        </div>
        <div className="mt-4">
          <button
            onClick={handleBackClick}
            className="bg-gray-500 hover:bg-gray-600 text-white font-medium py-2 px-4 rounded-lg transition-colors duration-200"
          >
            ← Back to Order
          </button>
        </div>
      </div>
    );
  }

  if (isCounselor && !isAdminOrCamperCare && order?.order_status !== 'submitted') {
    return (
      <div className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-9xl mx-auto">
        <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-md p-4">
          <p className="text-sm text-yellow-800 dark:text-yellow-200">
            Only orders with "submitted" status can be edited by counselors. This order has status: {order?.order_status}
          </p>
        </div>
        <div className="mt-4">
          <button
            onClick={handleBackClick}
            className="bg-gray-500 hover:bg-gray-600 text-white font-medium py-2 px-4 rounded-lg transition-colors duration-200"
          >
            ← Back to Order
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-9xl mx-auto">
      {/* Header */}
      <div className="mb-6 flex items-center space-x-4">
        <button
          onClick={handleBackClick}
          className="bg-gray-500 hover:bg-gray-600 text-white font-medium py-2 px-4 rounded-lg transition-colors duration-200"
        >
          ← Back to Order
        </button>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
          Edit Order #{orderId}
        </h1>
      </div>

      {updateError && (
        <div className="mb-6 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-md p-4">
          <div className="flex">
            <div className="flex-shrink-0">
              <svg className="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
              </svg>
            </div>
            <div className="ml-3">
              <p className="text-sm text-red-800 dark:text-red-200 whitespace-pre-line">{updateError}</p>
            </div>
          </div>
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-8">
        {/* Order Information */}
        <div className="bg-white dark:bg-gray-800 shadow rounded-lg">
          <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
            <h3 className="text-lg leading-6 font-medium text-gray-900 dark:text-gray-100">
              Order Information
            </h3>
          </div>
          <div className="px-6 py-4 space-y-6">
            <div>
              <label htmlFor="order_status" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                Status
              </label>
              <select
                id="order_status"
                name="order_status"
                value={formData.order_status}
                onChange={handleInputChange}
                disabled={!canEditStatus}
                className="mt-1 block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-gray-100 disabled:bg-gray-100 disabled:cursor-not-allowed"
              >
                <option value="submitted">Submitted</option>
                <option value="pending">Pending</option>
                <option value="completed">Completed</option>
                <option value="cancelled">Cancelled</option>
              </select>
              {!canEditStatus && (
                <p className="mt-1 text-xs text-gray-500">
                  {isCounselor ? 'Only Camper Care and Admin can change status from submitted' : 'You do not have permission to change order status'}
                </p>
              )}
            </div>
          </div>
        </div>

        {/* Order Items */}
        <div className="bg-white dark:bg-gray-800 shadow rounded-lg">
          <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">
            <h3 className="text-lg leading-6 font-medium text-gray-900 dark:text-gray-100">
              Order Items
            </h3>
            <button
              type="button"
              onClick={addOrderItem}
              className="bg-green-500 hover:bg-green-600 text-white font-medium py-2 px-4 rounded-lg transition-colors duration-200"
            >
              + Add Item
            </button>
          </div>
          <div className="px-6 py-4">
            {formData.order_items.length > 0 ? (
              <div className="space-y-4">
                {formData.order_items.map((item, index) => (
                  <div key={index} className="border border-gray-200 dark:border-gray-600 rounded-lg p-4">
                    <div className="flex items-center justify-between mb-4">
                      <h4 className="text-md font-medium text-gray-900 dark:text-gray-100">
                        Item #{index + 1}
                      </h4>
                      <button
                        type="button"
                        onClick={() => removeOrderItem(index)}
                        className="text-red-600 hover:text-red-800 dark:text-red-400 dark:hover:text-red-300"
                      >
                        Remove
                      </button>
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                      <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                          Item Name
                        </label>
                        {item.id ? (
                          // Existing item - show name as read-only
                          <div className="mt-1 block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-gray-50 dark:bg-gray-700 text-gray-700 dark:text-gray-300">
                            {item.item_name || 'Loading...'}
                          </div>
                        ) : (
                          // New item - show dropdown
                          <select
                            value={item.item || ''}
                            onChange={(e) => {
                              const selectedItem = availableItems.find(ai => ai.id === parseInt(e.target.value));
                              handleItemChange(index, 'item', e.target.value);
                              if (selectedItem) {
                                handleItemChange(index, 'item_name', selectedItem.item_name);
                                handleItemChange(index, 'item_description', selectedItem.item_description || '');
                              }
                            }}
                            className="mt-1 block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-gray-100"
                          >
                            <option value="">Select an item...</option>
                            {availableItems.map(availableItem => (
                              <option key={availableItem.id} value={availableItem.id}>
                                {availableItem.item_name}
                              </option>
                            ))}
                          </select>
                        )}
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                          Description
                        </label>
                        <div className="mt-1 block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-gray-50 dark:bg-gray-700 text-gray-700 dark:text-gray-300">
                          {item.item_description || 'No description available'}
                        </div>
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                          Quantity
                        </label>
                        <input
                          type="number"
                          min="1"
                          value={item.item_quantity || 1}
                          onChange={(e) => handleItemChange(index, 'item_quantity', parseInt(e.target.value) || 1)}
                          className="mt-1 block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-gray-100"
                        />
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-8">
                <p className="text-gray-500 dark:text-gray-400 mb-4">No items in this order</p>
                <button
                  type="button"
                  onClick={addOrderItem}
                  className="bg-blue-500 hover:bg-blue-600 text-white font-medium py-2 px-4 rounded-lg transition-colors duration-200"
                >
                  Add First Item
                </button>
              </div>
            )}
          </div>
        </div>

        {/* Form Actions */}
        <div className="flex items-center justify-end space-x-4">
          <button
            type="button"
            onClick={handleCancelClick}
            className="bg-gray-500 hover:bg-gray-600 text-white font-medium py-2 px-4 rounded-lg transition-colors duration-200"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={updating}
            className="bg-blue-500 hover:bg-blue-600 disabled:bg-blue-300 text-white font-medium py-2 px-4 rounded-lg transition-colors duration-200 flex items-center space-x-2"
          >
            {updating && (
              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
            )}
            <span>{updating ? 'Updating...' : 'Update Order'}</span>
          </button>
        </div>
      </form>
    </div>
  );
}

export default BunkOrderEdit;
