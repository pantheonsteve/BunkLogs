/**
 * Shared Bunk Dashboard — Step 7_7 (redesigned).
 *
 * Renders the full per-bunk payload returned by the unified
 * `GET /api/v1/dashboards/group/<id>/` endpoint when `group_type='bunk'`.
 * Counselor, Camper Care, Unit Head, Leadership Team, and Admin all read
 * here via `GroupDashboardPage`, which resolves the caller's role from
 * `role_context` and feeds the right `backTo` / camper-dashboard paths.
 *
 * Layout mirrors the production bunk page: header (name, date, counselors,
 * completion, view-only) → three attention summary cards (Not on Camp /
 * Unit Head Help / Camper Care Help) → Camper Daily Scores grid → Orders &
 * Tickets → Notes (single chronological stream). On the unified group
 * dashboard page the score grid is omitted and orders/notes render after
 * template responses instead (see ``GroupDashboardPage``).
 */

import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { groupDashboardLink, observationThreadLink, profileLink } from '../utils/dashboardLinks';
import { sensitivityAudience } from '../api/observations';
import ScoreGrid from './ScoreGrid';
import CounselorSelfReflectionsList, { counselorSelfReflectionSummary } from './CounselorSelfReflectionsList';

// Field types kept as grid columns. Triage single_choice/yes-no fields
// (on-camp, UH/CC help requests) are surfaced as cards + the On Camp column.
const GRID_COLUMN_TYPES = new Set([
  'single_rating',
  'rating_group',
  'textarea',
  'text',
]);

function camperDisplayName(c) {
  if (!c) return '';
  const first = c.preferred_name || c.first_name || '';
  const lastInitial = (c.last_name || '').slice(0, 1);
  return lastInitial ? `${first} ${lastInitial}.` : first;
}

function SectionCard({ title, count, action, children, testid, state = 'populated' }) {
  return (
    <section
      data-testid={testid}
      data-state={state}
      className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 shadow-sm"
    >
      <div className="flex items-center justify-between gap-2 px-4 sm:px-5 pt-4 pb-3">
        <h2 className="text-base font-semibold text-gray-900 dark:text-white">
          {title}
          {(typeof count === 'number' || typeof count === 'string') && (
            <span className="ml-2 text-xs font-medium text-gray-500 dark:text-gray-400">
              {count}
            </span>
          )}
        </h2>
        {action}
      </div>
      <div className="px-4 sm:px-5 pb-5">{children}</div>
    </section>
  );
}

const SUMMARY_TONES = {
  slate: { dot: 'bg-slate-400', badge: 'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-200' },
  amber: { dot: 'bg-amber-500', badge: 'bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-200' },
  rose: { dot: 'bg-rose-500', badge: 'bg-rose-100 text-rose-800 dark:bg-rose-900/40 dark:text-rose-200' },
};

