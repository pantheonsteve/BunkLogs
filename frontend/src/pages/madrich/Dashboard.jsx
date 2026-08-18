/**
 * Madrich (TBE) dashboard — Step 7_14, Stories 61 and 63.
 *
 * Three top-level sections (Story 61 criterion 3):
 *   1. Header — name, role label "Madrich", grade level, active program.
 *   2. My reflections — one card per template the Madrich currently owes
 *      (Story 63), each framed by its own cadence: "Week of [start]-[end]"
 *      for the recurring weekly 3-2-1, "Available to submit" for on-demand
 *      forms. An empty list is the nothing-assigned-yet state.
 *   3. History shortcut.
 *
 * No bunk lists, faculty submissions, peer-Madrich data, or camp-side
 * operational signal per Story 61 criterion 4. Per TBE Tier 1 scope:
 * English only, no LanguagePicker.
 */

import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { fetchDashboard, fetchTrends } from '../../api/madrich';
import { fetchAvailability } from '../../api/madrichAvailability';
import { fetchClassrooms } from '../../api/madrichChallenges';
import { useAuth } from '../../auth/AuthContext';
import RatingTrendChart from '../../components/charts/RatingTrendChart';
import CardSkeleton from '../../components/ui/CardSkeleton';
import HomeCard from '../../components/ui/HomeCard';
import UnreadDot from '../../components/ui/UnreadDot';
import { statusMeta } from '../../utils/availabilityStatus';

function formatPeriodLabel(cadence, periodStart, periodEnd) {
  if (cadence === 'on_demand') return 'Available to submit';
  if (!periodStart || !periodEnd) return '';
  const start = new Date(`${periodStart}T00:00:00`);
  const end = new Date(`${periodEnd}T00:00:00`);
  if (cadence === 'daily') {
    return start.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
  }
  if (cadence === 'monthly') {
    return start.toLocaleDateString(undefined, { month: 'long', year: 'numeric' });
  }
  const sameMonth = start.getMonth() === end.getMonth();
  const startLabel = start.toLocaleDateString(undefined, {
    month: 'short',
    day: 'numeric',
  });
  const endLabel = sameMonth
    ? end.toLocaleDateString(undefined, { day: 'numeric' })
    : end.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
  const range = `${startLabel}–${endLabel}`;
  return cadence === 'weekly' ? `Week of ${range}` : range;
}

const STRIP_SESSIONS = 4;

/**
 * The next few Sundays as coloured status pills (§4.1). Read from the
 * availability endpoint rather than the dashboard payload, which only carries
 * the next session and an unset count.
 */
function AvailabilityStrip() {
  const { orgSlug } = useAuth();
  const [sessions, setSessions] = useState(null);

  useEffect(() => {
    let active = true;
    fetchAvailability(orgSlug)
      .then((data) => {
        if (active) setSessions((data?.sessions || []).slice(0, STRIP_SESSIONS));
      })
      .catch(() => { if (active) setSessions([]); });
    return () => { active = false; };
  }, [orgSlug]);

  if (!sessions || sessions.length === 0) return null;

  return (
    <ul className="flex flex-wrap gap-2 mb-3" data-testid="md-availability-strip">
      {sessions.map((session) => {
        const status = session.commitment?.status || 'unset';
        const meta = statusMeta(status);
        return (
          <li key={session.session_date}>
            <span
              className={`inline-flex items-center gap-1.5 text-xs font-medium px-2 py-1 rounded-full ${meta.pill}`}
              data-testid={`md-availability-pill-${session.session_date}`}
            >
              {session.label}
              <span className="opacity-70">· {meta.label}</span>
            </span>
          </li>
        );
      })}
    </ul>
  );
}

function AvailabilityCard({ availability }) {
  const { upcoming_unset_count: unsetCount, next_session_date: nextDate, next_session_status: nextStatus } = availability || {};
  const hasUnset = (unsetCount ?? 0) > 0;
  const nextLabel = nextDate
    ? new Date(`${nextDate}T00:00:00`).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
    : null;
  const statusLabel = statusMeta(nextStatus || 'unset').label;

  return (
    <section
      aria-label="My availability"
      className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-4"
      data-testid="md-availability-card"
    >
      <h2 className="text-base font-semibold text-gray-900 dark:text-white mb-1">
        My availability
      </h2>
      <p className="text-sm text-gray-500 dark:text-gray-400 mb-3" data-testid="md-availability-subtitle">
        {hasUnset
          ? `${unsetCount} upcoming Sunday${unsetCount === 1 ? '' : 's'} not marked yet`
          : nextLabel
            ? `Next session (${nextLabel}): ${statusLabel}`
            : 'No upcoming sessions scheduled yet.'}
      </p>
      <AvailabilityStrip />
      <Link
        to={availability?.calendar_url || '/madrich/availability'}
        className="inline-block rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium px-4 py-2 transition-colors"
        data-testid="md-availability-cta"
      >
        Update availability
      </Link>
    </section>
  );
}

