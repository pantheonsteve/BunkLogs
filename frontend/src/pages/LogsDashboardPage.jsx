import AssignmentTemplatesDashboard from '../dashboards/assignmentTemplates/AssignmentTemplatesDashboard';

/** Group-assigned template picker (Logs dashboard). */
export default function LogsDashboardPage() {
  return (
    <AssignmentTemplatesDashboard
      title="Bunk Logs"
      description="Browse forms assigned to groups, then open responses by audience, program, or group."
      scope="logs"
      testIdPrefix="logs"
      emptyLabel="bunk logs"
    />
  );
}
