/**
 * Utilities for preserving state across page refreshes
 */

// Storage keys
const STORAGE_KEYS = {
  SELECTED_DATE: 'selectedDate',
}

/**
 * Saves the selected date to localStorage before page refresh
 * @param {Date|string} date - The date to preserve
 */
export const saveSelectedDate = (date) => {
  if (date) {
    const dateString = typeof date === 'object' ? date.toISOString() : date;
    localStorage.setItem(STORAGE_KEYS.SELECTED_DATE, dateString);
  }
};

/**
 * Retrieves the selected date from localStorage
 * @returns {Date|null} The stored date or null if not found
 */
export const getSelectedDate = () => {
  const dateString = localStorage.getItem(STORAGE_KEYS.SELECTED_DATE);
  if (dateString) {
    localStorage.removeItem(STORAGE_KEYS.SELECTED_DATE); // Clear after retrieving
    return new Date(dateString);
  }
  return null;
};