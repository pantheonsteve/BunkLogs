import { useAuth } from '../../../auth/AuthContext';
import { adminReportLinks } from '../../../partials/adminNavConfig';
import { orgSurfaces } from '../../../utils/auth/orgProfile';
import HubPage from '../HubPage';

/**
 * Which reports exist depends on the tenant: a religious school gets the
 * madrich reflection reports, a camp gets request planning.
 */
export default function ReportsHub() {
  const { user } = useAuth();
  const links = adminReportLinks(orgSurfaces(user));

  return (
    <HubPage
      title="Reports"
      subtitle="Where the answers end up: completion, trends and staffing across the whole organization."
      links={links}
      emptyTitle="No reports for this organization yet."
      emptyBody="Reports appear once your organization is using a surface that produces them."
      testId="admin-reports-hub"
    />
  );
}
