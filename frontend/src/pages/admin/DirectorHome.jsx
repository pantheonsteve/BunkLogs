/**
 * Director homepage cards — Step 4_9 §6.
 *
 * Rendered inside AdminHome for religious-school orgs only. "Director" is not
 * a role: it is the admin capability in a school org, and the same AdminHome
 * serves camp admins, so every card here sits behind
 * `orgSurfaces(user).gradeReflections`.
 *
 * Each card fetches independently. One slow or empty endpoint should degrade
 * to a skeleton or disappear, not blank the whole page.
 */
import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  CalendarDays,
  ChevronRight,
  Clock,
  MessageCircleQuestion,
  MessagesSquare,
  Tags,
  TrendingUp,
  Users,
} from 'lucide-react';
import {
  downloadMadrichimCsv,
  fetchDirectorCoverage,
  fetchDirectorFacultyActivity,
  fetchDirectorMadrichim,
  fetchDirectorPulse,
  fetchDirectorQueue,
  fetchDirectorThemes,
} from '../../api/director';
import CoverageDetailModal from '../../components/admin/CoverageDetailModal';
import CardSkeleton from '../../components/ui/CardSkeleton';
import HomeCard from '../../components/ui/HomeCard';
import UnreadDot from '../../components/ui/UnreadDot';
import { statusMeta } from '../../utils/availabilityStatus';

/** Fetch-once-on-mount helper. `null` means still loading, `false` means failed. */
function useCardData(fetcher) {
  const [data, setData] = useState(null);
  useEffect(() => {
    let active = true;
    fetcher()
      .then((result) => { if (active) setData(result); })
      .catch(() => { if (active) setData(false); });
    return () => { active = false; };
  }, [fetcher]);
  return data;
}

function formatDate(iso) {
  if (!iso) return '';
  const d = new Date(`${iso}T00:00:00`);
  return Number.isNaN(d.getTime())
    ? iso
    : d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
}

function percent(rate) {
  return rate === null || rate === undefined ? '—' : `${Math.round(rate * 100)}%`;
}

/**
 * Coverage cells are coloured by what the Director can act on, not by a
 * headcount target (none is configured). An unanswered Sunday is the most
 * actionable state, so it reads red even though nobody has said "no".
 */
function coverageTone(cell) {
  if (cell.unset > 0) return statusMeta('unavailable');
  if (cell.tentative > 0) return statusMeta('tentative');
  return statusMeta('available');
}

function PulseCard() {
  const pulse = useCardData(useCallback(fetchDirectorPulse, []));
  if (pulse === null) return <CardSkeleton rows={3} data-testid="dir-pulse-loading" />;
  if (pulse === false) return null;

  if (!pulse.available) {
    return (
      <HomeCard
        title="Reflection pulse"
        subtitle="No weekly reflection template is assigned yet."
        accent="indigo"
        icon={TrendingUp}
        data-testid="dir-pulse-card"
      />
    );
  }

  const current = pulse.current || {};
  const periods = pulse.periods || [];

  return (
    <HomeCard
      title="Reflection pulse"
      subtitle={`${pulse.active_madrichim} active Madrichim · ${pulse.template_name}`}
      accent="indigo"
      icon={TrendingUp}
      badge={pulse.open_question_count > 0 && (
        <UnreadDot
          count={pulse.open_question_count}
          label={`${pulse.open_question_count} questions for you`}
        />
      )}
      data-testid="dir-pulse-card"
    >
      <p className="text-3xl font-bold text-indigo-700 dark:text-indigo-300" data-testid="dir-pulse-rate">
        {percent(current.rate)}
        <span className="ml-2 text-sm font-normal text-gray-700 dark:text-gray-300">
          this week ({current.submitted} of {current.expected})
        </span>
      </p>
      <ul className="mt-3 flex items-end gap-1" data-testid="dir-pulse-sparkline">
        {periods.map((p) => (
          <li
            key={p.period_start}
            className="flex-1 bg-indigo-100 dark:bg-indigo-900/40 rounded-sm relative"
            style={{ height: '2.5rem' }}
            title={`Week of ${formatDate(p.period_start)}: ${percent(p.rate)}`}
          >
            <span
              className="absolute bottom-0 left-0 right-0 bg-indigo-600 dark:bg-indigo-400 rounded-sm"
              style={{ height: `${Math.round((p.rate || 0) * 100)}%` }}
            />
            <span className="sr-only">
              Week of {formatDate(p.period_start)}: {percent(p.rate)}
            </span>
          </li>
        ))}
      </ul>
    </HomeCard>
  );
}

