import React, { useState, useEffect } from 'react';
import { useParams, useLocation, useNavigate } from 'react-router-dom';
import axios from 'axios';
import api from '../api';
import { useBunk } from '../contexts/BunkContext';
import { saveSelectedDate, getSelectedDate } from '../utils/stateUtils';
import { useAuth } from '../auth/AuthContext';

import BunkPageSidebar from '../partials/bunk-dashboard/BunkPageSidebar';
import Header from '../partials/Header';
import FilterButton from '../components/DropdownFilter';
import SingleDatePicker from '../components/ui/SingleDatePicker';
import NotOnCampCard from '../partials/bunk-dashboard/NotOnCampCard';
import CamperCareHelpRequestedCard from '../partials/bunk-dashboard/CamperCareHelpRequestedCard';
import UnitHeadHelpRequestedCard from '../partials/bunk-dashboard/UnitHeadHelpRequestedCard';
import BunkLogsTableViewCard from '../partials/bunk-dashboard/BunkLogsTableViewCard';
import BunkLabelCard from '../partials/bunk-dashboard/BunkLabelCard';
import BunkLogForm from '../components/form/BunkLogForm';
import BunkLogFormModal from '../components/modals/BunkLogFormModal';
import CreateOrderModal from '../components/modals/CreateOrderModal';
import BunkOrderDetail from '../partials/bunk-dashboard/BunkOrderDetail';
import BunkOrderEdit from '../partials/bunk-dashboard/BunkOrderEdit';

