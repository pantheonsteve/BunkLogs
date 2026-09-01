/**
 * The admin landing page.
 *
 * It used to open onto a grid of thirteen navigation tiles, which answered
 * "where do I go" but not the two questions a director actually arrives
 * with: is this set up right, and who hasn't submitted. Both are answered
 * above the fold now, and every count links to the fix rather than just
 * reporting a number. Navigation went back to the sidebar, where it can
 * be reached from every page rather than only this one.
 */
import { useCallback, useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { AlertTriangle, Check } from 'lucide-react';

import { useAuth } from '../../auth/AuthContext';
import { fetchAdminDashboard } from '../../api/admin';
import { useAdminProgram } from '../../context/AdminProgramContext';
import { useTerm } from '../../context/OrgBrandingContext';
import Card, { CardBody, CardHeader } from '../../components/ui/Card';
import ErrorPanel from '../../components/ui/ErrorPanel';
import LoadingState from '../../components/ui/LoadingState';
import Note from '../../components/ui/Note';
import ProgressBar from '../../components/ui/ProgressBar';
import {
  daysBetween,
  formatMonthDay,
  formatWeekdayMonthDay,
  greetingFor,
  relativeTime,
} from '../../lib/adminDates';
import { programShortLabel } from '../../lib/programLabel';
import { orgSurfaces } from '../../utils/auth/orgProfile';
import DirectorHome from './DirectorHome';

/**
 * One line in the setup card. Resolves itself: once the underlying problem
 * is gone the row turns into a tick rather than disappearing, so the
 * director can see the check was actually run.
 */
function AttentionRow({ open, headline, detail, resolvedText, actionLabel, onAction, testId }) {
  if (!open) {
    return (
      <div className="flex items-start gap-3 py-2.5" data-testid={testId}>
        <span className="mt-0.5 inline-flex items-center justify-center w-5 h-5 rounded-full bg-green-100 dark:bg-green-900/40 text-green-700 dark:text-green-400 shrink-0">
          <Check size={12} aria-hidden="true" />
        </span>
        <p className="text-sm text-gray-600 dark:text-gray-400">{resolvedText}</p>
      </div>
    );
  }
  return (
    <div className="flex items-start gap-3 py-2.5" data-testid={testId}>
      <span className="mt-0.5 inline-flex items-center justify-center w-5 h-5 rounded-full bg-amber-100 dark:bg-amber-900/40 text-amber-700 dark:text-amber-400 shrink-0">
        <AlertTriangle size={12} aria-hidden="true" />
      </span>
      <div className="min-w-0 flex-1">
        <p className="text-sm font-semibold text-gray-900 dark:text-white">{headline}</p>
        {detail && (
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">{detail}</p>
        )}
      </div>
      <button
        type="button"
        onClick={onAction}
        className="shrink-0 px-3 py-1.5 rounded-lg text-xs font-semibold bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
      >
        {actionLabel}
      </button>
    </div>
  );
}

function Stat({ label, value, detail, tone, testId }) {
  return (
    <Card className="p-4" data-testid={testId}>
      <p className="text-[11px] font-bold uppercase tracking-wider text-gray-500 dark:text-gray-400">
        {label}
      </p>
      <p className="text-3xl font-bold text-gray-900 dark:text-white mt-1 tabular-nums">
        {value}
      </p>
      {detail && (
        <p
          className={`text-xs mt-1 ${
            tone === 'warn'
              ? 'text-amber-700 dark:text-amber-400 font-semibold'
              : 'text-gray-500 dark:text-gray-400'
          }`}
        >
          {detail}
        </p>
      )}
    </Card>
  );
}

function nameList(groups, max = 3) {
  const names = groups.map((g) => g.name);
  if (names.length <= max) return names.join(' · ');
  return `${names.slice(0, max).join(' · ')} and ${names.length - max} more`;
}

/**
 * Where the program sits relative to today. Before it starts the useful
 * number is the countdown; once it's running it's how far in you are.
 */
function programCountdown(program, today, shortLabel) {
  if (!program || !today) return null;
  const toStart = daysBetween(today, program.start_date);
  if (toStart !== null && toStart > 0) {
    return `${shortLabel} starts in ${toStart} ${toStart === 1 ? 'day' : 'days'}`;
  }
  const sinceStart = daysBetween(program.start_date, today);
  const toEnd = daysBetween(today, program.end_date);
  if (toEnd !== null && toEnd < 0) return `${shortLabel} has ended`;
  if (sinceStart === null) return null;
  return `Day ${sinceStart + 1} of ${shortLabel}`;
}

export default function AdminHome() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const term = useTerm();
  const { programId, program, ready: programReady } = useAdminProgram();
  const surfaces = orgSurfaces(user);

  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    if (!programReady) return;
    setLoading(true);
    setError('');
    try {
      setData(await fetchAdminDashboard(programId ? { program: programId } : {}));
    } catch (err) {
      setError(err?.response?.data?.detail || 'Could not load the dashboard.');
    } finally {
      setLoading(false);
    }
  }, [programId, programReady]);

  useEffect(() => {
    load();
  }, [load]);

  const groupsLo = term('group', { plural: true });
  const groupLo = term('group', { plural: false });
  const authorsLo = term('counselor', { plural: true });
  const subjectsLo = term('camper', { plural: true });
  const programLo = term('program');

  const attention = data?.setup_attention;
  const logs = data?.logs_this_week;
  const completed = attention?.completed || {};
  const noAuthor = attention?.groups_without_author || { count: 0, groups: [] };
  const noSubjects = attention?.groups_without_subjects || { count: 0, groups: [] };
  const neverInvited = attention?.people_never_invited?.count || 0;
  const awaitingSignIn = attention?.people_invited_not_signed_in?.count || 0;

  const groupsTotal = completed.groups_total || 0;
  const withForms = completed.groups_with_forms || 0;
  const withoutForms = Math.max(0, groupsTotal - withForms);

  const goToGroups = (params = '') => navigate(`/admin/groups${params}`);
  const goToNeverInvited = () => navigate('/admin/people?invite_status=never');

  // Order matters: the things already done sit above the things that
  // aren't, which is what turns the card from a list of complaints into
  // a progress report.
  const setupSteps = [
    {
      testId: 'setup-groups-created',
      open: groupsTotal === 0,
      headline: `No ${groupsLo} yet`,
      detail: `Nothing can be logged until at least one ${groupLo} exists.`,
      resolvedText: `${groupsTotal} ${groupsTotal === 1 ? groupLo : groupsLo} created`,
      actionLabel: 'Create',
      onAction: () => goToGroups(''),
    },
    {
      testId: 'setup-subjects-enrolled',
      open: (completed.subjects_enrolled || 0) === 0,
      headline: `No ${subjectsLo} enrolled`,
      detail: `Add the ${subjectsLo} the logs are about.`,
      resolvedText: `${completed.subjects_enrolled || 0} ${subjectsLo} enrolled`,
      actionLabel: 'Add',
      onAction: () => navigate('/admin/people'),
    },
    {
      testId: 'setup-forms-assigned',
      open: groupsTotal > 0 && withoutForms > 0,
      headline: `${withoutForms} ${withoutForms === 1 ? groupLo : groupsLo} ${withoutForms === 1 ? 'has' : 'have'} no form assigned`,
      detail: 'A group with no form has nothing for its staff to fill in.',
      resolvedText: `All ${groupsTotal} ${groupsLo} have a form assigned`,
      actionLabel: 'Assign',
      onAction: () => navigate('/admin/forms'),
    },
    {
      testId: 'attention-no-author',
      open: noAuthor.count > 0,
      headline: `${noAuthor.count} ${noAuthor.count === 1 ? groupLo : groupsLo} ${noAuthor.count === 1 ? 'has' : 'have'} no ${authorsLo} assigned`,
      detail: `${nameList(noAuthor.groups)} — nobody can write logs for ${noAuthor.count === 1 ? 'this' : 'these'} yet`,
      resolvedText: `Every ${groupLo} has at least one ${term('counselor')}`,
      actionLabel: 'Assign',
      onAction: () => goToGroups('?warning=no_author'),
    },
    {
      testId: 'attention-no-subjects',
      open: noSubjects.count > 0,
      headline: `${noSubjects.count} ${noSubjects.count === 1 ? groupLo : groupsLo} ${noSubjects.count === 1 ? 'has' : 'have'} no ${subjectsLo}`,
      detail: `${nameList(noSubjects.groups)} — mark ${noSubjects.count === 1 ? 'it' : 'them'} staff-only if that's intended`,
      resolvedText: `Every ${groupLo} either has ${subjectsLo} or is confirmed staff-only`,
      actionLabel: 'Review',
      onAction: () => goToGroups('?warning=no_subjects'),
    },
    {
      testId: 'attention-never-invited',
      open: neverInvited > 0,
      headline: `${neverInvited} ${neverInvited === 1 ? 'person has' : 'people have'} never been invited`,
      detail: awaitingSignIn > 0
        ? `${awaitingSignIn} more ${awaitingSignIn === 1 ? 'was' : 'were'} invited but ${awaitingSignIn === 1 ? "hasn't" : "haven't"} signed in yet`
        : null,
      resolvedText: 'Everyone has been invited',
      actionLabel: 'Send invitations',
      onAction: goToNeverInvited,
    },
  ];
  const stepsDone = setupSteps.filter((s) => !s.open).length;

  const shortLabel = programShortLabel(program);
  const countdown = programCountdown(program, data?.today, shortLabel);
  const firstName = user?.first_name;
  // Everyone who isn't a subject of the logs, which is who invitations
  // and sign-ins are actually about.
  const staffCount = (data?.org_snapshot?.memberships_by_role || [])
    .filter((r) => r.role !== 'camper')
    .reduce((sum, r) => sum + (r.count || 0), 0);
  const behindCount = logs?.behind?.length ?? 0;

  return (
    <main
      className="grow px-4 sm:px-6 lg:px-8 py-6 w-full max-w-[1180px] mx-auto"
      data-testid="admin-home"
    >
      <header className="mb-6">
        <h1 className="text-[27px] tracking-tight font-bold text-gray-900 dark:text-white">
          {greetingFor()}{firstName ? `, ${firstName}` : ''}
        </h1>
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
          {formatWeekdayMonthDay(data?.today)}
          {countdown ? ` · ${countdown}` : ''}
        </p>
      </header>

      {error && (
        <div className="mb-4">
          <ErrorPanel>{error}</ErrorPanel>
        </div>
      )}

      {loading ? (
        <LoadingState>Loading dashboard…</LoadingState>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
          <div className="lg:col-span-2 space-y-5">
            <Card data-testid="admin-home-setup">
              <CardHeader
                title={`${shortLabel || term('program', { capitalize: true })} setup`}
                subtitle={`${stepsDone} of ${setupSteps.length} steps complete`}
                action={(
                  <Link
                    to="/admin/setup"
                    className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-indigo-600 text-white hover:bg-indigo-700 transition-colors"
                  >
                    Continue setup →
                  </Link>
                )}
              >
                <ProgressBar
                  value={stepsDone}
                  total={setupSteps.length}
                  className="mt-2"
                  data-testid="setup-progress"
                />
              </CardHeader>
              <CardBody className="divide-y divide-gray-100 dark:divide-gray-800 py-1">
                {setupSteps.map((step) => (
                  <AttentionRow key={step.testId} {...step} />
                ))}
              </CardBody>
            </Card>

            <Card data-testid="admin-home-logs">
              <CardHeader
                title="Logs this week"
                subtitle={
                  logs
                    ? `Week of ${formatMonthDay(logs.window_start)} · ${logs.submitted} of ${logs.expected} expected`
                    : undefined
                }
                action={(
                  <Link
                    to="/admin/reports"
                    className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
                  >
                    All reports
                  </Link>
                )}
              />
              <CardBody>
                {!logs || logs.expected === 0 ? (
                  <p className="text-sm text-gray-500 dark:text-gray-400">
                    No {subjectsLo} are enrolled in this {programLo} yet, so
                    there is nothing to submit.
                  </p>
                ) : logs.behind.length === 0 ? (
                  <Note tone="ok" data-testid="logs-all-in">
                    Everything is in. Nice week.
                  </Note>
                ) : (
                  <>
                    <p className="text-xs text-gray-500 dark:text-gray-400 mb-3">
                      {term('group', { plural: true, capitalize: true })} behind, most
                      behind first:
                    </p>
                    <ul className="space-y-2.5">
                      {logs.behind.map((g) => (
                        <li key={g.id} className="flex items-center gap-3">
                          <Link
                            to={`/admin/groups/${g.id}`}
                            className="w-36 shrink-0 text-sm font-semibold text-gray-900 dark:text-white hover:text-blue-600 dark:hover:text-blue-400 truncate"
                          >
                            {g.name}
                          </Link>
                          <ProgressBar
                            value={g.submitted}
                            total={g.expected}
                            className="flex-1"
                          />
                          <span className="w-14 text-right text-xs text-gray-500 dark:text-gray-400 tabular-nums">
                            {g.submitted}/{g.expected}
                          </span>
                          <Link
                            to={`/admin/groups/${g.id}`}
                            className="shrink-0 px-2 py-1 rounded-md text-xs font-semibold text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
                          >
                            Open
                          </Link>
                        </li>
                      ))}
                    </ul>
                  </>
                )}
              </CardBody>
            </Card>
          </div>

          <div className="space-y-5">
            <div className="grid grid-cols-2 gap-4">
              <Stat
                testId="stat-subjects"
                label={term('camper', { plural: true, capitalize: true })}
                value={logs?.expected ?? 0}
                detail={
                  behindCount > 0
                    ? `${behindCount} ${behindCount === 1 ? groupLo : groupsLo} behind`
                    : `across ${groupsTotal} ${groupsTotal === 1 ? groupLo : groupsLo}`
                }
                tone={behindCount > 0 ? 'warn' : undefined}
              />
              <Stat
                testId="stat-staff"
                label="Staff"
                value={staffCount}
                detail={neverInvited > 0 ? `${neverInvited} not invited` : 'all invited'}
                tone={neverInvited > 0 ? 'warn' : undefined}
              />
            </div>

            <Card data-testid="admin-home-quick-actions">
              <CardHeader title="Quick actions" />
              <CardBody className="flex flex-col items-start gap-2">
                <button
                  type="button"
                  onClick={goToNeverInvited}
                  className="text-sm font-medium text-indigo-700 dark:text-indigo-300 hover:underline"
                >
                  Invite everyone who hasn&apos;t been invited
                </button>
                <Link
                  to="/admin/groups"
                  className="text-sm font-medium text-indigo-700 dark:text-indigo-300 hover:underline"
                >
                  Assign {authorsLo} to {groupsLo}
                </Link>
                <Link
                  to="/admin/people"
                  className="text-sm font-medium text-indigo-700 dark:text-indigo-300 hover:underline"
                >
                  Add a person
                </Link>
                <Link
                  to="/admin/setup"
                  className="text-sm font-medium text-indigo-700 dark:text-indigo-300 hover:underline"
                >
                  Set up next {programLo}
                </Link>
              </CardBody>
            </Card>

            <Card data-testid="admin-home-activity">
              <CardHeader title="Recent activity" />
              <CardBody>
                {(data?.recent_activity || []).length === 0 ? (
                  <p className="text-sm text-gray-500 dark:text-gray-400">
                    Nothing in the last week.
                  </p>
                ) : (
                  <ul className="space-y-2">
                    {data.recent_activity.slice(0, 6).map((e) => (
                      <li key={e.id}>
                        <Link
                          to={e.deep_link || '/admin'}
                          className="block text-sm text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white"
                        >
                          <span className="font-semibold text-gray-900 dark:text-white">
                            {e.actor || 'Someone'}
                          </span>{' '}
                          {e.summary.toLowerCase()}
                          {e.created_at && (
                            <span className="text-xs text-gray-400 dark:text-gray-500">
                              {' · '}{relativeTime(e.created_at)}
                            </span>
                          )}
                        </Link>
                      </li>
                    ))}
                  </ul>
                )}
              </CardBody>
            </Card>
          </div>
        </div>
      )}

      {surfaces.gradeReflections && (
        <section className="mt-8">
          <h2 className="text-sm font-bold uppercase tracking-wider text-gray-500 dark:text-gray-400 mb-3">
            Reflections
          </h2>
          <DirectorHome />
        </section>
      )}
    </main>
  );
}
