import React, { useState, useEffect, useRef } from 'react';
import api from '../../api';
import { useLocation, useNavigate, useParams } from 'react-router-dom';
import Wysiwyg from './Wysiwyg';
import { useAuth, AuthContext } from '../../auth/AuthContext';

function BunkLogForm({ bunk_id, camper_id, date, data, onClose, token: propsToken, currentCounselorId }) {
  const location = useLocation();
  const navigate = useNavigate();
  const params = useParams();
  const auth = useAuth();
  // Priority chain: 1. Props token 2. Auth context token 3. localStorage token
  const token = propsToken || auth?.token || localStorage.getItem('access_token');
  console.log('Token:', token); // Debug token value
  
  // Use props or fallback to params
  const bunkIdToUse = bunk_id || params.bunk_id; //WORKING
  const camperIdToUse = camper_id || params.camper_id;
  const dateToUse = date || (location.state?.selectedDate 
    ? new Date(location.state.selectedDate).toISOString().split('T')[0]
    : new Date().toISOString().split('T')[0]); //WORKING
  const Data = data || null;
  const bunk_assignment = Data?.campers?.find(c => c.camper_id == camperIdToUse)?.bunk_assignment?.id || null;
  
  // Check if user can edit based on role and date
  const canEdit = () => {
    const currentUser = auth?.user;
    if (!currentUser) return false;
    
    // Admin and staff can always edit
    if (currentUser.is_staff || currentUser.role === 'Admin' || currentUser.role === 'Unit Head') {
      return true;
    }
    
    // Check if there's an existing log
    const existingBunkLogCheck = Data?.campers?.find(item => item.camper_id === camperIdToUse);
    const existingLog = existingBunkLogCheck?.bunk_log;
    
    // For counselors
    if (currentUser.role === 'Counselor') {
      // If there's no existing log, counselors can create new logs for any date
      if (!existingLog) {
        return true;
      }
      
      // If there's an existing log, check two conditions:
      // 1. The counselor must be the one who created the log
      // 2. The edit must be happening on the same day the log was created
      const logCounselorId = existingLog.counselor;
      const today = new Date().toISOString().split('T')[0];
      const logCreatedDate = existingLog.created_at ? 
        new Date(existingLog.created_at).toISOString().split('T')[0] : 
        dateToUse; // Fallback to log date if created_at is not available
      
      // Must be the original counselor AND editing on the day it was created
      // Convert both to strings to handle type mismatch (number vs string)
      return String(logCounselorId) === String(currentUser.id) && today === logCreatedDate;
    }
    
    return false;
  };
  
  // For WYSIWYG editor
  const wysiwygRef = useRef(null);
  
  // State for camper data
  const [camperData, setCamperData] = useState(null);

  // Check if an existing bunk log is available
  const existingBunkLogCheck = Data?.campers?.find(item => item.camper_id === camperIdToUse);
  const hasExistingBunkLog = existingBunkLogCheck?.bunk_log ? true : false;
  
  // View/Edit mode toggle - start in view mode if there's existing data or if user can't edit
  const [isViewMode, setIsViewMode] = useState(hasExistingBunkLog || !canEdit());

  // Form state
  const [formData, setFormData] = useState({
    bunk_id: bunkIdToUse, //WORKING
    camper_id: camperIdToUse,
    bunk_assignment: bunk_assignment,
    counselor: '',
    date: dateToUse, //WORKING
    not_on_camp: false,
    request_unit_head_help: false,
    request_camper_care_help: false,
    behavior_score: 3,
    participation_score: 3,
    social_score: 3,
    description: '',
  });

  // Pre-select the logged-in counselor if creating a new log
  useEffect(() => {
    if (!hasExistingBunkLog && currentCounselorId) {
      setFormData(prev => ({
        ...prev,
        counselor: currentCounselorId
      }));
    }
  }, [hasExistingBunkLog, currentCounselorId]);

  
  // Add debug log for token
  useEffect(() => {
    console.log('Auth token available:', token ? 'Yes' : 'No');
  }, [token]);

  // Update form data when camperIdToUse changes
  useEffect(() => {
    console.log('CamperIdToUse:', camperIdToUse); // Debug
    try {
      // Look for existing bunklog data based on camperIdToUse, bunkIdToUse, and date
      const existingData = data?.campers?.find(item => 
        item.camper_id === camperIdToUse
      );
      if (existingData) {
        console.log('=== BunkLogForm: Found existing data ===');
        console.log('camper:', existingData); // Debug
        if (existingData.bunk_log) {
          console.log('bunk_log_data:', existingData.bunk_log); // Debug
          console.log('bunk_log description:', existingData.bunk_log.description); // Debug
        }
        
        setFormData(prev => {
          const newFormData = {
            ...prev,
            ...existingData.bunk_log,
            bunk_assignment: existingData.bunk_assignment_id,
            date: dateToUse,
            description: existingData?.bunk_log?.description || '',
          };
          
          console.log('=== BunkLogForm: Setting FormData ===');
          console.log('FormData being set:', newFormData); // Debug
          console.log('Description being set:', newFormData.description); // Debug
          console.log('Description type:', typeof newFormData.description); // Debug
          console.log('Description length:', newFormData.description ? newFormData.description.length : 0); // Debug
          
          // Use setTimeout to ensure Wysiwyg component receives the updated value
          setTimeout(() => {
            if (wysiwygRef.current && newFormData.description) {
              console.log('=== BunkLogForm: Manually setting Wysiwyg content ===');
              wysiwygRef.current.setContent(newFormData.description);
            }
          }, 100);
          
          return newFormData;
        });
      } else {
        setFormData(prev => ({
          ...prev,
          bunk_assignment: bunk_assignment,
          date: dateToUse,
        }));
      }
    }
    catch (error) {
      console.error('Error setting form data:', error);
    }
  }, [camperIdToUse]);

  
  // Loading state
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(false);
  
  // Get counselors for the dropdown
  const [counselors, setCounselors] = useState([]);

  // Fetch camper data when camper_id changes
  useEffect(() => {
    async function fetchCamperData() {
      if (camperIdToUse) {
        try {
          // Get the latest token directly from localStorage to ensure it's current
          const currentToken = localStorage.getItem('access_token');

          // Check if token exists
          if (!currentToken) {
            console.error('No authentication token available');
            setError('Authentication required. Please log in again.');
            return;
          }
          
          console.log('Using token for API request:', currentToken ? 'Token available' : 'No token');
          
          const headers = {
            'Authorization': `Bearer ${currentToken}`
          };
          console.log('Headers:', headers); // Debug headers
          
          const response = await api.get(
            `/api/v1/bunklogs/${bunkIdToUse}/logs/${date}/`
          );
          setCamperData(response.data);
        } catch (err) {
          console.error('Error fetching camper data:', err);
          if (err.response?.status === 401) {
            setError('Authentication expired. Please log in again.');
          } else {
            setError('Failed to load camper data');
          }
        }
      }
    }
    
    fetchCamperData();
  }, [camperIdToUse, token, bunkIdToUse, date]); // Added missing dependencies
  
  // Fetch counselors
  useEffect(() => {
    const counselors = camperData?.bunk?.counselors || [];
    setCounselors(
      counselors.map(counselor => ({
        id: counselor.id,
        name: `${counselor.first_name} ${counselor.last_name}`
      }))
  );
  }, [camperData]);
  
  // Handle form input changes
  const handleChange = (e) => {
    if (isViewMode) return; // Don't update form in view mode
    
    const { name, value, type, checked } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value,
    }));
  };
  
  // Handle form submission
  const handleSubmit = async (e) => {
    e.preventDefault();
    if (isViewMode) return; // Don't submit in view mode
    
    // Check permissions before submission
    if (!canEdit()) {
      setError('You do not have permission to submit this bunk log.');
      setLoading(false);
      return;
    }
    
    setLoading(true);
    setError(null);
    
    // Form validation
    if (!formData.counselor) {
      setError('Please select a counselor');
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
    
    console.log('Form submission with token:', currentToken ? 'Token available' : 'No token'); // Debug token value
    
    // Log complete form data including WYSIWYG content
    console.log('Form Data being submitted:', {
      ...formData,
      description: formData.description
    });
    
    try {
      // Reset certain fields if camper is not on camp
      const submissionData = { ...formData };
      if (submissionData.not_on_camp) {
        submissionData.request_unit_head_help = false;
        submissionData.request_camper_care_help = false;
        submissionData.behavior_score = null;
        submissionData.participation_score = null;
        submissionData.social_score = null;
        submissionData.description = '';
      }
      
      // Get API base URL from environment variable or use default
      const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';
      
      // Make sure we have a token - redundant check but keeping for safety
      if (!currentToken) {
        setError('You must be logged in to submit a bunk log');
        setLoading(false);
        return;
      }
      
      // Setup headers with proper authentication
      const headers = {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${currentToken}` // Use Bearer token format instead of Token
      };
      
      console.log('Sending with headers:', headers); // Debug headers
      
      // Determine if this is an update or create based on existing bunk log
      const existingBunkLog = Data?.campers?.find(item => item.camper_id === camperIdToUse)?.bunk_log;
      const isUpdate = existingBunkLog && existingBunkLog.id;
      
      let response;
      if (isUpdate) {
        // Update existing bunk log using PUT
        console.log('Updating existing bunk log with ID:', existingBunkLog.id);
        response = await api.put(
          `/api/v1/bunklogs/${existingBunkLog.id}/`,
          submissionData
        );
      } else {
        // Create new bunk log using POST
        console.log('Creating new bunk log');
        response = await api.post(
          `/api/v1/bunklogs/`,
          submissionData
        );
      }

      console.log('submission response:', response); // Debug
      
      if (response.status === 201 || response.status === 200) {
        setSuccess(true);
        
        // Convert dateToUse to proper format if needed
        const formattedDate = dateToUse;
        
        // Close the modal and trigger data refresh
        setTimeout(() => {
          if (onClose) {
            // IMPORTANT: Pass true to onClose to indicate successful form submission
            onClose(true); // This will inform the parent component that the form was submitted
            
            // Instead of forcing a page refresh, try to update the parent's date state
            // This should be handled by the parent component via the onClose callback
          } else {
            // When redirecting, ensure we're explicitly passing the correct date format
            console.log("Redirecting to bunk page with date:", formattedDate);
            
            // Use replace: true to avoid issues with history stack
            navigate(`/bunk/${bunkIdToUse}`, { 
              state: { date: formattedDate },
              replace: true
            });
          }
        }, 100); // Reduced timeout for better UX
      } else {
        setError(`Unexpected response: ${response.status}`);
      }
      
    } catch (err) {
      console.error('Error submitting form:', err);
      if (err.response) {
        // The request was made and the server responded with a status code
        // that falls out of the range of 2xx
        setError(`Error ${err.response.status}: ${err.response.data?.message || 'Failed to submit bunk log'}`);
      } else if (err.request) {
        // The request was made but no response was received
        setError('Network error: No response received from server');
      } else {
        // Something happened in setting up the request that triggered an Error
        setError(`Error: ${err.message}`);
      }
    } finally {
      setLoading(false);
    }
  };

  const campers = camperData?.campers || [];
  const selectedCamper = campers.find(c => c.camper_id == camperIdToUse) || 
                        Data?.campers?.find(c => c.camper_id === camperIdToUse);
  
  // Get camper name
  const camperName = selectedCamper
    ? `${selectedCamper.camper_first_name} ${selectedCamper.camper_last_name}`
    : 'Selected Camper';
    
  // Find counselor name for view mode
  const getCounselorName = () => {
    if (!formData.counselor) return '';
    const counselor = counselors.find(c => c.id === formData.counselor);
    return counselor ? counselor.name : '';
  };

  console.log('useAuth:', useAuth()); // Debug

  // InfoTooltip component for score explanations
  const InfoTooltip = ({ text }) => {
    const [visible, setVisible] = useState(false);
    const tooltipRef = useRef(null);

    // Hide tooltip on outside click (for mobile)
    useEffect(() => {
      if (!visible) return;
      const handleClick = (e) => {
        if (tooltipRef.current && !tooltipRef.current.contains(e.target)) {
          setVisible(false);
        }
      };
      document.addEventListener('mousedown', handleClick);
      return () => document.removeEventListener('mousedown', handleClick);
    }, [visible]);

    return (
      <span className="relative inline-block align-middle ml-1">
        <button
          type="button"
          aria-label="Info"
          tabIndex={0}
          className="text-blue-500 hover:text-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-400 rounded-full p-0.5"
          onMouseEnter={() => setVisible(true)}
          onMouseLeave={() => setVisible(false)}
          onClick={() => setVisible(v => !v)}
        >
          <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
            <path d="M18 10A8 8 0 11 2 10a8 8 0 0116 0zM9 8a1 1 0 112 0v4a1 1 0 11-2 0V8zm1-4a1.5 1.5 0 100 3 1.5 1.5 0 000-3z" />
          </svg>
        </button>
        {visible && (
          <div
            ref={tooltipRef}
            className="absolute z-20 left-1/2 -translate-x-1/2 mt-2 w-56 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded shadow-lg p-2 text-xs text-gray-800 dark:text-gray-100"
            style={{ minWidth: '180px' }}
          >
            {text}
          </div>
        )}
      </span>
    );
  };

  return (
    <div className="max-w-4xl mx-auto bg-white dark:bg-gray-800 shadow-lg rounded-xl p-6">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold text-gray-800 dark:text-white">
          {camperName}
        </h1>
        {/* View/Edit Mode Toggle - Only show if there's an existing bunk log */}
        {hasExistingBunkLog && (
          <div className="flex items-center space-x-3">
            {/* Permission indicator when editing is restricted */}
            {!canEdit() && (
              <div className="flex items-center text-yellow-600 dark:text-yellow-400">
                <svg className="w-4 h-4 mr-1" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                </svg>
                <span className="text-xs">
                  {auth?.user?.role === 'Counselor' 
                    ? (() => {
                        const existingLog = Data?.campers?.find(item => item.camper_id === camperIdToUse)?.bunk_log;
                        if (existingLog) {
                          const logCounselorId = existingLog.counselor;
                          const today = new Date().toISOString().split('T')[0];
                          const logCreatedDate = existingLog.created_at ? 
                            new Date(existingLog.created_at).toISOString().split('T')[0] : 
                            dateToUse;
                          
                          // Convert both to strings to handle type mismatch (number vs string)
                          if (String(logCounselorId) !== String(auth.user.id)) {
                            return 'Not your log - View only';
                          } else if (today !== logCreatedDate) {
                            return 'Can only edit on creation day - View only';
                          }
                        }
                        return 'View only';
                      })()
                    : 'View only'
                  }
                </span>
              </div>
            )}
            
            <div className="flex items-center">
              <span className="mr-2 text-sm text-gray-600 dark:text-gray-300">
                {isViewMode ? 'View Mode' : 'Edit Mode'}
              </span>
              <label className={`relative inline-flex items-center ${canEdit() ? 'cursor-pointer' : 'cursor-not-allowed opacity-50'}`}>
                <input 
                  type="checkbox"
                  className="sr-only peer"
                  checked={!isViewMode}
                  onChange={() => canEdit() && setIsViewMode(!isViewMode)}
                  disabled={!canEdit()}
                />
                <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 dark:peer-focus:ring-blue-800 rounded-full peer dark:bg-gray-700 peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all dark:border-gray-600 peer-checked:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed"></div>
              </label>
            </div>
          </div>
        )}
      </div>
      
      {/* Permission warning for creating new logs */}
      {!hasExistingBunkLog && !canEdit() && (
        <div className="mb-6 p-4 bg-yellow-50 border border-yellow-200 text-yellow-800 rounded-lg">
          <div className="flex items-center">
            <svg className="w-5 h-5 mr-2" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
            </svg>
            <div>
              <h3 className="text-sm font-medium">Cannot Create Bunk Log</h3>
              <p className="text-sm mt-1">
                You do not have permission to create bunk logs.
              </p>
            </div>
          </div>
        </div>
      )}
      
      {success && (
        <div className="mb-6 p-4 bg-green-100 border border-green-400 text-green-700 rounded">
          Bunk log successfully submitted! Redirecting...
        </div>
      )}
      
      {error && (
        <div className="mb-6 p-4 bg-red-100 border border-red-400 text-red-700 rounded">
          {error}
        </div>
      )}
      
      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Hidden field for camper_id */}
        <input 
          type="hidden" 
          name="camper_id" 
          value={camperIdToUse} 
        />
        
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

          {/* Counselor Selection */}
          <div>
            <label htmlFor="counselor" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Reporting Counselor
            </label>
            {isViewMode ? (
              <div className="w-full px-4 py-2 border border-gray-300 rounded-md bg-gray-100 dark:bg-gray-700 dark:border-gray-600 dark:text-white">
                {getCounselorName()}
              </div>
            ) : (
              <select
                id="counselor"
                name="counselor"
                value={formData.counselor}
                onChange={handleChange}
                required
                disabled={isViewMode}
                className={`w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white ${
                  isViewMode ? 'bg-gray-100 cursor-not-allowed' : ''
                }`}
              >
                <option value="">Select Counselor</option>
                {counselors.map(counselor => (
                  <option key={counselor.id} value={counselor.id}>
                    {counselor.name}
                  </option>
                ))}
              </select>
            )}
          </div>
        </div>

        {/* Not on Camp Checkbox */}
        <div className="space-y-2">
          <div className="flex items-center">
            {isViewMode ? (
              <>
                <div className={`h-5 w-5 border ${formData.not_on_camp ? 'bg-blue-600' : 'bg-white'} border-gray-300 rounded`}>
                  {formData.not_on_camp && (
                    <svg className="h-4 w-4 text-white mx-auto my-0.5" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
                      <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                    </svg>
                  )}
                </div>
                <label className="ml-2 block text-sm font-medium text-gray-700 dark:text-gray-300">
                  Camper not on camp today
                </label>
              </>
            ) : (
              <>
                <input
                  id="not_on_camp"
                  name="not_on_camp"
                  type="checkbox"
                  className="h-5 w-5 text-blue-600 border-gray-300 rounded focus:ring-blue-500 dark:border-gray-600"
                  checked={formData.not_on_camp}
                  onChange={handleChange}
                  disabled={isViewMode}
                />
                <label htmlFor="not_on_camp" className="ml-2 block text-sm font-medium text-gray-700 dark:text-gray-300">
                  Camper not on camp today
                </label>
              </>
            )}
          </div>
          <p className="text-xs text-gray-500">
            Check this if the camper was absent from camp today. All other fields will be disabled.
          </p>
        </div>

        {/* Conditional Fields - Only show if camper is on camp */}
        {!formData.not_on_camp && (
          <>
            {/* Help Request Checkboxes */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="flex items-center">
                {isViewMode ? (
                  <>
                    <div className={`h-5 w-5 border ${formData.request_unit_head_help ? 'bg-blue-600' : 'bg-white'} border-gray-300 rounded`}>
                      {formData.request_unit_head_help && (
                        <svg className="h-4 w-4 text-white mx-auto my-0.5" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
                          <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                        </svg>
                      )}
                    </div>
                    <label className="ml-2 block text-sm font-medium text-gray-700 dark:text-gray-300">
                      Unit Head Help Requested
                    </label>
                  </>
                ) : (
                  <>
                    <input
                      id="request_unit_head_help"
                      name="request_unit_head_help"
                      type="checkbox"
                      className="h-5 w-5 text-blue-600 border-gray-300 rounded focus:ring-blue-500 dark:border-gray-600"
                      checked={formData.request_unit_head_help}
                      onChange={handleChange}
                      disabled={isViewMode}
                    />
                    <label htmlFor="request_unit_head_help" className="ml-2 block text-sm font-medium text-gray-700 dark:text-gray-300">
                      Unit Head Help Requested
                    </label>
                  </>
                )}
              </div>
              
              <div className="flex items-center">
                {isViewMode ? (
                  <>
                    <div className={`h-5 w-5 border ${formData.request_camper_care_help ? 'bg-blue-600' : 'bg-white'} border-gray-300 rounded`}>
                      {formData.request_camper_care_help && (
                        <svg className="h-4 w-4 text-white mx-auto my-0.5" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
                          <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                        </svg>
                      )}
                    </div>
                    <label className="ml-2 block text-sm font-medium text-gray-700 dark:text-gray-300">
                      Camper Care Help Requested
                    </label>
                  </>
                ) : (
                  <>
                    <input
                      id="request_camper_care_help"
                      name="request_camper_care_help"
                      type="checkbox"
                      className="h-5 w-5 text-blue-600 border-gray-300 rounded focus:ring-blue-500 dark:border-gray-600"
                      checked={formData.request_camper_care_help}
                      onChange={handleChange}
                      disabled={isViewMode}
                    />
                    <label htmlFor="request_camper_care_help" className="ml-2 block text-sm font-medium text-gray-700 dark:text-gray-300">
                      Camper Care Help Requested
                    </label>
                  </>
                )}
              </div>
            </div>
            
            {/* Score Sliders */}
            <div className="space-y-4">
              <h3 className="text-lg font-medium text-gray-800 dark:text-white">Camper Scores</h3>
              
              {/* Behavior Score */}
              <div>
                <div className="flex justify-between items-center mb-1">
                  <label htmlFor="behavior_score" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                    Behavior Score: {formData.behavior_score}
                    <InfoTooltip text="How was this camper's behavior today?
5 - Very good day.
4 - Had a challenge they were able to resolve on their own.
3 - Had one minor challenge.
2 - Had a few challenging moments throughout the day.
1 - Had several challenging moments." />
                  </label>
                  <span className="text-sm text-gray-500">1-5</span>
                </div>
                <input
                  id="behavior_score"
                  name="behavior_score"
                  type="range"
                  min="1"
                  max="5"
                  className={`w-full h-2 bg-gray-200 rounded-lg appearance-none ${isViewMode ? 'cursor-not-allowed' : 'cursor-pointer'} dark:bg-gray-700`}
                  value={formData.behavior_score}
                  onChange={handleChange}
                  disabled={isViewMode}
                />
                <div className="flex justify-between text-xs text-gray-500 mt-1">
                  <span>Poor</span>
                  <span>Excellent</span>
                </div>
              </div>
              
              {/* Participation Score */}
              <div>
                <div className="flex justify-between items-center mb-1">
                  <label htmlFor="participation_score" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                    Participation Score: {formData.participation_score}
                    <InfoTooltip text="How often did the camper participate in the day's activities?
5 - Always participated in all activities.
4 - Mostly participated in all activities.
3 - Sometimes participated in activities they enjoyed.
2 - Reluctantly participated or participated with hesitation (i.e. joined after being asked).
1 - Did not participate (i.e. sat off to side, wandered, seemed disengaged)." />
                  </label>
                  <span className="text-sm text-gray-500">1-5</span>
                </div>
                <input
                  id="participation_score"
                  name="participation_score"
                  type="range"
                  min="1"
                  max="5"
                  className={`w-full h-2 bg-gray-200 rounded-lg appearance-none ${isViewMode ? 'cursor-not-allowed' : 'cursor-pointer'} dark:bg-gray-700`}
                  value={formData.participation_score}
                  onChange={handleChange}
                  disabled={isViewMode}
                />
                <div className="flex justify-between text-xs text-gray-500 mt-1">
                  <span>Poor</span>
                  <span>Excellent</span>
                </div>
              </div>
              
              {/* Social Score */}
              <div>
                <div className="flex justify-between items-center mb-1">
                  <label htmlFor="social_score" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                    Social Score: {formData.social_score}
                    <InfoTooltip text="Was the camper included socially today?
5 - Yes! The camper felt a sense of belonging at all times.
4 - Mostly! The camper was included most times of the day.
3 - Somewhat. The camper sometimes was included.
2 - With encouragement. The camper was only included with the encouragement of a staff member.
1 - Rarely or not at all. The camper spent the majority of the day alone or isolated." />
                  </label>
                  <span className="text-sm text-gray-500">1-5</span>
                </div>
                <input
                  id="social_score"
                  name="social_score"
                  type="range"
                  min="1"
                  max="5"
                  className={`w-full h-2 bg-gray-200 rounded-lg appearance-none ${isViewMode ? 'cursor-not-allowed' : 'cursor-pointer'} dark:bg-gray-700`}
                  value={formData.social_score}
                  onChange={handleChange}
                  disabled={isViewMode}
                />
                <div className="flex justify-between text-xs text-gray-500 mt-1">
                  <span>Poor</span>
                  <span>Excellent</span>
                </div>
              </div>
            </div>
            
            {/* Enhanced WYSIWYG Editor */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Daily Report
              </label>
              <div className={`border border-gray-300 rounded-md dark:border-gray-600 overflow-hidden ${isViewMode ? 'quill-view-only' : ''}`}>
                <Wysiwyg 
                  ref={wysiwygRef} 
                  value={formData.description}
                  readOnly={isViewMode}
                  showToolbar={!isViewMode}
                  onChange={(content) => {
                    if (!isViewMode) {
                      console.log('WYSIWYG onChange called with:', content);
                      setFormData(prev => ({ ...prev, description: content }))
                    }
                  }}
                />
              </div>
            </div>
          </>
        )}

        {/* Submit Button - Only show in edit mode and when user can edit */}
        {!isViewMode && canEdit() && (
          <div className="flex justify-end">
            <button
              type="submit"
              disabled={loading}
              className={`px-6 py-2 bg-blue-600 text-white rounded-md shadow-sm hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 ${
                loading ? 'opacity-70 cursor-not-allowed' : ''
              }`}
            >
              {loading ? 'Submitting...' : 'Submit Bunk Log'}
            </button>
          </div>
        )}
      </form>
    </div>
  );
}

export default BunkLogForm;