/**
 * Counselor home at `/counselor`, phone first (2027 refresh, 8_4).
 *
 * Day stepper, a hero card + camper list per bunk, the self-reflection
 * card, quick actions and recent requests; two columns from md up and a
 * bottom tab bar below lg. Per-camper status comes from the camper
 * reflection roster plus local drafts / the offline queue, so "Continue
 * logging" always names the first camper in roster order not yet done.
 */

import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import {
  ArrowRight,
  Check,
  CheckCircle,
  ChevronLeft,
  ChevronRight,
  ClipboardList,
  Flag,
  HeartHandshake,
  Home,
  MessageSquare,
  PenLine,
  User,
  Users,
  Wrench,
} from 'lucide-react';
import api from '../../api';
import { fetchCamperReflections, fetchCounselorDashboard } from '../../api/counselor';
import Badge from '../../components/ui/Badge';
import Button from '../../components/ui/Button';
import Card from '../../components/ui/Card';
import InitialsAvatar from '../../components/ui/InitialsAvatar';
import ProgressBar from '../../components/ui/ProgressBar';
import { SUBMISSION_KIND } from '../../lib/submissionQueue/queue';
import { useSubmissionQueue } from '../../lib/submissionQueue/useSubmissionQueue';
import {
  camperReflectionDraftKey,
  loadCounselorDraft,
  selfReflectionDraftKey,
} from '../../utils/counselor/counselorDraftStorage';

const REFRESH_INTERVAL_MS = 60_000;
const ROSTER_PATH = '/counselor/camper-reflections';

const CAMPER_STATUS = {
  complete: { label: 'Done', tone: 'ok', icon: true },
  syncing: { label: 'Syncing', tone: 'info' },
  draft_saved: { label: 'Draft saved', tone: 'warn' },
  none: { label: 'Not started', tone: 'neutral' },
  off_camp: {
    label: 'Off camp',
    colors: 'bg-transparent border border-line text-muted',
  },
};

const REQUEST_STATUS_TONE = {
  new: 'info',
  in_progress: 'warn',
  fulfilled: 'ok',
  unable_to_fulfill: 'neutral',
};

const SECTION_HEADING = 'text-[13px] font-bold uppercase tracking-wider text-ink-2';

function parseIso(iso) {
  const parsed = new Date(`${iso}T00:00:00`);
  return Number.isNaN(parsed.getTime()) ? null : parsed;
}

function shiftIso(iso, days) {
  const d = parseIso(iso);
  if (!d) return iso;
  d.setDate(d.getDate() + days);
  const mm = String(d.getMonth() + 1).padStart(2, '0');
  const dd = String(d.getDate()).padStart(2, '0');
  return `${d.getFullYear()}-${mm}-${dd}`;
}

function formatStepperDate(iso) {
  const d = iso ? parseIso(iso) : null;
  if (!d) return iso || '';
  return d.toLocaleDateString(undefined, { weekday: 'long', month: 'short', day: 'numeric' });
}

function relativeDayLabel(selectedIso, todayIso) {
  if (!selectedIso || !todayIso || selectedIso === todayIso) return 'Today';
  if (shiftIso(todayIso, -1) === selectedIso) return 'Yesterday';
  return 'Past day · read-only';
}

function formatRelative(iso) {
  if (!iso) return '';
  const diffMin = Math.round((Date.now() - new Date(iso)) / 60000);
  if (diffMin < 1) return 'just now';
  if (diffMin < 60) return `${diffMin}m ago`;
  const diffH = Math.round(diffMin / 60);
  if (diffH < 24) return `${diffH}h ago`;
  const diffD = Math.round(diffH / 24);
  return diffD === 1 ? 'yesterday' : `${diffD}d ago`;
}

function requestDetailPath(request) {
  if (request.type === 'camper_care') {
    return `/counselor/requests/camper-care/${request.id}`;
  }
  return `/counselor/requests/maintenance/${request.id}?from=counselor`;
}

