export default function AssignmentsEmptyPane({ leftLabel }) {
  return (
    <section
      className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900/40 p-3 min-h-[20rem] flex flex-col"
      data-testid="assignments-empty-pane"
    >
      <h2 className="text-sm font-semibold text-gray-900 dark:text-white">Assignments</h2>
      <p className="text-sm text-gray-500 dark:text-gray-400 mt-4">
        Select a {leftLabel.toLowerCase().replace(/s$/, '')} to view current assignments.
      </p>
    </section>
  );
}
