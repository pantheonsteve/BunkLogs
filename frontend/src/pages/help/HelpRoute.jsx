import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../auth/AuthContext';
import { hasCapability } from '../../utils/auth/capability';

/**
 * Help is for program leads and admins (inclusive of super-admins).
 */
export default function HelpRoute({ children }) {
  const { isAuthenticated, loading, user } = useAuth();
  const location = useLocation();

  if (loading) {
    return <div>Loading...</div>;
  }

  if (!isAuthenticated) {
    const next = `${location.pathname}${location.search}${location.hash}`;
    return (
      <Navigate
        to={`/signin?next=${encodeURIComponent(next)}`}
        replace
      />
    );
  }

  if (!hasCapability(user, 'program_lead')) {
    return <Navigate to="/" replace state={{ toast: 'Help is available to program leads and admins' }} />;
  }

  return children;
}