function camperStatus(camper, { pendingIds, date }) {
  if (pendingIds.has(String(camper.id))) return 'syncing';
  if (camper.submitted) return 'complete';
  if (date && loadCounselorDraft(camperReflectionDraftKey(camper.id, date))?.answers) {
    return 'draft_saved';
  }
  return 'none';
}

function camperFormPath(camper, { status, bunkId, editable, date }) {
  if (status === 'complete' && camper.editable && camper.reflection_id) {
    return `${ROSTER_PATH}/${camper.reflection_id}/edit`;
  }
  if (editable && status !== 'complete' && status !== 'syncing') {
    return `${ROSTER_PATH}/new?subject=${camper.id}&bunk=${bunkId}&name=${encodeURIComponent(camper.name || '')}`;
  }
  return editable ? ROSTER_PATH : `${ROSTER_PATH}/${date}`;
}

function shortName(camper) {
  const first = camper.preferred_name || camper.first_name;
  if (!first) return camper.name;
  return camper.last_initial ? `${first} ${camper.last_initial}.` : first;
}

/** Camper rows for one bunk, in roster order, with derived status + link. */
function buildCamperRows(rosterBunk, { pendingIds, date, editable }) {
  if (!rosterBunk) return null;
  const rows = (rosterBunk.campers || []).map((camper) => {
    const status = camperStatus(camper, { pendingIds, date });
    return {
      camper,
      status,
      to: camperFormPath(camper, { status, bunkId: rosterBunk.id, editable, date }),
    };
  });
  const offCamp = (rosterBunk.off_camp || []).map((camper) => ({
    camper,
    status: 'off_camp',
    to: null,
  }));
  return [...rows, ...offCamp];
}

function DayStepper({ selectedIso, todayIso, onChange, refreshing }) {
  const atToday = !selectedIso || !todayIso || selectedIso >= todayIso;
  const stepBtn =
    'w-11 h-11 shrink-0 rounded-[10px] flex items-center justify-center bg-line-soft text-ink hover:bg-line disabled:bg-transparent disabled:text-muted/50 disabled:cursor-not-allowed transition-colors';
  return (
    <div className="flex items-center gap-1.5" data-testid="counselor-day-stepper">
      <button
        type="button"
        aria-label="Previous day"
        className={stepBtn}
        onClick={() => onChange(shiftIso(selectedIso, -1))}
        data-testid="counselor-day-prev"
      >
        <ChevronLeft className="w-[18px] h-[18px]" aria-hidden="true" />
      </button>
      <label className="relative flex-1 text-center min-h-11 flex flex-col justify-center cursor-pointer">
        <span className="text-[17px] font-bold text-ink">{formatStepperDate(selectedIso)}</span>
        <span className="text-xs text-muted">
          {refreshing ? 'Refreshing…' : relativeDayLabel(selectedIso, todayIso)}
        </span>
        <input
          type="date"
          aria-label="Pick a date"
          value={selectedIso}
          max={todayIso}
          onChange={(e) => e.target.value && onChange(e.target.value)}
          className="absolute inset-0 opacity-0 cursor-pointer"
          data-testid="counselor-date-picker"
        />
      </label>
      <button
        type="button"
        aria-label="Next day"
        className={stepBtn}
        disabled={atToday}
        onClick={() => onChange(shiftIso(selectedIso, 1))}
        data-testid="counselor-day-next"
      >
        <ChevronRight className="w-[18px] h-[18px]" aria-hidden="true" />
      </button>
    </div>
  );
}

