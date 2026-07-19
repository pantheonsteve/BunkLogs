import { lazy } from 'react';
import { Navigate } from 'react-router-dom';

// Eager: lightweight route guards/redirects, shared layouts (mounted on
// nearly every authenticated route), and the unauthenticated entry page.
// Everything else is lazy-loaded per route below so a given role only
// downloads the code for the pages it actually visits.
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
import AdminLayout from '../layouts/AdminLayout';
import AppLayout from '../layouts/AppLayout';
import HelpRoute from '../pages/help/HelpRoute';
import Signin from '../pages/Signin';

// Lazy route pages (code-split). Each becomes its own chunk, loaded on demand
// behind the <Suspense> boundary in RootLayout (see ./guards.jsx).
const Signup = lazy(() => import('../pages/Signup'));
const Dashboard = lazy(() => import('../pages/Dashboard'));
const DatePickerTest = lazy(() => import('../pages/DatePickerTest'));
const AuthCallback = lazy(() => import('../pages/AuthCallback'));
const CallbackPage = lazy(() => import('../pages/CallbackPage'));
const ResetPassword = lazy(() => import('../pages/ResetPassword'));
const ResetPasswordConfirm = lazy(() => import('../pages/ResetPasswordConfirm'));
const AuthSuccess = lazy(() => import('../pages/AuthSuccess'));
const MigrationDashboard = lazy(() => import('../pages/MigrationDashboard'));
const MyReflectionsPage = lazy(() => import('../pages/MyReflectionsPage'));
const ReflectionDetailPage = lazy(() => import('../pages/ReflectionDetailPage'));
const ReflectionFormPage = lazy(() => import('../pages/ReflectionFormPage'));
const ReflectionSummaryPage = lazy(() => import('../pages/ReflectionSummaryPage'));
const ReflectionsDashboardPage = lazy(() => import('../pages/ReflectionsDashboardPage'));
const LogsDashboardPage = lazy(() => import('../pages/LogsDashboardPage'));
const WellnessDashboardPage = lazy(() => import('../pages/WellnessDashboardPage'));
const MembershipManagementPage = lazy(() => import('../pages/MembershipManagementPage'));
const AdminHub = lazy(() => import('../pages/admin/AdminHub'));
const AdminHome = lazy(() => import('../pages/admin/AdminHome'));
const AdminDashboardV2 = lazy(() => import('../pages/admin/Dashboard'));
const AdminPeople = lazy(() => import('../pages/admin/People'));
const AdminAssignments = lazy(() => import('../pages/admin/Assignments'));
const AdminSettingsPage = lazy(() => import('../pages/admin/Settings'));
const GroupListPage = lazy(() => import('../pages/admin/groups/GroupListPage'));
const GroupDetailPage = lazy(() => import('../pages/admin/groups/GroupDetailPage'));
const FieldKeyListPage = lazy(() => import('../pages/admin/field-keys/FieldKeyListPage'));
const CatalogManagePage = lazy(() => import('../pages/admin/catalog/CatalogManagePage'));
const CatalogPlanningDashboard = lazy(() => import('../pages/admin/catalog/PlanningDashboard'));
const TasksPage = lazy(() => import('../pages/TasksPage'));
const ObservationsInbox = lazy(() => import('../pages/observations/ObservationsInbox'));
const ObservationThread = lazy(() => import('../pages/observations/ObservationThread'));
const PerformanceDashboardPage = lazy(() => import('../pages/groups/PerformanceDashboardPage'));
const CoverageDashboardPage = lazy(() => import('../pages/dashboards/CoverageDashboardPage'));
const SubjectTrendsPage = lazy(() => import('../pages/dashboards/SubjectTrendsPage'));
const SubjectDetailPage = lazy(() => import('../pages/dashboards/SubjectDetailPage'));
const AuthorAttributionPage = lazy(() => import('../pages/dashboards/AuthorAttributionPage'));
const ConcernsInboxPage = lazy(() => import('../pages/dashboards/ConcernsInboxPage'));
const GroupDashboardPage = lazy(() => import('../pages/dashboards/GroupDashboardPage'));
const CounselorMobileDashboard = lazy(() => import('../pages/counselor/CounselorMobileDashboard'));
const UnitHeadDashboardV2 = lazy(() => import('../pages/unit-head/UnitHeadDashboard'));
const UnitHeadCamperDashboardPage = lazy(() => import('../pages/unit-head/UnitHeadCamperDashboardPage'));
const UnitHeadSelfReflectionPage = lazy(() => import('../pages/unit-head/UnitHeadSelfReflectionPage'));
const UnitHeadSelfReflectionHistoryPage = lazy(() => import('../pages/unit-head/UnitHeadSelfReflectionHistoryPage'));
const UnitHeadStaffReflectionsPage = lazy(() => import('../pages/unit-head/UnitHeadStaffReflectionsPage'));
const CamperCareDashboardV2 = lazy(() => import('../pages/camper-care/Dashboard'));
const CamperCareCamperDashboardPage = lazy(() => import('../pages/camper-care/CamperDashboardPage'));
const CamperCareFlagsPage = lazy(() => import('../pages/camper-care/Flags'));
const CamperCareOrdersPage = lazy(() => import('../pages/camper-care/Orders'));
const CamperCareOrderDetailPage = lazy(() => import('../pages/camper-care/OrderDetail'));
const CamperCareSelfReflectionPage = lazy(() => import('../pages/camper-care/SelfReflectionPage'));
const CamperCareSelfReflectionHistoryPage = lazy(() => import('../pages/camper-care/SelfReflectionHistoryPage'));
const KitchenStaffDashboard = lazy(() => import('../pages/kitchen-staff/Dashboard'));
const KitchenStaffReflectionForm = lazy(() => import('../pages/kitchen-staff/ReflectionForm'));
const KitchenStaffHistory = lazy(() => import('../pages/kitchen-staff/History'));
const MadrichDashboard = lazy(() => import('../pages/madrich/Dashboard'));
const MadrichReflectionForm = lazy(() => import('../pages/madrich/ReflectionForm'));
const MadrichHistory = lazy(() => import('../pages/madrich/History'));
const LeadershipTeamDashboard = lazy(() => import('../pages/leadership-team/Dashboard'));
const LeadershipTeamTeamDashboard = lazy(() => import('../pages/leadership-team/TeamDashboard'));
const LeadershipTeamMemberReflection = lazy(() => import('../pages/leadership-team/MemberReflection'));
const LeadershipTeamSelfReflectionPage = lazy(() => import('../pages/leadership-team/SelfReflectionPage'));
const LeadershipTeamTemplateLibrary = lazy(() => import('../pages/leadership-team/TemplateLibrary'));
const LeadershipTeamTemplateBuilderPage = lazy(() => import('../pages/leadership-team/TemplateBuilder/TemplateBuilderPage'));
const LeadershipTeamResponses = lazy(() => import('../pages/leadership-team/Responses'));
const HelpIndexPage = lazy(() => import('../pages/help/HelpIndexPage'));
const HelpArticlePage = lazy(() => import('../pages/help/HelpArticlePage'));
const SpecialistDashboard = lazy(() => import('../pages/specialist/Dashboard'));
const SpecialistCamperView = lazy(() => import('../pages/specialist/CamperView'));
const SpecialistSelfReflectionPage = lazy(() => import('../pages/specialist/SelfReflectionPage'));
const MaintenanceQueue = lazy(() => import('../pages/maintenance/Queue'));
const MaintenanceTicketDetail = lazy(() => import('../pages/maintenance/TicketDetail'));
const CamperReflectionListPage = lazy(() => import('../pages/counselor/CamperReflectionListPage'));
const CamperReflectionFormPage = lazy(() => import('../pages/counselor/CamperReflectionFormPage'));
const CounselorSelfReflectionPage = lazy(() => import('../pages/counselor/CounselorSelfReflectionPage'));
const CounselorSelfReflectionHistoryPage = lazy(() => import('../pages/counselor/CounselorSelfReflectionHistoryPage'));
const CounselorCamperCareRequestDetailPage = lazy(() => import('../pages/counselor/CounselorCamperCareRequestDetailPage'));
const CamperCareRequestFormPage = lazy(() => import('../pages/counselor/CamperCareRequestFormPage'));
const MaintenanceTicketFormPage = lazy(() => import('../pages/counselor/MaintenanceTicketFormPage'));

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
      { path: '/unit-head/staff-reflections', element: <UnitHeadStaffReflectionsPage /> },
      { path: '/camper-care', element: <CamperCareDashboardV2 /> },
      { path: '/camper-care/bunks/:bunkId', element: <LegacyBunkDashboardRedirect /> },
      { path: '/camper-care/campers/:camperId', element: <CamperCareCamperDashboardPage /> },
      { path: '/camper-care/flags', element: <CamperCareFlagsPage /> },
      { path: '/camper-care/orders', element: <CamperCareOrdersPage /> },
      { path: '/camper-care/orders/:orderId', element: <CamperCareOrderDetailPage /> },
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
      { path: 'catalog', element: admin(<CatalogManagePage />) },
      { path: 'catalog/planning', element: admin(<CatalogPlanningDashboard />) },
    ],
  },

  { path: '/admin/templates/:id/edit', element: <LegacyAdminTemplateEditRedirect /> },
  { path: '/', element: <HomeRedirect /> },
  { path: '*', element: <HomeRedirect /> },
];
