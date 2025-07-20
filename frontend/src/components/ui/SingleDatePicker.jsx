import * as React from "react"
import { format } from "date-fns"
import { cn } from "../../lib/utils"
import { Calendar } from "./calendar"
import { Popover, PopoverContent, PopoverTrigger } from "./popover"
import { useAuth } from '../../auth/AuthContext'
import api, { fetchStaffAssignmentSafe, getDateRangeForUser } from '../../api'

export default function SingleDatePicker({ className, date, setDate }) {
  const { user, token } = useAuth();
  
  // Initialize with today's date if no date is provided
  React.useEffect(() => {
    if (!date && setDate) {
      // Create today's date in local timezone
      const today = new Date();
      today.setHours(12, 0, 0, 0); // Set to noon to avoid timezone issues
      console.log('🗓️ Initializing date picker with today\'s date:', {
        date: today.toISOString(),
        localDate: `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`,
        timezone: Intl.DateTimeFormat().resolvedOptions().timeZone
      });
      setDate(today);
    }
  }, [date, setDate]);
  
  // Debug logging for component initialization
  React.useEffect(() => {
    const accessToken = localStorage.getItem('access_token');
    const refreshToken = localStorage.getItem('refresh_token');
    
    console.log('🚀 SingleDatePicker initialized with user:', {
      userId: user?.id,
      userRole: user?.role,
      hasToken: !!token,
      tokenPreview: token ? `${token.substring(0, 10)}...` : 'none',
      hasAccessToken: !!accessToken,
      hasRefreshToken: !!refreshToken,
      accessTokenPreview: accessToken ? `${accessToken.substring(0, 10)}...` : 'none'
    });
    
    // Check if token is expired
    if (accessToken) {
      try {
        const payload = JSON.parse(atob(accessToken.split('.')[1]));
        const isExpired = Date.now() >= payload.exp * 1000;
        console.log('🔍 Token expiration check:', {
          exp: new Date(payload.exp * 1000).toISOString(),
          now: new Date().toISOString(),
          isExpired
        });
        
        if (isExpired) {
          console.warn('⚠️ Access token is expired!');
        }
      } catch (e) {
        console.error('❌ Error parsing token:', e);
      }
    }
    
    // Debug: Log current date information
    const now = new Date();
    console.log('📅 Current date debugging:', {
      jsDate: now.toString(),
      jsDateLocal: `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`,
      jsISOString: now.toISOString(),
      jsISODate: now.toISOString().split('T')[0],
      timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
      timezoneOffset: now.getTimezoneOffset()
    });
  }, []);
  
  // Ensure the date is properly normalized to avoid timezone issues
  const normalizedDate = React.useMemo(() => {
    if (!date) return null;
    
    console.log('📅 Normalizing date:', {
      inputDate: date,
      inputType: typeof date,
      inputString: date?.toString(),
    });
    
    // Create a new date and set it to noon local time to avoid DST issues
    let d;
    if (typeof date === 'string') {
      // If it's a string, parse it carefully
      if (date.includes('T')) {
        d = new Date(date);
      } else {
        // If it's just YYYY-MM-DD, treat it as local date
        const [year, month, day] = date.split('-').map(Number);
        d = new Date(year, month - 1, day, 12, 0, 0, 0);
      }
    } else {
      // If it's already a Date object, use its year, month, day to avoid timezone issues
      const year = date.getFullYear();
      const month = date.getMonth();
      const day = date.getDate();
      d = new Date(year, month, day, 12, 0, 0, 0);
    }
    
    console.log('📅 Normalized date result:', {
      originalDate: date?.toString(),
      normalizedDate: d?.toString(),
      year: d?.getFullYear(),
      month: d?.getMonth(),
      day: d?.getDate(),
      formattedDate: d ? `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}` : null
    });
    
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

        // Check if user is admin or camper care - if so, set a reasonable date range without API call
        if (user?.role === 'Admin' || user?.role === 'Camper Care' || user?.is_staff === true || user?.is_superuser === true) {
          console.log('User is admin or camper care, setting broad date range without API call');
          const adminRange = getDateRangeForUser(user);
          setAllowedRange(adminRange);
          
          console.log('Set admin/camper care date range:', adminRange);
          return;
        }

        console.log('Fetching assignment data for user:', user.id);
        
        // Check token validity before making API call
        const accessToken = localStorage.getItem('access_token');
        if (accessToken) {
          try {
            const payload = JSON.parse(atob(accessToken.split('.')[1]));
            const isExpired = Date.now() >= payload.exp * 1000;
            if (isExpired) {
              console.error('❌ Cannot fetch assignment data - access token is expired');
              // Use fallback range
              const fallbackRange = getDateRangeForUser(user);
              setAllowedRange(fallbackRange);
              console.log('Set fallback date range due to expired token:', fallbackRange);
              return;
            }
          } catch (e) {
            console.error('❌ Error checking token validity:', e);
          }
        } else {
          console.error('❌ No access token available for API call');
          // Use fallback range
          const fallbackRange = getDateRangeForUser(user);
          setAllowedRange(fallbackRange);
          console.log('Set fallback date range due to missing token:', fallbackRange);
          return;
        }
        
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
        
        // Special handling for authentication errors
        if (error.response?.status === 401) {
          console.error('🚨 Authentication failed - token may be expired');
          
          // Check if this is a token expiration issue
          const accessToken = localStorage.getItem('access_token');
          if (accessToken) {
            try {
              const payload = JSON.parse(atob(accessToken.split('.')[1]));
              const isExpired = Date.now() >= payload.exp * 1000;
              if (isExpired) {
                console.error('🕒 Confirmed: Access token is expired');
                // Trigger a page refresh to force re-authentication
                console.log('🔄 Triggering page refresh to force re-authentication...');
                setTimeout(() => {
                  window.location.reload();
                }, 1000);
              }
            } catch (e) {
              console.error('❌ Error checking token expiration:', e);
            }
          }
        }
        
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
    
    // For counselors, only prevent selection of future dates - allow all past dates
    if (user?.role === 'Counselor') {
      const today = new Date();
      // Use local date comparison to avoid timezone issues
      const todayYear = today.getFullYear();
      const todayMonth = today.getMonth();
      const todayDay = today.getDate();
      
      const checkDate = new Date(date);
      const checkYear = checkDate.getFullYear();
      const checkMonth = checkDate.getMonth();
      const checkDay = checkDate.getDate();
      
      // Only disable future dates - allow today and all past dates
      const isFutureDate = (
        checkYear > todayYear || 
        (checkYear === todayYear && checkMonth > todayMonth) ||
        (checkYear === todayYear && checkMonth === todayMonth && checkDay > todayDay)
      );
      
      if (isFutureDate) {
        console.log('❌ Future date disabled for counselor:', {
          checkDate: `${checkYear}-${checkMonth + 1}-${checkDay}`,
          today: `${todayYear}-${todayMonth + 1}-${todayDay}`,
          isFuture: true
        });
        return true; // Disable future dates for counselors
      }
      
      // Allow today and all past dates for counselors
      console.log('✅ Date allowed for counselor (today or past date):', {
        checkDate: `${checkYear}-${checkMonth + 1}-${checkDay}`,
        today: `${todayYear}-${todayMonth + 1}-${todayDay}`,
        isFuture: false
      });
      return false;
    }
    
    // For camper care team members, allow all dates (like admins)
    if (user?.role === 'Camper Care') {
      console.log('✅ Camper Care role - allowing all dates');
      return false;
    }
    
    // For non-counselors (admin/staff), use the existing logic
    // If no allowed range is set, allow all dates (fallback for admin/staff or error cases)
    if (!allowedRange) {
      console.log('✅ No allowed range set - allowing all dates');
      return false;
    }
    
    if (!allowedRange.start_date) {
      console.log('✅ No start_date in allowed range - allowing all dates');
      return false;
    }
    
    // Parse the start date from the string format "YYYY-MM-DD"
    const startDateStr = allowedRange.start_date;
    console.log('📅 Parsing start date:', startDateStr);
    const [startYear, startMonth, startDay] = startDateStr.split('-').map(Number);
    
    // Parse the end date if it exists
    let endYear, endMonth, endDay;
    if (allowedRange.end_date) {
      const endDateStr = allowedRange.end_date;
      [endYear, endMonth, endDay] = endDateStr.split('-').map(Number);
    }
    
    // Get the date being checked in the same format (using local date components)
    const checkDate = new Date(date);
    const checkYear = checkDate.getFullYear();
    const checkMonth = checkDate.getMonth() + 1; // getMonth() is 0-indexed, but our strings are 1-indexed
    const checkDay = checkDate.getDate();
    
    // Check if date is before start date
    const beforeStartDate = (
      checkYear < startYear ||
      (checkYear === startYear && checkMonth < startMonth) ||
      (checkYear === startYear && checkMonth === startMonth && checkDay < startDay)
    );
    
    // Check if date is after end date (if end date exists)
    let afterEndDate = false;
    if (allowedRange.end_date) {
      afterEndDate = (
        checkYear > endYear ||
        (checkYear === endYear && checkMonth > endMonth) ||
        (checkYear === endYear && checkMonth === endMonth && checkDay > endDay)
      );
    }
    
    const isDisabled = beforeStartDate || afterEndDate;
    
    console.log('🔍 Date comparison result:', {
      checkDate: `${checkYear}-${checkMonth}-${checkDay}`,
      startDate: `${startYear}-${startMonth}-${startDay}`,
      endDate: allowedRange.end_date ? `${endYear}-${endMonth}-${endDay}` : 'null (ongoing)',
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
                // Create a new date object and set it to noon local time
                const newDate = new Date(selectedDate);
                newDate.setHours(12, 0, 0, 0);
                
                // Store as ISO string but ensure it's treated as local date
                const year = newDate.getFullYear();
                const month = String(newDate.getMonth() + 1).padStart(2, '0');
                const day = String(newDate.getDate()).padStart(2, '0');
                const dateString = `${year}-${month}-${day}`;
                
                console.log('📅 Date selected:', {
                  selectedDate: selectedDate.toString(),
                  newDate: newDate.toString(),
                  dateString: dateString,
                  timezone: Intl.DateTimeFormat().resolvedOptions().timeZone
                });
                
                localStorage.setItem('selectedDate', JSON.stringify(dateString));
                setDate(newDate);
              } else {
                localStorage.setItem('selectedDate', JSON.stringify(null));
                setDate(null);
              }
            }}
            defaultMonth={normalizedDate || new Date()}
          />
        </PopoverContent>
      </Popover>
    </div>
  );
}