import React from 'react';
import CamperCareDashboard from '@/components/CamperCareDashboard';

/**
 * Example page showing how to use the CamperCareDashboard component
 * This demonstrates the complete integration of the filtering system
 * that matches the admin dashboard styling
 */
const CamperCarePageExample = () => {
  // These would typically come from your app's auth/routing context
  const camperCareId = "26"; // Example camper care staff ID
  const authToken = "your-auth-token-here"; // User's authentication token

  return (
    <CamperCareDashboard 
      camperCareId={camperCareId}
      authToken={authToken}
    />
  );
};

export default CamperCarePageExample;