function ReportChallengeCard() {
  const { orgSlug } = useAuth();
  const [hasClassroom, setHasClassroom] = useState(false);

  useEffect(() => {
    let active = true;
    fetchClassrooms(orgSlug)
      .then((data) => {
        if (active) setHasClassroom((data?.classrooms || []).length > 0);
      })
      .catch(() => {
        if (active) setHasClassroom(false);
      });
    return () => { active = false; };
  }, [orgSlug]);

  if (!hasClassroom) return null;

  return (
    <section
      aria-label="Report a challenge"
      className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-4"
      data-testid="md-challenge-card"
    >
      <h2 className="text-base font-semibold text-gray-900 dark:text-white mb-1">
        Report a challenge
      </h2>
      <p className="text-sm text-gray-500 dark:text-gray-400 mb-3">
        Something need faculty attention in your classroom?
      </p>
      <Link
        to="/madrich/challenges/new"
        className="inline-block rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium px-4 py-2 transition-colors"
        data-testid="md-challenge-cta"
      >
        Report a challenge
      </Link>
    </section>
  );
}

function NoAssignmentsCard() {
  return (
    <section
      aria-label="My reflections"
      className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-4"
      data-testid="md-reflection-card"
    >
      <h2 className="text-base font-semibold text-gray-900 dark:text-white mb-1">
        My reflection
      </h2>
      <p className="text-sm text-gray-500 dark:text-gray-400">
        No reflections currently assigned. Your Director will set this up shortly.
      </p>
    </section>
  );
}

function ReflectionStatusCard({ card }) {
  const {
    template_id, template_name, cadence, state, reflection_id, editable,
  } = card;
  const isComplete = state === 'complete';
  const title = template_name || 'My reflection';
  const periodLabel = formatPeriodLabel(cadence, card.period?.start, card.period?.end);

  const actionPath = editable && reflection_id
    ? `/madrich/reflection/${reflection_id}/edit`
    : `/madrich/reflection/new?template=${template_id}`;

  const statusLabel = isComplete
    ? (cadence === 'weekly' ? 'Submitted for this week' : 'Submitted')
    : 'Not yet submitted';
  const statusClass = isComplete
    ? 'bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-300'
    : 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/40 dark:text-yellow-300';
  const ctaLabel = isComplete ? 'Edit reflection' : 'Start reflection';

  return (
    <section
      aria-label={title}
      className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-4"
      data-testid="md-reflection-card"
    >
      <div className="flex items-center justify-between gap-3 mb-1">
        <h2 className="text-base font-semibold text-gray-900 dark:text-white">
          {title}
        </h2>
        <span
          className={`shrink-0 text-xs font-medium px-2 py-0.5 rounded-full ${statusClass}`}
          data-testid="md-reflection-status"
        >
          {statusLabel}
        </span>
      </div>
      {periodLabel && (
        <p
          className="text-sm text-gray-500 dark:text-gray-400 mb-3"
          data-testid="md-week-label"
        >
          {periodLabel}
        </p>
      )}
      <Link
        to={actionPath}
        className="mt-2 inline-block rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium px-4 py-2 transition-colors"
        data-testid="md-reflection-cta"
      >
        {ctaLabel}
      </Link>
    </section>
  );
}

/**
 * One card per `thread_enabled` field, discovered from the template schema
 * (§4.3). Nothing here names a TBE field, so a Director adding a field to
 * the template gets a card without a frontend change.
 */
