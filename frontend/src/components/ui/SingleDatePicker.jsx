import * as React from "react"
import { format } from "date-fns"
import { cn } from "../../lib/utils"
import { Calendar } from "./calendar"
import { Popover, PopoverContent, PopoverTrigger } from "./popover"
import { useAuth } from '../../auth/AuthContext'
import api, { fetchStaffAssignmentSafe, getDateRangeForUser } from '../../api'

export default function SingleDatePicker({ className, date, setDate }) {
  const { user, token } = useAuth();
  
  // Debug logging for component initialization
  React.useEffect(() => {
    console.log('🚀 SingleDatePicker initialized with user:', {
      userId: user?.id,
      userRole: user?.role,
      hasToken: !!token,
      tokenPreview: token ? `${token.substring(0, 10)}...` : 'none'
    });
  }, []);
  
  // Ensure the date is set to noon
  const normalizedDate = React.useMemo(() => {
    if (!date) return null;
    const d = new Date(date);
    d.setHours(12, 0, 0, 0);
    return d;
  }, [date]);

  const [allowedRange, setAllowedRange] = React.useState(null);

  React.useEffect(() => {
    async function fetchDateRanges() {
      try {
        if (!user?.id) {
          console.warn('No user ID available');
          return;
        }

        if (!token) {
          console.warn('No access token available');
          return;
        }

        // Check if user is admin - if so, set a reasonable date range without API call
        if (user?.role === 'Admin' || user?.is_staff === true || user?.is_superuser === true) {
          console.log('User is admin, setting broad date range without API call');
          const adminRange = getDateRangeForUser(user);
          setAllowedRange(adminRange);
          
          console.log('Set admin date range:', adminRange);
          return;
        }

        console.log('Fetching assignment data for user:', user.id);
        
        // Try to get staff assignment safely
        const assignmentData = await fetchStaffAssignmentSafe(user.id);
        
        if (assignmentData && assignmentData.start_date) {
          // Set the allowed date range based on the response
          const rangeData = {
            start_date: assignmentData.start_date,
            end_date: assignmentData.end_date // Keep null if ongoing assignment
          };
          console.log('Setting allowed range from assignment:', rangeData);
          setAllowedRange(rangeData);
        } else if (assignmentData === null) {
          // No staff assignment found - user is likely admin
          console.log('No staff assignment found - treating as admin user');
          const adminRange = getDateRangeForUser(user);
          setAllowedRange(adminRange);
          console.log('Set admin date range:', adminRange);
        } else {
          console.error('Invalid assignment data - missing start_date:', assignmentData);
          // If data is invalid, use restrictive fallback
          const fallbackRange = getDateRangeForUser(user);
          console.log('Using fallback range:', fallbackRange);
          setAllowedRange(fallbackRange);
        }
      } catch (error) {
        console.error('Error fetching date ranges:', error);
        console.error('Error details:', {
          message: error.message,
          status: error.response?.status,
          statusText: error.response?.statusText,
          data: error.response?.data
        });
        
        // For any error, use fallback range based on user role
        const fallbackRange = getDateRangeForUser(user);
        setAllowedRange(fallbackRange);
        console.log('Set fallback date range due to error:', fallbackRange);
      }
    }

    fetchDateRanges();
  }, [user, token]);

  const isDateDisabled = (date) => {
    console.log('🗓️ isDateDisabled called with:', {
      date: date,
      dateString: date?.toString(),
      allowedRange: allowedRange,
      userRole: user?.role
    });
    
    // For counselors, prevent selection of future dates
    if (user?.role === 'Counselor') {
      const today = new Date();
      today.setHours(0, 0, 0, 0); // Set to start of today
      
      const checkDate = new Date(date);
      checkDate.setHours(0, 0, 0, 0); // Set to start of the date being checked
      
      if (checkDate > today) {
        console.log('❌ Future date disabled for counselor:', {
          checkDate: checkDate.toDateString(),
          today: today.toDateString(),
          isFuture: true
        });
        return true; // Disable future dates for counselors
      }
    }
    
    // If no allowed range is set, allow all dates (fallback for admin/staff or error cases)
    if (!allowedRange) {
      console.log('❌ No allowed range set - allowing all dates');
      return false;
    }
    
    if (!allowedRange.start_date) {
      console.log('❌ No start_date in allowed range - allowing all dates');
      return false;
    }
    
    // Parse the start date from the string format "YYYY-MM-DD"
    const startDateStr = allowedRange.start_date;
    console.log('📅 Parsing start date:', startDateStr);
    const [startYear, startMonth, startDay] = startDateStr.split('-').map(Number);
    const startDate = new Date(startYear, startMonth - 1, startDay); // Month is 0-indexed
    
    // Parse the end date if it exists
    let endDate = null;
    if (allowedRange.end_date) {
      const endDateStr = allowedRange.end_date;
      const [endYear, endMonth, endDay] = endDateStr.split('-').map(Number);
      endDate = new Date(endYear, endMonth - 1, endDay); // Month is 0-indexed
    }
    
    // Get the date being checked in the same format
    const checkDate = new Date(date);
    const checkYear = checkDate.getFullYear();
    const checkMonth = checkDate.getMonth();
    const checkDay = checkDate.getDate();
    const normalizedCheckDate = new Date(checkYear, checkMonth, checkDay);
    
    // Normalize start and end dates for comparison
    const normalizedStartDate = new Date(startDate.getFullYear(), startDate.getMonth(), startDate.getDate());
    const normalizedEndDate = endDate ? new Date(endDate.getFullYear(), endDate.getMonth(), endDate.getDate()) : null;
    
    // Disable dates OUTSIDE the allowed range
    const beforeStartDate = normalizedCheckDate < normalizedStartDate;
    const afterEndDate = normalizedEndDate ? normalizedCheckDate > normalizedEndDate : false;
    const isDisabled = beforeStartDate || afterEndDate;
    
    console.log('🔍 Date comparison result:', {
      checkDate: normalizedCheckDate.toDateString(),
      startDate: normalizedStartDate.toDateString(),
      endDate: normalizedEndDate ? normalizedEndDate.toDateString() : 'null (ongoing)',
      beforeStartDate,
      afterEndDate,
      isDisabled: isDisabled ? '❌ DISABLED' : '✅ ENABLED'
    });
    
    return isDisabled;
  };

  return (
    <div className={cn("grid gap-2", className)}>
      <Popover>
        <PopoverTrigger asChild>
          <button
            id="date"
            className={cn(
              "btn px-2.5 min-w-[15.5rem] bg-white border-gray-200 hover:border-gray-300 dark:border-gray-700/60 dark:hover:border-gray-600 dark:bg-gray-800 text-gray-600 hover:text-gray-800 dark:text-gray-300 dark:hover:text-gray-100 font-medium text-left justify-start",
              !normalizedDate && "text-muted-foreground"
            )}
          >
            <svg className="fill-current text-gray-400 dark:text-gray-500 ml-1 mr-2" width="16" height="16" viewBox="0 0 16 16">
              <path d="M5 4a1 1 0 0 0 0 2h6a1 1 0 1 0 0-2H5Z"></path>
              <path d="M4 0a4 4 0 0 0-4 4v8a4 4 0 0 0 4 4h8a4 4 0 0 0 4-4V4a4 4 0 0 0-4-4H4ZM2 4a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V4Z"></path>
            </svg>
            {normalizedDate ? format(normalizedDate, "LLL dd, y") : "Pick a date"}
          </button>
        </PopoverTrigger>
        <PopoverContent className="w-auto p-0" align="start">
          <Calendar
            mode="single"
            selected={normalizedDate}
            disabled={isDateDisabled}
            onSelect={(selectedDate) => {
              if (selectedDate) {
                const newDate = new Date(selectedDate);
                newDate.setHours(12, 0, 0, 0);
                localStorage.setItem('selectedDate', JSON.stringify(newDate));
                setDate(newDate);
              } else {
                localStorage.setItem('selectedDate', JSON.stringify(selectedDate));
                setDate(selectedDate);
              }
            }}
            defaultMonth={normalizedDate}
          />
        </PopoverContent>
      </Popover>
    </div>
  );
}