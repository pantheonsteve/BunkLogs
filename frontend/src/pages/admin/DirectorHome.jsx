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
  downloadMadrichimCsv,
  fetchDirectorCoverage,
  fetchDirectorFacultyActivity,
  fetchDirectorMadrichim,
  fetchDirectorPulse,
  fetchDirectorQueue,
  fetchDirectorThemes,
} from '../../api/director';
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

function PulseCard() {
  const pulse = useCardData(useCallback(fetchDirectorPulse, []));
  if (pulse === null) return <CardSkeleton rows={3} data-testid="dir-pulse-loading" />;
  if (pulse === false) return null;

  if (!pulse.available) {
    return (
      <HomeCard
        title="Reflection pulse"
        subtitle="No weekly reflection template is assigned yet."
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
      badge={pulse.open_question_count > 0 && (
        <UnreadDot
          count={pulse.open_question_count}
          label={`${pulse.open_question_count} questions for you`}
        />
      )}
      data-testid="dir-pulse-card"
    >
      <p className="text-2xl font-semibold text-gray-900 dark:text-white" data-testid="dir-pulse-rate">
        {percent(current.rate)}
        <span className="ml-2 text-sm font-normal text-gray-500 dark:text-gray-400">
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
      data-testid="dir-queue-card"
    >
      {items.length > 0 && (
        <ul className="space-y-2" data-testid="dir-queue-list">
          {items.map((item) => (
            <li key={item.id}>
              <Link
                to={`/admin/threads/${item.id}`}
                className="block rounded-lg border border-gray-200 dark:border-gray-700 px-3 py-2 hover:border-indigo-300 dark:hover:border-indigo-700"
                data-testid={`dir-queue-row-${item.id}`}
              >
                <div className="flex items-start justify-between gap-2">
                  <p className="text-sm font-medium text-gray-900 dark:text-white">
                    {item.subject_person?.display_name}
                  </p>
                  {item.age_days !== null && item.age_days !== undefined && (
                    <span className="text-xs text-gray-500 dark:text-gray-400 shrink-0">
                      {item.age_days === 0 ? 'today' : `${item.age_days}d ago`}
                    </span>
                  )}
                </div>
                <p className="mt-1 text-sm text-gray-700 dark:text-gray-300">{item.excerpt}</p>
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
  if (coverage === null) return <CardSkeleton rows={4} data-testid="dir-coverage-loading" />;
  if (coverage === false) return null;

  const sessions = coverage.sessions || [];
  const classrooms = coverage.classrooms || [];
  if (sessions.length === 0 || classrooms.length === 0) return null;

  return (
    <HomeCard
      title="Sunday coverage"
      subtitle="Flagged where anyone is tentative or hasn't answered."
      data-testid="dir-coverage-card"
      className="lg:col-span-2"
    >
      <div className="overflow-x-auto">
        <table className="min-w-full text-sm">
          <caption className="sr-only">
            Availability by classroom for the next {sessions.length} Sundays
          </caption>
          <thead>
            <tr>
              <th scope="col" className="text-left font-medium text-gray-500 dark:text-gray-400 pb-2 pr-3">
                Classroom
              </th>
              {sessions.map((session) => (
                <th
                  key={session}
                  scope="col"
                  className="text-left font-medium text-gray-500 dark:text-gray-400 pb-2 px-2 whitespace-nowrap"
                >
                  {formatDate(session)}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {classrooms.map((room) => (
              <tr key={room.id} className="border-t border-gray-100 dark:border-gray-700">
                <th
                  scope="row"
                  className="text-left font-normal text-gray-900 dark:text-white py-2 pr-3 whitespace-nowrap"
                >
                  {room.name}
                  <span className="text-gray-500 dark:text-gray-400"> ({room.roster_size})</span>
                </th>
                {room.cells.map((cell) => {
                  const meta = statusMeta(cell.flagged ? 'unset' : 'available');
                  return (
                    <td key={cell.session_date} className="py-2 px-2">
                      <span
                        className={`inline-block text-xs font-medium px-2 py-0.5 rounded-full ${meta.pill}`}
                        data-testid={`dir-coverage-${room.id}-${cell.session_date}`}
                      >
                        {cell.available}/{cell.roster_size}
                        {cell.unset > 0 && ` · ${cell.unset} unanswered`}
                        {cell.tentative > 0 && ` · ${cell.tentative} tentative`}
                      </span>
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
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
      data-testid="dir-activity-card"
    >
      <ul className="divide-y divide-gray-100 dark:divide-gray-700">
        {rows.map((row) => (
          <li
            key={row.person_id}
            className="py-2 flex flex-wrap items-baseline justify-between gap-2"
            data-testid={`dir-activity-row-${row.person_id}`}
          >
            <span className="text-sm text-gray-900 dark:text-white">
              {row.display_name}
              <span className="text-gray-500 dark:text-gray-400">
                {' '}· {row.assigned_madrich_count} Madrichim
              </span>
            </span>
            <span className="text-xs text-gray-500 dark:text-gray-400">
              {row.open_thread_count} open
              {row.median_response_hours !== null && ` · ${row.median_response_hours}h median`}
              {row.oldest_unanswered_days !== null
                && row.oldest_unanswered_days !== undefined
                && ` · oldest ${row.oldest_unanswered_days}d`}
            </span>
          </li>
        ))}
      </ul>
    </HomeCard>
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
      action={(
        <button
          type="button"
          onClick={handleExport}
          disabled={exporting}
          data-testid="dir-roster-export"
          className="rounded-lg border border-gray-300 dark:border-gray-600 text-sm font-medium px-3 py-1.5 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800 disabled:opacity-50"
        >
          {exporting ? 'Preparing…' : 'Export CSV'}
        </button>
      )}
      data-testid="dir-roster-card"
    >
      {exportError && (
        <p className="text-xs text-red-500 mb-2" role="alert">{exportError}</p>
      )}
      <ul className="divide-y divide-gray-100 dark:divide-gray-700">
        {rows.map((row) => (
          <li
            key={row.person_id}
            className="py-2 flex flex-wrap items-baseline justify-between gap-2"
            data-testid={`dir-roster-row-${row.person_id}`}
          >
            <span className="text-sm text-gray-900 dark:text-white">
              {row.display_name}
              <span className="text-gray-500 dark:text-gray-400">
                {typeof row.grade_level === 'number' && ` · Grade ${row.grade_level}`}
                {row.classroom && ` · ${row.classroom}`}
              </span>
            </span>
            <span className="flex items-center gap-2">
              {row.reflection_state && (
                <span
                  className={`text-xs font-medium px-2 py-0.5 rounded-full ${
                    row.reflection_state === 'complete'
                      ? 'bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-300'
                      : 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/40 dark:text-yellow-300'
                  }`}
                >
                  {row.reflection_state === 'complete' ? 'Submitted' : 'Not yet'}
                </span>
              )}
              {row.open_thread_count > 0 && (
                <span className="text-xs text-gray-500 dark:text-gray-400">
                  {row.open_thread_count} open
                </span>
              )}
            </span>
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
      action={(
        <Link
          to={themes.growth_dashboard_url || '/admin/reflections/growth'}
          className="text-sm text-indigo-600 dark:text-indigo-400 hover:underline"
          data-testid="dir-themes-growth-link"
        >
          Growth by grade →
        </Link>
      )}
      data-testid="dir-themes-card"
    >
      {rows.length === 0 ? (
        <p className="text-sm text-gray-500 dark:text-gray-400">
          Not enough tagged reflections yet.
        </p>
      ) : (
        <ul className="flex flex-wrap gap-2">
          {rows.map((theme) => (
            <li key={theme.theme_key}>
              <span
                className="inline-flex items-center gap-2 text-sm px-3 py-1 rounded-full bg-indigo-50 dark:bg-indigo-900/30 text-indigo-800 dark:text-indigo-200"
                data-testid={`dir-theme-${theme.theme_key}`}
              >
                {theme.label}
                <span className="text-xs opacity-75">{theme.mentions}</span>
              </span>
            </li>
          ))}
        </ul>
      )}
      {suppressed > 0 && (
        <p className="mt-3 text-xs text-gray-500 dark:text-gray-400" data-testid="dir-themes-suppressed">
          {suppressed} theme{suppressed === 1 ? '' : 's'} withheld to protect small groups
          (fewer than {themes.min_contributors} contributors).
        </p>
      )}
    </HomeCard>
  );
}

export default function DirectorHome() {
  return (
    <section aria-label="Religious school overview" className="mt-8" data-testid="director-home">
      <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-3">
        This week
      </h2>
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
          data-testid="dir-cohort-card"
          footer={(
            <Link
              to="/madrich/cohort"
              className="inline-block rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium px-4 py-2 transition-colors"
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
