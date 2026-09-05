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
import { fetchFacultyDashboard, fetchFacultyRoster } from '../../api/faculty';
import { useAuth } from '../../auth/AuthContext';
import { useTerm } from '../../context/OrgBrandingContext';
import CardSkeleton from '../../components/ui/CardSkeleton';
import HomeCard from '../../components/ui/HomeCard';
import UnreadDot from '../../components/ui/UnreadDot';
import { statusMeta } from '../../utils/availabilityStatus';

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

const ESCALATION = {
  overdue: {
    label: 'Two weeks waiting',
    pill: 'bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-300',
  },
  aging: {
    label: 'A week waiting',
    pill: 'bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300',
  },
  fresh: {
    label: 'This week',
    pill: 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300',
  },
};

/**
 * A routed question is escalated by age, not recency (§5.1). The failure this
 * card exists to prevent is a question sitting unanswered for three weeks, so
 * the oldest one is always on top and its age is stated in words.
 */
export function QueueRow({ item }) {
  const tier = ESCALATION[item.escalation] || ESCALATION.fresh;
  return (
    <li>
      <Link
        to={`/faculty/threads/${item.id}`}
        className="block rounded-lg border border-gray-200 dark:border-gray-700 px-3 py-2 hover:border-indigo-300 dark:hover:border-indigo-700"
        data-testid={`fac-queue-row-${item.id}`}
      >
        <div className="flex flex-wrap items-start justify-between gap-2">
          <p className="text-sm font-medium text-gray-900 dark:text-white">
            {item.subject_person?.display_name}
          </p>
          <div className="flex items-center gap-2 shrink-0">
            {item.unread && <UnreadDot label="Unread" />}
            <span
              className={`text-xs font-medium px-2 py-0.5 rounded-full ${tier.pill}`}
              data-testid={`fac-queue-escalation-${item.id}`}
            >
              {tier.label}
            </span>
          </div>
        </div>
        <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">{item.field_label}</p>
        <p className="mt-1 text-sm text-gray-700 dark:text-gray-300">{item.excerpt}</p>
      </Link>
    </li>
  );
}

function ResponseQueueCard({ queue }) {
  const items = queue?.items || [];
  const total = queue?.total ?? 0;
  const overdue = queue?.overdue_count ?? 0;

  return (
    <HomeCard
      title="Waiting on you"
      subtitle={
        total === 0
          ? 'No questions are waiting for a reply.'
          : `${total} question${total === 1 ? '' : 's'} routed to you, oldest first`
      }
      badge={overdue > 0 && (
        <span
          className="text-xs font-medium px-2 py-0.5 rounded-full bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-300"
          data-testid="fac-queue-overdue"
        >
          {overdue} overdue
        </span>
      )}
      action={total > items.length && (
        <Link
          to={queue?.url || '/faculty/queue'}
          className="text-sm text-indigo-600 dark:text-indigo-400 hover:underline"
          data-testid="fac-queue-link"
        >
          View all →
        </Link>
      )}
      data-testid="fac-queue-card"
    >
      {items.length > 0 && (
        <ul className="space-y-2" data-testid="fac-queue-list">
          {items.map((item) => <QueueRow key={item.id} item={item} />)}
        </ul>
      )}
    </HomeCard>
  );
}

