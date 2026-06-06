import {
  BrowserRouter,
  Routes,
  Route,
  Navigate,
  useLocation,
  useParams,
  useSearchParams,
} from 'react-router-dom';
import { useAuth } from './auth/AuthContext';
import { useEffect } from 'react';
import isSuperAdmin from './utils/auth/isSuperAdmin';
import { hasCapability } from './utils/auth/capability';
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
import ReflectionsDashboardPage from './pages/ReflectionsDashboardPage';
import LogsDashboardPage from './pages/LogsDashboardPage';
import WellnessDashboardPage from './pages/WellnessDashboardPage';
import MembershipManagementPage from './pages/MembershipManagementPage';
import AdminHub from './pages/admin/AdminHub';
import AdminHome from './pages/admin/AdminHome';
import AdminDashboardV2 from './pages/admin/Dashboard';
import AdminPeople from './pages/admin/People';
import AdminAssignments from './pages/admin/Assignments';
import AdminSettingsPage from './pages/admin/Settings';
import GroupListPage from './pages/admin/groups/GroupListPage';
import GroupDetailPage from './pages/admin/groups/GroupDetailPage';
import FieldKeyListPage from './pages/admin/field-keys/FieldKeyListPage';
import TasksPage from './pages/TasksPage';
import ObservationsInbox from './pages/observations/ObservationsInbox';
import ObservationThread from './pages/observations/ObservationThread';
import PerformanceDashboardPage from './pages/groups/PerformanceDashboardPage';
import CoverageDashboardPage from './pages/dashboards/CoverageDashboardPage';
import SubjectTrendsPage from './pages/dashboards/SubjectTrendsPage';
import SubjectDetailPage from './pages/dashboards/SubjectDetailPage';
import AuthorAttributionPage from './pages/dashboards/AuthorAttributionPage';
import ConcernsInboxPage from './pages/dashboards/ConcernsInboxPage';
import DashboardsHub from './pages/dashboards/DashboardsHub';
import GroupDashboardPage from './pages/dashboards/GroupDashboardPage';
import AdminLayout from './layouts/AdminLayout';
import AppLayout from './layouts/AppLayout';
import CounselorMobileDashboard from './pages/counselor/CounselorMobileDashboard';
import UnitHeadDashboardV2 from './pages/unit-head/UnitHeadDashboard';
import UnitHeadCamperDashboardPage from './pages/unit-head/UnitHeadCamperDashboardPage';
import UnitHeadSelfReflectionPage from './pages/unit-head/UnitHeadSelfReflectionPage';
import UnitHeadSelfReflectionHistoryPage from './pages/unit-head/UnitHeadSelfReflectionHistoryPage';
import CamperCareDashboardV2 from './pages/camper-care/Dashboard';
import CamperCareCamperDashboardPage from './pages/camper-care/CamperDashboardPage';
import CamperCareFlagsPage from './pages/camper-care/Flags';
import CamperCareOrdersPage from './pages/camper-care/Orders';
import CamperCareSelfReflectionPage from './pages/camper-care/SelfReflectionPage';
import CamperCareSelfReflectionHistoryPage from './pages/camper-care/SelfReflectionHistoryPage';
import KitchenStaffDashboard from './pages/kitchen-staff/Dashboard';
import KitchenStaffReflectionForm from './pages/kitchen-staff/ReflectionForm';
import KitchenStaffHistory from './pages/kitchen-staff/History';
import MadrichDashboard from './pages/madrich/Dashboard';
import MadrichReflectionForm from './pages/madrich/ReflectionForm';
import MadrichHistory from './pages/madrich/History';
import LeadershipTeamDashboard from './pages/leadership-team/Dashboard';
import LeadershipTeamTeamDashboard from './pages/leadership-team/TeamDashboard';
import LeadershipTeamMemberReflection from './pages/leadership-team/MemberReflection';
import LeadershipTeamSelfReflectionPage from './pages/leadership-team/SelfReflectionPage';
import LeadershipTeamTemplateLibrary from './pages/leadership-team/TemplateLibrary';
import LeadershipTeamTemplateBuilderPage from './pages/leadership-team/TemplateBuilder/TemplateBuilderPage';
import LeadershipTeamResponses from './pages/leadership-team/Responses';
import HelpIndexPage from './pages/help/HelpIndexPage';
import HelpArticlePage from './pages/help/HelpArticlePage';
import HelpRoute from './pages/help/HelpRoute';
import SpecialistDashboard from './pages/specialist/Dashboard';
import SpecialistCamperView from './pages/specialist/CamperView';
import SpecialistSelfReflectionPage from './pages/specialist/SelfReflectionPage';
import MaintenanceQueue from './pages/maintenance/Queue';
import MaintenanceTicketDetail from './pages/maintenance/TicketDetail';
import CamperReflectionListPage from './pages/counselor/CamperReflectionListPage';
import CamperReflectionFormPage from './pages/counselor/CamperReflectionFormPage';
import CounselorSelfReflectionPage from './pages/counselor/CounselorSelfReflectionPage';
import CounselorSelfReflectionHistoryPage from './pages/counselor/CounselorSelfReflectionHistoryPage';
import CounselorRequestsListPage from './pages/counselor/CounselorRequestsListPage';
import CamperCareRequestFormPage from './pages/counselor/CamperCareRequestFormPage';
import MaintenanceTicketFormPage from './pages/counselor/MaintenanceTicketFormPage';
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

