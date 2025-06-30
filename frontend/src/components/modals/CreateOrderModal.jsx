import React, { useState, useEffect } from 'react';
import api from '../../api';
import { useAuth } from '../../auth/AuthContext';

function CreateOrderModal({ isOpen, onClose, bunkId, date, onOrderCreated }) {
  const { user } = useAuth();
  const [orderTypes, setOrderTypes] = useState([]);
  const [selectedOrderType, setSelectedOrderType] = useState('');
  const [availableItems, setAvailableItems] = useState([]);
  const [selectedItems, setSelectedItems] = useState([]);
  const [narrativeDescription, setNarrativeDescription] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  // Fetch order types on component mount
  useEffect(() => {
    if (isOpen) {
      fetchOrderTypes();
    }
  }, [isOpen]);

  // Fetch available items when order type changes
  useEffect(() => {
    if (selectedOrderType) {
      fetchAvailableItems(selectedOrderType);
    } else {
      setAvailableItems([]);
      setSelectedItems([]);
    }
  }, [selectedOrderType]);

  const fetchOrderTypes = async () => {
    try {
      setLoading(true);
      const response = await api.get('/api/order-types/');
      setOrderTypes(response.data);
    } catch (error) {
      console.error('Error fetching order types:', error);
      setError('Failed to load order types');
    } finally {
      setLoading(false);
    }
  };

  const fetchAvailableItems = async (orderTypeId) => {
    try {
      setLoading(true);
      const response = await api.get(`/api/order-types/${orderTypeId}/items/`);
      setAvailableItems(response.data);
      setSelectedItems([]);
    } catch (error) {
      console.error('Error fetching available items:', error);
      setError('Failed to load available items');
    } finally {
      setLoading(false);
    }
  };

  const handleItemQuantityChange = (itemId, quantity) => {
    const parsedQuantity = parseInt(quantity) || 0;
    
    if (parsedQuantity <= 0) {
      // Remove item if quantity is 0 or invalid
      setSelectedItems(prev => prev.filter(item => item.item !== itemId));
    } else {
      // Update or add item
      setSelectedItems(prev => {
        const existingIndex = prev.findIndex(item => item.item === itemId);
        if (existingIndex >= 0) {
          const updated = [...prev];
          updated[existingIndex] = { item: itemId, item_quantity: parsedQuantity };
          return updated;
        } else {
          return [...prev, { item: itemId, item_quantity: parsedQuantity }];
        }
      });
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!selectedOrderType) {
      setError('Please select an order type');
      return;
    }
    
    if (selectedItems.length === 0) {
      setError('Please select at least one item');
      return;
    }

    setSubmitting(true);
    setError(null);

    try {
      const orderData = {
        order_status: 'submitted',
        order_bunk: parseInt(bunkId),
        order_type: parseInt(selectedOrderType),
        order_items: selectedItems,
        narrative_description: narrativeDescription
      };

      const response = await api.post('/api/orders/', orderData);
      
      // Call the callback to refresh orders or notify parent
      if (onOrderCreated) {
        onOrderCreated(response.data);
      }
      
      // Reset form and close modal
      resetForm();
      onClose();
      
    } catch (error) {
      console.error('Error creating order:', error);
      if (error.response?.data) {
        const errorMessages = Object.values(error.response.data).flat();
        setError(errorMessages.join(', '));
      } else {
        setError('Failed to create order. Please try again.');
      }
    } finally {
      setSubmitting(false);
    }
  };

  const resetForm = () => {
    setSelectedOrderType('');
    setAvailableItems([]);
    setSelectedItems([]);
    setNarrativeDescription('');
    setError(null);
  };

  const handleClose = () => {
    resetForm();
    onClose();
  };

  if (!isOpen) return null;

  return (
    <>
      {/* Backdrop */}
      <div className="fixed inset-0 bg-gray-900 bg-opacity-50 z-50 transition-opacity">
        <div className="fixed inset-0 z-50 overflow-y-auto">
          <div className="flex min-h-full items-end justify-center p-4 text-center sm:items-center sm:p-0">
            
            {/* Modal */}
            <div className="relative transform overflow-hidden rounded-lg bg-white dark:bg-gray-800 px-4 pb-4 pt-5 text-left shadow-xl transition-all sm:my-8 sm:w-full sm:max-w-lg sm:p-6">
              
              {/* Header */}
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-medium text-gray-900 dark:text-white">
                  Create New Order
                </h3>
                <button
                  type="button"
                  onClick={handleClose}
                  className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
                >
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>

              {/* Error Display */}
              {error && (
                <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-md">
                  <div className="text-sm text-red-700">{error}</div>
                </div>
              )}

              {/* Form */}
              <form onSubmit={handleSubmit} className="space-y-4">
                
                {/* Order Type Selection */}
                <div>
                  <label htmlFor="orderType" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    Order Type
                  </label>
                  <select
                    id="orderType"
                    value={selectedOrderType}
                    onChange={(e) => setSelectedOrderType(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white"
                    disabled={loading}
                  >
                    <option value="">Select an order type...</option>
                    {orderTypes.map(type => (
                      <option key={type.id} value={type.id}>
                        {type.type_name}
                      </option>
                    ))}
                  </select>
                </div>

                {/* Narrative Description */}
                <div>
                  <label htmlFor="narrativeDescription" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    Narrative Description (optional)
                  </label>
                  <textarea
                    id="narrativeDescription"
                    value={narrativeDescription}
                    onChange={e => setNarrativeDescription(e.target.value)}
                    rows={3}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white"
                    placeholder="Describe your order..."
                  />
                </div>

                {/* Items Selection */}
                {availableItems.length > 0 && (
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      Select Items
                    </label>
                    <div className="max-h-60 overflow-y-auto border border-gray-200 dark:border-gray-600 rounded-md">
                      {availableItems.map(item => {
                        const selectedItem = selectedItems.find(si => si.item === item.id);
                        const quantity = selectedItem ? selectedItem.item_quantity : '';
                        
                        return (
                          <div key={item.id} className="p-3 border-b border-gray-100 dark:border-gray-700 last:border-b-0">
                            <div className="flex items-center justify-between">
                              <div className="flex-1">
                                <h4 className="text-sm font-medium text-gray-900 dark:text-white">
                                  {item.item_name}
                                </h4>
                                {item.item_description && (
                                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                                    {item.item_description}
                                  </p>
                                )}
                              </div>
                              <div className="ml-4">
                                <input
                                  type="number"
                                  min="0"
                                  placeholder="Qty"
                                  value={quantity}
                                  onChange={(e) => handleItemQuantityChange(item.id, e.target.value)}
                                  className="w-16 px-2 py-1 text-sm border border-gray-300 rounded focus:ring-indigo-500 focus:border-indigo-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white"
                                />
                              </div>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}

                {/* Loading State */}
                {loading && (
                  <div className="flex justify-center py-4">
                    <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-indigo-600"></div>
                  </div>
                )}

                {/* Form Actions */}
                <div className="flex justify-end space-x-3 pt-4">
                  <button
                    type="button"
                    onClick={handleClose}
                    className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 dark:bg-gray-700 dark:text-gray-300 dark:border-gray-600 dark:hover:bg-gray-600"
                    disabled={submitting}
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    className="px-4 py-2 text-sm font-medium text-white bg-indigo-600 border border-transparent rounded-md hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed"
                    disabled={submitting || !selectedOrderType || selectedItems.length === 0}
                  >
                    {submitting ? 'Creating...' : 'Create Order'}
                  </button>
                </div>

              </form>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}

export default CreateOrderModal;