function BunkHeroCard({ bunk, rows, editable, rosterCovered, rosterTotal }) {
  const otherAssignments = (bunk.assignments || []).filter(
    (a) => a.action_path && !a.action_path.startsWith(ROSTER_PATH),
  );
  const rosterTile = (bunk.assignments || []).find(
    (a) => a.action_path?.startsWith(ROSTER_PATH),
  );
  const logged = rosterCovered ?? rosterTile?.covered ?? 0;
  const expected = rosterTotal ?? rosterTile?.total ?? 0;
  const next = rows?.find((r) => r.status !== 'complete' && r.status !== 'syncing' && r.to);
  const allDone = expected > 0 && rows ? !next : expected > 0 && logged >= expected;

  const subtitle = [
    bunk.co_counselor_names?.length ? `With ${bunk.co_counselor_names.join(', ')}` : null,
    `${bunk.camper_count} camper${bunk.camper_count === 1 ? '' : 's'}`,
    bunk.off_camp_count > 0 ? `${bunk.off_camp_count} off camp` : null,
  ].filter(Boolean).join(' · ');

  return (
    <Card
      as="section"
      className="rounded-2xl p-4 flex flex-col gap-3"
      data-testid={`counselor-bunk-tile-${bunk.id}`}
      aria-labelledby={`bunk-${bunk.id}-name`}
    >
      <div className="flex items-baseline justify-between gap-3">
        <h2 id={`bunk-${bunk.id}-name`} className="text-xl font-bold text-ink truncate">
          {bunk.name}
        </h2>
        {bunk.unit_name ? (
          <span className="text-[13px] text-muted shrink-0">{bunk.unit_name}</span>
        ) : null}
      </div>
      <p className="text-[13px] text-ink-2">{subtitle}</p>

      {expected > 0 ? (
        <div className="flex items-center gap-2.5">
          <ProgressBar
            value={logged}
            total={expected}
            className="h-2.5 flex-1"
            aria-label={`${logged} of ${expected} campers logged`}
          />
          <span className="text-sm font-bold text-ink tabular-nums">
            {logged} of {expected}
          </span>
        </div>
      ) : null}

      {allDone ? (
        <div
          className="flex items-start gap-3 rounded-xl bg-ok-soft px-4 py-3"
          data-testid={`counselor-bunk-done-${bunk.id}`}
          role="status"
        >
          <CheckCircle className="w-5 h-5 shrink-0 text-ok-ink mt-0.5" aria-hidden="true" />
          <div>
            <p className="text-sm font-semibold text-ok-ink">All campers logged</p>
            <p className="text-xs text-ok-ink/80 mt-0.5">
              Edits stay open until the day rolls over.
            </p>
          </div>
        </div>
      ) : next && editable ? (
        <Button
          as={Link}
          to={next.to}
          size="lg"
          className="w-full"
          data-testid={`counselor-continue-logging-${bunk.id}`}
        >
          Continue logging · {shortName(next.camper)}
          <ArrowRight className="w-[18px] h-[18px]" aria-hidden="true" />
        </Button>
      ) : null}

      {otherAssignments.length > 0 ? (
        <ul className="flex flex-col gap-1 border-t border-line-soft pt-2">
          {otherAssignments.map((a) => (
            <li key={a.template_id}>
              <Link
                to={a.action_path}
                data-testid={`bunk-assignment-action-${a.template_id}`}
                className="flex items-center justify-between gap-3 min-h-11 text-sm text-ink hover:text-brand"
              >
                <span className="font-medium truncate">{a.template_name}</span>
                <span className="text-xs text-muted shrink-0">{a.due_label}</span>
              </Link>
            </li>
          ))}
        </ul>
      ) : null}

      <Link
        to={bunk.dashboard_path}
        className="text-[13px] font-semibold text-brand hover:text-brand-hover self-start"
        data-testid={`counselor-bunk-dashboard-${bunk.id}`}
      >
        Open bunk dashboard
      </Link>
    </Card>
  );
}

function CamperStatusChip({ status }) {
  const cfg = CAMPER_STATUS[status] || CAMPER_STATUS.none;
  return (
    <Badge
      tone={cfg.tone}
      colors={cfg.colors}
      className="font-semibold px-2.5 py-1"
      data-testid="camper-status-chip"
      data-status={status}
    >
      {cfg.icon ? <Check className="w-3 h-3" strokeWidth={3} aria-hidden="true" /> : null}
      {cfg.label}
    </Badge>
  );
}

