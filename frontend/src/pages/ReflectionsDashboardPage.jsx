import AssignmentTemplatesDashboard from '../dashboards/assignmentTemplates/AssignmentTemplatesDashboard';

/** Self-reflection template picker. */
export default function ReflectionsDashboardPage() {
  return (
    <AssignmentTemplatesDashboard
      title="Reflections"
      description="Browse self-reflection forms, then open responses by audience, program, or group."
      scope="reflections"
      testIdPrefix="reflections"
      emptyLabel="reflections"
    />
  );
}
