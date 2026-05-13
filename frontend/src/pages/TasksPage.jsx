import ReflectionTasksPanel from '../partials/tasks/ReflectionTasksPanel';

/** Standalone `/tasks` route — roster-aware reflections due today. */
export default function TasksPage() {
  return <ReflectionTasksPanel variant="page" />;
}
