/**
 * Faculty (TBE) home (2027 refresh, 8_5) — the school version of the Unit
 * Head home.
 *
 * Own tasks first, then three attention cards (questions routed to me, open
 * classroom challenges aged by session date, who is out next session), a
 * classroom card grid, and the selected classroom's roster. Nouns come from
 * org terminology. `reflections` is null when no weekly template is
 * assigned and `availability` is null off-season; both render as copy, not
 * a misleading zero.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { Flag, LogOut, MessageCircleQuestion } from 'lucide-react';
import { fetchFacultyDashboard, fetchFacultyRoster } from '../../api/faculty';
import { fetchFacultyChallenges } from '../../api/facultyChallenges';
import { useAuth } from '../../auth/AuthContext';
import { useTerm } from '../../context/OrgBrandingContext';
import AttentionCard from '../../components/ui/AttentionCard';
import Badge from '../../components/ui/Badge';
import Button from '../../components/ui/Button';
import Card from '../../components/ui/Card';
import HomeCard from '../../components/ui/HomeCard';
import UnreadDot from '../../components/ui/UnreadDot';
import GroupCard from '../../components/supervisor/GroupCard';
import SupervisorHeading from '../../components/supervisor/SupervisorHeading';
import ReflectionTasksPanel from '../../partials/tasks/ReflectionTasksPanel';
import { statusMeta } from '../../utils/availabilityStatus';

const AGING_AFTER_DAYS = 7;
const OVERDUE_AFTER_DAYS = 14;

function formatDate(iso) {
  if (!iso) return '';
  return new Date(`${iso}T00:00:00`).toLocaleDateString(undefined, {
    month: 'short',
    day: 'numeric',
  });
}

function titleCase(s) {
  return String(s || '').replace(/\b\w/g, (c) => c.toUpperCase());
}

const ESCALATION = {
  overdue: {
    label: 'Two weeks waiting',
    tone: 'danger',
    pill: 'bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-300',
  },
  aging: {
    label: 'A week waiting',
    tone: 'warn',
    pill: 'bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300',
  },
  fresh: {
    label: 'This week',
    tone: 'neutral',
    pill: 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300',
  },
};

function escalationForDate(sessionIso, todayIso) {
  if (!sessionIso || !todayIso) return 'fresh';
  const days = Math.round(
    (new Date(`${todayIso}T00:00:00`) - new Date(`${sessionIso}T00:00:00`)) / 86_400_000,
  );
  if (days >= OVERDUE_AFTER_DAYS) return 'overdue';
  if (days >= AGING_AFTER_DAYS) return 'aging';
  return 'fresh';
}

/**
 * A routed question is escalated by age, not recency (§5.1). The failure this
 * row exists to prevent is a question sitting unanswered for three weeks, so
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

function ClassroomDetail({ classroom, rows, roster, forwardRef }) {
  const term = useTerm();
  const subjectsTitle = titleCase(term('camper', { plural: true }));
  return (
    <Card
      as="section"
      ref={forwardRef}
      aria-labelledby="fac-detail"
      className="px-[22px] py-5 flex flex-col gap-3.5 scroll-mt-4"
      data-testid="fac-roster-card"
    >
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <div>
          <h2 id="fac-detail" className="text-base font-bold text-ink">
            {classroom.name} · {subjectsTitle}
          </h2>
          <p className="text-[13px] text-muted mt-0.5">
            {roster?.period
              ? `Week of ${roster.period.start} – ${roster.period.end}`
              : `${rows.length} in this ${term('bunk')}`}
            {classroom.reflections
              ? ` · ${classroom.reflections.submitted} of ${classroom.reflections.expected} reflections in`
              : ''}
          </p>
        </div>
        <Button
          as={Link}
          variant="secondary"
          size="sm"
          className="min-h-9 text-[13px]"
          to={classroom.url || `/dashboards/group/${classroom.id}`}
          data-testid={`fac-classroom-${classroom.id}-cta`}
        >
          Open full dashboard
        </Button>
      </div>
      {rows.length === 0 ? (
        <p className="text-[13px] text-muted">{`No ${term('camper', { plural: true })} on this roster yet.`}</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full min-w-[560px] text-sm">
            <thead>
              <tr className="text-left text-xs text-muted">
                <th scope="col" className="font-semibold py-1 pr-3">{titleCase(term('camper'))}</th>
                <th scope="col" className="font-semibold py-1 px-2">Reflection</th>
                <th scope="col" className="font-semibold py-1 px-2" data-testid="fac-roster-availability-header">
                  Availability
                  {roster?.next_session && (
                    <span className="block font-normal text-muted">{formatDate(roster.next_session)}</span>
                  )}
                </th>
                <th scope="col" className="font-semibold py-1 px-2">Challenges</th>
                <th scope="col" className="py-1 pl-2 w-16"><span className="sr-only">Open reflection</span></th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => {
                const meta = statusMeta(row.next_session_availability || 'unset');
                return (
                  <tr key={row.person_id} className="border-t border-line-soft align-middle">
                    <td className="py-2.5 pr-3">
                      <span className="inline-flex items-center gap-2">
                        <Link
                          to={`/faculty/roster/${row.person_id}`}
                          className="font-semibold text-ink hover:underline"
                          data-testid={`fac-roster-row-${row.person_id}`}
                        >
                          {row.display_name}
                          {typeof row.grade_level === 'number' && (
                            <span className="font-normal text-muted"> · Grade {row.grade_level}</span>
                          )}
                        </Link>
                        <UnreadDot count={row.unread_thread_count} label={`${row.unread_thread_count} unread`} />
                      </span>
                    </td>
                    <td className="py-2.5 px-2">
                      {row.reflection_state && (
                        <Badge
                          tone={row.reflection_state === 'complete' ? 'ok' : 'warn'}
                          data-testid={`fac-roster-state-${row.person_id}`}
                        >
                          {row.reflection_state === 'complete' ? 'Submitted' : 'Not yet'}
                        </Badge>
                      )}
                    </td>
                    <td className="py-2.5 px-2">
                      <Badge colors={meta.pill}>{meta.label}</Badge>
                    </td>
                    <td className="py-2.5 px-2">
                      {row.open_challenge_count > 0
                        ? <Badge tone="danger">{row.open_challenge_count} open</Badge>
                        : <span className="text-muted">—</span>}
                    </td>
                    <td className="py-2.5 pl-2">
                      {row.reflection_id && (
                        <Button
                          as={Link}
                          size="sm"
                          to={`/reflections/${row.reflection_id}?returnTo=${encodeURIComponent('/faculty')}`}
                          data-testid={`fac-roster-open-${row.person_id}`}
                          aria-label={`Open ${row.display_name}'s reflection`}
                        >
                          Open
                        </Button>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </Card>
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
    <Card as="section" aria-label={`My ${term('bunk', { plural: true })}`} className="p-5" data-testid="fac-no-classrooms">
      <h2 className="text-base font-bold text-ink mb-1">{`No ${term('bunk', { plural: true })} yet`}</h2>
      <p className="text-sm text-muted">
        {`You aren't assigned to a ${term('bunk')} yet. The ${term('director')} `
          + 'sets this up when the roster is imported.'}
      </p>
    </Card>
  );
}

export default function FacultyDashboard() {
  const { orgSlug } = useAuth();
  const term = useTerm();
  const [dashboard, setDashboard] = useState(null);
  const [roster, setRoster] = useState(null);
  const [challenges, setChallenges] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedId, setSelectedId] = useState(null);
  const detailRef = useRef(null);

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

  useEffect(() => {
    let active = true;
    fetchFacultyRoster(orgSlug)
      .then((data) => { if (active) setRoster(data); })
      .catch(() => { if (active) setRoster(null); });
    fetchFacultyChallenges(orgSlug, { status: 'open' })
      .then((data) => { if (active) setChallenges(data?.results || []); })
      .catch(() => { if (active) setChallenges([]); });
    return () => { active = false; };
  }, [orgSlug]);

  const rosterRows = useMemo(() => roster?.results || [], [roster]);

  if (loading) {
    return (
      <div className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-[1240px] mx-auto" data-testid="fac-loading">
        <p className="text-muted">Loading…</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-[1240px] mx-auto" data-testid="fac-error">
        <p className="text-danger-ink">{error}</p>
        <button onClick={load} className="mt-3 text-sm text-brand underline">
          Retry
        </button>
      </div>
    );
  }

  const {
    header, classrooms, challenges_url: challengesUrl,
    response_queue: queue, today,
  } = dashboard;
  const rooms = Array.isArray(classrooms) ? classrooms : [];
  const roomName = Object.fromEntries(rooms.map((r) => [r.id, r.name]));
  const subjectTotal = rooms.reduce((n, c) => n + (c.subject_count || 0), 0);
  const reflDone = rooms.reduce((n, c) => n + (c.reflections?.submitted || 0), 0);
  const reflTotal = rooms.reduce((n, c) => n + (c.reflections?.expected || 0), 0);
  const groupWord = (n) => term('bunk', { plural: n !== 1 });
  const subjectWord = (n) => term('camper', { plural: n !== 1 });

  const queueItems = queue?.items || [];
  const queueRows = queueItems.map((item) => {
    const tier = ESCALATION[item.escalation] || ESCALATION.fresh;
    return {
      id: item.id,
      name: item.subject_person?.display_name || 'Unknown',
      where: item.field_label,
      age: tier.label,
      ageTone: tier.tone,
      to: `/faculty/threads/${item.id}`,
    };
  });
  const challengeRows = challenges.map((c) => {
    const tier = ESCALATION[escalationForDate(c.session_date, today)];
    return {
      id: c.id,
      name: c.author?.display_name || c.author?.display || 'Unknown',
      where: c.category_label || c.assignment_group?.name,
      age: tier.label,
      ageTone: tier.tone,
      to: `/faculty/challenges/${c.id}`,
    };
  });
  const outRows = rosterRows
    .filter((r) => r.next_session_availability === 'unavailable')
    .map((r) => ({
      id: r.person_id,
      name: r.display_name,
      where: roomName[r.classroom_id],
      to: `/faculty/roster/${r.person_id}`,
    }));

  const selected = rooms.find((r) => r.id === selectedId) || rooms[0];
  const selectRoom = (id) => {
    setSelectedId(id);
    detailRef.current?.scrollIntoView?.({ behavior: 'smooth', block: 'start' });
  };

  return (
    <div className="px-4 sm:px-6 lg:px-8 pt-7 pb-12 w-full max-w-[1240px] flex flex-col gap-6">
      <SupervisorHeading
        eyebrow={[header?.role_label || 'Faculty', header?.name].filter(Boolean).join(' · ')}
        title={header?.program_name || `My ${term('bunk', { plural: true })}`}
        summary={`${rooms.length} ${groupWord(rooms.length)} · ${subjectTotal} ${subjectWord(subjectTotal)}`}
        progressLabel="Reflections this week"
        done={reflDone}
        total={reflTotal}
        progressTestId="fac-reflections-progress"
      />

      <ReflectionTasksPanel variant="embedded" testId="fac-tasks-card" />

      <div className="grid gap-4 grid-cols-[repeat(auto-fit,minmax(260px,1fr))]">
        <AttentionCard
          title="Help from you"
          icon={MessageCircleQuestion}
          tone="warn"
          count={queue?.total ?? queueRows.length}
          rows={queueRows}
          emptyText="No questions are waiting for a reply."
          action={(queue?.total ?? 0) > queueRows.length && (
            <Link
              to={queue?.url || '/faculty/queue'}
              className="text-[13px] font-semibold text-brand hover:text-brand-hover"
              data-testid="fac-queue-link"
            >
              View all →
            </Link>
          )}
          data-testid="fac-queue-card"
        />
        <AttentionCard
          title={`${titleCase(term('bunk'))} challenges`}
          icon={Flag}
          tone="danger"
          rows={challengeRows}
          emptyText="Nothing needs your attention right now."
          moreTo={challengesUrl || '/faculty/challenges'}
          data-testid="fac-challenges-section"
        />
        <AttentionCard
          title={roster?.next_session ? `Out ${formatDate(roster.next_session)}` : 'Out next session'}
          icon={LogOut}
          tone="neutral"
          rows={outRows}
          emptyText="No one has marked themselves out."
          data-testid="fac-out-card"
        />
      </div>

      {rooms.length === 0 ? (
        <NoClassroomsCard />
      ) : (
        <>
          <section aria-labelledby="fac-groups" className="flex flex-col gap-3">
            <h2 id="fac-groups" className="text-base font-bold text-ink">
              My {term('bunk', { plural: true })}
            </h2>
            <div className="grid gap-3 grid-cols-[repeat(auto-fill,minmax(200px,1fr))]">
              {rooms.map((room) => (
                <GroupCard
                  key={room.id}
                  testId={`fac-classroom-${room.id}`}
                  name={room.name}
                  staff={[
                    `${room.subject_count} ${subjectWord(room.subject_count)}`,
                    room.availability
                      ? `${room.availability.available} in ${formatDate(room.availability.date)}`
                      : null,
                  ].filter(Boolean).join(' · ')}
                  done={room.reflections?.submitted ?? 0}
                  total={room.reflections?.expected ?? 0}
                  noTotalText="No weekly form assigned yet"
                  flags={room.open_challenge_count || 0}
                  selected={selected?.id === room.id}
                  onSelect={() => selectRoom(room.id)}
                />
              ))}
            </div>
          </section>

          {selected && (
            <ClassroomDetail
              classroom={selected}
              rows={rosterRows.filter((r) => r.classroom_id === selected.id)}
              roster={roster}
              forwardRef={detailRef}
            />
          )}
        </>
      )}

      <UpcomingSessionsCard classrooms={rooms} />
    </div>
  );
}
