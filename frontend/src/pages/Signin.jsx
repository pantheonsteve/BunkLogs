import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import ProviderList from '../socialaccount/ProviderList';
import SocialLoginButton from "../components/SocialLoginButton";
import api from "../api";

import AuthImage from "../images/auth-image.jpg";

function Signin() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const navigate = useNavigate();
  const { login } = useAuth();
  
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
                <Link className="block" to="/">
                  <svg className="fill-violet-500" xmlns="http://www.w3.org/2000/svg" width={32} height={32}>
                    <path d="M31.956 14.8C31.372 6.92 25.08.628 17.2.044V5.76a9.04 9.04 0 0 0 9.04 9.04h5.716ZM14.8 26.24v5.716C6.92 31.372.63 25.08.044 17.2H5.76a9.04 9.04 0 0 1 9.04 9.04Zm11.44-9.04h5.716c-.584 7.88-6.876 14.172-14.756 14.756V26.24a9.04 9.04 0 0 1 9.04-9.04ZM.044 14.8C.63 6.92 6.92.628 14.8.044V5.76a9.04 9.04 0 0 1-9.04 9.04H.044Z" />
                  </svg>
                </Link>
              </div>
            </div>

            <div className="max-w-sm mx-auto w-full px-4 py-8">
              <h1 className="text-3xl text-gray-800 dark:text-gray-100 font-bold mb-2">Welcome back!</h1>
              <p className="text-gray-600 dark:text-gray-400 mb-6">Sign in to your account to continue</p>
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
                {/* Warning */}
                <div className="mt-5">
                  <div className="bg-yellow-500/20 text-yellow-700 px-3 py-2 rounded-sm">
                    <svg className="inline w-3 h-3 shrink-0 fill-current mr-2" viewBox="0 0 12 12">
                      <path d="M10.28 1.28L3.989 7.575 1.695 5.28A1 1 0 00.28 6.695l3 3a1 1 0 001.414 0l7-7A1 1 0 0010.28 1.28z" />
                    </svg>
                    <span className="text-sm">To support you during the pandemic super pro features are free until March 31st.</span>
                  </div>
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
