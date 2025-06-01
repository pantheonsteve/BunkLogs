import React, { useState, useEffect } from "react";
import { Link, useParams, useNavigate } from "react-router-dom";
import { getPasswordReset, resetPassword } from "../lib/allauth";

import AuthImage from "../images/auth-image.jpg";

function ResetPasswordConfirm() {
  const { key } = useParams();
  const navigate = useNavigate();
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isSuccess, setIsSuccess] = useState(false);
  const [isValidKey, setIsValidKey] = useState(null);

  useEffect(() => {
    const validateKey = async () => {
      if (!key) {
        setError("Invalid reset link");
        setIsValidKey(false);
        return;
      }

      try {
        setIsLoading(true);
        const response = await getPasswordReset(key);
        
        if (response.status === 200) {
          setIsValidKey(true);
        } else {
          setIsValidKey(false);
          setError("This password reset link is invalid or has expired.");
        }
      } catch (error) {
        console.error("Key validation error:", error);
        setIsValidKey(false);
        setError("This password reset link is invalid or has expired.");
      } finally {
        setIsLoading(false);
      }
    };

    validateKey();
  }, [key]);

  const validatePasswords = () => {
    if (!password || !confirmPassword) {
      setError("Both password fields are required");
      return false;
    }

    if (password.length < 8) {
      setError("Password must be at least 8 characters long");
      return false;
    }

    if (password !== confirmPassword) {
      setError("Passwords do not match");
      return false;
    }

    return true;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");

    if (!validatePasswords()) {
      return;
    }

    setIsLoading(true);

    try {
      const response = await resetPassword({
        key,
        password,
        password_confirm: confirmPassword
      });
      
      if (response.status === 200) {
        setIsSuccess(true);
        setTimeout(() => {
          navigate("/signin", { 
            state: { message: "Your password has been successfully reset. Please sign in with your new password." }
          });
        }, 3000);
      } else {
        setError("Failed to reset password. Please try again.");
      }
    } catch (error) {
      console.error("Password reset error:", error);
      
      if (error.response?.status === 400) {
        const data = error.response.data;
        if (data.password) {
          setError(data.password[0] || "Invalid password");
        } else if (data.password_confirm) {
          setError(data.password_confirm[0] || "Password confirmation error");
        } else {
          setError("Please check your passwords and try again");
        }
      } else {
        setError("Failed to reset password. Please try again.");
      }
    } finally {
      setIsLoading(false);
    }
  };

  if (isValidKey === null) {
    return (
      <main className="bg-white dark:bg-gray-900">
        <div className="relative md:flex">
          <div className="md:w-1/2">
            <div className="min-h-[100dvh] h-full flex flex-col after:flex-1">
              <div className="max-w-sm mx-auto w-full px-4 py-8">
                <div className="text-center">
                  <div className="spinner-border" role="status">
                    <span className="sr-only">Loading...</span>
                  </div>
                  <p className="mt-4">Validating reset link...</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </main>
    );
  }

  if (!isValidKey) {
    return (
      <main className="bg-white dark:bg-gray-900">
        <div className="relative md:flex">
          <div className="md:w-1/2">
            <div className="min-h-[100dvh] h-full flex flex-col after:flex-1">
              <div className="flex-1">
                <div className="flex items-center justify-between h-16 px-4 sm:px-6 lg:px-8">
                  <Link className="block" to="/">
                    <svg className="fill-violet-500" xmlns="http://www.w3.org/2000/svg" width={32} height={32}>
                      <path d="M31.956 14.8C31.372 6.92 25.08.628 17.2.044V5.76a9.04 9.04 0 0 0 9.04 9.04h5.716ZM14.8 26.24v5.716C6.92 31.372.63 25.08.044 17.2H5.76a9.04 9.04 0 0 1 9.04 9.04Zm11.44-9.04h5.716c-.584 7.88-6.876 14.172-14.756 14.756V26.24a9.04 9.04 0 0 1 9.04-9.04ZM.044 14.8C.63 6.92 6.92.628 14.8.044V5.76a9.04 9.04 0 0 1-9.04 9.04H.044Z" />
                    </svg>
                  </Link>
                </div>
              </div>

              <div className="max-w-sm mx-auto w-full px-4 py-8">
                <h1 className="text-3xl text-gray-800 dark:text-gray-100 font-bold mb-6">Invalid Reset Link</h1>
                
                <div className="mb-4 p-4 bg-red-100 border border-red-400 text-red-700 rounded">
                  <svg className="w-6 h-6 mx-auto mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12"></path>
                  </svg>
                  {error}
                </div>

                <p className="text-gray-600 dark:text-gray-400 mb-6">
                  Please request a new password reset link.
                </p>

                <div className="flex justify-between items-center">
                  <Link 
                    className="text-sm text-violet-500 hover:text-violet-600 dark:hover:text-violet-400" 
                    to="/signin"
                  >
                    ← Back to Sign In
                  </Link>
                  <Link 
                    to="/reset-password"
                    className="btn bg-violet-500 text-white hover:bg-violet-600 dark:bg-violet-600 dark:hover:bg-violet-700"
                  >
                    Request New Link
                  </Link>
                </div>
              </div>
            </div>
          </div>

          <div className="hidden md:block absolute top-0 bottom-0 right-0 md:w-1/2" aria-hidden="true">
            <img className="object-cover object-center w-full h-full" src={AuthImage} width="760" height="1024" alt="Authentication" />
          </div>
        </div>
      </main>
    );
  }

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
              <h1 className="text-3xl text-gray-800 dark:text-gray-100 font-bold mb-6">Set New Password</h1>
              
              {isSuccess ? (
                <div className="text-center">
                  <div className="mb-4 p-4 bg-green-100 border border-green-400 text-green-700 rounded">
                    <svg className="w-6 h-6 mx-auto mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 13l4 4L19 7"></path>
                    </svg>
                    Your password has been successfully reset! Redirecting to sign in...
                  </div>
                </div>
              ) : (
                <>
                  <p className="text-gray-600 dark:text-gray-400 mb-6">
                    Enter your new password below.
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
                        <label className="block text-sm font-medium mb-1" htmlFor="password">
                          New Password <span className="text-red-500">*</span>
                        </label>
                        <input 
                          id="password" 
                          className="form-input w-full" 
                          type="password" 
                          value={password}
                          onChange={(e) => setPassword(e.target.value)}
                          required
                          disabled={isLoading}
                          minLength={8}
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium mb-1" htmlFor="confirmPassword">
                          Confirm New Password <span className="text-red-500">*</span>
                        </label>
                        <input 
                          id="confirmPassword" 
                          className="form-input w-full" 
                          type="password" 
                          value={confirmPassword}
                          onChange={(e) => setConfirmPassword(e.target.value)}
                          required
                          disabled={isLoading}
                          minLength={8}
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
                        {isLoading ? "Updating..." : "Update Password"}
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

export default ResetPasswordConfirm;
