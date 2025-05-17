import React from 'react';

const ErrorMessage = ({ message, onDismiss }) => {
  if (!message) return null;
  
  return (
    <div style={{
      backgroundColor: '#ffebee',
      color: '#c62828',
      padding: '10px 16px',
      borderRadius: '4px',
      margin: '10px 0',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      fontSize: '14px',
    }}>
      <div style={{ display: 'flex', alignItems: 'center' }}>
        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ marginRight: '8px' }}>
          <circle cx="12" cy="12" r="10"></circle>
          <line x1="12" y1="8" x2="12" y2="12"></line>
          <line x1="12" y1="16" x2="12.01" y2="16"></line>
        </svg>
        {message}
      </div>
      {onDismiss && (
        <button 
          onClick={onDismiss}
          style={{
            background: 'none',
            border: 'none',
            cursor: 'pointer',
            color: '#c62828',
            fontWeight: 'bold',
            fontSize: '16px',
          }}
          aria-label="Dismiss error"
        >
          ×
        </button>
      )}
    </div>
  );
};

export default ErrorMessage;