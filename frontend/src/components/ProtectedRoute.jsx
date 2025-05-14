import { Navigate, Outlet } from 'react-router-dom';
import { useAuth } from '../auth';

const ProtectedRoute = () => {
  const { isAuthorized } = useAuth();

  if (!isAuthorized) {
    return <Navigate to="/signin" replace />;
  }

  return <Outlet />;
};

export default ProtectedRoute;