import { redirectToProvider, AuthProcess } from "../lib/allauth";
import { useConfig } from "../context/AllAuthContext";

function SocialLoginButton({ provider = "google" }) {
  const { config, loading } = useConfig();

  const handleLogin = async () => {
    console.log("Initiating social login with provider:", provider);
    
    // Check if provider is available
    const providers = config?.socialaccount?.providers || [];
    const availableProvider = providers.find(p => p.id === provider);
    
    if (!availableProvider) {
      console.error(`Provider ${provider} is not available. Available providers:`, providers);
      alert(`${provider} login is not configured. Please contact support.`);
      return;
    }

    try {
      // Call your custom Google OAuth endpoint to get the auth URL
      const response = await fetch(`${import.meta.env.VITE_API_URL || 'https://admin.bunklogs.net'}/api/auth/google/`, {
        method: 'GET',
        credentials: 'include',
        headers: {
          'Accept': 'application/json',
        }
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();
      console.log("Got auth URL:", data.auth_url);

      // Redirect to Google OAuth
      window.location.href = data.auth_url;
      
    } catch (error) {
      console.error("Error getting Google auth URL:", error);
      alert("Failed to initiate Google login. Please try again.");
    }
  };

  // Don't render if config is still loading
  if (loading) {
    return (
      <button 
        disabled
        className="w-full flex justify-center py-2 px-4 border border-gray-300 rounded-md shadow-sm bg-gray-100 text-sm font-medium text-gray-400"
      >
        <div className="animate-spin rounded-full h-4 w-4 border-t-2 border-b-2 border-gray-400 mr-2"></div>
        Loading...
      </button>
    );
  }

  return (
    <button 
      onClick={handleLogin}
      className="w-full flex justify-center py-2 px-4 border border-gray-300 rounded-md shadow-sm bg-white text-sm font-medium text-gray-500 hover:bg-gray-50"
    >
      <svg className="w-5 h-5 mr-2" viewBox="0 0 24 24" fill="currentColor">
        <path d="M12.545,10.239v3.821h5.445c-0.712,2.315-2.647,3.972-5.445,3.972c-3.332,0-6.033-2.701-6.033-6.032 s2.701-6.032,6.033-6.032c1.498,0,2.866,0.549,3.921,1.453l2.814-2.814C17.503,2.988,15.139,2,12.545,2 C7.021,2,2.543,6.477,2.543,12s4.478,10,10.002,10c8.396,0,10.249-7.85,9.426-11.748L12.545,10.239z"/>
      </svg>
      Sign in with {provider.charAt(0).toUpperCase() + provider.slice(1)}
    </button>
  );
}

export default SocialLoginButton;