function SummaryCard({ title, tone, people, bunkLabel, toProfile, testid }) {
  const t = SUMMARY_TONES[tone] || SUMMARY_TONES.slate;
  return (
    <div
      data-testid={testid}
      data-count={people.length}
      className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 shadow-sm p-4"
    >
      <div className="flex items-center justify-between gap-2 mb-2">
        <span className="flex items-center gap-2 text-sm font-bold text-gray-900 dark:text-white">
          <span className={`h-2.5 w-2.5 rounded-full ${t.dot}`} aria-hidden="true" />
          {title}
        </span>
        <span className={`text-xs font-bold rounded-full px-2 py-0.5 ${t.badge}`}>
          {people.length}
        </span>
      </div>
      {people.length === 0 ? (
        <p className="text-xs text-gray-400 dark:text-gray-500 pt-1">None today.</p>
      ) : (
        <ul className="divide-y divide-gray-100 dark:divide-gray-800">
          {people.map((p) => (
            <li key={p.id} className="flex items-center justify-between gap-2 py-1.5 text-sm">
              <Link
                to={toProfile(p.id)}
                className="font-medium text-gray-900 dark:text-white hover:text-blue-700 dark:hover:text-blue-300 hover:underline"
              >
                {p.name}
              </Link>
              {bunkLabel && (
                <span className="text-xs text-gray-500 dark:text-gray-400 shrink-0">{bunkLabel}</span>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function CounselorSelfReflectionsSection({ entries }) {
  const list = entries || [];
  if (list.length === 0) return null;
  const { submitted, expected } = counselorSelfReflectionSummary(list);
  return (
    <SectionCard
      title="Counselor reflections"
      count={`${submitted}/${expected}`}
      testid="section-counselor-self-reflections"
      state={submitted === 0 ? 'empty' : 'populated'}
    >
      <CounselorSelfReflectionsList entries={list} />
    </SectionCard>
  );
}

const STATUS_LABELS = {
  new: 'New',
  in_progress: 'In progress',
  fulfilled: 'Fulfilled',
  unable_to_fulfill: 'Unable to fulfill',
};

const STATUS_TONES = {
  new: 'text-amber-700 dark:text-amber-300',
  in_progress: 'text-blue-700 dark:text-blue-300',
  fulfilled: 'text-green-700 dark:text-green-300',
  unable_to_fulfill: 'text-gray-500 dark:text-gray-400',
};

function OrderRow({ order }) {
  const isMaintenance = order.kind === 'maintenance';
  return (
    <li
      data-testid={`order-${order.id}`}
      className="rounded-lg border border-gray-100 dark:border-gray-800 px-3 py-2.5"
    >
      <div className="flex items-center justify-between gap-2">
        <span
          className={`inline-block text-[10px] uppercase tracking-wide font-bold px-1.5 py-0.5 rounded ${
            isMaintenance
              ? 'bg-orange-100 text-orange-800 dark:bg-orange-900/40 dark:text-orange-200'
              : 'bg-purple-100 text-purple-800 dark:bg-purple-900/40 dark:text-purple-200'
          }`}
        >
          {isMaintenance ? 'Maintenance' : 'Camper care'}
        </span>
        <span className={`text-xs font-semibold ${STATUS_TONES[order.status] || 'text-gray-500'}`}>
          {STATUS_LABELS[order.status] || order.status}
        </span>
      </div>
      <p className="mt-1.5 text-sm font-medium text-gray-900 dark:text-white">
        {isMaintenance ? order.location : order.item}
      </p>
      <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
        by {order.submitter || 'unknown'}
        {order.submitted_at ? ` · ${new Date(order.submitted_at).toLocaleString()}` : ''}
      </p>
    </li>
  );
}

function OrdersSection({ orders }) {
  const { today = [], carried_over: carriedOver = [], counts = {} } = orders || {};
  const total = today.length + carriedOver.length;
  return (
    <SectionCard
      title="Orders & Tickets"
      count={total}
      testid="section-orders"
      state={total === 0 ? 'empty' : 'populated'}
    >
      {total === 0 ? (
        <p className="text-sm text-gray-500 dark:text-gray-400">None today.</p>
      ) : (
        <>
          <p className="text-xs text-gray-500 dark:text-gray-400 mb-3">
            {counts.open || 0} open · {counts.in_progress || 0} in progress ·{' '}
            {counts.resolved || 0} resolved today
          </p>
          {carriedOver.length > 0 && (
            <div className="mb-4">
              <p className="text-[11px] font-semibold uppercase tracking-wide text-gray-400 dark:text-gray-500 mb-2">
                Carried over from prior days
              </p>
              <ul className="space-y-2">
                {carriedOver.map((o) => (
                  <OrderRow key={o.id} order={o} />
                ))}
              </ul>
            </div>
          )}
          {today.length > 0 && (
            <div>
              {carriedOver.length > 0 && (
                <p className="text-[11px] font-semibold uppercase tracking-wide text-gray-400 dark:text-gray-500 mb-2">
                  Today
                </p>
              )}
              <ul className="space-y-2">
                {today.map((o) => (
                  <OrderRow key={o.id} order={o} />
                ))}
              </ul>
            </div>
          )}
        </>
      )}
    </SectionCard>
  );
}

const SOURCE_TAG = {
  bunk_concern: {
    label: 'Bunk concern',
    cls: 'bg-amber-50 text-amber-800 dark:bg-amber-900/30 dark:text-amber-200',
  },
  specialist: {
    label: 'Specialist report',
    cls: 'bg-indigo-50 text-indigo-800 dark:bg-indigo-900/30 dark:text-indigo-200',
  },
};

function formatRoleLabel(role) {
  if (!role) return null;
  return String(role).replace(/_/g, ' ');
}

function streamSortTime(iso) {
  if (!iso) return 0;
  const t = new Date(iso).getTime();
  return Number.isNaN(t) ? 0 : t;
}

function buildNotesStream({
  bunkConcerns,
  specialistReports,
  observations,
  observationReturnTo = null,
  observationReturnLabel = null,
}) {
  const today = specialistReports?.today || [];
  const recent = specialistReports?.recent || [];
  const items = [];

  for (const concern of bunkConcerns || []) {
    const body = [concern.note, concern.open_concern].filter(Boolean).join('\n\n');
    if (!body) continue;
    items.push({
      key: `concern-${concern.reflection_id}`,
      kind: 'bunk_concern',
      sortAt: concern.submitted_at,
      author: concern.author,
      authorRole: concern.author_role,
      body,
      testid: `bunk-concern-${concern.reflection_id}`,
    });
  }

  for (const obs of observations || []) {
    if (!obs.body_preview) continue;
    items.push({
      key: `obs-${obs.id}`,
      kind: 'observation',
      sortAt: obs.observed_at,
      author: obs.author_name,
      body: obs.body_preview,
      sensitivity: obs.sensitivity,
      context: obs.context,
      subjects: obs.subjects,
      href: observationReturnTo
        ? observationThreadLink(obs.id, observationReturnTo, {
          contextLabel: observationReturnLabel,
        })
        : `/observations/${obs.id}`,
      testid: `bunk-observation-${obs.id}`,
    });
  }

  for (const note of [...today, ...recent]) {
    items.push({
      key: `spec-${note.id}`,
      kind: 'specialist',
      sortAt: note.created_at,
      author: note.author,
      subject: note.subject,
      body: note.body,
      preview: note.preview,
      isLong: note.is_long,
      testid: `specialist-note-${note.id}`,
    });
  }

  items.sort((a, b) => streamSortTime(b.sortAt) - streamSortTime(a.sortAt));
  return items;
}

function NoteStreamMeta({ item }) {
  const tags = [];
  if (item.kind === 'observation') {
    if (item.sensitivity) {
      tags.push(
        <span
          key="sensitivity"
          className="text-xs rounded-full bg-amber-50 dark:bg-amber-900/20 px-2 py-0.5 text-amber-800 dark:text-amber-200"
        >
          {sensitivityAudience(item.sensitivity)}
        </span>,
      );
    }
    if (item.context) {
      tags.push(
        <span key="context" className="text-xs text-gray-500 dark:text-gray-400">
          {item.context}
        </span>,
      );
    }
  } else {
    const meta = SOURCE_TAG[item.kind];
    if (meta) {
      tags.push(
        <span
          key="source"
          className={`text-xs rounded-full px-2 py-0.5 font-medium ${meta.cls}`}
        >
          {meta.label}
        </span>,
      );
    }
    if (item.authorRole) {
      tags.push(
        <span key="role" className="text-xs text-gray-500 dark:text-gray-400 capitalize">
          {formatRoleLabel(item.authorRole)}
        </span>,
      );
    }
  }

  return (
    <div className="flex flex-wrap items-center gap-2 min-w-0">
      {tags}
      {item.author && (
        <span className="text-sm font-semibold text-gray-900 dark:text-white truncate">
          {item.author}
        </span>
      )}
      {item.sortAt && (
        <span className="text-xs text-gray-400 dark:text-gray-500 ml-auto shrink-0">
          {new Date(item.sortAt).toLocaleString()}
        </span>
      )}
    </div>
  );
}

function NoteStreamItem({ item, toProfile }) {
  const [expanded, setExpanded] = useState(false);
  const subjectLabel = (item.subjects || []).map((s) => s.name).filter(Boolean).join(', ');
  const bodyText = item.kind === 'specialist' && item.isLong && !expanded
    ? item.preview
    : item.body;

  const content = (
    <>
      <NoteStreamMeta item={item} />
      {item.kind === 'specialist' && item.subject?.id && (
        <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
          re:{' '}
          <Link
            to={toProfile(item.subject.id)}
            className="font-medium text-blue-700 dark:text-blue-300 hover:underline"
          >
            {camperDisplayName(item.subject)}
          </Link>
        </p>
      )}
      {subjectLabel && item.kind === 'observation' && (
        <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
          re: {subjectLabel}
        </p>
      )}
      <p className="mt-1.5 text-sm text-gray-700 dark:text-gray-200 whitespace-pre-wrap">
        {bodyText}
      </p>
      {item.kind === 'specialist' && item.isLong && (
        <button
          type="button"
          onClick={() => setExpanded((v) => !v)}
          className="text-xs text-blue-700 dark:text-blue-300 hover:underline mt-1"
        >
          {expanded ? 'Show less' : 'Read more'}
        </button>
      )}
    </>
  );

  return (
    <li
      data-testid={item.testid}
      data-kind={item.kind}
      className="rounded-lg border border-gray-200 dark:border-gray-700 px-3 py-2.5 text-sm hover:bg-gray-50 dark:hover:bg-gray-800/40"
    >
      {item.href ? (
        <Link to={item.href} className="block">
          {content}
        </Link>
      ) : content}
    </li>
  );
}

function NotesSection({
  bunkConcerns,
  specialistReports,
  observations = [],
  toProfile,
  notesLink,
  observationReturnTo = null,
  observationReturnLabel = null,
}) {
  const sensitiveCounts = specialistReports?.sensitive_counts_by_camper || {};
  const sensitiveTotal = Object.values(sensitiveCounts).reduce((s, n) => s + n, 0);
  const stream = useMemo(
    () => buildNotesStream({
      bunkConcerns,
      specialistReports,
      observations,
      observationReturnTo,
      observationReturnLabel,
    }),
    [bunkConcerns, specialistReports, observations, observationReturnTo, observationReturnLabel],
  );
  const isEmpty = stream.length === 0 && sensitiveTotal === 0;

  return (
    <SectionCard
      title="Notes"
      testid="section-notes"
      state={isEmpty ? 'empty' : 'populated'}
      action={
        notesLink ? (
          <Link to={notesLink} className="text-xs font-semibold text-blue-700 dark:text-blue-300 hover:underline">
            Open notes →
          </Link>
        ) : undefined
      }
    >
      {isEmpty ? (
        <p className="text-sm text-gray-500 dark:text-gray-400">No notes today.</p>
      ) : (
        <>
          <ul className="space-y-2.5" data-testid="notes-stream">
            {stream.map((item) => (
              <NoteStreamItem key={item.key} item={item} toProfile={toProfile} />
            ))}
          </ul>
          {sensitiveTotal > 0 && (
            <p className="text-xs text-gray-500 dark:text-gray-400 italic mt-3">
              {sensitiveTotal} sensitive note{sensitiveTotal === 1 ? '' : 's'} not visible
              (Camper Care).
            </p>
          )}
        </>
      )}
    </SectionCard>
  );
}

function resolveObservationReturn(data, profileLinkContext) {
  if (!profileLinkContext?.groupId) {
    return { observationReturnTo: null, observationReturnLabel: null };
  }
  return {
    observationReturnTo: groupDashboardLink(profileLinkContext.groupId, {
      date: profileLinkContext.date || data?.header?.date,
    }),
    observationReturnLabel: data?.header?.bunk?.name || 'Group dashboard',
  };
}

export function BunkDashboardOrdersAndNotes({
  data,
  camperDashboardPath = '/unit-head/campers',
  profileLinkContext = null,
  notesLink = '/observations',
}) {
  const toProfile = (id) => (
    profileLinkContext
      ? profileLink(id, profileLinkContext)
      : `${camperDashboardPath}/${id}`
  );
  const { observationReturnTo, observationReturnLabel } = resolveObservationReturn(
    data,
    profileLinkContext,
  );
  return (
    <>
      <OrdersSection orders={data?.orders} />
      <NotesSection
        bunkConcerns={data?.bunk_concerns || []}
        specialistReports={data?.specialist_reports}
        observations={data?.observations || []}
        toProfile={toProfile}
        notesLink={notesLink}
        observationReturnTo={observationReturnTo}
        observationReturnLabel={observationReturnLabel}
      />
    </>
  );
}

export default function BunkDashboard({
  data,
  selectedDate,
  onDateChange,
  camperDashboardPath = '/unit-head/campers',
  profileLinkContext = null,
  backTo = '/unit-head',
  notesLink = '/observations',
  programName,
  showScoreGrid = true,
  showOrders = true,
  showNotes = true,
}) {
  const toProfile = (id) => (
    profileLinkContext
      ? profileLink(id, profileLinkContext)
      : `${camperDashboardPath}/${id}`
  );
  const { observationReturnTo, observationReturnLabel } = resolveObservationReturn(
    data,
    profileLinkContext,
  );
  const today = data?.header?.today;
  const date = data?.header?.date;
  const resolvedProgramName = programName ?? data?.header?.program_name;
  const helpRequested = data?.help_requested || [];
  const camperCareHelpRequested = data?.camper_care_help_requested || [];
  const offCamp = data?.off_camp || [];
  const bunkConcerns = data?.bunk_concerns || [];
  const orders = data?.orders;
  const scoreGrid = useMemo(() => data?.score_grid || { columns: [], rows: [] }, [data]);

  const gridColumns = useMemo(
    () => (scoreGrid.columns || []).filter((c) => GRID_COLUMN_TYPES.has(c.field_type)),
    [scoreGrid],
  );

  const offCampIds = useMemo(() => new Set(offCamp.map((c) => c.id)), [offCamp]);

  // Completion derived from the score-grid rows (one row per rostered camper;
  // `reflection_id` is null until submitted). Off-camp campers aren't expected.
  const completion = useMemo(() => {
    const rows = scoreGrid.rows || [];
    const expectedRows = rows.filter((r) => !offCampIds.has(r.camper?.id));
    const submitted = expectedRows.filter((r) => r.reflection_id != null).length;
    return { submitted, expected: expectedRows.length };
  }, [scoreGrid, offCampIds]);

  const notOnCamp = useMemo(
    () => offCamp.map((c) => ({ id: c.id, name: camperDisplayName(c) })),
    [offCamp],
  );
  const uhHelp = useMemo(
    () => helpRequested.map((c) => ({ id: c.id, name: camperDisplayName(c) })),
    [helpRequested],
  );
  const camperCareHelp = useMemo(
    () => camperCareHelpRequested.map((c) => ({ id: c.id, name: camperDisplayName(c) })),
    [camperCareHelpRequested],
  );

  return (
    <div
      data-testid="bunk-dashboard"
      className={`px-4 sm:px-6 lg:px-8 pt-8 ${showOrders || showNotes ? 'pb-8' : 'pb-0'} w-full max-w-[80rem] mx-auto space-y-5`}
    >
      <header className="space-y-3">
        <Link to={backTo} className="text-sm font-semibold text-blue-700 dark:text-blue-300 hover:underline">
          ← Back
        </Link>
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h1 className="text-2xl font-semibold text-gray-900 dark:text-white">
              {data?.header?.bunk?.name}
            </h1>
            {resolvedProgramName && (
              <p className="text-sm font-medium text-gray-700 dark:text-gray-300">
                {resolvedProgramName}
              </p>
            )}
            {data?.header?.bunk?.unit_name && (
              <p className="text-sm text-gray-600 dark:text-gray-400">
                {data.header.bunk.unit_name}
              </p>
            )}
          </div>
          <div className="flex items-center gap-2 flex-wrap">
            {completion.expected > 0 && (
              <span
                data-testid="bunk-completion"
                className="inline-flex items-center gap-1.5 rounded-full border border-green-200 bg-green-50 dark:border-green-900 dark:bg-green-900/30 px-3 py-1 text-xs font-semibold text-green-700 dark:text-green-300"
              >
                {completion.submitted} of {completion.expected} reflections submitted
              </span>
            )}
            <span className="inline-flex items-center gap-1.5 rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 px-3 py-1 text-xs font-semibold text-gray-600 dark:text-gray-300">
              View only
            </span>
          </div>
        </div>
        <div className="flex items-center gap-4 flex-wrap">
          <label className="text-sm text-gray-700 dark:text-gray-200 flex items-center gap-2">
            <span>Date:</span>
            <input
              type="date"
              value={selectedDate || date || ''}
              max={today}
              onChange={(e) => onDateChange?.(e.target.value)}
              data-testid="bunk-dashboard-date"
              className="rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 px-2.5 py-1.5 text-sm"
            />
          </label>
          {data?.header?.counselor_names?.length > 0 && (
            <p className="text-xs text-gray-500 dark:text-gray-400">
              Counselors: {data.header.counselor_names.join(' · ')}
            </p>
          )}
        </div>
      </header>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        <SummaryCard
          title="Not on Camp"
          tone="slate"
          people={notOnCamp}
          bunkLabel={data?.header?.bunk?.name}
          toProfile={toProfile}
          testid="card-not-on-camp"
        />
        <SummaryCard
          title="Unit Head Help Requested"
          tone="amber"
          people={uhHelp}
          bunkLabel={data?.header?.bunk?.name}
          toProfile={toProfile}
          testid="card-uh-help"
        />
        <SummaryCard
          title="Camper Care Help"
          tone="rose"
          people={camperCareHelp}
          bunkLabel={data?.header?.bunk?.name}
          toProfile={toProfile}
          testid="card-cc-help"
        />
      </div>

      <CounselorSelfReflectionsSection entries={data?.counselor_self_reflections} />

      {showScoreGrid && (
        <SectionCard
          title="Camper Daily Scores"
          testid="section-score-grid"
          action={
            <span className="text-xs font-medium text-gray-500 dark:text-gray-400">
              {scoreGrid.rows?.length || 0} campers
            </span>
          }
        >
          <ScoreGrid
            columns={gridColumns}
            rows={scoreGrid.rows}
            camperLinkFor={toProfile}
            offCampIds={offCampIds}
          />
        </SectionCard>
      )}

      {showOrders && <OrdersSection orders={orders} />}
      {showNotes && (
        <NotesSection
          bunkConcerns={bunkConcerns}
          specialistReports={data?.specialist_reports}
          observations={data?.observations || []}
          toProfile={toProfile}
          notesLink={notesLink}
          observationReturnTo={observationReturnTo}
          observationReturnLabel={observationReturnLabel}
        />
      )}
    </div>
  );
}
