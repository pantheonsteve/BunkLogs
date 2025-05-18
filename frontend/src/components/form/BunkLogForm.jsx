import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { useLocation, useNavigate, useParams } from 'react-router-dom';
import Wysiwyg from './Wysiwyg';
import { useAuth } from '../../auth/AuthContext';

function BunkLogForm({ bunk_id, camper_id, date, data, onClose }) {
  const location = useLocation();
  const navigate = useNavigate();
  const params = useParams();
  const { token } = useAuth(); // Extract token from auth context
  
  // Use props or fallback to params
  const bunkIdToUse = bunk_id || params.bunk_id; //WORKING
  const camperIdToUse = camper_id || params.camper_id;
  const dateToUse = date || (location.state?.selectedDate 
    ? new Date(location.state.selectedDate).toISOString().split('T')[0]
    : new Date().toISOString().split('T')[0]); //WORKING
  const Data = data || null;
  const bunk_assignment = Data?.campers?.find(c => c.camper_id == camperIdToUse)?.bunk_assignment?.id || null;
  
  // For Quill editor
  const editorRef = useRef(null);
  const quillRef = useRef(null);
  
  // State for camper data
  const [camperData, setCamperData] = useState(null);

  // Check if an existing bunk log is available
  const existingBunkLogCheck = Data?.campers?.find(item => item.camper_id === camperIdToUse);
  const hasExistingBunkLog = existingBunkLogCheck?.bunk_log ? true : false;
  
  // View/Edit mode toggle - start in view mode if there's existing data
  const [isViewMode, setIsViewMode] = useState(hasExistingBunkLog);

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

  
  // Update form data when camperIdToUse changes
  useEffect(() => {
    console.log('CamperIdToUse:', camperIdToUse); // Debug
    try {
      // Look for existing bunklog data based on camperIdToUse, bunkIdToUse, and date
      const existingData = data?.campers?.find(item => 
        item.camper_id === camperIdToUse
      );
      if (existingData) {
        console.log('camper:', existingData); // Debug
        if (existingData.bunk_log) {
          console.log('bunk_log_data:', existingData.bunk_log); // Debug
        }
        setFormData(prev => ({
          ...prev,
          ...existingData.bunk_log,
          bunk_assignment: existingData.bunk_assignment.id,
          date: dateToUse,
          description: existingData?.bunk_log?.description || '',
        }));
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
          // Check if token exists
          if (!token) {
            console.error('No authentication token available');
            setError('Authentication required. Please log in again.');
            return;
          }
          
          const headers = {
            'Authorization': `Token ${token}`
          };
          
          const response = await axios.get(
            `http://127.0.0.1:8000/api/v1/bunklogs/${bunkIdToUse}/${date}/`,
            { headers }
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


  // Initialize Quill editor
  useEffect(() => {
    if (editorRef.current && !quillRef.current) {
      const toolbarOptions = [
        [{ 'header': [1, 2, false] }],
        ['bold', 'italic', 'underline'],
        ['link', 'list', 'align', 'justify'],
        ['clean']
      ];

      quillRef.current = new Quill(editorRef.current, {
        modules: {
          toolbar: isViewMode ? false : toolbarOptions
        },
        theme: 'snow',
        readOnly: isViewMode
      });

      // Update form data when editor content changes
      quillRef.current.on('text-change', function() {
        if (!isViewMode) {
          setFormData(prev => ({
            ...prev,
            description: quillRef.current.root.innerHTML
          }));
        }
      });
    }
    
    // If not on camp is checked, clear the editor
    if (formData.not_on_camp && quillRef.current) {
      quillRef.current.setText('');
    }
    
    // Update editor's readonly state when view mode changes
    if (quillRef.current) {
      quillRef.current.enable(!isViewMode);
      
      // Hide/show toolbar based on view mode
      const toolbarElement = editorRef.current.parentElement.querySelector('.ql-toolbar');
      if (toolbarElement) {
        toolbarElement.style.display = isViewMode ? 'none' : 'block';
      }
    }
  }, [formData.not_on_camp, isViewMode]);
  
  // Update Quill editor content when description changes in formData
  useEffect(() => {
    if (quillRef.current && formData.description) {
      // Only update if the current content differs from formData.description
      // to avoid an infinite loop
      if (quillRef.current.root.innerHTML !== formData.description) {
        quillRef.current.root.innerHTML = formData.description;
      }
    }
  }, [formData.description]);
  
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
    
    setLoading(true);
    setError(null);
    
    // Form validation
    if (!formData.counselor) {
      setError('Please select a counselor');
      setLoading(false);
      return;
    }
    
    // Verify token exists before attempting submission
    if (!token) {
      setError('Authentication required. Please log in again.');
      setLoading(false);
      return;
    }
    
    console.log('Form submission with token:', token); // Debug token value
    
    // Log complete form data including WYSIWYG content
    console.log('Form Data being submitted:', {
      ...formData,
      description: formData.description || (quillRef.current ? quillRef.current.root.innerHTML : '')
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
      const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://127.0.0.1:8000/api/v1';
      
      // Make sure we have a token
      if (!token) {
        setError('You must be logged in to submit a bunk log');
        setLoading(false);
        return;
      }
      
      // Setup headers with proper authentication
      const headers = {
        'Content-Type': 'application/json',
        'Authorization': `Token ${token}` // Ensure token is always included
      };
      
      console.log('Sending with headers:', headers); // Debug headers
      
      // API call to submit the form
      const response = await axios.post(
        `${API_BASE_URL}/bunklogs/`,
        submissionData,
        { headers, withCredentials: true } // Add withCredentials to include cookies
      );

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

  return (
    <div className="max-w-4xl mx-auto bg-white dark:bg-gray-800 shadow-lg rounded-xl p-6">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold text-gray-800 dark:text-white">
          {camperName}
        </h1>
        {/* View/Edit Mode Toggle - Only show if there's an existing bunk log */}
        {hasExistingBunkLog && (
          <div className="flex items-center">
            <span className="mr-2 text-sm text-gray-600 dark:text-gray-300">
              {isViewMode ? 'View Mode' : 'Edit Mode'}
            </span>
            <label className="relative inline-flex items-center cursor-pointer">
              <input 
                type="checkbox"
                className="sr-only peer"
                checked={!isViewMode}
                onChange={() => setIsViewMode(!isViewMode)}
              />
              <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 dark:peer-focus:ring-blue-800 rounded-full peer dark:bg-gray-700 peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all dark:border-gray-600 peer-checked:bg-blue-600"></div>
            </label>
          </div>
        )}
      </div>
      
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
            
            {/* Quill WYSIWYG Editor */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Daily Report
              </label>
              <div className={`border border-gray-300 rounded-md dark:border-gray-600 overflow-hidden ${isViewMode ? 'quill-view-only' : ''}`}>
                <Wysiwyg 
                  ref={editorRef} 
                  onChange={(content) => {
                    if (!isViewMode) {
                      setFormData(prev => ({ ...prev, description: content }))
                    }
                  }}
                />
              </div>
            </div>
          </>
        )}

        {/* Submit Button - Only show in edit mode */}
        {!isViewMode && (
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