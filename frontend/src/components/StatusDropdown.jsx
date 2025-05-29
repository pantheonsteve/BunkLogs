import React, { useState } from 'react';
import api from '../api';

const STATUS_OPTIONS = [
  { value: 'submitted', label: 'Submitted', color: 'bg-blue-500/20 text-blue-700' },
  { value: 'pending', label: 'Pending', color: 'bg-yellow-500/20 text-yellow-700' },
  { value: 'completed', label: 'Completed', color: 'bg-green-500/20 text-green-700' },
  { value: 'cancelled', label: 'Cancelled', color: 'bg-red-500/20 text-red-700' },
];

function StatusDropdown({ orderId, currentStatus, onStatusUpdate, userRole, disabled = false }) {
  const [isOpen, setIsOpen] = useState(false);
  const [isUpdating, setIsUpdating] = useState(false);

  // Check if user can update status
  const canUpdateStatus = userRole === 'Admin' || userRole === 'Camper Care';
  
  // If user can't update status or it's disabled, just show the current status
  if (!canUpdateStatus || disabled) {
    const currentOption = STATUS_OPTIONS.find(option => option.value === currentStatus) || STATUS_OPTIONS[0];
    return (
      <div className={`inline-flex font-medium rounded-full text-center px-2.5 py-0.5 ${currentOption.color}`}>
        {currentOption.label}
      </div>
    );
  }

  const handleStatusChange = async (newStatus) => {
    if (newStatus === currentStatus || isUpdating) return;
    
    setIsUpdating(true);
    try {
      const response = await api.patch(`/api/orders/${orderId}/`, {
        order_status: newStatus
      });
      
      if (onStatusUpdate) {
        onStatusUpdate(orderId, newStatus, response.data);
      }
      
      setIsOpen(false);
    } catch (error) {
      console.error('Error updating order status:', error);
      alert('Failed to update order status. Please try again.');
    } finally {
      setIsUpdating(false);
    }
  };

  const currentOption = STATUS_OPTIONS.find(option => option.value === currentStatus) || STATUS_OPTIONS[0];

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        disabled={isUpdating}
        className={`inline-flex items-center font-medium rounded-full text-center px-2.5 py-0.5 transition-colors hover:bg-opacity-80 ${currentOption.color} ${isUpdating ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
      >
        {isUpdating ? (
          <>
            <svg className="animate-spin -ml-1 mr-1 h-3 w-3" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            Updating...
          </>
        ) : (
          <>
            {currentOption.label}
            <svg className="ml-1 h-3 w-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 9l-7 7-7-7" />
            </svg>
          </>
        )}
      </button>

      {isOpen && !isUpdating && (
        <>
          {/* Backdrop */}
          <div 
            className="fixed inset-0 z-10" 
            onClick={() => setIsOpen(false)}
          />
          
          {/* Dropdown */}
          <div className="absolute z-20 mt-1 w-40 bg-white dark:bg-gray-800 rounded-md shadow-lg border border-gray-200 dark:border-gray-700">
            <div className="py-1">
              {STATUS_OPTIONS.map((option) => (
                <button
                  key={option.value}
                  onClick={() => handleStatusChange(option.value)}
                  className={`w-full text-left px-3 py-2 text-sm transition-colors hover:bg-gray-100 dark:hover:bg-gray-700 ${
                    option.value === currentStatus 
                      ? 'bg-gray-50 dark:bg-gray-700' 
                      : ''
                  }`}
                >
                  <span className={`inline-flex font-medium rounded-full text-center px-2 py-0.5 text-xs ${option.color}`}>
                    {option.label}
                  </span>
                </button>
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  );
}

export default StatusDropdown;
