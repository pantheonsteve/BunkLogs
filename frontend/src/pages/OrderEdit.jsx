import React, { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';
import api from '../api';
import Sidebar from '../partials/Sidebar';
import Header from '../partials/Header';

function OrderEdit() {
  const { orderId } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  
  const [order, setOrder] = useState(null);
  const [orderTypes, setOrderTypes] = useState([]);
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  
  const [formData, setFormData] = useState({
    order_type: '',
    order_items: [],
    narrative_description: ''
  });

  // Check if user is a counselor
  const isCounselor = user?.role === 'Counselor';

  // Helper to get current order type object
  const currentOrderTypeObj = orderTypes.find(type => type.id === formData.order_type);
  const isMaintenanceRequest = currentOrderTypeObj?.type_name === 'Maintenance Request';

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        setError(null);
        
        // Fetch order details
        const orderResponse = await api.get(`/api/orders/${orderId}/`);
        
        const orderData = orderResponse.data;
        setOrder(orderData);
        console.log('Fetched order:', orderData);
        
        // Check if user can edit this order (counselor and submitted status)
        if (!isCounselor || orderData.order_status !== 'submitted') {
          setError('You do not have permission to edit this order');
          return;
        }
        
        // Fetch order types
        const orderTypesResponse = await api.get('/api/order-types/');
        setOrderTypes(orderTypesResponse.data);
        console.log('Fetched order types:', orderTypesResponse.data);
        
        // Fetch items for the current order type
        if (orderData.order_type) {
          const itemsResponse = await api.get(`/api/items/?order_type=${orderData.order_type}`);
          setItems(itemsResponse.data);
          
          // Set form data with all items for this order type
          // Create order_items array with quantities for all items
          const orderItemsMap = new Map();
          orderData.order_items?.forEach(item => {
            orderItemsMap.set(item.item, item.item_quantity);
          });
          
          const allOrderItems = itemsResponse.data.map(item => ({
            item: item.id,
            item_quantity: orderItemsMap.get(item.id) || 0
          }));
          
          setFormData({
            order_type: orderData.order_type,
            order_items: allOrderItems
          });
        }
        
        if (orderData.narrative_description) {
          setFormData(prev => ({ ...prev, narrative_description: orderData.narrative_description }));
        }
        
      } catch (error) {
        console.error('Error fetching data:', error);
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
      fetchData();
    }
  }, [orderId, isCounselor]);

  const handleItemChange = (itemId, quantity) => {
    setFormData(prev => {
      const existingItems = prev.order_items.filter(item => item.item !== itemId);
      if (quantity > 0) {
        return {
          ...prev,
          order_items: [...existingItems, { item: itemId, item_quantity: quantity }]
        };
      } else {
        return {
          ...prev,
          order_items: existingItems
        };
      }
    });
  };

  const handleItemCheckboxChange = (itemId, checked) => {
    setFormData(prev => {
      const existingItems = prev.order_items.filter(item => item.item !== itemId);
      if (checked) {
        return {
          ...prev,
          order_items: [...existingItems, { item: itemId, item_quantity: 1 }]
        };
      } else {
        return {
          ...prev,
          order_items: existingItems
        };
      }
    });
  };

  const getItemQuantity = (itemId) => {
    const item = formData.order_items.find(item => item.item === itemId);
    return item ? item.item_quantity : 0;
  };

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!formData.order_type) {
      setError('Please select an order type');
      return;
    }
    
    // Check if at least one item has quantity > 0
    const itemsWithQuantity = formData.order_items.filter(item => item.item_quantity > 0);
    if (itemsWithQuantity.length === 0) {
      setError('Please select at least one item with a quantity greater than 0');
      return;
    }

    try {
      setSaving(true);
      setError(null);
      
      const updateData = {
        order_type: formData.order_type,
        order_items: itemsWithQuantity, // Only send items with quantity > 0
        narrative_description: formData.narrative_description
      };
      
      await api.patch(`/api/orders/${orderId}/`, updateData);
      
      // Navigate back to order detail page
      navigate(`/orders/${orderId}`);
    } catch (error) {
      console.error('Error updating order:', error);
      setError(error.response?.data?.detail || 'Failed to update order');
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="flex h-[100dvh] overflow-hidden">
        <Sidebar sidebarOpen={false} setSidebarOpen={() => {}} />
        <div className="relative flex flex-col flex-1 overflow-y-auto overflow-x-hidden">
          <Header sidebarOpen={false} setSidebarOpen={() => {}} />
          <main className="grow">
            <div className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-9xl mx-auto">
              <div className="flex justify-center items-center py-8">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900">
                </div>
                <span className="ml-2 text-gray-600">Loading order details...</span>
              </div>
            </div>
          </main>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex h-[100dvh] overflow-hidden">
        <Sidebar sidebarOpen={false} setSidebarOpen={() => {}} />
        <div className="relative flex flex-col flex-1 overflow-y-auto overflow-x-hidden">
          <Header sidebarOpen={false} setSidebarOpen={() => {}} />
          <main className="grow">
            <div className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-9xl mx-auto">
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
              <Link
                to={`/orders/${orderId}`}
                className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700"
              >
                ← Back to Order
              </Link>
            </div>
          </main>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-[100dvh] overflow-hidden">
      <Sidebar sidebarOpen={false} setSidebarOpen={() => {}} />
      <div className="relative flex flex-col flex-1 overflow-y-auto overflow-x-hidden">
        <Header sidebarOpen={false} setSidebarOpen={() => {}} />
        <main className="grow">
          <div className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-9xl mx-auto">

            {/* Page header */}
            <div className="sm:flex sm:justify-between sm:items-center mb-8">
              <div className="mb-4 sm:mb-0">
                <h1 className="text-2xl md:text-3xl text-gray-800 dark:text-gray-100 font-bold">
                  Edit Order #{order?.id}
                </h1>
                <div className="mt-2 space-y-1">
                  <p className="text-gray-600 dark:text-gray-400">
                    <span className="font-medium">Bunk:</span> {order?.order_bunk_name || order?.order_bunk_cabin || 'N/A'}
                  </p>
                  <p className="text-gray-600 dark:text-gray-400">
                    <span className="font-medium">Created:</span> {order?.order_date ? new Date(order.order_date).toLocaleDateString('en-US', { 
                      weekday: 'long',
                      year: 'numeric', 
                      month: 'long', 
                      day: 'numeric',
                      hour: '2-digit',
                      minute: '2-digit'
                    }) : 'N/A'}
                  </p>
                  <p className="text-sm text-gray-500 dark:text-gray-500">
                    Make changes to your order before it's processed
                  </p>
                </div>
              </div>

              <div className="flex space-x-3">
                <Link
                  to={`/orders/${orderId}`}
                  className="inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50"
                >
                  Cancel
                </Link>
              </div>
            </div>

            {/* Edit form */}
            <div className="bg-white dark:bg-gray-800 shadow rounded-lg">
              <form onSubmit={handleSubmit}>
                <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
                  <h3 className="text-lg leading-6 font-medium text-gray-900 dark:text-gray-100">
                    Order Details
                  </h3>
                </div>
                <div className="px-6 py-4 space-y-6">
                  {/* Order Type Display (Read-only) */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      Order Type
                    </label>
                    <div className="block w-full px-3 py-2 border border-gray-300 rounded-md bg-gray-50 text-gray-700">
                      {orderTypes.find(type => type.id === formData.order_type)?.type_name || 'Loading...'}
                    </div>
                    <p className="mt-1 text-xs text-gray-500">Order type cannot be changed when editing an existing order</p>
                  </div>

                  {/* Narrative Description */}
                  <div>
                    <label htmlFor="narrativeDescription" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      Narrative Description (optional)
                    </label>
                    <textarea
                      id="narrativeDescription"
                      name="narrative_description"
                      value={formData.narrative_description}
                      onChange={handleInputChange}
                      rows={3}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white"
                      placeholder="Describe your order..."
                    />
                  </div>

                  {/* Items Selection - Show All Items for this Order Type */}
                  {formData.order_type && items.length > 0 && (
                    <div>
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                        Order Items
                      </label>
                      {isMaintenanceRequest ? (
                        <div className="space-y-3 max-h-64 overflow-y-auto border border-gray-200 rounded-md p-4">
                          {items.map((item) => {
                            const selectedItem = formData.order_items.find(i => i.item === item.id);
                            return (
                              <div key={item.id} className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-700 rounded-lg">
                                <div className="flex-1">
                                  <h4 className="text-sm font-medium text-gray-900 dark:text-gray-100">{item.item_name}</h4>
                                  <p className="text-xs text-gray-500 dark:text-gray-400">{item.item_description || 'No description available'}</p>
                                </div>
                                <div className="flex items-center space-x-2">
                                  <input
                                    type="checkbox"
                                    checked={!!selectedItem && selectedItem.item_quantity > 0}
                                    onChange={e => handleItemCheckboxChange(item.id, e.target.checked)}
                                    className="w-5 h-5 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                                  />
                                </div>
                              </div>
                            );
                          })}
                        </div>
                      ) : (
                        <div className="space-y-3 max-h-64 overflow-y-auto border border-gray-200 rounded-md p-4">
                          {items.map((item) => (
                            <div key={item.id} className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-700 rounded-lg">
                              <div className="flex-1">
                                <h4 className="text-sm font-medium text-gray-900 dark:text-gray-100">{item.item_name}</h4>
                                <p className="text-xs text-gray-500 dark:text-gray-400">{item.item_description || 'No description available'}</p>
                              </div>
                              <div className="flex items-center space-x-2">
                                <label htmlFor={`quantity-${item.id}`} className="text-sm text-gray-700 dark:text-gray-300">
                                  Qty:
                                </label>
                                <input
                                  type="number"
                                  id={`quantity-${item.id}`}
                                  min="0"
                                  max="100"
                                  value={getItemQuantity(item.id)}
                                  onChange={e => handleItemChange(item.id, parseInt(e.target.value) || 0)}
                                  className="w-16 px-2 py-1 text-sm border border-gray-300 rounded focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                                />
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}

                  {/* Selected Items Summary - Only show items with quantity > 0 */}
                  {formData.order_items.filter(item => item.item_quantity > 0).length > 0 && (
                    <div>
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                        Order Summary ({formData.order_items.filter(item => item.item_quantity > 0).length} items)
                      </label>
                      <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
                        <ul className="space-y-1">
                          {formData.order_items.filter(item => item.item_quantity > 0).map((orderItem) => {
                            const item = items.find(i => i.id === orderItem.item);
                            return (
                              <li key={orderItem.item} className="text-sm text-blue-800 dark:text-blue-200">
                                {item?.item_name} - Quantity: {orderItem.item_quantity}
                              </li>
                            );
                          })}
                        </ul>
                      </div>
                    </div>
                  )}

                  {error && (
                    <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
                      <p className="text-sm text-red-700">{error}</p>
                    </div>
                  )}
                </div>

                <div className="px-6 py-4 bg-gray-50 dark:bg-gray-700 flex justify-end space-x-3">
                  <Link
                    to={`/orders/${orderId}`}
                    className="px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50"
                  >
                    Cancel
                  </Link>
                  <button
                    type="submit"
                    disabled={saving || formData.order_items.filter(item => item.item_quantity > 0).length === 0}
                    className="px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {saving ? 'Updating...' : 'Update Order'}
                  </button>
                </div>
              </form>
            </div>

          </div>
        </main>
      </div>
    </div>
  );
}

export default OrderEdit;
