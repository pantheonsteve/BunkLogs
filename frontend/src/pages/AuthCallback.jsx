import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';

function AuthCallback() {
  const [status, setStatus] = useState('Processing authentication...');
  const navigate = useNavigate();
  const { login } = useAuth();

  useEffect(() => {
    // Extract tokens from URL hash
    const processAuth = () => {
      try {
        // URL format: /auth/callback#access_token=xxx&refresh_token=yyy
        const hash = window.location.hash.substring(1);
        const params = new URLSearchParams(hash);
        
        const accessToken = params.get('access_token');
        const refreshToken = params.get('refresh_token');
        
        if (!accessToken) {
          setStatus('Authentication failed. No token received.');
          setTimeout(() => navigate('/signin'), 2000);
          return;
        }
        
        // Store tokens and update auth context
        login({ 
          access_token: accessToken, 
          refresh_token: refreshToken 
        });
        
        setStatus('Authentication successful! Redirecting...');
        setTimeout(() => navigate('/dashboard'), 1000);
      } catch (error) {
        console.error('Auth callback error:', error);
        setStatus('Authentication error: ' + error.message);
        setTimeout(() => navigate('/signin'), 2000);
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