import React, { useState, useEffect, useRef } from 'react';
import api from '../../api';
import { useLocation, useNavigate, useParams } from 'react-router-dom';
import Wysiwyg from './Wysiwyg';
import { useAuth } from '../../auth/AuthContext';

function CounselorLogForm({ date, existingLog, onClose, token: propsToken, viewOnly = false }) {
  const location = useLocation();
  const navigate = useNavigate();
  const params = useParams();
  const auth = useAuth();
  
  // Priority chain: 1. Props token 2. Auth context token 3. localStorage token
  const token = propsToken || auth?.token || localStorage.getItem('access_token');
  
  // Use props or fallback to params
  const dateToUse = date || (location.state?.selectedDate 
    ? new Date(location.state.selectedDate).toISOString().split('T')[0]
    : new Date().toISOString().split('T')[0]);
  
  // Check if user can edit based on role and date
  const canEdit = () => {
    const currentUser = auth?.user;
    
    if (!currentUser) {
      return false;
    }
    
    // Admin and staff can always edit
    if (currentUser.is_staff || currentUser.role === 'Admin') {
      return true;
    }
    
    // Only counselors can create/edit counselor logs
    if (currentUser.role === 'Counselor') {
      // Check if there's an existing log
      if (existingCounselorLog) {
        // Must be the original counselor AND editing on the day it was created
        const now = new Date();
        const today = now.getFullYear() + '-' + 
                     String(now.getMonth() + 1).padStart(2, '0') + '-' + 
                     String(now.getDate()).padStart(2, '0');
        
        const logCreatedDate = existingCounselorLog.created_at ? 
          (() => {
            const createdAt = new Date(existingCounselorLog.created_at);
            return createdAt.getFullYear() + '-' + 
                   String(createdAt.getMonth() + 1).padStart(2, '0') + '-' + 
                   String(createdAt.getDate()).padStart(2, '0');
          })() : 
          dateToUse;
        
        const canEditExisting = String(existingCounselorLog.counselor) === String(currentUser.id) && today === logCreatedDate;
        return canEditExisting;
      }
      
      // For new logs, counselors can only create logs for today or past dates (no future dates)
      const now = new Date();
      const today = now.getFullYear() + '-' + 
                   String(now.getMonth() + 1).padStart(2, '0') + '-' + 
                   String(now.getDate()).padStart(2, '0');
      const logDate = dateToUse;
      
      if (logDate > today) {
        return false; // Cannot create logs for future dates
      }
      
      // If there's no existing log and date is valid, counselors can create new logs
      return true;
    }
    
    return false;
  };
  
  // Check if the selected date is in the future
  const isDateInFuture = () => {
    const now = new Date();
    const today = now.getFullYear() + '-' + 
                 String(now.getMonth() + 1).padStart(2, '0') + '-' + 
                 String(now.getDate()).padStart(2, '0');
    return dateToUse > today;
  };
  
  // For WYSIWYG editors
  const elaborationRef = useRef(null);
  const valuesReflectionRef = useRef(null);
  
  // State for counselor log data
  const [counselorLogData, setCounselorLogData] = useState(null);
  const [existingCounselorLog, setExistingCounselorLog] = useState(null);

  // Check if an existing counselor log is available
  const hasExistingCounselorLog = existingCounselorLog ? true : false;
  
  // View/Edit mode toggle - start in view mode if there's existing data, user can't edit, or viewOnly prop is true
  const [isViewMode, setIsViewMode] = useState(viewOnly || false);

  // Form state
  const [formData, setFormData] = useState({
    counselor: auth?.user?.id || '',
    date: dateToUse,
    day_quality_score: 3,
    support_level_score: 3,
    elaboration: '',
    day_off: false,
    staff_care_support_needed: false,
    values_reflection: '',
  });

  // Pre-select the logged-in counselor
  useEffect(() => {
    if (auth?.user?.id) {
      setFormData(prev => ({
        ...prev,
        counselor: auth.user.id
      }));
    }
  }, [auth?.user?.id]);

  // Fetch existing counselor log data when component loads
  useEffect(() => {
    // If existingLog is passed as prop, use it directly
    if (existingLog) {
      console.log('Using existing log from props:', existingLog);
      setExistingCounselorLog(existingLog);
      
      // Update form data with existing log
      setFormData(prev => ({
        ...prev,
        ...existingLog,
        date: dateToUse,
      }));
      
      // Set content for WYSIWYG editors after a delay
      setTimeout(() => {
        if (elaborationRef.current && existingLog.elaboration) {
          elaborationRef.current.setContent(existingLog.elaboration);
        }
        if (valuesReflectionRef.current && existingLog.values_reflection) {
          valuesReflectionRef.current.setContent(existingLog.values_reflection);
        }
      }, 100);
      
      // Start in view mode if viewOnly prop is true, there's existing data and user can't edit
      setIsViewMode(viewOnly || !canEdit());
      return;
    }

    async function fetchCounselorLogData() {
      if (!auth?.user?.id || !dateToUse) return;
      
      try {
        // Get the latest token directly from localStorage to ensure it's current
        const currentToken = localStorage.getItem('access_token');        // Check if token exists
        if (!currentToken) {
          setError('Authentication required. Please log in again.');
          return;
        }

        console.log('Fetching counselor log data for date:', dateToUse);
        
        const headers = {
          'Authorization': `Bearer ${currentToken}`
        };
        
        // Try to get existing counselor log for this date
        const response = await api.get(
          `/api/v1/counselorlogs/?date=${dateToUse}`,
          { headers }
        );
        
        if (response.data && response.data.results && response.data.results.length > 0) {
          const existingLog = response.data.results[0];
          setExistingCounselorLog(existingLog);
          
          // Update form data with existing log
          setFormData(prev => ({
            ...prev,
            ...existingLog,
            date: dateToUse,
          }));
          
          // Set content for WYSIWYG editors after a delay
          setTimeout(() => {
            if (elaborationRef.current && existingLog.elaboration) {
              elaborationRef.current.setContent(existingLog.elaboration);
            }
            if (valuesReflectionRef.current && existingLog.values_reflection) {
              valuesReflectionRef.current.setContent(existingLog.values_reflection);
            }
          }, 100);
          
          // Start in view mode if viewOnly prop is true, there's existing data and user can't edit
          setIsViewMode(viewOnly || !canEdit());
        }
        
      } catch (err) {
        console.error('Error fetching counselor log data:', err);
        if (err.response?.status === 401) {
          setError('Authentication expired. Please log in again.');
        } else if (err.response?.status === 404) {
          // No existing log found, which is fine
          console.log('No existing counselor log found for this date');
        } else {
          setError('Failed to load counselor log data');
        }
      }
    }
    
    fetchCounselorLogData();
  }, [auth?.user?.id, dateToUse, existingLog]);

  // Loading state
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(false);

  // Handle form input changes
  const handleChange = (e) => {
    if (isViewMode) return; // Don't update form in view mode
    
    const { name, value, type, checked } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value,
    }));
  };
  
  // Client-side validation function for counselor logs
  const validateCounselorForm = () => {
    const errors = [];
    
    // Validate date constraints for counselors - use local timezone to avoid UTC conversion issues
    const now = new Date();
    const today = now.getFullYear() + '-' + 
                  String(now.getMonth() + 1).padStart(2, '0') + '-' + 
                  String(now.getDate()).padStart(2, '0');
    
    const thirtyDaysAgo = new Date();
    thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30);
    const thirtyDaysAgoStr = thirtyDaysAgo.getFullYear() + '-' + 
                            String(thirtyDaysAgo.getMonth() + 1).padStart(2, '0') + '-' + 
                            String(thirtyDaysAgo.getDate()).padStart(2, '0');
    
    // Counselors can submit logs for today and past dates (up to 30 days back), but not future dates
    if (auth?.user?.role === 'Counselor') {
      if (formData.date > today) {
        errors.push('Cannot create logs for future dates');
      }
      
      if (formData.date < thirtyDaysAgoStr) {
        errors.push('⚠️ You can only submit counselor logs for today\'s date or up to 30 days back. Please select a more recent date.');
      }
    } else {
      // Admin/staff can submit for any reasonable date range
      const now = new Date();
      const today = now.getFullYear() + '-' + 
                   String(now.getMonth() + 1).padStart(2, '0') + '-' + 
                   String(now.getDate()).padStart(2, '0');
      
      if (formData.date > today) {
        errors.push('Cannot create logs for future dates');
      }
      
      if (formData.date < thirtyDaysAgoStr) {
        errors.push('Cannot create logs older than 30 days');
      }
    }
    
    // Validate required fields for work days
    if (!formData.day_off) {
      if (!formData.elaboration?.trim()) {
        errors.push('Elaboration is required for work days');
      }
      
      if (!formData.values_reflection?.trim()) {
        errors.push('Values reflection is required for work days');
      }
    }
    
    // Validate staff care support request
    if (formData.staff_care_support_needed && !formData.elaboration?.trim()) {
      errors.push('Please explain why you need staff care support in the elaboration field');
    }
    
    return errors;
  };

  // Handle form submission
  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (isViewMode) {
      return; // Don't submit in view mode
    }
    
    // Check permissions before submission
    if (!canEdit()) {
      setError('You do not have permission to submit this counselor log.');
      setLoading(false);
      return;
    }
    
    setLoading(true);
    setError(null);
    
    // Client-side validation
    const validationErrors = validateCounselorForm();
    if (validationErrors.length > 0) {
      setError(`Validation Error: ${validationErrors.join(', ')}`);
      setLoading(false);
      return;
    }
    
    // Get the latest token directly from localStorage
    const currentToken = localStorage.getItem('access_token');
    
    // Verify token exists before attempting submission
    if (!currentToken) {
      setError('Authentication required. Please log in again.');
      setLoading(false);
      return;
    }
    
    console.log('Form submission with token:', currentToken ? 'Token available' : 'No token');
    
    // Log complete form data including WYSIWYG content
    console.log('Form Data being submitted:', formData);
    
    try {
      const submissionData = { ...formData };
         // Convert scores to integers (they come from range inputs as strings)
    submissionData.day_quality_score = parseInt(submissionData.day_quality_score, 10);
    submissionData.support_level_score = parseInt(submissionData.support_level_score, 10);
    
    // Ensure counselor is an integer
    submissionData.counselor = parseInt(submissionData.counselor, 10);
      
      // Setup headers with proper authentication
      const headers = {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${currentToken}`
      };
      
      // Determine if this is an update or create based on existing counselor log
      const isUpdate = existingCounselorLog && existingCounselorLog.id;
      
      let response;
      if (isUpdate) {
        // Update existing counselor log using PUT
        response = await api.put(
          `/api/v1/counselorlogs/${existingCounselorLog.id}/`,
          submissionData,
          { headers }
        );
      } else {
        // Create new counselor log using POST
        response = await api.post(
          `/api/v1/counselorlogs/`,
          submissionData,
          { headers }
        );
      }
      
      if (response.status === 201 || response.status === 200) {
        setSuccess(true);
        
        // Close the modal and trigger data refresh
        setTimeout(() => {
          if (onClose) {
            // Pass true to onClose to indicate successful form submission
            onClose(true);
          } else {
            // When redirecting, go back to counselor dashboard
            navigate(`/counselor-dashboard`, { 
              state: { date: dateToUse },
              replace: true
            });
          }
        }, 100);
      } else {
        setError(`Unexpected response: ${response.status}`);
      }
      
    } catch (err) {
      console.error('Error submitting form:', err);
      
      // Log the specific non_field_errors to see the actual message
      if (err.response?.data?.non_field_errors) {
        console.error('Non-field errors:', err.response.data.non_field_errors);
      }
      
      if (err.response) {
        // Handle validation errors from our new model constraints
        if (err.response.status === 400 && err.response.data) {
          const validationErrors = err.response.data;
          
          // Handle specific validation error messages
          if (validationErrors.date) {
            setError(`Date Error: ${validationErrors.date}`);
          } else if (validationErrors.elaboration) {
            setError(`Elaboration Error: ${validationErrors.elaboration}`);
          } else if (validationErrors.values_reflection) {
            setError(`Values Reflection Error: ${validationErrors.values_reflection}`);
          } else if (validationErrors.__all__) {
            setError(`Validation Error: ${validationErrors.__all__}`);
          } else if (validationErrors.non_field_errors) {
            const nonFieldErrors = validationErrors.non_field_errors;
            
            // Special handling for duplicate log error
            if (nonFieldErrors.some(error => error.includes('already exists for this date'))) {
              setError('A reflection already exists for this date. The form will switch to edit mode.');
              
              // Try to fetch the existing log and switch to edit mode
              setTimeout(async () => {
                try {
                  const currentToken = localStorage.getItem('access_token');
                  const response = await api.get(
                    `/api/v1/counselorlogs/?date=${dateToUse}`,
                    { headers: { 'Authorization': `Bearer ${currentToken}` } }
                  );
                  
                  if (response.data && response.data.results && response.data.results.length > 0) {
                    const existingLog = response.data.results[0];
                    setExistingCounselorLog(existingLog);
                    
                    // Update form data with existing log
                    setFormData(prev => ({
                      ...prev,
                      ...existingLog,
                      date: dateToUse,
                    }));
                    
                    // Set content for WYSIWYG editors
                    setTimeout(() => {
                      if (elaborationRef.current && existingLog.elaboration) {
                        elaborationRef.current.setContent(existingLog.elaboration);
                      }
                      if (valuesReflectionRef.current && existingLog.values_reflection) {
                        valuesReflectionRef.current.setContent(existingLog.values_reflection);
                      }
                    }, 100);
                    
                    setError('Switched to edit mode for existing reflection.');
                  }
                } catch (fetchErr) {
                  console.error('Error fetching existing log:', fetchErr);
                }
              }, 1000);
              
              return;
            }
            
            errorMessage += `: ${nonFieldErrors.join(', ')}`;
          } else {
            // Show field-specific errors
            const fieldErrors = [];
            Object.keys(err.response.data).forEach(field => {
              if (Array.isArray(err.response.data[field])) {
                fieldErrors.push(`${field}: ${err.response.data[field].join(', ')}`);
              }
            });
            if (fieldErrors.length > 0) {
              errorMessage += `: ${fieldErrors.join('; ')}`;
            } else {
              errorMessage += ': Failed to submit counselor log';
            }
          }
        }
        
        setError(errorMessage);
      } else if (err.request) {
        setError('Network error: No response received from server');
      } else {
        setError(`Error: ${err.message}`);
      }
    } finally {
      setLoading(false);
    }
  };

  // Get counselor name for view mode
  const getCounselorName = () => {
    if (auth?.user) {
      return `${auth.user.first_name} ${auth.user.last_name}`;
    }
    return '';
  };

  return (
    <div className="max-w-4xl mx-auto bg-white dark:bg-gray-800 shadow-lg rounded-xl p-6">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold text-gray-800 dark:text-white">
          Counselor Daily Reflection
        </h1>
        
        {/* View/Edit Mode Toggle - Only show if there's an existing log */}
        {hasExistingCounselorLog && (
          <div className="flex items-center space-x-3">
            {/* Permission indicator when editing is restricted */}
            {!canEdit() && (
              <div className="flex items-center text-yellow-600 dark:text-yellow-400">
                <svg className="w-4 h-4 mr-1" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                </svg>
                <span className="text-xs">
                  {auth?.user?.role === 'Counselor' 
                    ? 'Can only edit on creation day - View only'
                    : 'View only'
                  }
                </span>
              </div>
            )}
            
            <div className="flex items-center">
              <span className="mr-2 text-sm text-gray-600 dark:text-gray-300">
                {isViewMode ? 'View Mode' : 'Edit Mode'}
              </span>
              <label className={`relative inline-flex items-center ${(canEdit() && !viewOnly) ? 'cursor-pointer' : 'cursor-not-allowed opacity-50'}`}>
                <input 
                  type="checkbox"
                  className="sr-only peer"
                  checked={!isViewMode}
                  onChange={() => (canEdit() && !viewOnly) && setIsViewMode(!isViewMode)}
                  disabled={!canEdit() || viewOnly}
                />
                <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 dark:peer-focus:ring-blue-800 rounded-full peer dark:bg-gray-700 peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all dark:border-gray-600 peer-checked:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed"></div>
              </label>
            </div>
          </div>
        )}
      </div>
      
      {/* Permission warning for creating new logs */}
      {!hasExistingCounselorLog && !canEdit() && (
        <div className="mb-6 p-4 bg-yellow-50 border border-yellow-200 text-yellow-800 rounded-lg">
          <div className="flex items-center">
            <svg className="w-5 h-5 mr-2" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
            </svg>
            <div>
              <h3 className="text-sm font-medium">Cannot Create Counselor Log</h3>
              <p className="text-sm mt-1">
                {isDateInFuture() 
                  ? "You cannot create logs for future dates. Please select today's date or a past date."
                  : "You do not have permission to create counselor logs."
                }
              </p>
            </div>
          </div>
        </div>
      )}
      
      {success && (
        <div className="mb-6 p-4 bg-green-100 border border-green-400 text-green-700 rounded">
          Counselor log successfully submitted!
        </div>
      )}
      
      {error && (
        <div className="mb-6 p-4 bg-red-100 border border-red-400 text-red-700 rounded">
          {error}
        </div>
      )}
      
      <form onSubmit={handleSubmit} className="space-y-6">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Date
            </label>
            <input 
              type="date" 
              value={dateToUse || ''} 
              readOnly 
              className="w-full px-4 py-2 border border-gray-300 rounded-md bg-gray-100 dark:bg-gray-700 dark:border-gray-600 cursor-not-allowed"
            />
            <p className="text-xs text-gray-500 mt-1">
              Date is set from the dashboard
            </p>
          </div>

          <div>
            <label htmlFor="counselor" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Counselor
            </label>
            <div className="w-full px-4 py-2 border border-gray-300 rounded-md bg-gray-100 dark:bg-gray-700 dark:border-gray-600 dark:text-white">
              {getCounselorName()}
            </div>
          </div>
        </div>

        {/* Day Off Checkbox */}
        <div className="space-y-2">
          <div className="flex items-center">
            {isViewMode ? (
              <>
                <div className={`h-5 w-5 border ${formData.day_off ? 'bg-blue-600' : 'bg-white'} border-gray-300 rounded`}>
                  {formData.day_off && (
                    <svg className="h-4 w-4 text-white mx-auto my-0.5" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
                      <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                    </svg>
                  )}
                </div>
                <label className="ml-2 block text-sm font-medium text-gray-700 dark:text-gray-300">
                  Day off
                </label>
              </>
            ) : (
              <>
                <input
                  id="day_off"
                  name="day_off"
                  type="checkbox"
                  className="h-5 w-5 text-blue-600 border-gray-300 rounded focus:ring-blue-500 dark:border-gray-600"
                  checked={formData.day_off}
                  onChange={handleChange}
                  disabled={isViewMode}
                />
                <label htmlFor="day_off" className="ml-2 block text-sm font-medium text-gray-700 dark:text-gray-300">
                  Day off
                </label>
              </>
            )}
          </div>
          <p className="text-xs text-gray-500">
            Check this if you are on a day off today.
          </p>
        </div>

        {/* Conditional Fields - Only show if not on day off */}
        {!formData.day_off && (
          <>
            {/* Score Sliders */}
            <div className="space-y-4">
              <h3 className="text-lg font-medium text-gray-800 dark:text-white">Daily Reflection Scores</h3>
              
              {/* Day Quality Score */}
              <div>
                <div className="flex justify-between items-center mb-1">
                  <label htmlFor="day_quality_score" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                    How was your day? {formData.day_quality_score}
                  </label>
                  <span className="text-sm text-gray-500">1-5</span>
                </div>
                <input
                  id="day_quality_score"
                  name="day_quality_score"
                  type="range"
                  min="1"
                  max="5"
                  className={`w-full h-2 bg-gray-200 rounded-lg appearance-none ${isViewMode ? 'cursor-not-allowed' : 'cursor-pointer'} dark:bg-gray-700`}
                  value={formData.day_quality_score}
                  onChange={handleChange}
                  disabled={isViewMode}
                />
                <div className="flex justify-between text-xs text-gray-500 mt-1">
                  <span>Terrible</span>
                  <span>Best day ever</span>
                </div>
              </div>
              
              {/* Support Level Score */}
              <div>
                <div className="flex justify-between items-center mb-1">
                  <label htmlFor="support_level_score" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                    How supported did you feel today? {formData.support_level_score}
                  </label>
                  <span className="text-sm text-gray-500">1-5</span>
                </div>
                <input
                  id="support_level_score"
                  name="support_level_score"
                  type="range"
                  min="1"
                  max="5"
                  className={`w-full h-2 bg-gray-200 rounded-lg appearance-none ${isViewMode ? 'cursor-not-allowed' : 'cursor-pointer'} dark:bg-gray-700`}
                  value={formData.support_level_score}
                  onChange={handleChange}
                  disabled={isViewMode}
                />
                <div className="flex justify-between text-xs text-gray-500 mt-1">
                  <span>Unsupported</span>
                  <span>Fully supported</span>
                </div>
              </div>
            </div>

            {/* Staff Care Support Checkbox */}
            <div className="flex items-center">
              {isViewMode ? (
                <>
                  <div className={`h-5 w-5 border ${formData.staff_care_support_needed ? 'bg-blue-600' : 'bg-white'} border-gray-300 rounded`}>
                    {formData.staff_care_support_needed && (
                      <svg className="h-4 w-4 text-white mx-auto my-0.5" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
                        <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                      </svg>
                    )}
                  </div>
                  <label className="ml-2 block text-sm font-medium text-gray-700 dark:text-gray-300">
                    I would like staff care/engagement support
                  </label>
                </>
              ) : (
                <>
                  <input
                    id="staff_care_support_needed"
                    name="staff_care_support_needed"
                    type="checkbox"
                    className="h-5 w-5 text-blue-600 border-gray-300 rounded focus:ring-blue-500 dark:border-gray-600"
                    checked={formData.staff_care_support_needed}
                    onChange={handleChange}
                    disabled={isViewMode}
                  />
                  <label htmlFor="staff_care_support_needed" className="ml-2 block text-sm font-medium text-gray-700 dark:text-gray-300">
                    I would like staff care/engagement support
                  </label>
                </>
              )}
            </div>
            
            {/* Elaboration WYSIWYG Editor */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Elaborate on why - positive or negative
              </label>
              <div className={`border border-gray-300 rounded-md dark:border-gray-600 overflow-hidden ${isViewMode ? 'quill-view-only' : ''}`}>
                <Wysiwyg 
                  ref={elaborationRef} 
                  value={formData.elaboration}
                  readOnly={isViewMode}
                  showToolbar={!isViewMode}
                  onChange={(content) => {
                    if (!isViewMode) {
                      console.log('Elaboration WYSIWYG onChange called with:', content);
                      setFormData(prev => ({ ...prev, elaboration: content }))
                    }
                  }}
                />
              </div>
            </div>

            {/* Values Reflection WYSIWYG Editor */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                How did the bunk exemplify our values today?
              </label>
              <div className={`border border-gray-300 rounded-md dark:border-gray-600 overflow-hidden ${isViewMode ? 'quill-view-only' : ''}`}>
                <Wysiwyg 
                  ref={valuesReflectionRef} 
                  value={formData.values_reflection}
                  readOnly={isViewMode}
                  showToolbar={!isViewMode}
                  onChange={(content) => {
                    if (!isViewMode) {
                      console.log('Values reflection WYSIWYG onChange called with:', content);
                      setFormData(prev => ({ ...prev, values_reflection: content }))
                    }
                  }}
                />
              </div>
            </div>
          </>
        )}

        {/* Submit/Save Button - Only show in edit mode and when user can edit */}
        {!isViewMode && canEdit() && (
          <div className="flex justify-end">
            <button
              type="submit"
              disabled={loading}
              className={`px-6 py-2 bg-blue-600 text-white rounded-md shadow-sm hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 ${
                loading ? 'opacity-70 cursor-not-allowed' : ''
              }`}
            >
              {loading 
                ? 'Saving...' 
                : (existingCounselorLog && existingCounselorLog.id ? 'Save Changes' : 'Submit Counselor Log')
              }
            </button>
          </div>
        )}
      </form>
    </div>
  );
}

export default CounselorLogForm;
