// src/components/CSRFDebug.jsx
import React, { useEffect, useState } from 'react';

const CSRFDebug = () => {
  const [csrfToken, setCsrfToken] = useState(null);
  const [cookies, setCookies] = useState('');
  
  useEffect(() => {
    // Get CSRF token from cookies
    const getCSRFToken = () => {
      let cookieValue = null;
      if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
          const cookie = cookies[i].trim();
          if (cookie.substring(0, 'csrftoken='.length) === 'csrftoken=') {
            cookieValue = decodeURIComponent(cookie.substring('csrftoken='.length));
            break;
          }
        }
      }
      return cookieValue;
    };
    
    setCsrfToken(getCSRFToken());
    setCookies(document.cookie);
    
    // Try to get a CSRF token by making a request to the backend
    fetch('http://localhost:8000/', {
      credentials: 'include',
    })
    .then(() => {
      setCsrfToken(getCSRFToken());
      setCookies(document.cookie);
    })
    .catch(err => console.error('Error fetching CSRF token:', err));
  }, []);
  
  return (
    <div className="mt-4 p-4 bg-gray-100 rounded text-sm text-left">
      <h3 className="font-bold">Debug Information:</h3>
      <p>CSRF Token: {csrfToken ? `✅ Present (${csrfToken.substring(0, 6)}...)` : '❌ Missing'}</p>
      <details>
        <summary className="cursor-pointer">All Cookies (click to view)</summary>
        <pre className="whitespace-pre-wrap text-xs mt-2">{cookies || 'No cookies found'}</pre>
      </details>
    </div>
  );
};

export default CSRFDebug;