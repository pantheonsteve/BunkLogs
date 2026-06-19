import { Navigate } from 'react-router-dom';
import Signin from '../pages/Signin';
import Signup from '../pages/Signup';
import Dashboard from '../pages/Dashboard';
import AdminDashboard from '../pages/AdminDashboard';
import BunkDashboard from '../pages/BunkDashboard';
import CamperDashboard from '../pages/CamperDashboard';
import CounselorDashboard from '../pages/CounselorDashboard';
import UnitHeadDashboard from '../pages/UnitHeadDashboard';
import CamperCareDashboard from '../pages/CamperCareDashboard';
import DatePickerTest from '../pages/DatePickerTest';
import AuthCallback from '../pages/AuthCallback';
import CallbackPage from '../pages/CallbackPage';
import ResetPassword from '../pages/ResetPassword';
import ResetPasswordConfirm from '../pages/ResetPasswordConfirm';
import AuthSuccess from '../pages/AuthSuccess';
import Orders from '../pages/Orders';
import OrderDetail from '../pages/OrderDetail';
import OrderEdit from '../pages/OrderEdit';
import AdminBunkLogs from '../pages/AdminBunkLogs';
import StaffMemberHistory from '../pages/StaffMemberHistory';
import MigrationDashboard from '../pages/MigrationDashboard';
import MyReflectionsPage from '../pages/MyReflectionsPage';
import ReflectionDetailPage from '../pages/ReflectionDetailPage';
import ReflectionFormPage from '../pages/ReflectionFormPage';
import ReflectionSummaryPage from '../pages/ReflectionSummaryPage';
import ReflectionsDashboardPage from '../pages/ReflectionsDashboardPage';
import LogsDashboardPage from '../pages/LogsDashboardPage';
import WellnessDashboardPage from '../pages/WellnessDashboardPage';
import MembershipManagementPage from '../pages/MembershipManagementPage';
import AdminHub from '../pages/admin/AdminHub';
import AdminHome from '../pages/admin/AdminHome';
import AdminDashboardV2 from '../pages/admin/Dashboard';
import AdminPeople from '../pages/admin/People';
import AdminAssignments from '../pages/admin/Assignments';
import AdminSettingsPage from '../pages/admin/Settings';
import GroupListPage from '../pages/admin/groups/GroupListPage';
import GroupDetailPage from '../pages/admin/groups/GroupDetailPage';
import FieldKeyListPage from '../pages/admin/field-keys/FieldKeyListPage';
import TasksPage from '../pages/TasksPage';
import ObservationsInbox from '../pages/observations/ObservationsInbox';
import ObservationThread from '../pages/observations/ObservationThread';
import PerformanceDashboardPage from '../pages/groups/PerformanceDashboardPage';
import CoverageDashboardPage from '../pages/dashboards/CoverageDashboardPage';
import SubjectTrendsPage from '../pages/dashboards/SubjectTrendsPage';
import SubjectDetailPage from '../pages/dashboards/SubjectDetailPage';
import AuthorAttributionPage from '../pages/dashboards/AuthorAttributionPage';
import ConcernsInboxPage from '../pages/dashboards/ConcernsInboxPage';
import GroupDashboardPage from '../pages/dashboards/GroupDashboardPage';
import AdminLayout from '../layouts/AdminLayout';
import AppLayout from '../layouts/AppLayout';
import CounselorMobileDashboard from '../pages/counselor/CounselorMobileDashboard';
import UnitHeadDashboardV2 from '../pages/unit-head/UnitHeadDashboard';
import UnitHeadCamperDashboardPage from '../pages/unit-head/UnitHeadCamperDashboardPage';
import UnitHeadSelfReflectionPage from '../pages/unit-head/UnitHeadSelfReflectionPage';
import UnitHeadSelfReflectionHistoryPage from '../pages/unit-head/UnitHeadSelfReflectionHistoryPage';
import CamperCareDashboardV2 from '../pages/camper-care/Dashboard';
import CamperCareCamperDashboardPage from '../pages/camper-care/CamperDashboardPage';
import CamperCareFlagsPage from '../pages/camper-care/Flags';
import CamperCareOrdersPage from '../pages/camper-care/Orders';
import CamperCareSelfReflectionPage from '../pages/camper-care/SelfReflectionPage';
import CamperCareSelfReflectionHistoryPage from '../pages/camper-care/SelfReflectionHistoryPage';
import KitchenStaffDashboard from '../pages/kitchen-staff/Dashboard';
import KitchenStaffReflectionForm from '../pages/kitchen-staff/ReflectionForm';
import KitchenStaffHistory from '../pages/kitchen-staff/History';
import MadrichDashboard from '../pages/madrich/Dashboard';
import MadrichReflectionForm from '../pages/madrich/ReflectionForm';
import MadrichHistory from '../pages/madrich/History';
import LeadershipTeamDashboard from '../pages/leadership-team/Dashboard';
import LeadershipTeamTeamDashboard from '../pages/leadership-team/TeamDashboard';
import LeadershipTeamMemberReflection from '../pages/leadership-team/MemberReflection';
import LeadershipTeamSelfReflectionPage from '../pages/leadership-team/SelfReflectionPage';
import LeadershipTeamTemplateLibrary from '../pages/leadership-team/TemplateLibrary';
import LeadershipTeamTemplateBuilderPage from '../pages/leadership-team/TemplateBuilder/TemplateBuilderPage';
import LeadershipTeamResponses from '../pages/leadership-team/Responses';
import HelpIndexPage from '../pages/help/HelpIndexPage';
import HelpArticlePage from '../pages/help/HelpArticlePage';
import HelpRoute from '../pages/help/HelpRoute';
import SpecialistDashboard from '../pages/specialist/Dashboard';
import SpecialistCamperView from '../pages/specialist/CamperView';
import SpecialistSelfReflectionPage from '../pages/specialist/SelfReflectionPage';
import MaintenanceQueue from '../pages/maintenance/Queue';
import MaintenanceTicketDetail from '../pages/maintenance/TicketDetail';
import CamperReflectionListPage from '../pages/counselor/CamperReflectionListPage';
import CamperReflectionFormPage from '../pages/counselor/CamperReflectionFormPage';
import CounselorSelfReflectionPage from '../pages/counselor/CounselorSelfReflectionPage';
import CounselorSelfReflectionHistoryPage from '../pages/counselor/CounselorSelfReflectionHistoryPage';
import CounselorCamperCareRequestDetailPage from '../pages/counselor/CounselorCamperCareRequestDetailPage';
import CamperCareRequestFormPage from '../pages/counselor/CamperCareRequestFormPage';
import MaintenanceTicketFormPage from '../pages/counselor/MaintenanceTicketFormPage';
import {
  AdminRoute,
  DashboardsIndex,
  HomeRedirect,
  LegacyAdminTemplateEditRedirect,
  LegacyBunkDashboardRedirect,
  LegacyLtTemplatesRedirect,
  LeadershipTemplatesRoute,
  ProtectedRoute,
  SubjectProfileRedirect,
} from './guards';

