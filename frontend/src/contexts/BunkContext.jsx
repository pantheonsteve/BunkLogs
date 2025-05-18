// BunkContext.jsx
import React, { createContext, useState, useContext } from 'react';

// Create the context with default values to prevent destructuring errors
const BunkContext = createContext({
  bunkData: null,
  setBunkData: () => {}
});

// Create a custom hook to use the context
export function useBunk() {
  return useContext(BunkContext);
}

// Create the provider component
export function BunkProvider({ children }) {
  const [bunkData, setBunkData] = useState(null);

  // Value to be provided to consuming components
  const value = {
    bunkData,
    setBunkData
  };

  return (
    <BunkContext.Provider value={value}>
      {children}
    </BunkContext.Provider>
  );
}