// Step 7_23: redirect the legacy /dashboards/subject/:personId path to the
// renamed /profile/:personId surface, preserving any query string.
function SubjectProfileRedirect() {
  const { personId } = useParams();
  const location = useLocation();
  return <Navigate to={`/profile/${personId}${location.search}`} replace />;
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

// Permanent redirect for the legacy per-role bunk dashboard URLs +
// the prior `/dashboards/bunk/:bunkId` URL from the bunk-only
// consolidation. Everything now lives at `/dashboards/group/:id`.
// We preserve the `?date=` query so deep-linked past-day views
// survive the redirect.
function LegacyBunkDashboardRedirect() {
  const { bunkId } = useParams();
  const [searchParams] = useSearchParams();
  const qs = searchParams.toString();
  const target = `/dashboards/group/${bunkId}${qs ? `?${qs}` : ''}`;
  return <Navigate to={target} replace />;
}

/** Retired /leadership-team/templates* → /admin/templates* (bookmarks). */
function LegacyLtTemplatesRedirect() {
  const location = useLocation();
  const target = location.pathname.replace(/^\/leadership-team\/templates/, '/admin/templates');
  return <Navigate to={`${target}${location.search}${location.hash}`} replace />;
}

/** Retired legacy admin editor URL → LT builder at /admin/templates/:id. */
function LegacyAdminTemplateEditRedirect() {
  const { id } = useParams();
  const location = useLocation();
  return <Navigate to={`/admin/templates/${id}${location.search}${location.hash}`} replace />;
}

/** Admins land on Admin Home; supervisors/program leads keep the dashboards hub. */
function DashboardsIndex() {
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

        {/* 3.33 follow-up: pages that originally rendered as
            single-column mobile-first surfaces (no Sidebar / Header)
            now share the AppLayout chrome so the new capability-aware
            sidebar from 3.32 is always reachable. ProtectedRoute sits
            on the layout so the gate fires once for every child. */}
        <Route
          element={
            <ProtectedRoute>
              <AppLayout />
            </ProtectedRoute>
          }
        >
          <Route path="/reflect" element={<ReflectionFormPage />} />
          <Route path="/reflect/summary" element={<ReflectionSummaryPage />} />
          <Route path="/tasks" element={<TasksPage />} />
          <Route
            path="/help"
            element={
              <HelpRoute>
                <HelpIndexPage />
              </HelpRoute>
            }
          />
          <Route
            path="/help/:slug"
            element={
              <HelpRoute>
                <HelpArticlePage />
              </HelpRoute>
            }
          />
          <Route path="/notes" element={<Navigate to="/observations" replace />} />
          <Route path="/notes/*" element={<Navigate to="/observations" replace />} />
          <Route path="/subject-notes" element={<Navigate to="/observations" replace />} />
          <Route path="/observations" element={<ObservationsInbox />} />
          <Route path="/observations/:observationId" element={<ObservationThread />} />
          <Route path="/groups/performance" element={<PerformanceDashboardPage />} />
          <Route path="/supervisor/coverage" element={<Navigate to="/groups/performance" replace />} />
          {/* 7_6d: Counselor mobile flow. Lives under AppLayout so the
              sidebar/header chrome (3.32 / 3.33) stays available on the
              dashboard, roster, and form screens. The legacy
              `/counselor-dashboard` route still serves the old
              CounselorDashboard.jsx self-reflection surface and is
              untouched while 7_6d/e migrate counselors over. */}
          <Route path="/counselor" element={<CounselorMobileDashboard />} />
          <Route
            path="/counselor/camper-reflections"
            element={<CamperReflectionListPage />}
          />
          <Route
            path="/counselor/camper-reflections/:date"
            element={<CamperReflectionListPage />}
          />
          <Route
            path="/counselor/camper-reflections/new"
            element={<CamperReflectionFormPage />}
          />
          <Route
            path="/counselor/camper-reflections/:reflectionId/edit"
            element={<CamperReflectionFormPage />}
          />
          {/* 7_6e: Counselor self-reflection. ``/self-reflection`` auto-routes
              to today's edit URL if a submission already exists, otherwise
              renders the create form. ``/history`` is a dedicated paginated
              view (Story 6 criterion 6); gap days are rendered as
              "No submission" rows by the server. */}
          <Route
            path="/counselor/self-reflection"
            element={<CounselorSelfReflectionPage />}
          />
          <Route
            path="/counselor/self-reflection/history"
            element={<CounselorSelfReflectionHistoryPage />}
          />
          <Route
            path="/counselor/self-reflection/:reflectionId/edit"
            element={<CounselorSelfReflectionPage />}
          />
          {/* 7_6f: Camper Care + Maintenance request flow. The list view
              accepts ``?status=open|all`` so counselors can confirm a
              request closed without leaving the surface. Both per-type
              forms have a stable client_submission_id ref so an offline
              replay POSTs the same row instead of duplicating. */}
          <Route
            path="/counselor/requests"
            element={<CounselorRequestsListPage />}
          />
          <Route
            path="/counselor/requests/camper-care/new"
            element={<CamperCareRequestFormPage />}
          />
          <Route
            path="/counselor/requests/maintenance/new"
            element={<MaintenanceTicketFormPage />}
          />
          {/* 7_7: Unit Head mobile flow. The legacy `/dashboard/unithead`
              route is preserved above and still serves the old surface;
              the new `/unit-head` flow renders the supervised bunk list,
              shared Bunk/Camper Dashboards, and the UH self-reflection
              form + history. */}
          <Route path="/unit-head" element={<UnitHeadDashboardV2 />} />
          <Route
            path="/unit-head/bunks/:bunkId"
            element={<LegacyBunkDashboardRedirect />}
          />
          <Route
            path="/unit-head/campers/:camperId"
            element={<UnitHeadCamperDashboardPage />}
          />
          <Route
            path="/unit-head/self-reflection"
            element={<UnitHeadSelfReflectionPage />}
          />
          <Route
            path="/unit-head/self-reflection/history"
            element={<UnitHeadSelfReflectionHistoryPage />}
          />
          <Route
            path="/unit-head/self-reflection/:reflectionId/edit"
            element={<UnitHeadSelfReflectionPage />}
          />
          {/* 7_8b: Camper Care mobile flow. Lives under AppLayout so the
              sidebar/header chrome stays available across the dashboard,
              flag/order workspaces, and the note form. The legacy
              `/dashboard/campercare` route still serves the old
              CamperCareDashboard.jsx surface and is untouched while
              wave 5 migration progresses. Bunk + camper drill-down
              pages (Story 18 c.9 + Story 21 in-context note CTA) were
              shipped in 7_8c and reuse the shared BunkDashboard +
              CamperDashboard components with caseload-scoped CC views. */}
          <Route path="/camper-care" element={<CamperCareDashboardV2 />} />
          <Route
            path="/camper-care/bunks/:bunkId"
            element={<LegacyBunkDashboardRedirect />}
          />
          <Route
            path="/camper-care/campers/:camperId"
            element={<CamperCareCamperDashboardPage />}
          />
          <Route path="/camper-care/flags" element={<CamperCareFlagsPage />} />
          <Route path="/camper-care/orders" element={<CamperCareOrdersPage />} />
          <Route path="/camper-care/notes/*" element={<Navigate to="/camper-care" replace />} />
          <Route
            path="/camper-care/self-reflection"
            element={<CamperCareSelfReflectionPage />}
          />
          <Route
            path="/camper-care/self-reflection/history"
            element={<CamperCareSelfReflectionHistoryPage />}
          />
          <Route
            path="/camper-care/self-reflection/:reflectionId/edit"
            element={<CamperCareSelfReflectionPage />}
          />
          {/* 7_10: Maintenance staff flow. The queue is the post-login landing
              page for maintenance staff (Story 30 criterion 2). No self-
              reflection card — maintenance has no reflection requirement
              (Story 30 criterion 9). The ticket detail preserves the active
              queue filter via the `from` query param so back navigation
              restores the correct view. */}
          <Route path="/maintenance" element={<MaintenanceQueue />} />
          <Route
            path="/maintenance/tickets/:ticketId"
            element={<MaintenanceTicketDetail />}
          />

          {/* ------------------------------------------------------------------ */}
          {/* Specialist (Step 7_9, Stories 24-29)                               */}
          {/* ------------------------------------------------------------------ */}
          <Route path="/specialist" element={<SpecialistDashboard />} />
          <Route path="/specialist/notes/*" element={<Navigate to="/specialist/campers" replace />} />
          <Route path="/specialist/campers/:camperId" element={<SpecialistCamperView />} />
          <Route path="/specialist/self-reflection/new" element={<SpecialistSelfReflectionPage />} />
          <Route
            path="/specialist/self-reflection/:reflectionId/edit"
            element={<SpecialistSelfReflectionPage />}
          />

          {/* Kitchen Staff (Step 7_11, Stories 37-44) */}
          <Route path="/kitchen-staff" element={<KitchenStaffDashboard />} />
          <Route path="/kitchen-staff/history" element={<KitchenStaffHistory />} />
          <Route path="/kitchen-staff/reflection/new" element={<KitchenStaffReflectionForm />} />
          <Route
            path="/kitchen-staff/reflection/:reflectionId/edit"
            element={<KitchenStaffReflectionForm />}
          />

          {/* Madrich (TBE) (Step 7_14, Stories 61-65) */}
          <Route path="/madrich" element={<MadrichDashboard />} />
          <Route path="/madrich/history" element={<MadrichHistory />} />
          <Route path="/madrich/reflection/new" element={<MadrichReflectionForm />} />
          <Route
            path="/madrich/reflection/:reflectionId/edit"
            element={<MadrichReflectionForm />}
          />

          {/* Leadership Team (Step 7_12, Stories 45-53) */}
          <Route path="/leadership-team" element={<LeadershipTeamDashboard />} />
          <Route
            path="/leadership-team/teams/:teamRole"
            element={<LeadershipTeamTeamDashboard />}
          />
          <Route
            path="/leadership-team/teams/:teamRole/members/:membershipId"
            element={<LeadershipTeamMemberReflection />}
          />
          <Route
            path="/leadership-team/self-reflection"
            element={<LeadershipTeamSelfReflectionPage />}
          />
          <Route
            path="/leadership-team/self-reflection/:reflectionId/edit"
            element={<LeadershipTeamSelfReflectionPage />}
          />
          <Route path="/leadership-team/templates/*" element={<LegacyLtTemplatesRedirect />} />

          {/* Subject Trend Grid — moved inside AppLayout for consistent chrome */}
          <Route
            path="/dashboards/subject-trends/:groupId"
            element={<SubjectTrendsPage />}
          />

          {/* Unified per-group dashboard. One URL serves every group
              type the backend knows how to render — bunk, unit,
              division, classroom. Counselor, CC, UH, Leadership
              Team, Admin, and (for classrooms) Faculty/Madrich all
              read here. The backend resolves role + group_type
              server-side and returns a `role_context` block the
              page uses to pick the right presentational component
              and chrome. The legacy /unit-head/bunks/:bunkId,
              /camper-care/bunks/:bunkId, and /dashboards/bunk/:bunkId
              URLs all redirect here so old bookmarks keep working. */}
          <Route
            path="/dashboards/group/:groupId"
            element={<GroupDashboardPage />}
          />
          <Route
            path="/dashboards/bunk/:bunkId"
            element={<LegacyBunkDashboardRedirect />}
          />
        </Route>

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
          element={<Navigate to="/dashboards/logs" replace />}
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
              <DashboardsIndex />
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
        {/* Step 7_23: the per-person dashboard is now the "Profile". The old
            /dashboards/subject/:personId path redirects here for compatibility. */}
        <Route
          path="/profile/:personId"
          element={
            <ProtectedRoute>
              <SubjectDetailPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/dashboards/subject/:personId"
          element={<SubjectProfileRedirect />}
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
          element={<Navigate to="/dashboards/logs" replace />}
        />
        <Route
          path="/dashboards/logs"
          element={
            <ProtectedRoute>
              <LogsDashboardPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/dashboards/reflections"
          element={
            <ProtectedRoute>
              <ReflectionsDashboardPage />
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
          <Route index element={<Navigate to="/admin/home" replace />} />
          <Route
            path="home"
            element={
              <AdminRoute>
                <AdminHome />
              </AdminRoute>
            }
          />
          {/* Legacy card hub — bookmarks from before Admin Home shipped. */}
          <Route
            path="hub"
            element={
              <AdminRoute>
                <AdminHub />
              </AdminRoute>
            }
          />
          <Route
            path="dashboard"
            element={
              <AdminRoute>
                <AdminDashboardV2 />
              </AdminRoute>
            }
          />
          <Route path="memberships" element={<MembershipManagementPage />} />
          {/* 7_13 PR2 — People, Assignments, Settings (Stories 55, 56, 58). */}
          <Route
            path="people"
            element={
              <AdminRoute>
                <AdminPeople />
              </AdminRoute>
            }
          />
          <Route
            path="assignments"
            element={
              <AdminRoute>
                <AdminAssignments />
              </AdminRoute>
            }
          />
          <Route
            path="settings"
            element={
              <AdminRoute>
                <AdminSettingsPage />
              </AdminRoute>
            }
          />
          {/* Template library + builder (LT UI, admin-only via AdminRoute). */}
          <Route
            path="templates"
            element={
              <AdminRoute>
                <LeadershipTeamTemplateLibrary />
              </AdminRoute>
            }
          />
          <Route
            path="templates/library"
            element={<Navigate to="/admin/templates" replace />}
          />
          <Route
            path="templates/new"
            element={
              <AdminRoute>
                <LeadershipTeamTemplateBuilderPage />
              </AdminRoute>
            }
          />
          <Route
            path="templates/:id/responses"
            element={
              <AdminRoute>
                <LeadershipTeamResponses />
              </AdminRoute>
            }
          />
          <Route
            path="templates/:id"
            element={
              <AdminRoute>
                <LeadershipTeamTemplateBuilderPage />
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
          {/* 3.29: FieldKey registry CRUD. Gated AdminRoute for v1; the
              underlying API also allows org admins via
              IsOrgAdminOrSuperuser, so we can broaden later without
              backend changes. */}
          <Route
            path="field-keys"
            element={
              <AdminRoute>
                <FieldKeyListPage />
              </AdminRoute>
            }
          />
        </Route>

        <Route
          path="/admin/templates/:id/edit"
          element={<LegacyAdminTemplateEditRedirect />}
        />

        {/* Default redirect */}
        <Route path="/" element={<Navigate to="/dashboard" />} />
        <Route path="*" element={<Navigate to="/dashboard" />} />
      </Routes>
    </BrowserRouter>
  );
}

export default Router;