function ThreadedFieldCard({ card }) {
  const { field_key: fieldKey, label, total, unread_count: unreadCount, entries } = card;
  const rows = Array.isArray(entries) ? entries : [];

  return (
    <HomeCard
      title={label}
      subtitle={total === 0 ? 'Nothing here yet' : `${total} entr${total === 1 ? 'y' : 'ies'}`}
      badge={<UnreadDot count={unreadCount} label={`${unreadCount} unread`} />}
      action={total > 0 && (
        <Link
          to={`/madrich/entries/${encodeURIComponent(fieldKey)}`}
          className="text-sm text-indigo-600 dark:text-indigo-400 hover:underline"
          data-testid={`md-entries-link-${fieldKey}`}
        >
          View all →
        </Link>
      )}
      data-testid={`md-entry-card-${fieldKey}`}
    >
      {rows.length === 0 ? (
        <p className="text-sm text-gray-500 dark:text-gray-400">
          This fills in when you submit your next reflection.
        </p>
      ) : (
        <ul className="space-y-2">
          {rows.map((entry) => (
            <li key={entry.thread_id}>
              <Link
                to={`/madrich/threads/${entry.thread_id}`}
                className="block rounded-lg border border-gray-200 dark:border-gray-700 px-3 py-2 hover:border-indigo-300 dark:hover:border-indigo-700"
                data-testid={`md-entry-row-${entry.thread_id}`}
              >
                <div className="flex items-start justify-between gap-2">
                  <p className="text-sm text-gray-900 dark:text-white">{entry.excerpt}</p>
                  {entry.unread && <UnreadDot label="Unread reply" />}
                </div>
                <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-gray-500 dark:text-gray-400">
                  <span>{entry.date}</span>
                  {entry.message_count > 0 && (
                    <span>{entry.message_count} repl{entry.message_count === 1 ? 'y' : 'ies'}</span>
                  )}
                  {entry.awaiting_reply && (
                    <span
                      className="text-amber-700 dark:text-amber-400"
                      data-testid={`md-awaiting-${entry.thread_id}`}
                    >
                      Sent to your {entry.routes_to === 'director' ? 'Director' : 'faculty'} — no reply yet
                    </span>
                  )}
                  {entry.resolved_at && <span>Resolved</span>}
                </div>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </HomeCard>
  );
}

function TrendsCard() {
  const { orgSlug } = useAuth();
  const [series, setSeries] = useState(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let active = true;
    fetchTrends(orgSlug)
      .then((data) => { if (active) setSeries(data?.series || []); })
      .catch(() => { if (active) setFailed(true); });
    return () => { active = false; };
  }, [orgSlug]);

  if (failed) return null;
  if (series === null) return <CardSkeleton rows={4} data-testid="md-trends-loading" />;
  if (series.length === 0) return null;

  return (
    <HomeCard
      title="How I'm rating myself"
      subtitle="Each chart uses the full scale from your reflection form."
      data-testid="md-trends-card"
    >
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {series.map((s) => <RatingTrendChart key={s.trend_key} series={s} />)}
      </div>
    </HomeCard>
  );
}

function CohortCard({ cohort }) {
  if (!cohort?.enabled) return null;
  const unread = cohort.unread_count ?? 0;

  return (
    <HomeCard
      title="My cohort"
      subtitle={
        unread > 0
          ? `${unread} new post${unread === 1 ? '' : 's'} from your classmates`
          : 'Ideas your classmates chose to share'
      }
      badge={<UnreadDot count={unread} label={`${unread} unread cohort posts`} />}
      data-testid="md-cohort-card"
      footer={(
        <Link
          to={cohort.url || '/madrich/cohort'}
          className="inline-block rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium px-4 py-2 transition-colors"
          data-testid="md-cohort-cta"
        >
          Open cohort feed
        </Link>
      )}
    />
  );
}

export default function MadrichDashboard() {
  const { orgSlug } = useAuth();
  const [dashboard, setDashboard] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [nudgeDismissed, setNudgeDismissed] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await fetchDashboard(orgSlug);
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
      <div className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-[96rem] mx-auto" data-testid="md-loading">
        <p className="text-gray-500 dark:text-gray-400">Loading…</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-[96rem] mx-auto" data-testid="md-error">
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
    header, my_reflections, history_entry, availability,
    availability_nudge: availabilityNudge, entry_cards, cohort,
  } = dashboard;
  const cards = Array.isArray(my_reflections) ? my_reflections : [];
  const entryCards = Array.isArray(entry_cards) ? entry_cards : [];
  const gradeLevel = header?.grade_level;

  return (
    <div className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-[96rem] mx-auto space-y-4">
      <div>
        <p className="text-sm text-gray-500 dark:text-gray-400">{header.program_name}</p>
        <h1 className="text-xl font-bold text-gray-900 dark:text-white">{header.name}</h1>
        <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
          Madrich{typeof gradeLevel === 'number' ? ` · Grade ${gradeLevel}` : ''}
        </p>
      </div>

      {availabilityNudge && !nudgeDismissed && (
        <div
          className="rounded-xl border border-yellow-300 dark:border-yellow-700 bg-yellow-50 dark:bg-yellow-900/30 p-3 flex items-center justify-between gap-3"
          data-testid="md-availability-nudge"
        >
          <p className="text-sm text-yellow-800 dark:text-yellow-200">
            Please mark your availability for upcoming Sundays.
          </p>
          <button
            type="button"
            onClick={() => setNudgeDismissed(true)}
            className="text-sm text-yellow-800 dark:text-yellow-200 underline shrink-0"
            data-testid="md-availability-nudge-dismiss"
          >
            Dismiss
          </button>
        </div>
      )}

      {cards.length === 0 ? (
        <NoAssignmentsCard />
      ) : (
        cards.map(card => (
          <ReflectionStatusCard key={card.template_id} card={card} />
        ))
      )}

      {entryCards.map((card) => (
        <ThreadedFieldCard key={card.field_key} card={card} />
      ))}

      <TrendsCard />

      <CohortCard cohort={cohort} />

      <AvailabilityCard availability={availability} />

      <ReportChallengeCard />

      <section
        aria-label="My reflections"
        className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-4"
        data-testid="md-history-section"
      >
        <div className="flex items-center justify-between">
          <h2 className="text-base font-semibold text-gray-900 dark:text-white">
            My reflections
          </h2>
          <Link
            to={history_entry?.url ?? '/madrich/history'}
            className="text-sm text-indigo-600 dark:text-indigo-400 hover:underline"
            data-testid="md-history-link"
          >
            View history →
          </Link>
        </div>
      </section>
    </div>
  );
}
