import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { useAuth } from './auth/AuthContext';
import { useEffect } from 'react';
import Signin from './pages/Signin';
import Signup from './pages/Signup';
import Dashboard from './pages/Dashboard';
import AdminDashboard from './pages/AdminDashboard';
import BunkDashboard from './pages/BunkDashboard';
import CamperDashboard from './pages/CamperDashboard';
import CounselorDashboard from './pages/CounselorDashboard';
import UnitHeadDashboard from './pages/UnitHeadDashboard';
import CamperCareDashboard from './pages/CamperCareDashboard';
import DatePickerTest from './pages/DatePickerTest';
import AuthCallback from './pages/AuthCallback';
import CallbackPage from './pages/CallbackPage';
import ResetPassword from './pages/ResetPassword';
import ResetPasswordConfirm from './pages/ResetPasswordConfirm';
import AuthSuccess from './pages/AuthSuccess';
import Orders from './pages/Orders';
import OrderDetail from './pages/OrderDetail';
import OrderEdit from './pages/OrderEdit';
import AdminBunkLogs from './pages/AdminBunkLogs';
import { useBunk } from './contexts/BunkContext';

// Protected route component
function ProtectedRoute({ children }) {
  const { isAuthenticated, loading } = useAuth();
  
  if (loading) {
    return <div>Loading...</div>;
  }
  
  if (!isAuthenticated) {
    return <Navigate to="/signin" />;
  }
  
  return children;
}

// Component to handle redirected paths from 404 page
function RedirectHandler() {
  useEffect(() => {
    const redirectPath = sessionStorage.getItem('redirectPath');
    if (redirectPath) {
      sessionStorage.removeItem('redirectPath');
      // Use replace to avoid adding to history
      window.location.replace(redirectPath);
    }
  }, []);
  
  return null;
}

function Router() {
  return (
    <BrowserRouter>
      <RedirectHandler />
      <Routes>
        {/* Public routes */}
        <Route path="/signin" element={<Signin />} />
        <Route path="/signup" element={<Signup />} />
        <Route path="/reset-password" element={<ResetPassword />} />
        <Route path="/accounts/password/reset/key/:key" element={<ResetPasswordConfirm />} />
        <Route path="/auth/callback" element={<AuthCallback />} />
        <Route path="/callback" element={<CallbackPage />} />
        <Route path="/account/provider/callback" element={<CallbackPage />} />
        <Route path="/auth/success" element={<AuthSuccess />} />
        
        {/* Protected routes */}
        <Route 
          path="/dashboard" 
          element={
            <ProtectedRoute>
              <Dashboard />
            </ProtectedRoute>
          } 
        />
        <Route 
          path="/admin-dashboard" 
          element={
            <ProtectedRoute>
              <AdminDashboard />
            </ProtectedRoute>
          } 
        />
        <Route 
          path="/admin-dashboard/:date" 
          element={
            <ProtectedRoute>
              <AdminDashboard />
            </ProtectedRoute>
          } 
        />
        <Route 
          path="/admin-bunk-logs" 
          element={
            <ProtectedRoute>
              <AdminBunkLogs />
            </ProtectedRoute>
          } 
        />
        <Route 
          path="/admin-bunk-logs/:date" 
          element={
            <ProtectedRoute>
              <AdminBunkLogs />
            </ProtectedRoute>
          } 
        />
        <Route 
          path="/dashboard/unithead" 
          element={
            <ProtectedRoute>
              <UnitHeadDashboard />
            </ProtectedRoute>
          } 
        />
        <Route 
          path="/unithead/:id/:date" 
          element={
            <ProtectedRoute>
              <UnitHeadDashboard />
            </ProtectedRoute>
          } 
        />
        <Route 
          path="/dashboard/campercare" 
          element={
            <ProtectedRoute>
              <CamperCareDashboard />
            </ProtectedRoute>
          } 
        />
        <Route 
          path="/counselor-dashboard" 
          element={
            <ProtectedRoute>
              <CounselorDashboard />
            </ProtectedRoute>
          } 
        />
        <Route 
          path="/counselor-dashboard/:date" 
          element={
            <ProtectedRoute>
              <CounselorDashboard />
            </ProtectedRoute>
          } 
        />
        <Route 
          path="/campercare/:id/:date" 
          element={
            <ProtectedRoute>
              <CamperCareDashboard />
            </ProtectedRoute>
          } 
        />
        <Route 
          path="/bunk/:bunk_id/:date" 
          element={
            <ProtectedRoute>
              <BunkDashboard />
            </ProtectedRoute>
          } 
        />
        
        <Route 
          path="/bunk/:bunk_id/:date/orders/:orderId" 
          element={
            <ProtectedRoute>
              <BunkDashboard />
            </ProtectedRoute>
          } 
        />
        
        <Route 
          path="/bunk/:bunk_id/:date/orders/:orderId/edit" 
          element={
            <ProtectedRoute>
              <BunkDashboard />
            </ProtectedRoute>
          } 
        />

        <Route 
          path="/bunk/:bunk_id/:date/orders/:orderId" 
          element={
            <ProtectedRoute>
              <BunkDashboard />
            </ProtectedRoute>
          } 
        />

        <Route 
          path="/bunk/:bunk_id/:date/orders/:orderId/edit" 
          element={
            <ProtectedRoute>
              <BunkDashboard />
            </ProtectedRoute>
          } 
        />

        <Route 
          path="/camper/:camper_id/:date" 
          element={
            <ProtectedRoute>
              <CamperDashboard />
            </ProtectedRoute>
          } 
        />

        <Route 
          path="/orders" 
          element={
            <ProtectedRoute>
              <Orders />
            </ProtectedRoute>
          } 
        />

        <Route 
          path="/orders/:orderId" 
          element={
            <ProtectedRoute>
              <OrderDetail />
            </ProtectedRoute>
          } 
        />

        <Route 
          path="/orders/:orderId/edit" 
          element={
            <ProtectedRoute>
              <OrderEdit />
            </ProtectedRoute>
          } 
        />

        <Route path="/test-datepicker" element={<DatePickerTest />} />
        
        {/* Default redirect */}
        <Route path="/" element={<Navigate to="/dashboard" />} />
        <Route path="*" element={<Navigate to="/dashboard" />} />
      </Routes>
    </BrowserRouter>
  );
}

export default Router;