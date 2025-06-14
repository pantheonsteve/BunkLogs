import React, { useState, useEffect } from "react";
import { Link, useNavigate, useLocation, NavLink } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import ProviderList from '../socialaccount/ProviderList';
import CampLogo from "../../src/images/clc-logo.jpeg";
import SocialLoginButton from "../components/SocialLoginButton";
import api from "../api";

import AuthImage from "../images/crane_lake/DSC_1985.png";

function Signin() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [successMessage, setSuccessMessage] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();
  const { login } = useAuth();

  useEffect(() => {
    // Check for success message from signup
    if (location.state?.message) {
      setSuccessMessage(location.state.message);
      // Clear the state to prevent showing the message on refresh
      navigate(location.pathname, { replace: true });
    }
  }, [location, navigate]);
  
  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setIsLoading(true);
    
    try {
      // Call the JWT token endpoint
      const response = await api.post("/api/auth/token/", {
        email,
        password
      });
      
      console.log("Login successful:", response.data);
      
      // Store the tokens and user data
      const tokens = {
        access_token: response.data.access,
        refresh_token: response.data.refresh,
        user: response.data.user // Include user data from response
      };
      
      // Call the login function from AuthContext
      login(tokens);
      
      // Redirect to dashboard
      navigate("/dashboard");
    } catch (error) {
      console.error("Login error:", error);
      
      if (error.response?.status === 401) {
        setError("Invalid email or password");
      } else if (error.response?.data?.detail) {
        setError(error.response.data.detail);
      } else {
        setError("Login failed. Please try again.");
      }
    } finally {
      setIsLoading(false);
    }
  };
  return (
    <main className="bg-white dark:bg-gray-900">
      <div className="relative md:flex">
        {/* Content */}
        <div className="md:w-1/2">
          <div className="min-h-[100dvh] h-full flex flex-col after:flex-1">
            {/* Header */}
            <div className="flex-1">
              <div className="flex items-center justify-between h-16 px-4 sm:px-6 lg:px-8">
                {/* Logo */}
                {/* Logo */}
                <NavLink end to="/" className="block">
                  <img className="shrink-0 mr-2 sm:mr-3" width="70" height="35" viewBox="0 0 36 36" src={CampLogo} />
                </NavLink>
              </div>
            </div>

            <div className="max-w-sm mx-auto w-full px-4 py-8">
              <h1 className="text-3xl text-gray-800 dark:text-gray-100 font-bold mb-2">Crane Lake Camp Bunk Logs</h1>
              <p className="text-gray-600 dark:text-gray-400 mb-6">Welcome back! Sign in to your account to continue</p>
              
              {successMessage && (
                <div className="mb-4 p-3 bg-green-100 border border-green-400 text-green-700 rounded">
                  {successMessage}
                </div>
              )}

              {/* Form */}
              <form onSubmit={handleSubmit}>
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium mb-1" htmlFor="email">
                      Email Address
                    </label>
                    <input 
                      id="email" 
                      className="form-input w-full" 
                      type="email" 
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      required
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-1" htmlFor="password">
                      Password
                    </label>
                    <input 
                      id="password" 
                      className="form-input w-full" 
                      type="password" 
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      autoComplete="current-password" 
                      required
                    />
                  </div>
                  
                  {error && (
                    <div className="text-red-600 text-sm mt-1">
                      {error}
                    </div>
                  )}
                </div>
                
                <div className="flex items-center justify-between mt-6">
                  <div className="mr-1">
                    <Link className="text-sm underline hover:no-underline" to="/reset-password">
                      Forgot Password?
                    </Link>
                  </div>
                  <button
                    type="submit"
                    className="btn bg-violet-600 hover:bg-violet-700 text-white ml-3"
                    disabled={isLoading}
                  >
                    {isLoading ? "Signing in..." : "Sign In"}
                  </button>
                </div>
              </form>
              <h2>Or use a social account</h2>
              <SocialLoginButton />
              {/* Footer */}
              <div className="pt-5 mt-6 border-t border-gray-100 dark:border-gray-700/60">
                <div className="text-sm">
                  Don’t you have an account?{" "}
                  <Link className="font-medium text-violet-500 hover:text-violet-600 dark:hover:text-violet-400" to="/signup">
                    Sign Up
                  </Link>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Image */}
        <div className="hidden md:block absolute top-0 bottom-0 right-0 md:w-1/2" aria-hidden="true">
          <img className="object-cover object-center w-full h-full" src={AuthImage} width="760" height="1024" alt="Authentication" />
        </div>
      </div>
    </main>
  );
}

export default Signin;
