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
    const cookieToken = getCookie('csrftoken') || getCookie('__Secure-csrftoken');
    if (cookieToken) {
      console.log('CSRF token from cookie:', cookieToken.substring(0, 6) + '...');
      return cookieToken;
    }

    // Return cached token if available
    if (cachedCSRFToken) {
      console.log('CSRF token from cache:', cachedCSRFToken.substring(0, 6) + '...');
      return cachedCSRFToken;
    }

    console.log('No CSRF token available - fetching from server asynchronously');
    
    // Fetch from server asynchronously and cache it
    const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
    fetch(`${apiUrl}/api/get-csrf-token/`, {
      credentials: 'include'
    })
    .then(response => response.json())
    .then(data => {
      cachedCSRFToken = data.csrfToken;
      console.log('CSRF token fetched from server:', cachedCSRFToken.substring(0, 6) + '...');
    })
    .catch(error => {
      console.warn('Failed to fetch CSRF token from server:', error);
    });

    // Return null for now - the async fetch will cache it for next time
    return null;
  }