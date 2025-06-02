import React, { useState } from "react";
import { Link, NavLink } from "react-router-dom";
import { requestPasswordReset } from "../lib/allauth";

import AuthImage from "../images/crane_lake/DSC_1985.png";
import CampLogo from "../images/clc-logo.jpeg";

function ResetPassword() {
  const [email, setEmail] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isSuccess, setIsSuccess] = useState(false);

  const validateEmail = (email) => {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setMessage("");

    if (!email) {
      setError("Email address is required");
      return;
    }

    if (!validateEmail(email)) {
      setError("Please enter a valid email address");
      return;
    }

    setIsLoading(true);

    try {
      const response = await requestPasswordReset(email);
      
      if (response.status === 200) {
        setIsSuccess(true);
        setMessage("Password reset instructions have been sent to your email address. Please check your inbox.");
      } else {
        setError("Failed to send reset email. Please try again.");
      }
    } catch (error) {
      console.error("Password reset error:", error);
      
      if (error.response?.status === 400) {
        setError("Please check your email address and try again");
      } else if (error.response?.data?.email) {
        setError(error.response.data.email[0] || "Invalid email address");
      } else {
        setError("Failed to send reset email. Please try again.");
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
                <NavLink end to="/" className="block">
                  <img className="shrink-0 mr-2 sm:mr-3" width="70" height="35" viewBox="0 0 36 36" src={CampLogo} />
                </NavLink>
              </div>
            </div>

            <div className="max-w-sm mx-auto w-full px-4 py-8">
              <h1 className="text-3xl text-gray-800 dark:text-gray-100 font-bold mb-6">Reset your Password</h1>
              
              {isSuccess ? (
                <div className="text-center">
                  <div className="mb-4 p-4 bg-green-100 border border-green-400 text-green-700 rounded">
                    <svg className="w-6 h-6 mx-auto mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 13l4 4L19 7"></path>
                    </svg>
                    {message}
                  </div>
                  <Link 
                    to="/signin" 
                    className="btn bg-violet-500 text-white hover:bg-violet-600 dark:bg-violet-600 dark:hover:bg-violet-700"
                  >
                    Back to Sign In
                  </Link>
                </div>
              ) : (
                <>
                  <p className="text-gray-600 dark:text-gray-400 mb-6">
                    Enter your email address and we'll send you instructions to reset your password.
                  </p>
                  
                  {error && (
                    <div className="mb-4 p-3 bg-red-100 border border-red-400 text-red-700 rounded">
                      {error}
                    </div>
                  )}

                  {/* Form */}
                  <form onSubmit={handleSubmit}>
                    <div className="space-y-4">
                      <div>
                        <label className="block text-sm font-medium mb-1" htmlFor="email">
                          Email Address <span className="text-red-500">*</span>
                        </label>
                        <input 
                          id="email" 
                          className="form-input w-full" 
                          type="email" 
                          value={email}
                          onChange={(e) => setEmail(e.target.value)}
                          required
                          disabled={isLoading}
                        />
                      </div>
                    </div>
                    <div className="flex justify-between items-center mt-6">
                      <Link 
                        className="text-sm text-violet-500 hover:text-violet-600 dark:hover:text-violet-400" 
                        to="/signin"
                      >
                        ← Back to Sign In
                      </Link>
                      <button 
                        type="submit"
                        disabled={isLoading}
                        className="btn bg-violet-500 text-white hover:bg-violet-600 dark:bg-violet-600 dark:hover:bg-violet-700 whitespace-nowrap disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        {isLoading ? "Sending..." : "Send Reset Link"}
                      </button>
                    </div>
                  </form>
                </>
              )}
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

export default ResetPassword;
