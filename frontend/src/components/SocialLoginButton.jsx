import { getCSRFToken } from "../utils/cookies";
import { useEffect } from "react";

function SocialLoginButton({ provider = "GoogleOAuth" }) {

  useEffect(() => {
    fetch("http://localhost:8000/api/get-csrf-token/", {
      credentials: "include"
    });
  }, []);

  const handleLogin = () => {
    // Get backend URL from env or default
    const backendUrl = import.meta.env.VITE_API_URL || "http://localhost:8000";
    const callbackUrl = "http://localhost:8000/api/auth/google/callback/";
    
    console.log("Initiating social login with:", {
      provider,
      callbackUrl,
      csrfToken: getCSRFToken()
    });
    
    // Create and submit a form
    const form = document.createElement("form");
    form.method = "POST";
    form.action = `${backendUrl}/_allauth/browser/v1/auth/provider/redirect`;
    
    // Add form data
    const formData = {
      provider: provider, // Now it will use "GoogleOAuth"
      callback_url: callbackUrl,
      csrfmiddlewaretoken: getCSRFToken() || "",
      process: "login"
    };
    
    // Create and append input fields
    Object.entries(formData).forEach(([key, value]) => {
      const input = document.createElement("input");
      input.type = "hidden";
      input.name = key;
      input.value = value;
      form.appendChild(input);
    });
    
    // Append and submit form
    document.body.appendChild(form);
    console.log("Form action:", form.action);
    console.log("Form data:", formData);

    //debugger;
    
    form.submit();
  };

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