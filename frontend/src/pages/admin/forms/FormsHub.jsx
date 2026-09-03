import { adminFormLinks } from '../../../partials/adminNavConfig';
import HubPage from '../HubPage';

/** Everything that shapes what people are asked to fill in. */
export default function FormsHub() {
  return (
    <HubPage
      title="Forms"
      subtitle="The questions people answer, and the shared field names that let dashboards compare answers across forms."
      links={adminFormLinks()}
      testId="admin-forms-hub"
    />
  );
}
