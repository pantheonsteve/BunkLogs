/**
 * Classroom dashboard.
 *
 * Roster + authors for everyone, plus three faculty-only sections the
 * backend populates only on the faculty-author path: open challenges
 * (Step 4_8, MA7), weekly reflection completion, and Sunday
 * availability (Step 7_24). A Madrich landing here sees none of them —
 * peer completion state is off-limits per Story 61 criterion 4.
 *
 * `completion` and `availability` arrive as explicit nulls when the
 * program has no weekly template assigned / no upcoming sessions, which
 * is a different message than "you can't see this".
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

const AVAILABILITY_STYLES = {
  available: 'bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-300',
  unavailable: 'bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-300',
  tentative: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/40 dark:text-yellow-300',
};

function formatSession(iso) {
  if (!iso) return '';
  return new Date(`${iso}T00:00:00`).toLocaleDateString(undefined, {
    month: 'short',
    day: 'numeric',
  });
}

function Card({ title, count, testId, children }) {
  return (
    <section
      data-testid={testId}
      className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 px-4 py-3 shadow-sm"
    >
      <div className="flex items-center justify-between gap-3 mb-2">
        <h2 className="text-base font-semibold text-gray-900 dark:text-white">
          {title}
          {count && (
            <span className="ml-2 text-xs text-gray-500 dark:text-gray-400">{count}</span>
          )}
        </h2>
      </div>
      {children}
    </section>
  );
}

function CompletionSection({ completion, returnTo }) {
  if (!completion) {
    return (
      <Card title="Weekly reflections" testId="classroom-completion-section">
        <p className="text-sm text-gray-500 dark:text-gray-400">
          No weekly reflection form is assigned to this program yet.
        </p>
      </Card>
    );
  }
  const {
    students = [], submitted_count: submitted, expected_count: expected,
    template_name: templateName, period,
  } = completion;
  return (
    <Card
      title="Weekly reflections"
      count={`${submitted} of ${expected} submitted`}
      testId="classroom-completion-section"
    >
      <p className="text-xs text-gray-500 dark:text-gray-400 mb-2">
        {templateName}
        {period?.start && ` · week of ${formatSession(period.start)}`}
      </p>
      {students.length === 0 ? (
        <p className="text-sm text-gray-500 dark:text-gray-400">no students enrolled yet.</p>
      ) : (
        <ul className="grid grid-cols-1 sm:grid-cols-2 gap-1 text-sm">
          {students.map((s) => (
            <li
              key={s.person_id}
              data-testid={`classroom-completion-${s.person_id}`}
              className="flex items-center justify-between gap-2 px-2 py-1 rounded bg-gray-50 dark:bg-gray-800"
            >
              <span className="truncate text-gray-900 dark:text-white">{s.name}</span>
              <span className="flex items-center gap-2 shrink-0">
                <span
                  className={`text-xs font-medium px-2 py-0.5 rounded-full ${
                    s.state === 'complete'
                      ? 'bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-300'
                      : 'bg-gray-200 text-gray-700 dark:bg-gray-700 dark:text-gray-300'
                  }`}
                >
                  {s.state === 'complete' ? 'Submitted' : 'Missing'}
                </span>
                {s.reflection_id && (
                  <Link
                    to={
                      returnTo
                        ? `/reflections/${s.reflection_id}?returnTo=${encodeURIComponent(returnTo)}`
                        : `/reflections/${s.reflection_id}`
                    }
                    className="inline-flex items-center rounded-md bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-medium px-2.5 py-1 transition-colors"
                    data-testid={`classroom-completion-open-${s.person_id}`}
                    aria-label={`Open ${s.name}'s reflection`}
                  >
                    Open
                  </Link>
                )}
              </span>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}

function AvailabilitySection({ availability }) {
  if (!availability) {
    return (
      <Card title="Sunday availability" testId="classroom-availability-section">
        <p className="text-sm text-gray-500 dark:text-gray-400">
          No upcoming sessions are scheduled.
        </p>
      </Card>
    );
  }
  const { sessions = [], rows = [], unset_counts: unsetCounts = {} } = availability;
  const next = availability.next_session;
  return (
    <Card
      title="Sunday availability"
      count={next && `${next.available} available on ${formatSession(next.date)}`}
      testId="classroom-availability-section"
    >
      {rows.length === 0 ? (
        <p className="text-sm text-gray-500 dark:text-gray-400">no students enrolled yet.</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-xs text-gray-500 dark:text-gray-400 text-left">
                <th className="font-normal py-1 pr-3">Madrich</th>
                {sessions.map((s) => (
                  <th key={s} className="font-normal py-1 px-2 whitespace-nowrap">
                    {formatSession(s)}
                    {unsetCounts[s] > 0 && (
                      <span className="ml-1 text-gray-400">({unsetCounts[s]} unset)</span>
                    )}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr
                  key={row.person_id}
                  data-testid={`classroom-availability-${row.person_id}`}
                  className="border-t border-gray-100 dark:border-gray-800"
                >
                  <td className="py-1 pr-3 text-gray-900 dark:text-white whitespace-nowrap">
                    {row.display_name}
                  </td>
                  {row.cells.map((cell) => (
                    <td key={cell.session_date} className="py-1 px-2">
                      <span
                        className={`inline-block text-xs font-medium px-2 py-0.5 rounded-full ${
                          AVAILABILITY_STYLES[cell.status]
                          || 'bg-gray-100 text-gray-500 dark:bg-gray-800 dark:text-gray-400'
                        }`}
                      >
                        {cell.status
                          ? cell.status.charAt(0).toUpperCase() + cell.status.slice(1)
                          : 'Not set'}
                      </span>
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Card>
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
  // The faculty-only blocks arrive together, as explicit nulls when
  // unconfigured — so key presence, not truthiness, marks the viewer.
  const isFacultyView = data ? 'completion' in data : false;

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

      {isFacultyView ? (
        <>
          {challenges && <ChallengesSection challenges={challenges} />}
          <CompletionSection
            completion={data.completion}
            returnTo={group.id ? `/dashboards/group/${group.id}` : undefined}
          />
          <AvailabilitySection availability={data.availability} />
        </>
      ) : (
        <section
          data-testid="classroom-reflections-stub"
          className="rounded-xl border border-amber-200 dark:border-amber-900 bg-amber-50 dark:bg-amber-900/30 px-4 py-3 text-sm text-amber-900 dark:text-amber-100"
        >
          Reflection completion and Sunday availability are shown to this
          classroom&apos;s faculty.
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
