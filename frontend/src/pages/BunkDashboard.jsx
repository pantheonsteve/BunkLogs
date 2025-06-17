import React, { useState, useEffect } from 'react';
import { useParams, useLocation, useNavigate } from 'react-router-dom';
import axios from 'axios';
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

  const handleDateChange = React.useCallback((newDate) => {
    // Ensure a clean, new date object is set
    if (!newDate || !new Date(newDate).getTime()) {
      console.log('[BunkDashboard] Invalid date provided to handleDateChange');
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
    setSelectedCamperId(camperId);
    setCamperBunkAssignmentId(camper_bunk_assignment_id);
    setBunkLogFormModalOpen(true);
  };
  
  const handleModalClose = (wasSubmitted) => {
    console.log(`[BunkDashboard] Closing modal, submission status: ${wasSubmitted}`);
    if(wasSubmitted) {
      saveSelectedDate(selectedDate);
      setFormSubmitted(true);
    }
    setBunkLogFormModalOpen(false);
  };

  const handleOrderCreated = () => {
    console.log('[BunkDashboard] Order created successfully');
    setCreateOrderModalOpen(false);
    // Optionally refresh data here if needed
    // You might want to refetch the data to show updated orders
  };

  // Check if user is a counselor
  const isCounselor = user?.role === 'Counselor';

  useEffect(() => {
    async function fetchData() {
      console.log(`[BunkDashboard] Starting data fetch for bunk_id: ${bunk_id}`);
      try {
        setLoading(true);
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
          'Authorization': `Token ${currentToken}`
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
        setError(error);
      } finally {
        console.log('[BunkDashboard] Data fetch completed');
        setLoading(false);
      }
    }
    
    fetchData();
  }, [bunk_id, selectedDate, token]);

  const cabin_name = data?.bunk?.cabin?.name || "Bunk X"; // Default if cabin_name is not available
  const session_name = data?.bunk?.session?.name || "Session X"; // Default if session_name is not available
  const bunk_label = `${cabin_name}`;
  const selected_date = data?.date || "2025-01-01"; // Format date as YYYY-MM-DD
  
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

          {/* Cards */}
          <div className="grid grid-cols-12 gap-6">
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
              />
            </BunkLogFormModal>
            
            {/* Create Order Modal */}
            <CreateOrderModal
              isOpen={createOrderModalOpen}
              onClose={() => setCreateOrderModalOpen(false)}
              onOrderCreated={handleOrderCreated}
              bunkId={bunk_id}
              date={selected_date}
            />
            
            <NotOnCampCard bunkData={data} />
            <UnitHeadHelpRequestedCard bunkData={data} />
            <CamperCareHelpRequestedCard bunkData={data} />
            <BunkLogsTableViewCard bunkData={data} />
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