function BunkDashboard() {
  console.log('[BunkDashboard] Component initializing');
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const { token, user } = useAuth(); // Get authentication token and user
  const [bunkLogModalOpen, setBunkLogFormModalOpen] = useState(false);
  const [createOrderModalOpen, setCreateOrderModalOpen] = useState(false);
  const [selectedCamperId, setSelectedCamperId] = useState(null);
  const [camperBunkAssignmentId, setCamperBunkAssignmentId] = useState(null);
  const [refreshTrigger, setRefreshTrigger] = useState(0); // Add refresh trigger for data updates
  const [previousOrderId, setPreviousOrderId] = useState(null); // Track order navigation for refresh
  const { bunk_id, date, orderId } = useParams();
  const location = useLocation();
  const navigate = useNavigate();
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [formSubmitted, setFormSubmitted] = useState(false);

  const { bunkData, setBunkData } = useBunk();
  
  // Add redirect if no date parameter
  useEffect(() => {
    if (!date || date === 'undefined') {
      const today = new Date();
      const year = today.getFullYear();
      const month = String(today.getMonth() + 1).padStart(2, '0');
      const day = String(today.getDate()).padStart(2, '0');
      const formattedDate = `${year}-${month}-${day}`;
      
      console.log(`[BunkDashboard] No date in URL, redirecting to today: ${formattedDate}`);
      navigate(`/bunk/${bunk_id}/${formattedDate}`, { replace: true });
    }
  }, [date, bunk_id, navigate]);
  
  // Handle route changes (e.g., when navigating back from order views)
  useEffect(() => {
    console.log(`[BunkDashboard] Route change detected: orderId=${orderId}, pathname=${location.pathname}`);
    
    // If we're back to the main dashboard view (no orderId), ensure we refetch data if needed
    if (!orderId && (!data?.bunk || Object.keys(data).length === 0)) {
      console.log('[BunkDashboard] Back to main dashboard but no data, triggering refetch');
      setLoading(true);
      setError(null);
    }
  }, [orderId, location.pathname, data]);
  
  // Additional effect to refresh data when returning from order views
  // This ensures that if orders were edited, we see the latest changes
  useEffect(() => {
    if (previousOrderId && !orderId) {
      // We've navigated back from an order view to the main dashboard
      console.log('[BunkDashboard] Returned from order view, triggering refresh');
      setRefreshTrigger(prev => prev + 1);
    }
    setPreviousOrderId(orderId);
  }, [orderId, previousOrderId]);
  
  // Ensure proper date handling with timezone consistency
  const [selectedDate, setSelectedDate] = useState(() => {
    if (!date) {
      console.log('[BunkDashboard] No date provided in URL, using default date');
      return new Date(); // Default to today if no date is provided
    } else if (date && date !== 'undefined') {
      // Prioritize date from URL parameter
      const [year, month, day] = date.split('-').map(Number);
      console.log(`[BunkDashboard] Initializing with date from URL parameter: ${date}`);
      return new Date(year, month - 1, day);
    } else if (location.state?.selectedDate) {
      const dateStr = location.state.selectedDate;
      const [year, month, day] = dateStr.split('-').map(Number);
      console.log(`[BunkDashboard] Initializing with date from location state: ${dateStr}`);
      return new Date(year, month - 1, day);
    } else {
      const storedDate = getSelectedDate();
      console.log(`[BunkDashboard] Using stored date: ${storedDate || 'none, defaulting to today'}`);
      return storedDate || new Date();
    }
  });

  // Keep selectedDate in sync with URL parameter
  useEffect(() => {
    if (date) {
      const [year, month, day] = date.split('-').map(Number);
      const dateFromUrl = new Date(year, month - 1, day);
      console.log(`[BunkDashboard] Updating selectedDate from URL: ${date}`);
      setSelectedDate(dateFromUrl);
    }
  }, [date]);

  // State for assignment-based date validation
  const [assignmentDateRange, setAssignmentDateRange] = React.useState(null);

  // Fetch assignment date range for validation
  React.useEffect(() => {
    async function fetchAssignmentRange() {
      if (!user?.id || !token) return;
      
      try {
        const response = await api.get(`/api/v1/unit-staff-assignments/${user.id}/`, {
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          }
        });
        
        if (response.status === 200) {
          const data = response.data;
          setAssignmentDateRange({
            start_date: data.start_date,
            end_date: data.end_date
          });
          console.log('[BunkDashboard] Assignment date range loaded:', data.start_date, 'to', data.end_date || 'ongoing');
        }
      } catch (error) {
        console.warn('[BunkDashboard] Could not fetch assignment dates:', error);
        // Allow all dates if assignment fetch fails
        setAssignmentDateRange(null);
      }
    }
    
    fetchAssignmentRange();
  }, [user?.id, token]);

  const validateDate = (date) => {
    if (!date || !date.getTime()) {
      return false;
    }
    
    // If no assignment range loaded, allow the date (fallback behavior)
    if (!assignmentDateRange || !assignmentDateRange.start_date) {
      return true;
    }
    
    // Use the same date validation logic as SingleDatePicker
    const startDateStr = assignmentDateRange.start_date;
    const [startYear, startMonth, startDay] = startDateStr.split('-').map(Number);
    const startDate = new Date(startYear, startMonth - 1, startDay);
    
    let endDate = null;
    if (assignmentDateRange.end_date) {
      const endDateStr = assignmentDateRange.end_date;
      const [endYear, endMonth, endDay] = endDateStr.split('-').map(Number);
      endDate = new Date(endYear, endMonth - 1, endDay);
    }
    
    // Normalize dates for comparison
    const checkDate = new Date(date);
    const normalizedCheckDate = new Date(checkDate.getFullYear(), checkDate.getMonth(), checkDate.getDate());
    const normalizedStartDate = new Date(startDate.getFullYear(), startDate.getMonth(), startDate.getDate());
    const normalizedEndDate = endDate ? new Date(endDate.getFullYear(), endDate.getMonth(), endDate.getDate()) : null;
    
    // Check if date is within assignment range
    const beforeStartDate = normalizedCheckDate < normalizedStartDate;
    const afterEndDate = normalizedEndDate ? normalizedCheckDate > normalizedEndDate : false;
    const isValid = !beforeStartDate && !afterEndDate;
    
    console.log('[BunkDashboard] Date validation:', {
      date: normalizedCheckDate.toDateString(),
      startDate: normalizedStartDate.toDateString(),
      endDate: normalizedEndDate ? normalizedEndDate.toDateString() : 'ongoing',
      isValid: isValid ? '✅ VALID' : '❌ INVALID'
    });
    
    return isValid;
  };

  const handleDateChange = React.useCallback((newDate) => {
    // Ensure a clean, new date object is set
    if (!newDate || !new Date(newDate).getTime()) {
      console.log('[BunkDashboard] Invalid date provided to handleDateChange');
      return;
    }

    if (!validateDate(newDate)) {
      console.warn('[BunkDashboard] Date out of range:', newDate);
      const startDate = assignmentDateRange?.start_date || 'unknown';
      const endDate = assignmentDateRange?.end_date || 'ongoing';
      setError({
        message: 'Date Outside Assignment Period',
        details: `You can only access data from ${startDate} to ${endDate}. Please select a date within your assignment period.`,
        code: 400,
      });
      return;
    }

    // Create a new date object at midnight in local timezone
    const year = newDate.getFullYear();
    const month = newDate.getMonth();
    const day = newDate.getDate();
    const standardizedDate = new Date(year, month, day);

    console.log(`[BunkDashboard] Date changed: ${standardizedDate.toISOString()} (local: ${standardizedDate.toString()})`);
    
    // Format date for URL: YYYY-MM-DD
    const formattedDate = `${year}-${String(month + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
    
    // Navigate to new URL with selected date
    navigate(`/bunk/${bunk_id}/${formattedDate}`);
    
    // Update the selected date state
    setSelectedDate(standardizedDate);
  }, [bunk_id, navigate]);

  const handleOpenBunkLogModal = (camperId, camper_bunk_assignment_id) => {
    console.log(`[BunkDashboard] Opening bunk log modal for camper: ${camperId}, assignment: ${camper_bunk_assignment_id}`);
    // Only allow Counselors to open the modal
    if (!isCounselor) {
      console.log('[BunkDashboard] Access denied: Only Counselors can edit bunk logs');
      return;
    }
    // Check if a log exists for this camper/date
    const camperData = data?.campers?.find(item => item.camper_id === camperId);
    const existingLog = camperData?.bunk_log;
    if (existingLog) {
      // Only allow if the logged-in user is the author - convert both to strings to handle type mismatch
      if (String(existingLog.counselor) !== String(user.id)) {
        console.log('[BunkDashboard] Access denied: Only the author can edit this bunk log');
        return;
      }
    }
    setSelectedCamperId(camperId);
    setCamperBunkAssignmentId(camper_bunk_assignment_id);
    setBunkLogFormModalOpen(true);
  };
  
  const handleModalClose = (wasSubmitted) => {
    console.log(`[BunkDashboard] Closing modal, submission status: ${wasSubmitted}`);
    if(wasSubmitted) {
      saveSelectedDate(selectedDate);
      setFormSubmitted(true);
      // Trigger data refresh to show updated bunk logs
      setRefreshTrigger(prev => prev + 1);
    }
    setBunkLogFormModalOpen(false);
  };

  const handleOrderCreated = () => {
    console.log('[BunkDashboard] Order created successfully');
    setCreateOrderModalOpen(false);
    // Trigger data refresh to show the new order
    setRefreshTrigger(prev => prev + 1);
  };

  // Check user roles
  const isAdmin = user?.role === 'Admin';
  const isCounselor = user?.role === 'Counselor';
  const isCamperCare = user?.role === 'Camper Care';
  const isUnitHead = user?.role === 'Unit Head';
  
  // Define view-only roles that can see cards but cannot edit
  const isViewOnlyRole = isCamperCare || isUnitHead || isAdmin;

  useEffect(() => {
    async function fetchData() {
      console.log(`[BunkDashboard] Starting data fetch for bunk_id: ${bunk_id}`);
      try {
        setLoading(true);
        setError(null); // Clear any previous errors
        
        // Format date consistently for API request
        const year = selectedDate.getFullYear();
        const month = String(selectedDate.getMonth() + 1).padStart(2, '0');
        const day = String(selectedDate.getDate()).padStart(2, '0');
        const formattedDate = `${year}-${month}-${day}`;
        console.log(`Formatted Date: ${formattedDate}`);
        
        
        const url = `${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/api/v1/bunklogs/${bunk_id}/logs/${formattedDate}/`;
        console.log(`[BunkDashboard] Fetching data from URL: ${url}`);
        
        // Get token from context or localStorage
        const currentToken = token || localStorage.getItem('access_token');
        console.log(`[BunkDashboard] Token available: ${currentToken ? 'Yes' : 'No'}`);
        
        // Set headers with token if available
        const headers = currentToken ? {
          'Authorization': `Bearer ${currentToken}`
        } : {};
        
        const response = await axios.get(url, {
          withCredentials: true,
          headers
        })
         
        console.log(`[BunkDashboard] Data fetched successfully. Campers: ${response.data?.campers?.length || 0}`);
        setData(response.data);
        setBunkData(response.data);
      } catch (error) {
        console.error(`[BunkDashboard] API Error:`, error);
        
        // Handle specific error cases
        if (error.response?.status === 403) {
          setError({
            message: 'Access Denied',
            details: 'You do not have permission to view this bunk. Please contact an administrator if you believe this is an error.',
            code: 403
          });
        } else if (error.response?.status === 401) {
          setError({
            message: 'Authentication Required',
            details: 'Your session has expired. Please log in again.',
            code: 401
          });
        } else if (error.response?.status === 404) {
          setError({
            message: 'Bunk Not Found',
            details: 'The requested bunk could not be found. It may have been deleted or moved.',
            code: 404
          });
        } else {
          setError({
            message: 'Loading Error',
            details: error.response?.data?.message || error.message || 'Failed to load bunk dashboard data',
            code: error.response?.status || 500
          });
        }
      } finally {
        console.log('[BunkDashboard] Data fetch completed');
        setLoading(false);
      }
    }
    
    fetchData();
  }, [bunk_id, selectedDate, token, refreshTrigger]);

  const cabin_name = data?.bunk?.cabin?.name || "Bunk X"; // Default if cabin_name is not available
  const session_name = data?.bunk?.session?.name || "Session X"; // Default if session_name is not available
  const bunk_label = `${cabin_name}`;
  const selected_date = data?.date || new Date().toISOString().split('T')[0]; // Format date as YYYY-MM-DD, default to today
  
  console.log(`[BunkDashboard] Rendering with bunk label: "${bunk_label}", date: ${selected_date}`);
  
  // Determine what content to show based on URL parameters
  const isOrderView = Boolean(orderId);
  const isOrderEdit = Boolean(orderId && location.pathname.includes('/edit'));
  
  console.log(`[BunkDashboard] Route analysis: orderId=${orderId}, isOrderView=${isOrderView}, isOrderEdit=${isOrderEdit}, pathname=${location.pathname}`);
  
  const renderMainContent = () => {
    if (isOrderEdit) {
      return <BunkOrderEdit orderId={orderId} bunk_id={bunk_id} date={date} />;
    } else if (isOrderView) {
      return <BunkOrderDetail orderId={orderId} bunk_id={bunk_id} date={date} />;
    } else {
      // Default dashboard content - show loading if data is still being fetched
      if (loading) {
        return (
          <div className="flex justify-center items-center py-8">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900"></div>
            <span className="ml-2 text-gray-600">Loading dashboard...</span>
          </div>
        );
      }
      
      if (error) {
        return (
          <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-md p-4">
            <p className="text-sm text-red-800 dark:text-red-200">
              Error loading dashboard: {error.message || error}
            </p>
          </div>
        );
      }
      
      // Debug: Check if we have the necessary data
      console.log(`[BunkDashboard] Rendering dashboard with data:`, { 
        hasData: !!data, 
        hasBunk: !!data?.bunk, 
        dataKeys: data ? Object.keys(data) : [],
        loading, 
        error,
        bunk_id,
        date,
        selected_date
      });
      
      // If no data at all, show a minimal loading state
      if (!data || Object.keys(data).length === 0) {
        console.log('[BunkDashboard] No data available, showing loading state');
        return (
          <div className="flex justify-center items-center py-8">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900"></div>
            <span className="ml-2 text-gray-600">Loading dashboard data...</span>
          </div>
        );
      }
      
      return (
        <>
          {/* Dashboard actions - Main Row Container */}
          <div className="w-full mb-8">
            {/* Responsive Grid: 3 columns that stack on smaller screens */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              
              {/* Column A: Title */}
              <div className="p-4">
                <BunkLabelCard bunkLabel={bunk_label} session={session_name} />
              </div>
              
              {/* Column B: Filter & Date Picker that stay side by side */}
              <div className="p-4">
                <div className="flex flex-row">
                  
                  {/* Date Picker (9/12 width) */}
                  <div className="w-9/12">
                    <SingleDatePicker 
                      align="left" 
                      date={selectedDate} 
                      setDate={handleDateChange} 
                    />
                  </div>
                </div>
              </div>
              
              {/* Column C: Action Buttons that become full width on small screens */}
              <div className="p-4">
                <div className="flex flex-col sm:flex-row gap-2 items-start sm:items-center">
                  {/* Role indicator - always show */}
                  <div className={`inline-flex items-center px-3 py-2 rounded-lg border ${
                    isCounselor 
                      ? 'bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800' 
                      : isViewOnlyRole 
                        ? 'bg-blue-50 dark:bg-blue-900/20 border-blue-200 dark:border-blue-800'
                        : 'bg-gray-50 dark:bg-gray-900/20 border-gray-200 dark:border-gray-800'
                  }`}>
                    {isCounselor ? (
                      <>
                        <svg className="w-4 h-4 mr-2 text-green-600 dark:text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"></path>
                        </svg>
                        <span className="text-sm font-medium text-green-700 dark:text-green-300">Full Access</span>
                      </>
                    ) : (
                      <>
                        <svg className="w-4 h-4 mr-2 text-blue-600 dark:text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"></path>
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"></path>
                        </svg>
                        <span className="text-sm font-medium text-blue-700 dark:text-blue-300">View Only</span>
                      </>
                    )}
                  </div>
                  
                  {/* Create Order button - only for Counselors */}
                  {isCounselor && (
                    <button
                      onClick={() => setCreateOrderModalOpen(true)}
                      className="bg-blue-500 hover:bg-blue-600 text-white font-medium py-2 px-4 rounded-lg transition-colors duration-200"
                    >
                      Create Order
                    </button>
                  )}
                </div>
              </div>
            </div>
          </div>

          {/* Cards - Conditionally render based on user role */}
          <div className="grid grid-cols-12 gap-6">
            {/* Bunk Log Form Modal - Only for Counselors */}
            {isCounselor && (
              <BunkLogFormModal 
                id="bunk-log-form"
                title="Add Bunk Log"
                modalOpen={bunkLogModalOpen}
                setModalOpen={setBunkLogFormModalOpen}
                formSubmitted={formSubmitted}
              >
                <BunkLogForm 
                  bunk_id={bunk_id}
                  camper_id={selectedCamperId}
                  date={selected_date}
                  data={data}
                  onClose={handleModalClose}
                  // Pass token explicitly through props as a backup
                  token={token || localStorage.getItem('access_token')}
                  currentCounselorId={user.id}
                />
              </BunkLogFormModal>
            )}
              
              {/* Create Order Modal - Only for Counselors */}
              {isCounselor && (
                <CreateOrderModal
                  isOpen={createOrderModalOpen}
                  onClose={() => setCreateOrderModalOpen(false)}
                  onOrderCreated={handleOrderCreated}
                  bunkId={bunk_id}
                  date={selected_date}
                />
              )}
              
              {/* Cards visible to Camper Care and Unit Head roles */}
              {isViewOnlyRole && (
                <>
                  <NotOnCampCard bunkData={data} />
                  <UnitHeadHelpRequestedCard bunkData={data} />
                  <CamperCareHelpRequestedCard bunkData={data} />
                  <BunkLogsTableViewCard bunkData={data} />
                </>
              )}
              
              {/* Cards visible to Counselors (all cards) */}
              {isCounselor && (
                <>
                  <NotOnCampCard bunkData={data} />
                  <UnitHeadHelpRequestedCard bunkData={data} />
                  <CamperCareHelpRequestedCard bunkData={data} />
                  <BunkLogsTableViewCard bunkData={data} />
                </>
              )}
            </div>
        </>
      );
    }
  };
  
  return (
    <div className="flex h-screen overflow-hidden">

      {/* BunkPageSidebar */}
      <BunkPageSidebar 
        sidebarOpen={sidebarOpen} 
        setSidebarOpen={setSidebarOpen} 
        date={selected_date} 
        bunk={bunk_id} 
        openBunkModal={handleOpenBunkLogModal}
        refreshTrigger={refreshTrigger}
        userRole={user?.role}
      />

      {/* Content area */}
      <div className="relative flex flex-col flex-1 overflow-y-auto overflow-x-hidden">

        {/*  Site header */}
        <Header sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} />

        <main className="grow">
          <div className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-9xl mx-auto">
            <div key={`${orderId || 'dashboard'}-${location.pathname}`}>
              {renderMainContent()}
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}

export default BunkDashboard;