const protect = (node) => <ProtectedRoute>{node}</ProtectedRoute>;
const admin = (node) => <AdminRoute>{node}</AdminRoute>;
const ltTemplates = (node) => <LeadershipTemplatesRoute>{node}</LeadershipTemplatesRoute>;

export const routeConfig = [
  { path: '/signin', element: <Signin /> },
  { path: '/signup', element: <Signup /> },
  { path: '/reset-password', element: <ResetPassword /> },
  { path: '/accounts/password/reset/key/:key', element: <ResetPasswordConfirm /> },
  { path: '/auth/callback', element: <AuthCallback /> },
  { path: '/callback', element: <CallbackPage /> },
  { path: '/account/provider/callback', element: <CallbackPage /> },
  { path: '/auth/success', element: <AuthSuccess /> },

  { path: '/dashboard', element: protect(<Dashboard />) },
  { path: '/admin-dashboard', element: protect(<AdminDashboard />) },
  { path: '/admin-dashboard/:date', element: protect(<AdminDashboard />) },
  { path: '/admin-bunk-logs', element: protect(<AdminBunkLogs />) },
  { path: '/admin-bunk-logs/:date', element: protect(<AdminBunkLogs />) },
  { path: '/dashboard/unithead', element: protect(<UnitHeadDashboard />) },
  { path: '/unithead/:id/:date', element: protect(<UnitHeadDashboard />) },
  { path: '/dashboard/campercare', element: protect(<CamperCareDashboard />) },
  { path: '/counselor-dashboard', element: protect(<CounselorDashboard />) },
  { path: '/counselor-dashboard/:date', element: protect(<CounselorDashboard />) },
  { path: '/campercare/:id/:date', element: protect(<CamperCareDashboard />) },
  { path: '/bunk/:bunk_id/:date', element: protect(<BunkDashboard />) },
  { path: '/bunk/:bunk_id/:date/orders/:orderId', element: protect(<BunkDashboard />) },
  { path: '/bunk/:bunk_id/:date/orders/:orderId/edit', element: protect(<BunkDashboard />) },
  { path: '/camper/:camper_id/:date', element: protect(<CamperDashboard />) },
  { path: '/orders', element: protect(<Orders />) },
  { path: '/orders/:orderId', element: protect(<OrderDetail />) },
  { path: '/orders/:orderId/edit', element: protect(<OrderEdit />) },
  { path: '/admin-staff/:staffId', element: protect(<StaffMemberHistory />) },
  { path: '/test-datepicker', element: <DatePickerTest /> },
  { path: '/migration-dashboard', element: protect(<MigrationDashboard />) },

  {
    element: protect(<AppLayout />),
    children: [
      { path: '/reflect', element: <ReflectionFormPage /> },
      { path: '/reflect/summary', element: <ReflectionSummaryPage /> },
      { path: '/tasks', element: <TasksPage /> },
      {
        path: '/help',
        element: (
          <HelpRoute>
            <HelpIndexPage />
          </HelpRoute>
        ),
      },
      {
        path: '/help/:slug',
        element: (
          <HelpRoute>
            <HelpArticlePage />
          </HelpRoute>
        ),
      },
      { path: '/notes', element: <Navigate to="/observations" replace /> },
      { path: '/notes/*', element: <Navigate to="/observations" replace /> },
      { path: '/subject-notes', element: <Navigate to="/observations" replace /> },
      { path: '/observations', element: <ObservationsInbox /> },
      { path: '/observations/:observationId', element: <ObservationThread /> },
      { path: '/groups/performance', element: <PerformanceDashboardPage /> },
      { path: '/supervisor/coverage', element: <Navigate to="/groups/performance" replace /> },
      { path: '/counselor', element: <CounselorMobileDashboard /> },
      { path: '/counselor/camper-reflections', element: <CamperReflectionListPage /> },
      { path: '/counselor/camper-reflections/:date', element: <CamperReflectionListPage /> },
      { path: '/counselor/camper-reflections/new', element: <CamperReflectionFormPage /> },
      { path: '/counselor/camper-reflections/:reflectionId/edit', element: <CamperReflectionFormPage /> },
      { path: '/counselor/self-reflection', element: <CounselorSelfReflectionPage /> },
      { path: '/counselor/self-reflection/history', element: <CounselorSelfReflectionHistoryPage /> },
      { path: '/counselor/self-reflection/:reflectionId/edit', element: <CounselorSelfReflectionPage /> },
      { path: '/counselor/requests', element: <Navigate to="/counselor" replace /> },
      { path: '/counselor/requests/camper-care/new', element: <CamperCareRequestFormPage /> },
      { path: '/counselor/requests/camper-care/:orderId/edit', element: <CamperCareRequestFormPage /> },
      { path: '/counselor/requests/camper-care/:orderId', element: <CounselorCamperCareRequestDetailPage /> },
      { path: '/counselor/requests/maintenance/:ticketId', element: <MaintenanceTicketDetail /> },
      { path: '/counselor/requests/maintenance/new', element: <MaintenanceTicketFormPage /> },
      { path: '/unit-head', element: <UnitHeadDashboardV2 /> },
      { path: '/unit-head/bunks/:bunkId', element: <LegacyBunkDashboardRedirect /> },
      { path: '/unit-head/campers/:camperId', element: <UnitHeadCamperDashboardPage /> },
      { path: '/unit-head/self-reflection', element: <UnitHeadSelfReflectionPage /> },
      { path: '/unit-head/self-reflection/history', element: <UnitHeadSelfReflectionHistoryPage /> },
      { path: '/unit-head/self-reflection/:reflectionId/edit', element: <UnitHeadSelfReflectionPage /> },
      { path: '/camper-care', element: <CamperCareDashboardV2 /> },
      { path: '/camper-care/bunks/:bunkId', element: <LegacyBunkDashboardRedirect /> },
      { path: '/camper-care/campers/:camperId', element: <CamperCareCamperDashboardPage /> },
      { path: '/camper-care/flags', element: <CamperCareFlagsPage /> },
      { path: '/camper-care/orders', element: <CamperCareOrdersPage /> },
      { path: '/camper-care/notes/*', element: <Navigate to="/camper-care" replace /> },
      { path: '/camper-care/self-reflection', element: <CamperCareSelfReflectionPage /> },
      { path: '/camper-care/self-reflection/history', element: <CamperCareSelfReflectionHistoryPage /> },
      { path: '/camper-care/self-reflection/:reflectionId/edit', element: <CamperCareSelfReflectionPage /> },
      { path: '/maintenance', element: <MaintenanceQueue /> },
      { path: '/maintenance/tickets/:ticketId', element: <MaintenanceTicketDetail /> },
      { path: '/specialist', element: <SpecialistDashboard /> },
      { path: '/specialist/notes/*', element: <Navigate to="/specialist/campers" replace /> },
      { path: '/specialist/campers/:camperId', element: <SpecialistCamperView /> },
      { path: '/specialist/self-reflection/new', element: <SpecialistSelfReflectionPage /> },
      { path: '/specialist/self-reflection/:reflectionId/edit', element: <SpecialistSelfReflectionPage /> },
      { path: '/kitchen-staff', element: <KitchenStaffDashboard /> },
      { path: '/kitchen-staff/history', element: <KitchenStaffHistory /> },
      { path: '/kitchen-staff/reflection/new', element: <KitchenStaffReflectionForm /> },
      { path: '/kitchen-staff/reflection/:reflectionId/edit', element: <KitchenStaffReflectionForm /> },
      { path: '/madrich', element: <MadrichDashboard /> },
      { path: '/madrich/history', element: <MadrichHistory /> },
      { path: '/madrich/reflection/new', element: <MadrichReflectionForm /> },
      { path: '/madrich/reflection/:reflectionId/edit', element: <MadrichReflectionForm /> },
      { path: '/leadership-team', element: <LeadershipTeamDashboard /> },
      { path: '/leadership-team/teams/:teamRole', element: <LeadershipTeamTeamDashboard /> },
      { path: '/leadership-team/teams/:teamRole/members/:membershipId', element: <LeadershipTeamMemberReflection /> },
      { path: '/leadership-team/self-reflection', element: <LeadershipTeamSelfReflectionPage /> },
      { path: '/leadership-team/self-reflection/:reflectionId/edit', element: <LeadershipTeamSelfReflectionPage /> },
      { path: '/leadership-team/templates/*', element: <LegacyLtTemplatesRedirect /> },
      { path: '/dashboards/subject-trends/:groupId', element: <SubjectTrendsPage /> },
      { path: '/dashboards/group/:groupId', element: <GroupDashboardPage /> },
      { path: '/dashboards/bunk/:bunkId', element: <LegacyBunkDashboardRedirect /> },
    ],
  },

  { path: '/my-reflections', element: protect(<MyReflectionsPage />) },
  { path: '/reflections/:id', element: protect(<ReflectionDetailPage />) },
  { path: '/team/dashboard', element: <Navigate to="/dashboards/logs" replace /> },
  { path: '/wellness/dashboard', element: <Navigate to="/dashboards/wellness" replace /> },
  { path: '/dashboards', element: protect(<DashboardsIndex />) },
  { path: '/dashboards/coverage', element: protect(<CoverageDashboardPage />) },
  { path: '/profile/:personId', element: protect(<SubjectDetailPage />) },
  { path: '/dashboards/subject/:personId', element: <SubjectProfileRedirect /> },
  { path: '/dashboards/authors', element: protect(<AuthorAttributionPage />) },
  { path: '/dashboards/concerns', element: protect(<ConcernsInboxPage />) },
  { path: '/dashboards/team', element: <Navigate to="/dashboards/logs" replace /> },
  { path: '/dashboards/logs', element: protect(<LogsDashboardPage />) },
  { path: '/dashboards/reflections', element: protect(<ReflectionsDashboardPage />) },
  { path: '/dashboards/wellness', element: protect(<WellnessDashboardPage />) },

  {
    path: '/admin',
    element: protect(<AdminLayout />),
    children: [
      { index: true, element: <Navigate to="/admin/home" replace /> },
      { path: 'home', element: admin(<AdminHome />) },
      { path: 'hub', element: admin(<AdminHub />) },
      { path: 'dashboard', element: admin(<AdminDashboardV2 />) },
      { path: 'memberships', element: <MembershipManagementPage /> },
      { path: 'people', element: admin(<AdminPeople />) },
      { path: 'assignments', element: admin(<AdminAssignments />) },
      { path: 'settings', element: admin(<AdminSettingsPage />) },
      { path: 'templates', element: ltTemplates(<LeadershipTeamTemplateLibrary />) },
      { path: 'templates/library', element: <Navigate to="/admin/templates" replace /> },
      { path: 'templates/new', element: ltTemplates(<LeadershipTeamTemplateBuilderPage />) },
      { path: 'templates/:id/responses', element: ltTemplates(<LeadershipTeamResponses />) },
      { path: 'templates/:id', element: ltTemplates(<LeadershipTeamTemplateBuilderPage />) },
      { path: 'groups', element: admin(<GroupListPage />) },
      { path: 'groups/:id', element: admin(<GroupDetailPage />) },
      { path: 'field-keys', element: admin(<FieldKeyListPage />) },
    ],
  },

  { path: '/admin/templates/:id/edit', element: <LegacyAdminTemplateEditRedirect /> },
  { path: '/', element: <HomeRedirect /> },
  { path: '*', element: <HomeRedirect /> },
];
