/**
 * Faculty (TBE) home — Step 7_24.
 *
 * One card per classroom this faculty member authors, each showing the
 * three signals they act on: weekly 3-2-1 completion, the next Sunday's
 * availability, and open challenges. Cards link to the classroom's full
 * dashboard at /dashboards/group/:id.
 *
 * `reflections` is null when the Director hasn't assigned a weekly
 * template yet, and `availability` is null off-season — both are
 * rendered as explanatory copy rather than a misleading zero.
 */

import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { fetchFacultyDashboard } from '../../api/faculty';
import { useAuth } from '../../auth/AuthContext';

function formatDate(iso) {
  if (!iso) return '';
  return new Date(`${iso}T00:00:00`).toLocaleDateString(undefined, {
    month: 'short',
    day: 'numeric',
  });
}

function Stat({ label, value, hint, testId }) {
  return (
    <div data-testid={testId}>
      <p className="text-xs uppercase tracking-wide text-gray-500 dark:text-gray-400">
        {label}
      </p>
      <p className="text-lg font-semibold text-gray-900 dark:text-white">{value}</p>
      {hint && (
        <p className="text-xs text-gray-500 dark:text-gray-400">{hint}</p>
      )}
    </div>
  );
}

function ClassroomCard({ classroom }) {
  const {
    id, name, url, subject_count: subjectCount,
    reflections, availability, open_challenge_count: openChallenges,
  } = classroom;

  return (
    <section
      aria-label={name}
      className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-4"
      data-testid={`fac-classroom-${id}`}
    >
      <div className="flex flex-wrap items-start justify-between gap-3 mb-3">
        <div>
          <h2 className="text-base font-semibold text-gray-900 dark:text-white">
            {name}
          </h2>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            {subjectCount} {subjectCount === 1 ? 'Madrich' : 'Madrichim'}
          </p>
        </div>
        {openChallenges > 0 && (
          <span
            className="shrink-0 text-xs font-medium px-2 py-0.5 rounded-full bg-yellow-100 text-yellow-800 dark:bg-yellow-900/40 dark:text-yellow-300"
            data-testid={`fac-classroom-${id}-challenges`}
          >
            {openChallenges} open {openChallenges === 1 ? 'challenge' : 'challenges'}
          </span>
        )}
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-3">
        {reflections ? (
          <Stat
            label="This week's reflections"
            value={`${reflections.submitted} of ${reflections.expected}`}
            hint={reflections.template_name}
            testId={`fac-classroom-${id}-reflections`}
          />
        ) : (
          <Stat
            label="This week's reflections"
            value="—"
            hint="No weekly form assigned yet"
            testId={`fac-classroom-${id}-reflections`}
          />
        )}
        {availability ? (
          <Stat
            label={`Next session (${formatDate(availability.date)})`}
            value={`${availability.available} available`}
            hint={
              availability.unset > 0
                ? `${availability.unset} haven't answered`
                : 'Everyone has answered'
            }
            testId={`fac-classroom-${id}-availability`}
          />
        ) : (
          <Stat
            label="Next session"
            value="—"
            hint="No upcoming sessions scheduled"
            testId={`fac-classroom-${id}-availability`}
          />
        )}
      </div>

      <Link
        to={url || `/dashboards/group/${id}`}
        className="inline-block rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium px-4 py-2 transition-colors"
        data-testid={`fac-classroom-${id}-cta`}
      >
        Open classroom
      </Link>
    </section>
  );
}

function NoClassroomsCard() {
  return (
    <section
      aria-label="My classrooms"
      className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-4"
      data-testid="fac-no-classrooms"
    >
      <h2 className="text-base font-semibold text-gray-900 dark:text-white mb-1">
        No classrooms yet
      </h2>
      <p className="text-sm text-gray-500 dark:text-gray-400">
        You aren&apos;t assigned to a classroom yet. Your Director sets this
        up when the roster is imported.
      </p>
    </section>
  );
}

export default function FacultyDashboard() {
  const { orgSlug } = useAuth();
  const [dashboard, setDashboard] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await fetchFacultyDashboard(orgSlug);
      setDashboard(data);
      setError(null);
    } catch {
      setError('Could not load dashboard.');
    } finally {
      setLoading(false);
    }
  }, [orgSlug]);

  useEffect(() => {
    load();
  }, [load]);

  if (loading) {
    return (
      <div className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-[96rem] mx-auto" data-testid="fac-loading">
        <p className="text-gray-500 dark:text-gray-400">Loading…</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-[96rem] mx-auto" data-testid="fac-error">
        <p className="text-red-600 dark:text-red-400">{error}</p>
        <button
          onClick={load}
          className="mt-3 text-sm text-indigo-600 dark:text-indigo-400 underline"
        >
          Retry
        </button>
      </div>
    );
  }

  const { header, classrooms, challenges_url: challengesUrl } = dashboard;
  const rooms = Array.isArray(classrooms) ? classrooms : [];
  const totalOpen = rooms.reduce((n, c) => n + (c.open_challenge_count || 0), 0);

  return (
    <div className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-[96rem] mx-auto space-y-4">
      <div>
        <p className="text-sm text-gray-500 dark:text-gray-400">{header?.program_name}</p>
        <h1 className="text-xl font-bold text-gray-900 dark:text-white">{header?.name}</h1>
        <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">Faculty</p>
      </div>

      {rooms.length === 0 ? (
        <NoClassroomsCard />
      ) : (
        rooms.map((classroom) => (
          <ClassroomCard key={classroom.id} classroom={classroom} />
        ))
      )}

      <section
        aria-label="Challenges"
        className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-4"
        data-testid="fac-challenges-section"
      >
        <div className="flex items-center justify-between gap-3">
          <div>
            <h2 className="text-base font-semibold text-gray-900 dark:text-white">
              Challenges
            </h2>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              {totalOpen > 0
                ? `${totalOpen} open across your classrooms`
                : 'Nothing needs your attention right now.'}
            </p>
          </div>
          <Link
            to={challengesUrl || '/faculty/challenges'}
            className="text-sm text-indigo-600 dark:text-indigo-400 hover:underline shrink-0"
            data-testid="fac-challenges-link"
          >
            View inbox →
          </Link>
        </div>
      </section>
    </div>
  );
}
