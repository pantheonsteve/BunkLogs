import AssignmentTemplatesDashboard from '../dashboards/assignmentTemplates/AssignmentTemplatesDashboard';

/** Group-assigned template picker (Log Entries dashboard). */
export default function LogsDashboardPage() {
  return (
    <AssignmentTemplatesDashboard
      title="Log Entries"
      description="Browse forms assigned to groups, then open responses by audience, program, or group."
      scope="logs"
      testIdPrefix="logs"
      emptyLabel="log entries"
    />
  );
}
