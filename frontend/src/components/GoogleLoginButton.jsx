import { GoogleLogin } from '@react-oauth/google';
import axios from 'axios';

function GoogleLoginButton() {
    const handleSuccess = async (credentialResponse) => {
        try {
          const response = await axios.post(
            'http://localhost:8000/api/google/validate_token/',
            { credential: credentialResponse.credential },
            { 
              withCredentials: true,
              headers: {
                'Content-Type': 'application/json',
                // If you're using a token-based approach in other parts of your app
                // 'Authorization': 'Bearer ' + localStorage.getItem('access')
              }
            }
          );
          
          console.log('Login success:', response.data);
        } catch (error) {
          console.error('Login error:', error);
        }
      };

  return (
    <div>
      <h2>Sign in with Google</h2>
      <GoogleLogin
        onSuccess={handleSuccess}
        onError={() => console.log('Login Failed')}
        useOneTap
      />
    </div>
  );
}

export default GoogleLoginButton;