// Test the date logic used in the SingleDatePicker component

// Test future date detection for counselors
function testFutureDateLogic() {
  console.log('=== Testing Future Date Logic ===');
  
  const today = new Date();
  const todayYear = today.getFullYear();
  const todayMonth = today.getMonth();
  const todayDay = today.getDate();
  
  console.log('Today:', {
    year: todayYear,
    month: todayMonth + 1, // Display month is 1-indexed
    day: todayDay,
    dateString: `${todayYear}-${todayMonth + 1}-${todayDay}`
  });
  
  // Test cases
  const testDates = [
    // Yesterday
    new Date(todayYear, todayMonth, todayDay - 1),
    // Today
    new Date(todayYear, todayMonth, todayDay),
    // Tomorrow
    new Date(todayYear, todayMonth, todayDay + 1),
    // Next month
    new Date(todayYear, todayMonth + 1, todayDay),
    // Next year
    new Date(todayYear + 1, todayMonth, todayDay),
    // Last year
    new Date(todayYear - 1, todayMonth, todayDay)
  ];
  
  testDates.forEach((testDate, index) => {
    const checkYear = testDate.getFullYear();
    const checkMonth = testDate.getMonth();
    const checkDay = testDate.getDate();
    
    // Logic from SingleDatePicker
    const isFutureDate = (
      checkYear > todayYear || 
      (checkYear === todayYear && checkMonth > todayMonth) ||
      (checkYear === todayYear && checkMonth === todayMonth && checkDay > todayDay)
    );
    
    console.log(`Test ${index + 1}:`, {
      testDate: `${checkYear}-${checkMonth + 1}-${checkDay}`,
      isFuture: isFutureDate,
      disabled: isFutureDate ? 'YES' : 'NO'
    });
  });
}

// Test date initialization logic
function testDateInitialization() {
  console.log('\n=== Testing Date Initialization ===');
  
  // Test today initialization
  const today = new Date();
  today.setHours(12, 0, 0, 0);
  
  console.log('Today initialization:', {
    date: today.toString(),
    localDate: `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`,
    timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
    timezoneOffset: today.getTimezoneOffset()
  });
  
  // Test URL date parsing
  const testUrlDate = '2024-01-15';
  const [year, month, day] = testUrlDate.split('-').map(Number);
  const parsedDate = new Date(year, month - 1, day, 12, 0, 0, 0);
  
  console.log('URL date parsing:', {
    urlDate: testUrlDate,
    parsedYear: year,
    parsedMonth: month,
    parsedDay: day,
    parsedDate: parsedDate.toString(),
    isValidDate: !isNaN(parsedDate.getTime())
  });
}

// Test today redirect logic
function testTodayRedirect() {
  console.log('\n=== Testing Today Redirect Logic ===');
  
  const today = new Date();
  const year = today.getFullYear();
  const month = String(today.getMonth() + 1).padStart(2, '0');
  const day = String(today.getDate()).padStart(2, '0');
  const formattedDate = `${year}-${month}-${day}`;
  
  console.log('Today redirect format:', {
    todayDate: today.toString(),
    formattedDate: formattedDate,
    redirectPath: `/counselor-dashboard/${formattedDate}`
  });
}

// Run all tests
testFutureDateLogic();
testDateInitialization();
testTodayRedirect();
