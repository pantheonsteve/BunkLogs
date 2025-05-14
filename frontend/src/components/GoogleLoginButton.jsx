import { GoogleLogin } from '@react-oauth/google';
import axios from 'axios';

const GoogleLoginButton = () => {
    const handleClick = () => {
      window.location.href = 'http://localhost:8000/api/auth/google/';
    };
  
    return (
      <button onClick={handleClick} className="google-login-button">
        Login with Google
      </button>
    );
  };

export default GoogleLoginButton;