function RosterCard() {
  const { orgSlug } = useAuth();
  const [roster, setRoster] = useState(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let active = true;
    fetchFacultyRoster(orgSlug)
      .then((data) => { if (active) setRoster(data); })
      .catch(() => { if (active) setFailed(true); });
    return () => { active = false; };
  }, [orgSlug]);

  if (failed) return null;
  if (!roster) return <CardSkeleton rows={4} data-testid="fac-roster-loading" />;

  const rows = roster.results || [];
  if (rows.length === 0) return null;

  return (
    <HomeCard
      title="My Madrichim"
      subtitle={
        roster.period
          ? `Week of ${roster.period.start} – ${roster.period.end}`
          : `${rows.length} in your classrooms`
      }
      data-testid="fac-roster-card"
    >
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-xs uppercase tracking-wide text-gray-500 dark:text-gray-400">
            <th className="font-normal pb-2 pr-3">Madrich</th>
            <th className="font-normal pb-2 px-2">Reflection</th>
            <th className="font-normal pb-2 px-2" data-testid="fac-roster-availability-header">
              Availability
              {roster.next_session && (
                <span className="block normal-case tracking-normal text-gray-400 dark:text-gray-500">
                  {formatDate(roster.next_session)}
                </span>
              )}
            </th>
            <th className="font-normal pb-2 pl-2 w-16">
              <span className="sr-only">Open reflection</span>
            </th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => {
            const meta = statusMeta(row.next_session_availability || 'unset');
            return (
              <tr
                key={row.person_id}
                className="align-middle border-t border-gray-200 dark:border-gray-600 odd:bg-gray-50 dark:odd:bg-gray-700/40"
              >
                <td className="py-3 pr-3 first:pl-2">
                  <span className="inline-flex items-center gap-2">
                    <Link
                      to={`/faculty/roster/${row.person_id}`}
                      className="text-sm text-gray-900 dark:text-white hover:underline"
                      data-testid={`fac-roster-row-${row.person_id}`}
                    >
                      {row.display_name}
                      {typeof row.grade_level === 'number' && (
                        <span className="text-gray-500 dark:text-gray-400"> · Grade {row.grade_level}</span>
                      )}
                    </Link>
                    <UnreadDot
                      count={row.unread_thread_count}
                      label={`${row.unread_thread_count} unread`}
                    />
                  </span>
                </td>
                <td className="py-3 px-2">
                  {row.reflection_state && (
                    <span
                      className={`text-xs font-medium px-2 py-0.5 rounded-full ${
                        row.reflection_state === 'complete'
                          ? 'bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-300'
                          : 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/40 dark:text-yellow-300'
                      }`}
                      data-testid={`fac-roster-state-${row.person_id}`}
                    >
                      {row.reflection_state === 'complete' ? 'Submitted' : 'Not yet'}
                    </span>
                  )}
                </td>
                <td className="py-3 px-2">
                  <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${meta.pill}`}>
                    {meta.label}
                  </span>
                </td>
                <td className="py-3 pl-2">
                  {row.reflection_id && (
                    <Link
                      to={`/reflections/${row.reflection_id}?returnTo=${encodeURIComponent('/faculty')}`}
                      className="inline-flex items-center rounded-md bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-medium px-2.5 py-1 transition-colors"
                      data-testid={`fac-roster-open-${row.person_id}`}
                      aria-label={`Open ${row.display_name}'s reflection`}
                    >
                      Open
                    </Link>
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </HomeCard>
  );
}

function UpcomingSessionsCard({ classrooms }) {
  const rooms = classrooms.filter((c) => (c.upcoming_sessions || []).length > 0);
  if (rooms.length === 0) return null;

  return (
    <HomeCard
      title="Upcoming Sundays"
      subtitle="Anyone who hasn't answered is counted separately from a no."
      data-testid="fac-upcoming-card"
    >
      <div className="space-y-3">
        {rooms.map((room) => (
          <div key={room.id}>
            <p className="text-sm font-medium text-gray-900 dark:text-white">{room.name}</p>
            <ul className="mt-1 flex flex-wrap gap-2">
              {room.upcoming_sessions.map((session) => {
                // An unanswered Sunday is the actionable state; a full house
                // needs no colour.
                const meta = statusMeta(session.unset > 0 ? 'unset' : 'available');
                return (
                  <li key={session.date}>
                    <span
                      className={`inline-flex items-center gap-1.5 text-xs font-medium px-2 py-1 rounded-full ${meta.pill}`}
                      data-testid={`fac-session-${room.id}-${session.date}`}
                    >
                      {formatDate(session.date)}
                      <span className="opacity-80">
                        {session.available} in
                        {session.unset > 0 && `, ${session.unset} unanswered`}
                      </span>
                    </span>
                  </li>
                );
              })}
            </ul>
          </div>
        ))}
      </div>
    </HomeCard>
  );
}

function NoClassroomsCard() {
  const term = useTerm();
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
        {`You aren't assigned to a classroom yet. The ${term('director')} `
          + 'sets this up when the roster is imported.'}
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
    } catch (err) {
      const detail = err?.response?.data?.detail;
      setError(typeof detail === 'string' ? detail : 'Could not load dashboard.');
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

  const {
    header, classrooms, challenges_url: challengesUrl,
    response_queue: responseQueue,
  } = dashboard;
  const rooms = Array.isArray(classrooms) ? classrooms : [];
  const totalOpen = rooms.reduce((n, c) => n + (c.open_challenge_count || 0), 0);

  return (
    <div className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-[96rem] mx-auto space-y-4">
      <div>
        <p className="text-sm text-gray-500 dark:text-gray-400">{header?.program_name}</p>
        <h1 className="text-xl font-bold text-gray-900 dark:text-white">{header?.name}</h1>
        <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">Faculty</p>
      </div>

      {responseQueue && <ResponseQueueCard queue={responseQueue} />}

      {rooms.length === 0 ? (
        <NoClassroomsCard />
      ) : (
        rooms.map((classroom) => (
          <ClassroomCard key={classroom.id} classroom={classroom} />
        ))
      )}

      <RosterCard />

      <UpcomingSessionsCard classrooms={rooms} />

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
