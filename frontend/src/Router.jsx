import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { useAuth } from './auth/AuthContext';
import { useEffect } from 'react';
import isSuperAdmin from './utils/auth/isSuperAdmin';
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
import StaffMemberHistory from './pages/StaffMemberHistory';
import MigrationDashboard from './pages/MigrationDashboard';
import MyReflectionsPage from './pages/MyReflectionsPage';
import ReflectionDetailPage from './pages/ReflectionDetailPage';
import ReflectionFormPage from './pages/ReflectionFormPage';
import ReflectionSummaryPage from './pages/ReflectionSummaryPage';
import TeamDashboardPage from './pages/TeamDashboardPage';
import WellnessDashboardPage from './pages/WellnessDashboardPage';
import MembershipManagementPage from './pages/MembershipManagementPage';
import AdminHub from './pages/admin/AdminHub';
import TemplateListPage from './pages/admin/templates/TemplateListPage';
import TemplateEditorPage from './pages/admin/templates/TemplateEditorPage';
import TemplateNewPage from './pages/admin/templates/TemplateNewPage';
import GroupListPage from './pages/admin/groups/GroupListPage';
import GroupDetailPage from './pages/admin/groups/GroupDetailPage';
import TasksPage from './pages/TasksPage';
import SupervisorCoveragePage from './pages/SupervisorCoveragePage';
import CoverageDashboardPage from './pages/dashboards/CoverageDashboardPage';
import SubjectTrendsPage from './pages/dashboards/SubjectTrendsPage';
import SubjectDetailPage from './pages/dashboards/SubjectDetailPage';
import AuthorAttributionPage from './pages/dashboards/AuthorAttributionPage';
import ConcernsInboxPage from './pages/dashboards/ConcernsInboxPage';
import DashboardsHub from './pages/dashboards/DashboardsHub';
import AdminLayout from './layouts/AdminLayout';
import { useBunk } from './contexts/BunkContext';

// Protected route component
function ProtectedRoute({ children }) {
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

// Admin-only route: Super Admin (is_staff || is_superuser) or User.role === 'admin'.
// See `frontend/src/utils/auth/isSuperAdmin.js` for the canonical helper.
function AdminRoute({ children }) {
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

        <Route
          path="/admin-staff/:staffId"
          element={
            <ProtectedRoute>
              <StaffMemberHistory />
            </ProtectedRoute>
          }
        />

        <Route path="/test-datepicker" element={<DatePickerTest />} />

        <Route
          path="/migration-dashboard"
          element={
            <ProtectedRoute>
              <MigrationDashboard />
            </ProtectedRoute>
          }
        />

        <Route
          path="/reflect"
          element={
            <ProtectedRoute>
              <ReflectionFormPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/reflect/summary"
          element={
            <ProtectedRoute>
              <ReflectionSummaryPage />
            </ProtectedRoute>
          }
        />

        <Route
          path="/my-reflections"
          element={
            <ProtectedRoute>
              <MyReflectionsPage />
            </ProtectedRoute>
          }
        />

        {/* 3.27: Single-reflection read-only viewer. Replaces the broken
            /reflect/summary?reflection=<id> deep-links from concerns /
            subject / trends, and unblocks the coverage popover "View"
            button on /tasks (which already routes here). */}
        <Route
          path="/reflections/:id"
          element={
            <ProtectedRoute>
              <ReflectionDetailPage />
            </ProtectedRoute>
          }
        />

        {/* Legacy off-pattern dashboard URLs -- preserve as redirects so
            existing bookmarks still land. The canonical URLs now live
            under /dashboards/* (see below). */}
        <Route
          path="/team/dashboard"
          element={<Navigate to="/dashboards/team" replace />}
        />
        <Route
          path="/wellness/dashboard"
          element={<Navigate to="/dashboards/wellness" replace />}
        />

        {/* Step 3.20 + 3.26: Coverage / trends / subject / authors /
            concerns / team / wellness dashboards, plus the /dashboards
            hub landing page. */}
        <Route
          path="/dashboards"
          element={
            <ProtectedRoute>
              <DashboardsHub />
            </ProtectedRoute>
          }
        />
        <Route
          path="/dashboards/coverage"
          element={
            <ProtectedRoute>
              <CoverageDashboardPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/dashboards/subject-trends/:groupId"
          element={
            <ProtectedRoute>
              <SubjectTrendsPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/dashboards/subject/:personId"
          element={
            <ProtectedRoute>
              <SubjectDetailPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/dashboards/authors"
          element={
            <ProtectedRoute>
              <AuthorAttributionPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/dashboards/concerns"
          element={
            <ProtectedRoute>
              <ConcernsInboxPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/dashboards/team"
          element={
            <ProtectedRoute>
              <TeamDashboardPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/dashboards/wellness"
          element={
            <ProtectedRoute>
              <WellnessDashboardPage />
            </ProtectedRoute>
          }
        />

        {/* 3.28: Admin routes share one shell via AdminLayout. Every
            child renders inside Sidebar + Header so navigation stays in
            place when you click between admin surfaces. AdminRoute is
            applied per-child (not on the layout) so that
            /admin/memberships can stay ProtectedRoute -- its in-page
            "Access restricted" branch must keep rendering for non-admin
            authenticated users instead of redirecting. */}
        <Route
          path="/admin"
          element={
            <ProtectedRoute>
              <AdminLayout />
            </ProtectedRoute>
          }
        >
          <Route
            index
            element={
              <AdminRoute>
                <AdminHub />
              </AdminRoute>
            }
          />
          <Route path="memberships" element={<MembershipManagementPage />} />
          <Route
            path="templates"
            element={
              <AdminRoute>
                <TemplateListPage />
              </AdminRoute>
            }
          />
          <Route
            path="templates/new"
            element={
              <AdminRoute>
                <TemplateNewPage />
              </AdminRoute>
            }
          />
          <Route
            path="groups"
            element={
              <AdminRoute>
                <GroupListPage />
              </AdminRoute>
            }
          />
          <Route
            path="groups/:id"
            element={
              <AdminRoute>
                <GroupDetailPage />
              </AdminRoute>
            }
          />
        </Route>

        {/* 3.28: Template editor is a deliberate exception. It is a
            focused full-bleed editor with its own sticky in-page header
            (inline name editing, language switcher, save). Pulling it
            under AdminLayout would either double-stack stickies or
            shrink the working pane used by the split-pane editor.
            Future contributors: do NOT move this under the layout
            without re-evaluating that tradeoff. */}
        <Route
          path="/admin/templates/:id/edit"
          element={
            <AdminRoute>
              <TemplateEditorPage />
            </AdminRoute>
          }
        />

        {/* Roster-aware tasks home screen */}
        <Route
          path="/tasks"
          element={
            <ProtectedRoute>
              <TasksPage />
            </ProtectedRoute>
          }
        />

        {/* Supervisor coverage view */}
        <Route
          path="/supervisor/coverage"
          element={
            <ProtectedRoute>
              <SupervisorCoveragePage />
            </ProtectedRoute>
          }
        />

        {/* Default redirect */}
        <Route path="/" element={<Navigate to="/dashboard" />} />
        <Route path="*" element={<Navigate to="/dashboard" />} />
      </Routes>
    </BrowserRouter>
  );
}

export default Router;