function CamperList({ bunk, rows, showBunkName }) {
  if (!rows?.length) return null;
  const rowCls = 'flex items-center gap-3 min-h-[52px] border-t border-line-soft text-ink';
  return (
    <Card
      as="section"
      className="rounded-2xl px-4 py-1.5"
      data-testid={`counselor-camper-list-${bunk.id}`}
      aria-label={`${bunk.name} campers`}
    >
      <h2 className={`${SECTION_HEADING} pt-2.5 pb-1`}>
        {showBunkName ? `${bunk.name} campers` : 'Campers'}
      </h2>
      <ul>
        {rows.map(({ camper, status, to }) => {
          const content = (
            <>
              <InitialsAvatar name={camper.name} size="sm" tone="neutral" aria-hidden="true" />
              <span className="flex-1 min-w-0 truncate text-[15px] font-medium">{camper.name}</span>
              <CamperStatusChip status={status} />
            </>
          );
          return (
            <li key={camper.id} data-testid={`counselor-camper-row-${camper.id}`}>
              {to ? (
                <Link to={to} className={`${rowCls} hover:text-brand`}>
                  {content}
                </Link>
              ) : (
                <div className={`${rowCls} text-muted`}>{content}</div>
              )}
            </li>
          );
        })}
      </ul>
    </Card>
  );
}

function SelfReflectionCard({ section, hasDraft, hasPendingSync, streak, cadence }) {
  const { state, is_day_off: isDayOff, template, reflection_id: reflectionId } = section || {};
  const done = state === 'complete';

  let subtitle = 'Your reflection';
  if (template === null) {
    subtitle = 'No self-reflection template is configured for your role.';
  } else if (done && isDayOff) {
    subtitle = 'Day off recorded';
  } else if (hasPendingSync && !done) {
    subtitle = 'Saved on this device · will sync when connected';
  } else if (hasDraft && !done) {
    subtitle = 'Draft saved';
  }
  if (template !== null && streak > 0) {
    const unit = cadence === 'weekly' ? 'week' : cadence === 'daily' || !cadence ? 'day' : 'period';
    subtitle = `${subtitle} · ${streak}-${unit} streak`;
  }

  let action = null;
  if (template !== null) {
    if (done) {
      action = {
        label: 'Done',
        to: reflectionId ? `/counselor/self-reflection/${reflectionId}/edit` : '/counselor/self-reflection',
      };
    } else if (hasDraft || hasPendingSync) {
      action = { label: 'Continue', to: '/counselor/self-reflection' };
    } else {
      action = { label: 'Start', to: '/counselor/self-reflection' };
    }
  }

  return (
    <Card
      as="section"
      className="rounded-2xl p-4 flex items-center gap-3.5"
      data-testid="counselor-section-self"
      data-state={state}
      aria-labelledby="counselor-self-heading"
    >
      <span className="w-[42px] h-[42px] rounded-xl bg-brand-soft text-brand flex items-center justify-center shrink-0">
        <PenLine className="w-5 h-5" aria-hidden="true" />
      </span>
      <div className="flex-1 min-w-0">
        <h2 id="counselor-self-heading" className="text-[15px] font-bold text-ink">
          How was your day?
        </h2>
        <p className="text-[13px] text-muted" data-testid="counselor-section-self-subtitle">
          {subtitle}
        </p>
      </div>
      {action ? (
        <Link
          to={action.to}
          data-testid="counselor-section-self-action"
          className={
            done
              ? 'inline-flex items-center gap-1.5 min-h-11 px-3.5 rounded-[10px] bg-ok-soft text-ok-ink text-sm font-semibold shrink-0'
              : 'inline-flex items-center min-h-11 px-3.5 rounded-[10px] border border-line text-brand text-sm font-semibold hover:bg-line-soft shrink-0'
          }
        >
          {done ? <Check className="w-4 h-4" strokeWidth={3} aria-hidden="true" /> : null}
          {action.label}
        </Link>
      ) : null}
    </Card>
  );
}

