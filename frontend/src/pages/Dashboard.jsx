import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';
import { homePathForUser } from '../utils/auth/capability';

/**
 * Role-based landing page.
 *
 * Reads membership roles and immediately redirects to the appropriate
 * new-model role dashboard. This component is reachable from the Sidebar
 * "Home" link, the / root, and the * catch-all.
 */
function Dashboard() {
  const { loading: authLoading, isAuthenticating, user } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    if (authLoading || isAuthenticating) return;

    const destination = homePathForUser(user);
    navigate(destination === '/dashboard' ? '/admin/home' : destination, { replace: true });
  }, [user, navigate, authLoading, isAuthenticating]);

  return (
    <div className="flex items-center justify-center min-h-[50vh]">
      <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-blue-500" />
    </div>
  );
}

export default Dashboard;
