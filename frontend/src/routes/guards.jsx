import { Suspense, useEffect } from 'react';
import {
  Navigate,
  Outlet,
  useLocation,
  useParams,
  useSearchParams,
} from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';
import isSuperAdmin from '../utils/auth/isSuperAdmin';
import { hasCapability, homePathForUser } from '../utils/auth/capability';
import DashboardsHub from '../pages/dashboards/DashboardsHub';
import DevImpersonation from '../dev/DevImpersonation';

/** Fallback shown while a lazily-loaded route chunk is fetched. */
function RouteFallback() {
  return (
    <div className="flex items-center justify-center min-h-screen bg-gray-100 dark:bg-gray-900">
      <div className="animate-spin rounded-full h-10 w-10 border-t-2 border-b-2 border-violet-500" />
    </div>
  );
}

export function RootLayout() {
  return (
    <>
      <RedirectHandler />
      <DevImpersonation />
      <Suspense fallback={<RouteFallback />}>
        <Outlet />
      </Suspense>
    </>
  );
}

export function HomeRedirect() {
  const { user, loading } = useAuth();
  if (loading) return <div>Loading...</div>;
  return <Navigate to={homePathForUser(user)} replace />;
}

export function ProtectedRoute({ children }) {
  const { isAuthenticated, loading } = useAuth();
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

  return children;
}

export function SubjectProfileRedirect() {
  const { personId } = useParams();
  const location = useLocation();
  return <Navigate to={`/profile/${personId}${location.search}`} replace />;
}

export function AdminRoute({ children }) {
  const { isAuthenticated, loading, user } = useAuth();
  const location = useLocation();

  if (loading) {
    return <div>Loading...</div>;
  }

  if (!isAuthenticated) {
    const next = `${location.pathname}${location.search}${location.hash}`;
    return <Navigate to={`/signin?next=${encodeURIComponent(next)}`} replace />;
  }

  const isAdmin = isSuperAdmin(user) || user?.role?.toLowerCase() === 'admin';
  if (!isAdmin) {
    return <Navigate to="/" replace state={{ toast: 'Admin access required' }} />;
  }

  return children;
}

export function LeadershipTemplatesRoute({ children }) {
  const { isAuthenticated, loading, user } = useAuth();
  const location = useLocation();

  if (loading) {
    return <div>Loading...</div>;
  }

  if (!isAuthenticated) {
    const next = `${location.pathname}${location.search}${location.hash}`;
    return <Navigate to={`/signin?next=${encodeURIComponent(next)}`} replace />;
  }

  const canAccess =
    isSuperAdmin(user)
    || user?.role?.toLowerCase() === 'admin'
    || hasCapability(user, 'program_lead');
  if (!canAccess) {
    return <Navigate to="/" replace state={{ toast: 'Admin access required' }} />;
  }

  return children;
}

export function LegacyBunkDashboardRedirect() {
  const { bunkId } = useParams();
  const [searchParams] = useSearchParams();
  const qs = searchParams.toString();
  const target = `/dashboards/group/${bunkId}${qs ? `?${qs}` : ''}`;
  return <Navigate to={target} replace />;
}

export function LegacyLtTemplatesRedirect() {
  const location = useLocation();
  const target = location.pathname.replace(/^\/leadership-team\/templates/, '/admin/templates');
  return <Navigate to={`${target}${location.search}${location.hash}`} replace />;
}

export function LegacyAdminTemplateEditRedirect() {
  const { id } = useParams();
  const location = useLocation();
  return <Navigate to={`/admin/templates/${id}${location.search}${location.hash}`} replace />;
}

export function DashboardsIndex() {
  const { user, loading } = useAuth();
  if (loading) {
    return <div>Loading...</div>;
  }
  const isAdmin = hasCapability(user, 'admin') || isSuperAdmin(user);
  if (isAdmin) {
    return <Navigate to="/admin/home" replace />;
  }
  return <DashboardsHub />;
}

function RedirectHandler() {
  useEffect(() => {
    const redirectPath = sessionStorage.getItem('redirectPath');
    if (redirectPath) {
      sessionStorage.removeItem('redirectPath');
      window.location.replace(redirectPath);
    }
  }, []);

  return null;
}
