import { useState, useEffect } from 'react';
import SingleDatePicker from '../components/ui/SingleDatePicker';

export default function DatePickerTest() {
  const [selectedDate, setSelectedDate] = useState(new Date());

  // Set test user data in localStorage to simulate login
  useEffect(() => {
    const testUser = {
      id: 26,
      first_name: "CamperCare",
      last_name: "One", 
      email: "cc1@clc.org",
      role: "camper_care"
    };
    localStorage.setItem('user', JSON.stringify(testUser));
    console.log('Test user set in localStorage:', testUser);
  }, []);

  return (
    <div className="min-h-screen bg-gray-100 dark:bg-gray-900 p-8">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-8">
          Date Picker Test - User ID 26 (CamperCare One)
        </h1>
        
        <div className="bg-white dark:bg-gray-800 rounded-lg p-6 shadow-lg">
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-4">
            Single Date Picker (Assignment: 2025-06-19 to ongoing)
          </h2>
          
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Select Date (only dates from June 19, 2025 onwards should be selectable):
              </label>
              <SingleDatePicker 
                date={selectedDate} 
                setDate={setSelectedDate}
              />
            </div>
            
            <div className="mt-4 p-4 bg-gray-50 dark:bg-gray-700 rounded">
              <p className="text-sm text-gray-600 dark:text-gray-400">
                Selected Date: {selectedDate ? selectedDate.toISOString() : 'None'}
              </p>
            </div>
            
            <div className="mt-4 p-4 bg-blue-50 dark:bg-blue-900 rounded">
              <p className="text-sm text-blue-600 dark:text-blue-400">
                Instructions: Open browser dev tools console to see debug logs.
                The date picker should only allow dates within the user's assignment range.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