const QUICK_ACTIONS = [
  {
    to: '/counselor/requests/camper-care/new',
    icon: HeartHandshake,
    label: 'Camper care request',
    iconCls: 'text-danger-ink',
    testid: 'counselor-action-camper-care',
  },
  {
    to: '/counselor/requests/maintenance/new',
    icon: Wrench,
    label: 'Maintenance ticket',
    iconCls: 'text-warn-ink',
    testid: 'counselor-action-maintenance',
  },
  {
    to: '/observations',
    icon: MessageSquare,
    label: 'Note about a camper',
    iconCls: 'text-brand',
    testid: 'counselor-action-observation',
  },
  {
    to: '/help',
    icon: Flag,
    label: 'Report an issue',
    iconCls: 'text-ink-2',
    testid: 'counselor-action-report-issue',
  },
];

function QuickActions() {
  return (
    <section
      data-testid="counselor-quick-actions"
      aria-labelledby="counselor-quick-heading"
      className="flex flex-col gap-2"
    >
      <h2 id="counselor-quick-heading" className={SECTION_HEADING}>Quick actions</h2>
      <div className="grid grid-cols-2 gap-2">
        {QUICK_ACTIONS.map(({ to, icon: Icon, label, iconCls, testid }) => (
          <Link
            key={testid}
            to={to}
            data-testid={testid}
            className="flex flex-col gap-2 p-3.5 min-h-[84px] rounded-[14px] bg-white dark:bg-gray-900 border border-line text-ink hover:border-brand/40 transition-colors"
          >
            <Icon className={`w-5 h-5 ${iconCls}`} aria-hidden="true" />
            <span className="text-sm font-semibold">{label}</span>
          </Link>
        ))}
      </div>
    </section>
  );
}

