/**
 * Classroom dashboard (TBE stub).
 *
 * Roster + authors only. Classroom reflection templates aren't
 * designed yet, so this view explicitly tells the user that
 * reflections aren't configured. Replaces nothing in production
 * (TBE launches Fall 2026); ships now so faculty/madrich can verify
 * their assignments via the unified dashboard URL.
 */

import { Link } from 'react-router-dom';

export default function ClassroomDashboard({
  data, selectedDate, onDateChange, backTo = '/dashboards',
}) {
  const group = data?.header?.group || {};
  const summary = data?.summary || {};
  const subjects = data?.subjects || [];
  const authors = data?.authors || [];

  return (
    <div
      data-testid="group-dashboard-classroom"
      className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-[96rem] mx-auto space-y-4"
    >
      <header className="space-y-2">
        <Link
          to={backTo}
          className="text-sm text-blue-700 dark:text-blue-300 hover:underline"
        >
          ← Back
        </Link>
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <h1 className="text-2xl font-semibold text-gray-900 dark:text-white">
              {group.name || 'Classroom'}
            </h1>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              Classroom dashboard · {summary.subject_count || 0} students · {summary.author_count || 0} staff
            </p>
          </div>
          <label className="text-sm text-gray-700 dark:text-gray-200">
            Date{' '}
            <input
              type="date"
              value={selectedDate || ''}
              onChange={(e) => onDateChange?.(e.target.value)}
              className="ml-2 rounded border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 px-2 py-1"
            />
          </label>
        </div>
      </header>

      <section
        data-testid="classroom-reflections-stub"
        className="rounded-xl border border-amber-200 dark:border-amber-900 bg-amber-50 dark:bg-amber-900/30 px-4 py-3 text-sm text-amber-900 dark:text-amber-100"
      >
        Reflections aren't configured for classrooms yet. Once classroom
        templates are defined we'll show completion + help-requested
        sections here.
      </section>

      <section
        data-testid="section-subjects"
        className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 px-4 py-3 shadow-sm"
      >
        <h2 className="text-base font-semibold text-gray-900 dark:text-white mb-2">
          Students{' '}
          <span className="ml-2 text-xs text-gray-500 dark:text-gray-400">
            ({subjects.length})
          </span>
        </h2>
        {subjects.length === 0 ? (
          <p className="text-sm text-gray-500 dark:text-gray-400">no students enrolled yet.</p>
        ) : (
          <ul className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-1 text-sm">
            {subjects.map((s) => (
              <li
                key={s.id}
                data-testid={`classroom-subject-${s.id}`}
                className="px-2 py-1 rounded bg-gray-50 dark:bg-gray-800"
              >
                {s.preferred_name || s.first_name} {s.last_name}
              </li>
            ))}
          </ul>
        )}
      </section>

      <section
        data-testid="section-authors"
        className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 px-4 py-3 shadow-sm"
      >
        <h2 className="text-base font-semibold text-gray-900 dark:text-white mb-2">
          Faculty & Madrich{' '}
          <span className="ml-2 text-xs text-gray-500 dark:text-gray-400">
            ({authors.length})
          </span>
        </h2>
        {authors.length === 0 ? (
          <p className="text-sm text-gray-500 dark:text-gray-400">no staff assigned yet.</p>
        ) : (
          <ul className="text-sm space-y-1">
            {authors.map((a) => (
              <li key={a.id} data-testid={`classroom-author-${a.id}`}>
                {a.name}
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
