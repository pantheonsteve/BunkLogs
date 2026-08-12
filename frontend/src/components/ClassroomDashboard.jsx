/**
 * Classroom dashboard.
 *
 * Roster + authors, plus an "Open challenges" section (Step 4_8, MA7)
 * that only appears for faculty viewers — the backend only populates
 * `data.challenges` on the faculty-author path, so a Madrich landing
 * here (if ever routed there) still sees the reflections-not-configured
 * stub. Classroom reflection templates aren't designed yet either, so
 * that stub remains otherwise.
 */

import { Link } from 'react-router-dom';

const STATUS_STYLES = {
  open: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/40 dark:text-yellow-300',
  acknowledged: 'bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-300',
  resolved: 'bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-300',
};

function StatusBadge({ status }) {
  const cls = STATUS_STYLES[status] || 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300';
  const label = status ? status.charAt(0).toUpperCase() + status.slice(1) : 'Unknown';
  return (
    <span className={`shrink-0 text-xs font-medium px-2 py-0.5 rounded-full ${cls}`}>
      {label}
    </span>
  );
}

function ChallengesSection({ challenges }) {
  const recent = challenges.recent || [];
  return (
    <section
      data-testid="classroom-challenges-section"
      className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 px-4 py-3 shadow-sm"
    >
      <div className="flex items-center justify-between gap-3 mb-2">
        <h2 className="text-base font-semibold text-gray-900 dark:text-white">
          Open challenges{' '}
          <span
            className="ml-2 text-xs text-gray-500 dark:text-gray-400"
            data-testid="classroom-challenges-open-count"
          >
            ({challenges.open_count ?? 0})
          </span>
        </h2>
        <Link
          to={challenges.list_url || '/faculty/challenges'}
          className="text-sm text-indigo-600 dark:text-indigo-400 hover:underline"
          data-testid="classroom-challenges-inbox-link"
        >
          View inbox →
        </Link>
      </div>
      {recent.length === 0 ? (
        <p className="text-sm text-gray-500 dark:text-gray-400">No challenges reported yet.</p>
      ) : (
        <ul className="space-y-2">
          {recent.map((c) => (
            <li
              key={c.id}
              className="flex items-center justify-between gap-3 rounded-lg border border-gray-100 dark:border-gray-800 px-3 py-2"
              data-testid={`classroom-challenge-${c.id}`}
            >
              <div className="min-w-0">
                <p className="text-sm text-gray-900 dark:text-white truncate">{c.body_preview}</p>
                <p className="text-xs text-gray-500 dark:text-gray-400">{c.category_label}</p>
              </div>
              <StatusBadge status={c.status} />
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

export default function ClassroomDashboard({
  data, selectedDate, onDateChange, backTo = '/dashboards',
}) {
  const group = data?.header?.group || {};
  const summary = data?.summary || {};
  const subjects = data?.subjects || [];
  const authors = data?.authors || [];
  const challenges = data?.challenges || null;

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

      {challenges ? (
        <ChallengesSection challenges={challenges} />
      ) : (
        <section
          data-testid="classroom-reflections-stub"
          className="rounded-xl border border-amber-200 dark:border-amber-900 bg-amber-50 dark:bg-amber-900/30 px-4 py-3 text-sm text-amber-900 dark:text-amber-100"
        >
          Reflections aren't configured for classrooms yet. Once classroom
          templates are defined we'll show completion + help-requested
          sections here.
        </section>
      )}

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
