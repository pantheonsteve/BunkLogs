import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';
import { jwtDecode } from 'jwt-decode';
import api from '../api';

function AuthCallback() {
  const [status, setStatus] = useState('Processing authentication...');
  const navigate = useNavigate();
  const { login, isAuthenticated, loading } = useAuth();
  
  // Add logging for debugging authentication state
  useEffect(() => {
    console.log('Auth state in callback:', { isAuthenticated, loading });
  }, [isAuthenticated, loading]);

  useEffect(() => {
  const processAuth = async () => {
    try {
      // Process tokens as you're already doing
      const hash = window.location.hash.substring(1);
      const params = new URLSearchParams(hash);
      const accessToken = params.get('access_token');
      const refreshToken = params.get('refresh_token');
      
      if (!accessToken) {
        console.error('No access token found in URL');
        setStatus('Authentication failed. No token received.');
        return;
      }
      
      // Store tokens in localStorage
      localStorage.setItem('access_token', accessToken);
      if (refreshToken) {
        localStorage.setItem('refresh_token', refreshToken);
      }
      
      // Decode JWT to get user email
      const decoded = jwtDecode(accessToken);
      console.log('Decoded JWT:', decoded);
      let userEmail = decoded.email; // JWT should contain email
      let userId = decoded.user_id; // JWT should contain user_id
      
      // If email not in token, fetch from user endpoint
      if (!userEmail) {
        console.error('Email not found in token, fetching from user endpoint...');
        console.log(`/api/v1/users/${userId}`);
        const userResponse = await api.get(`/api/v1/users/${userId}`);
        console.log('User response:', userResponse.status);
        if (userResponse.status === 200) {
          userEmail = userResponse.data.email; // Get email from user response
          localStorage.setItem('user_profile', JSON.stringify(userResponse.data));
          // Get the JSON string from localStorage
          const userProfileString = localStorage.getItem('user_profile');

          // Parse the string into a JavaScript object
          const userProfile = JSON.parse(userProfileString);

          // Now you can access individual properties
          const { first_name, last_name, email, role } = userProfile;

          console.log(`Hello, ${first_name} ${last_name}`);
          console.log(`Email: ${email}`);
          console.log(`Role: ${role}`);
        }
      }
      
      // Now fetch user details using the email
      if (userEmail) {
        try {
          const profileResponse = await api.get(`/api/v1/users/email/${userEmail}/`);
          // Store full profile data
          localStorage.setItem('user_profile', JSON.stringify(profileResponse.data));
          
          // Important: Update the auth context with login
          login({ access_token: accessToken, refresh_token: refreshToken });
          
          setStatus('Authentication successful. Redirecting...');
        } catch (profileError) {
          console.error('Error fetching user profile:', profileError);
          setStatus('Error loading user profile.');
        }
      }
      
      // Wait briefly to ensure context is updated before redirect
      setTimeout(() => {
        navigate('/dashboard');
      }, 500);
    } catch (error) {
      console.error('Auth processing error:', error);
      setStatus('Authentication failed: ' + (error.message || 'Unknown error'));
    }
  };
  
    processAuth();
  }, [login, navigate]);

  return (
    <div className="flex justify-center items-center min-h-screen bg-gray-100">
      <div className="p-8 bg-white rounded shadow-md">
        <h1 className="text-2xl font-bold mb-4">Authentication</h1>
        <p className="text-gray-700">{status}</p>
      </div>
    </div>
  );
}

export default AuthCallback;