function QuestionQueueCard() {
  const queue = useCardData(useCallback(() => fetchDirectorQueue({ pageSize: 5 }), []));
  if (queue === null) return <CardSkeleton rows={3} data-testid="dir-queue-loading" />;
  if (queue === false) return null;

  const items = queue.results || [];

  return (
    <HomeCard
      title="Questions for you"
      subtitle={
        items.length === 0
          ? 'Nothing routed to you is waiting.'
          : `${queue.count} routed to the Director, oldest first`
      }
      accent="amber"
      icon={MessageCircleQuestion}
      data-testid="dir-queue-card"
    >
      {items.length > 0 && (
        <ul className="space-y-2" data-testid="dir-queue-list">
          {items.map((item) => (
            <li key={item.id}>
              <Link
                to={`/admin/threads/${item.id}`}
                className="block rounded-lg border border-amber-200 dark:border-amber-900/50 bg-amber-50/60 dark:bg-amber-900/15 px-3 py-2 hover:border-amber-400 dark:hover:border-amber-600 hover:bg-amber-50 dark:hover:bg-amber-900/25 transition-colors"
                data-testid={`dir-queue-row-${item.id}`}
              >
                <div className="flex items-start justify-between gap-2">
                  <p className="text-sm font-semibold text-gray-900 dark:text-white">
                    {item.subject_person?.display_name}
                  </p>
                  {item.age_days !== null && item.age_days !== undefined && (
                    <span className="text-xs font-medium text-amber-800 dark:text-amber-300 shrink-0">
                      {item.age_days === 0 ? 'today' : `${item.age_days}d ago`}
                    </span>
                  )}
                </div>
                <p className="mt-1 text-sm text-gray-800 dark:text-gray-200">{item.excerpt}</p>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </HomeCard>
  );
}

function CoverageCard() {
  const coverage = useCardData(useCallback(fetchDirectorCoverage, []));
  // `{ sessionDate, classroomId }` for the open drill-down, or null.
  const [detail, setDetail] = useState(null);
  if (coverage === null) return <CardSkeleton rows={4} data-testid="dir-coverage-loading" />;
  if (coverage === false) return null;

  const sessions = coverage.sessions || [];
  const classrooms = coverage.classrooms || [];
  if (sessions.length === 0 || classrooms.length === 0) return null;

  return (
    <HomeCard
      title="Sunday coverage"
      subtitle="Pick a date to see who is in and who is out."
      accent="teal"
      icon={CalendarDays}
      data-testid="dir-coverage-card"
      className="lg:col-span-2"
    >
      <div className="overflow-x-auto">
        <table className="min-w-full text-sm">
          <caption className="sr-only">
            Availability by classroom for the next {sessions.length} Sundays
          </caption>
          <thead>
            <tr className="bg-gray-100 dark:bg-gray-700/60">
              <th
                scope="col"
                className="text-left text-xs font-semibold uppercase tracking-wide text-gray-700 dark:text-gray-200 py-2 pl-3 pr-3 rounded-l-lg"
              >
                Classroom
              </th>
              {sessions.map((session, i) => (
                <th
                  key={session}
                  scope="col"
                  className={`text-left text-xs font-semibold uppercase tracking-wide text-gray-700 dark:text-gray-200 py-2 px-2 whitespace-nowrap ${
                    i === sessions.length - 1 ? 'rounded-r-lg pr-3' : ''
                  }`}
                >
                  <button
                    type="button"
                    onClick={() => setDetail({ sessionDate: session, classroomId: null })}
                    className="uppercase tracking-wide hover:text-indigo-700 dark:hover:text-indigo-300 hover:underline"
                    data-testid={`dir-coverage-date-${session}`}
                  >
                    {formatDate(session)}
                  </button>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {classrooms.map((room) => (
              <tr
                key={room.id}
                className="border-t border-gray-200 dark:border-gray-700 even:bg-gray-50/70 dark:even:bg-gray-900/30"
              >
                <th
                  scope="row"
                  className="text-left font-semibold text-gray-900 dark:text-white py-2 pl-3 pr-3 whitespace-nowrap"
                >
                  {room.name}
                  <span className="font-normal text-gray-600 dark:text-gray-300"> ({room.roster_size})</span>
                </th>
                {room.cells.map((cell) => {
                  const meta = coverageTone(cell);
                  return (
                    <td key={cell.session_date} className="py-2 px-2">
                      <button
                        type="button"
                        onClick={() => setDetail({
                          sessionDate: cell.session_date, classroomId: room.id,
                        })}
                        title={`${room.name} on ${formatDate(cell.session_date)} — who is in and who is out`}
                        className={`inline-block text-xs font-semibold px-2 py-1 rounded-full ring-1 ring-inset ring-current/25 hover:ring-current/60 ${meta.pill}`}
                        data-testid={`dir-coverage-${room.id}-${cell.session_date}`}
                      >
                        {cell.available}/{cell.roster_size}
                        {cell.unset > 0 && ` · ${cell.unset} unanswered`}
                        {cell.tentative > 0 && ` · ${cell.tentative} tentative`}
                      </button>
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <ul className="mt-3 flex flex-wrap gap-2" data-testid="dir-coverage-legend">
        {[
          ['unavailable', 'Someone has not answered'],
          ['tentative', 'Someone is tentative'],
          ['available', 'Everyone is in'],
        ].map(([status, label]) => (
          <li
            key={status}
            className={`text-xs font-medium px-2 py-1 rounded-full ring-1 ring-inset ring-current/25 ${statusMeta(status).pill}`}
          >
            {label}
          </li>
        ))}
      </ul>
      {detail && (
        <CoverageDetailModal
          sessionDate={detail.sessionDate}
          classroomId={detail.classroomId}
          onClose={() => setDetail(null)}
          onClearClassroom={() => setDetail((d) => ({ ...d, classroomId: null }))}
        />
      )}
    </HomeCard>
  );
}

function FacultyActivityCard() {
  const activity = useCardData(useCallback(fetchDirectorFacultyActivity, []));
  if (activity === null) return <CardSkeleton rows={3} data-testid="dir-activity-loading" />;
  if (activity === false) return null;

  const rows = activity.results || [];
  if (rows.length === 0) return null;

  return (
    <HomeCard
      title="Faculty responsiveness"
      subtitle="Median time to a first reply. Blank means nothing answered yet."
      accent="sky"
      icon={Clock}
      data-testid="dir-activity-card"
    >
      <ul className="space-y-1.5">
        {rows.map((row) => (
          <li key={row.person_id}>
            <RosterRow
              to={
                row.membership_id
                  ? `/admin/reflections/faculty/members/${row.membership_id}`
                  : null
              }
              testId={`dir-activity-row-${row.person_id}`}
              primary={row.display_name}
              secondary={`${row.assigned_madrich_count} Madrichim`}
              trailing={(
                <span className="flex flex-wrap items-center gap-1.5">
                  <span
                    className={`text-xs font-semibold px-2 py-0.5 rounded-full ${
                      row.open_thread_count > 0
                        ? 'bg-amber-100 text-amber-900 dark:bg-amber-900/50 dark:text-amber-200'
                        : 'bg-green-100 text-green-800 dark:bg-green-900/50 dark:text-green-200'
                    }`}
                  >
                    {row.open_thread_count} open
                  </span>
                  {row.median_response_hours !== null && (
                    <span className="text-xs font-medium text-gray-700 dark:text-gray-300">
                      {row.median_response_hours}h median
                    </span>
                  )}
                  {row.oldest_unanswered_days !== null
                    && row.oldest_unanswered_days !== undefined && (
                    <span className="text-xs font-medium text-rose-700 dark:text-rose-300">
                      oldest {row.oldest_unanswered_days}d
                    </span>
                  )}
                </span>
              )}
            />
          </li>
        ))}
      </ul>
    </HomeCard>
  );
}

/**
 * One clickable person row, shared by the roster and faculty cards.
 *
 * Falls back to a plain row when `to` is null so a payload missing
 * `membership_id` degrades to the old read-only display rather than a
 * link that 404s.
 */
function RosterRow({ to, testId, primary, secondary, trailing }) {
  const body = (
    <>
      <span className="min-w-0">
        <span className="text-sm font-medium text-gray-900 dark:text-white">{primary}</span>
        {secondary && (
          <span className="block text-xs text-gray-600 dark:text-gray-300">{secondary}</span>
        )}
      </span>
      <span className="flex items-center gap-2 shrink-0">
        {trailing}
        {to && (
          <ChevronRight
            size={16}
            aria-hidden="true"
            className="text-gray-400 dark:text-gray-500"
          />
        )}
      </span>
    </>
  );

  const shared = 'flex flex-wrap items-center justify-between gap-2 rounded-lg px-2 py-2';
  if (!to) {
    return <span className={shared} data-testid={testId}>{body}</span>;
  }
  return (
    <Link
      to={to}
      data-testid={testId}
      className={`${shared} border border-gray-200 dark:border-gray-700 hover:border-indigo-400 dark:hover:border-indigo-500 hover:bg-indigo-50/70 dark:hover:bg-indigo-900/20 transition-colors`}
    >
      {body}
    </Link>
  );
}

function RosterCard() {
  const roster = useCardData(useCallback(() => fetchDirectorMadrichim({ pageSize: 10 }), []));
  const [exporting, setExporting] = useState(false);
  const [exportError, setExportError] = useState(null);

  async function handleExport() {
    setExporting(true);
    setExportError(null);
    try {
      await downloadMadrichimCsv();
    } catch {
      setExportError('Could not download the CSV.');
    } finally {
      setExporting(false);
    }
  }

  if (roster === null) return <CardSkeleton rows={4} data-testid="dir-roster-loading" />;
  if (roster === false) return null;

  const rows = roster.results || [];

  return (
    <HomeCard
      title="Madrichim"
      subtitle={`${roster.count ?? rows.length} in the program`}
      accent="violet"
      icon={Users}
      action={(
        <button
          type="button"
          onClick={handleExport}
          disabled={exporting}
          data-testid="dir-roster-export"
          className="rounded-lg border border-violet-300 dark:border-violet-700 text-sm font-medium px-3 py-1.5 text-violet-700 dark:text-violet-300 hover:bg-violet-50 dark:hover:bg-violet-900/30 disabled:opacity-50"
        >
          {exporting ? 'Preparing…' : 'Export CSV'}
        </button>
      )}
      data-testid="dir-roster-card"
    >
      {exportError && (
        <p className="text-xs text-red-600 dark:text-red-400 mb-2" role="alert">{exportError}</p>
      )}
      <ul className="space-y-1.5">
        {rows.map((row) => (
          <li key={row.person_id}>
            <RosterRow
              to={
                row.membership_id
                  ? `/admin/reflections/madrich/members/${row.membership_id}`
                  : null
              }
              testId={`dir-roster-row-${row.person_id}`}
              primary={row.display_name}
              secondary={[
                typeof row.grade_level === 'number' ? `Grade ${row.grade_level}` : null,
                row.classroom,
              ].filter(Boolean).join(' · ')}
              trailing={(
                <span className="flex items-center gap-2">
                  {row.reflection_state && (
                    <span
                      className={`text-xs font-semibold px-2 py-0.5 rounded-full ${
                        row.reflection_state === 'complete'
                          ? 'bg-green-100 text-green-800 dark:bg-green-900/50 dark:text-green-200'
                          : 'bg-amber-100 text-amber-900 dark:bg-amber-900/50 dark:text-amber-200'
                      }`}
                    >
                      {row.reflection_state === 'complete' ? 'Submitted' : 'Not yet'}
                    </span>
                  )}
                  {row.open_thread_count > 0 && (
                    <span className="text-xs font-medium text-gray-700 dark:text-gray-300">
                      {row.open_thread_count} open
                    </span>
                  )}
                </span>
              )}
            />
          </li>
        ))}
      </ul>
    </HomeCard>
  );
}

function ThemesCard() {
  const themes = useCardData(useCallback(fetchDirectorThemes, []));
  if (themes === null) return <CardSkeleton rows={3} data-testid="dir-themes-loading" />;
  if (themes === false) return null;

  const rows = themes.themes || [];
  const suppressed = themes.suppressed_count ?? 0;

  return (
    <HomeCard
      title="What they're talking about"
      subtitle="Anonymized. Themes from fewer than five Madrichim are withheld."
      accent="emerald"
      icon={Tags}
      action={(
        <Link
          to={themes.growth_dashboard_url || '/admin/reflections/growth'}
          className="text-sm font-medium text-emerald-700 dark:text-emerald-300 hover:underline"
          data-testid="dir-themes-growth-link"
        >
          Growth by grade →
        </Link>
      )}
      data-testid="dir-themes-card"
    >
      {rows.length === 0 ? (
        <p className="text-sm text-gray-600 dark:text-gray-300">
          Not enough tagged reflections yet.
        </p>
      ) : (
        <ul className="flex flex-wrap gap-2">
          {rows.map((theme) => (
            <li key={theme.theme_key}>
              <span
                className="inline-flex items-center gap-2 text-sm font-medium px-3 py-1 rounded-full bg-emerald-100 dark:bg-emerald-900/40 text-emerald-900 dark:text-emerald-200 ring-1 ring-inset ring-emerald-600/20"
                data-testid={`dir-theme-${theme.theme_key}`}
              >
                {theme.label}
                <span className="text-xs font-semibold px-1.5 rounded-full bg-emerald-600/15 dark:bg-emerald-300/15">
                  {theme.mentions}
                </span>
              </span>
            </li>
          ))}
        </ul>
      )}
      {suppressed > 0 && (
        <p className="mt-3 text-xs text-gray-600 dark:text-gray-300" data-testid="dir-themes-suppressed">
          {suppressed} theme{suppressed === 1 ? '' : 's'} withheld to protect small groups
          (fewer than {themes.min_contributors} contributors).
        </p>
      )}
    </HomeCard>
  );
}

export default function DirectorHome() {
  return (
    <section aria-label="Religious school overview" className="mt-10" data-testid="director-home">
      <div className="flex items-center gap-3 mb-4">
        <h2 className="text-xl font-bold text-gray-900 dark:text-white">This week</h2>
        <span className="h-px flex-1 bg-gradient-to-r from-indigo-400 via-violet-300 to-transparent dark:from-indigo-500 dark:via-violet-700" />
      </div>
      {/* items-start so a short card does not stretch to the height of a long
          neighbour in the same grid row. */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 items-start">
        <PulseCard />
        <QuestionQueueCard />
        <CoverageCard />
        <RosterCard />
        <FacultyActivityCard />
        <ThemesCard />
        <HomeCard
          title="Cohort feed"
          subtitle="Read what Madrichim are sharing, and hide anything that shouldn't be up."
          accent="rose"
          icon={MessagesSquare}
          data-testid="dir-cohort-card"
          footer={(
            <Link
              to="/madrich/cohort"
              className="inline-block rounded-lg bg-rose-600 hover:bg-rose-700 text-white text-sm font-semibold px-4 py-2 shadow-sm transition-colors"
              data-testid="dir-cohort-link"
            >
              Open cohort feed
            </Link>
          )}
        />
      </div>
    </section>
  );
}
