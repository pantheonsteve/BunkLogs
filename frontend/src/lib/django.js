// Cache for CSRF token
let cachedCSRFToken = null;

function getCookie (name) {
    let cookieValue = null
    if (document.cookie && document.cookie !== '') {
      const cookies = document.cookie.split(';')
      for (let i = 0; i < cookies.length; i++) {
        const cookie = cookies[i].trim()
        // Does this cookie string begin with the name we want?
        if (cookie.substring(0, name.length + 1) === (name + '=')) {
          cookieValue = decodeURIComponent(cookie.substring(name.length + 1))
          break
        }
      }
    }
    return cookieValue
  }

  // Enhanced CSRF token function that tries multiple methods
  export function getCSRFToken () {
    // First try to get from cookies (works for same-domain)
    // CRITICAL FIX: Check production cookie name FIRST
    const cookieToken = getCookie('__Secure-csrftoken') || getCookie('csrftoken');
    if (cookieToken) {
      console.log('CSRF token from cookie:', cookieToken.substring(0, 6) + '...');
      return cookieToken;
    }

    // Return cached token if available
    if (cachedCSRFToken) {
      console.log('CSRF token from cache:', cachedCSRFToken.substring(0, 6) + '...');
      return cachedCSRFToken;
    }

    console.warn('No CSRF token available - this may cause API requests to fail');
    
    // Try to fetch from server synchronously as a last resort (not recommended but needed for allauth)
    try {
      const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
      // This is a synchronous XMLHttpRequest - not ideal but necessary for allauth compatibility
      const xhr = new XMLHttpRequest();
      xhr.open('GET', `${apiUrl}/api/get-csrf-token/`, false); // false = synchronous
      xhr.withCredentials = true;
      xhr.send();
      
      if (xhr.status === 200) {
        const data = JSON.parse(xhr.responseText);
        cachedCSRFToken = data.csrfToken;
        console.log('CSRF token fetched synchronously:', cachedCSRFToken.substring(0, 6) + '...');
        return cachedCSRFToken;
      }
    } catch (error) {
      console.error('Failed to fetch CSRF token synchronously:', error);
    }

    // Return null as last resort
    return null;
    return null;
  }