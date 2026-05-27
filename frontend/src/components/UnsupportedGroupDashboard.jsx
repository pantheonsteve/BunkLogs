/**
 * Empty-state for group types we haven't built dashboards for yet.
 *
 * Used when the backend serves a 400 for an unsupported group_type
 * (caseload, cohort, specialty, custom) OR when the response shape
 * contains a group_type the frontend doesn't know how to render.
 */

import { Link } from 'react-router-dom';

export default function UnsupportedGroupDashboard({
  groupType, message, backTo = '/dashboards',
}) {
  return (
    <div
      data-testid="group-dashboard-unsupported"
      className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-3xl mx-auto space-y-4"
    >
      <Link
        to={backTo}
        className="text-sm text-blue-700 dark:text-blue-300 hover:underline"
      >
        ← Back
      </Link>
      <div
        role="alert"
        className="rounded-xl border border-amber-200 dark:border-amber-900 bg-amber-50 dark:bg-amber-900/30 px-4 py-3 text-sm text-amber-900 dark:text-amber-100"
      >
        <p className="font-semibold">Dashboard not yet available</p>
        <p className="mt-1">
          {message
            || `We don't have a dashboard for ${groupType ? `"${groupType}"` : 'this'} groups yet.`}
        </p>
      </div>
    </div>
  );
}