function MyRequests({ viewerRequests }) {
  const recent = [...viewerRequests]
    .sort((a, b) => String(b.submitted_at || '').localeCompare(String(a.submitted_at || '')))
    .slice(0, 2);
  return (
    <Card
      as="section"
      className="rounded-2xl px-4 py-1.5"
      data-testid="counselor-requests-widget"
      aria-labelledby="counselor-requests-heading"
    >
      <div className="flex items-center justify-between pt-2.5 pb-1">
        <h2 id="counselor-requests-heading" className={SECTION_HEADING}>My requests</h2>
        <Link
          to="/counselor/requests"
          className="text-[13px] font-semibold text-brand hover:text-brand-hover min-h-11 inline-flex items-center"
          data-testid="counselor-requests-all"
        >
          All
        </Link>
      </div>
      {recent.length === 0 ? (
        <p className="border-t border-line-soft py-4 text-sm text-muted">
          No open requests. Use a quick action to file one.
        </p>
      ) : (
        <ul>
          {recent.map((request) => (
            <li key={`${request.type}-${request.id}`}>
              <Link
                to={requestDetailPath(request)}
                data-testid={`counselor-request-${request.type}-${request.id}`}
                className="flex items-center gap-3 min-h-[52px] py-1.5 border-t border-line-soft text-ink hover:text-brand"
              >
                <span className="flex-1 min-w-0">
                  <span className="block text-sm font-semibold truncate">{request.title}</span>
                  <span className="block text-xs text-muted truncate">
                    {[
                      request.type === 'camper_care' ? 'Camper care' : 'Maintenance',
                      request.subtitle,
                      formatRelative(request.submitted_at),
                    ].filter(Boolean).join(' · ')}
                  </span>
                </span>
                <Badge
                  tone={REQUEST_STATUS_TONE[request.status] || 'neutral'}
                  className="font-semibold px-2.5 py-1"
                >
                  {request.status_label || request.status}
                </Badge>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}

function MoreLinks() {
  const cls = 'flex-1 flex items-center justify-center gap-2 min-h-11 rounded-[14px] border border-line bg-white dark:bg-gray-900 text-sm font-semibold text-ink hover:border-brand/40';
  return (
    <div className="flex gap-2" data-testid="counselor-work-links">
      <Link to="/tasks" className={cls} data-testid="counselor-action-tasks">
        <ClipboardList className="w-4 h-4 text-brand" aria-hidden="true" />
        My tasks
      </Link>
      <Link to="/my-reflections" className={cls} data-testid="counselor-action-my-reflections">
        <PenLine className="w-4 h-4 text-ok-ink" aria-hidden="true" />
        My reflections
      </Link>
    </div>
  );
}

function BottomTabBar({ campersPath }) {
  const tabs = [
    { label: 'Today', to: '/counselor', icon: Home, active: true },
    { label: 'Campers', to: campersPath, icon: Users },
    { label: 'Requests', to: '/counselor/requests', icon: ClipboardList },
    { label: 'Me', to: '/counselor/self-reflection/history', icon: User },
  ];
  return (
    <nav
      aria-label="Counselor"
      data-testid="counselor-tab-bar"
      className="lg:hidden fixed inset-x-0 bottom-0 z-30 grid grid-cols-4 bg-white dark:bg-gray-900 border-t border-line px-1 pt-1.5 pb-[max(0.5rem,env(safe-area-inset-bottom))]"
    >
      {tabs.map(({ label, to, icon: Icon, active }) => (
        <Link
          key={label}
          to={to}
          aria-current={active ? 'page' : undefined}
          className={`flex flex-col items-center justify-center gap-0.5 min-h-12 text-[11px] font-semibold ${
            active ? 'text-brand' : 'text-muted hover:text-ink'
          }`}
        >
          <Icon className="w-[22px] h-[22px]" aria-hidden="true" />
          {label}
        </Link>
      ))}
    </nav>
  );
}

export default function CounselorMobileDashboard() {
  const [searchParams, setSearchParams] = useSearchParams();
  const dateParam = searchParams.get('date') || '';
  const skipCache = searchParams.get('nocache') === '1';
  const { pending } = useSubmissionQueue();

  const [data, setData] = useState(null);
  const [roster, setRoster] = useState(null);
  const [summary, setSummary] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const load = useCallback(
    async ({ background = false } = {}) => {
      if (background) {
        setRefreshing(true);
      } else {
        setLoading(true);
      }
      setError('');
      const date = dateParam || undefined;
      // Roster and streak are enhancements; the page still renders without them.
      const rosterReq = fetchCamperReflections({ date }).catch(() => null);
      const summaryReq = api
        .get('/api/v1/reflections/my-summary/')
        .then((r) => r.data)
        .catch(() => null);
      try {
        const payload = await fetchCounselorDashboard({
          noCache: background || skipCache,
          date,
        });
        setData(payload);
        setRoster(await rosterReq);
        setSummary(await summaryReq);
      } catch (err) {
        const detail = err?.response?.data?.detail;
        const status = err?.response?.status;
        if (status === 403) {
          setError(typeof detail === 'string' ? detail : 'You do not have access to the counselor dashboard.');
        } else {
          setError(typeof detail === 'string' ? detail : 'Could not load your dashboard.');
        }
      } finally {
        if (background) {
          setRefreshing(false);
        } else {
          setLoading(false);
        }
      }
    },
    [dateParam, skipCache],
  );

  useEffect(() => {
    load();
  }, [load]);

  const isToday = data?.is_today ?? true;

  useEffect(() => {
    if (!data || !isToday) return undefined;
    const id = setInterval(() => {
      load({ background: true });
    }, REFRESH_INTERVAL_MS);
    return () => clearInterval(id);
  }, [data, isToday, load]);

  const selectedDateIso = data?.selected_date || dateParam || data?.today || '';
  const rosterDate = roster?.date || selectedDateIso;

  const pendingCamperIds = useMemo(
    () => new Set(
      pending
        .filter(
          (entry) =>
            entry.kind === SUBMISSION_KIND.CAMPER_REFLECTION
            && entry.metadata?.date === rosterDate,
        )
        .map((entry) => String(entry.metadata?.subjectId)),
    ),
    [pending, rosterDate],
  );

  const handleDateChange = (next) => {
    const params = new URLSearchParams(searchParams);
    if (next && next !== data?.today) params.set('date', next);
    else params.delete('date');
    setSearchParams(params, { replace: true });
  };

  if (loading) {
    return (
      <div
        className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-6xl mx-auto"
        data-testid="counselor-dashboard-loading"
      >
        <p className="text-muted">Loading your dashboard…</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-6xl mx-auto">
        <div
          className="rounded-lg border border-warn-ink/20 bg-warn-soft px-4 py-3 text-sm text-warn-ink"
          role="alert"
          data-testid="counselor-dashboard-error"
        >
          {error}
        </div>
      </div>
    );
  }

  if (!data) return null;

  const { all_set: allSet, sections, program, bunks = [], viewer_requests: viewerRequests = [] } = data;
  const rosterEditable = roster?.editable ?? isToday;
  const rosterBunks = new Map((roster?.bunks || []).map((b) => [b.id, b]));
  const hasSelfDraft = !!(
    selectedDateIso
    && loadCounselorDraft(selfReflectionDraftKey(selectedDateIso))?.answers
  );
  const hasSelfPendingSync = pending.some(
    (entry) =>
      entry.kind === SUBMISSION_KIND.SELF_REFLECTION
      && entry.metadata?.date === selectedDateIso,
  );

  return (
    <div className="px-4 sm:px-6 lg:px-8 pt-4 pb-28 lg:py-8 w-full max-w-6xl mx-auto flex flex-col gap-4">
      <header className="flex flex-col gap-3">
        {program?.name ? (
          <p className="text-[13px] text-ink-2">{program.name}</p>
        ) : null}
        <DayStepper
          selectedIso={selectedDateIso}
          todayIso={data.today}
          onChange={handleDateChange}
          refreshing={refreshing}
        />
      </header>

      {allSet && isToday ? (
        <div
          className="flex items-start gap-3 rounded-2xl bg-ok-soft px-4 py-3"
          data-testid="counselor-all-set"
          role="status"
        >
          <CheckCircle className="h-5 w-5 shrink-0 text-ok-ink mt-0.5" aria-hidden="true" />
          <div>
            <p className="text-sm font-semibold text-ok-ink">
              You&apos;re all set for today — nice work.
            </p>
            <p className="text-xs text-ok-ink/80 mt-0.5">
              Edits stay open until the day rolls over.
            </p>
          </div>
        </div>
      ) : null}

      <div className="grid grid-cols-1 md:grid-cols-[minmax(0,3fr)_minmax(0,2fr)] gap-4 items-start">
        <div className="flex flex-col gap-4" data-testid="counselor-bunks-section">
          {bunks.length === 0 ? (
            <p className="text-sm text-muted rounded-2xl border border-dashed border-line px-4 py-6 text-center">
              You&apos;re not assigned as an author on any bunk yet. Once your camp
              assigns you to a group, it will appear here.
            </p>
          ) : (
            bunks.map((bunk) => {
              const rosterBunk = rosterBunks.get(bunk.id);
              const rows = buildCamperRows(rosterBunk, {
                pendingIds: pendingCamperIds,
                date: rosterDate,
                editable: rosterEditable,
              });
              return (
                <div key={bunk.id} className="flex flex-col gap-4">
                  <BunkHeroCard
                    bunk={bunk}
                    rows={rows}
                    editable={rosterEditable}
                    rosterCovered={rosterBunk?.covered}
                    rosterTotal={rosterBunk?.total}
                  />
                  <CamperList bunk={bunk} rows={rows} showBunkName={bunks.length > 1} />
                </div>
              );
            })
          )}
        </div>

        <div className="flex flex-col gap-4">
          <SelfReflectionCard
            section={sections?.self_reflection}
            hasDraft={hasSelfDraft}
            hasPendingSync={hasSelfPendingSync}
            streak={summary?.streak ?? 0}
            cadence={summary?.template?.cadence}
          />
          <QuickActions />
          <MyRequests viewerRequests={viewerRequests} />
          <MoreLinks />
        </div>
      </div>

      <BottomTabBar campersPath={bunks[0]?.dashboard_path || ROSTER_PATH} />
    </div>
  );
}
