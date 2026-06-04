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
 * Tickets → Notes (bunk concerns + specialist reports). On the unified group
 * dashboard page the score grid is omitted and orders/notes render after
 * template responses instead (see ``GroupDashboardPage``).
 */

import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { profileLink } from '../utils/dashboardLinks';
import ScoreGrid from './ScoreGrid';

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
          {typeof count === 'number' && (
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

function SpecialistNote({ note, toProfile }) {
  const [expanded, setExpanded] = useState(false);
  return (
    <li data-testid={`specialist-note-${note.id}`} className="text-sm">
      <p className="text-xs text-gray-500 dark:text-gray-400">
        <Link
          to={toProfile(note.subject.id)}
          className="font-semibold text-blue-700 dark:text-blue-300 hover:underline"
        >
          {camperDisplayName(note.subject)}
        </Link>{' '}
        · {note.author} · {new Date(note.created_at).toLocaleDateString()}
      </p>
      <p className="mt-1 text-gray-800 dark:text-gray-200 whitespace-pre-wrap">
        {expanded || !note.is_long ? note.body : note.preview}
      </p>
      {note.is_long && (
        <button
          type="button"
          onClick={() => setExpanded((v) => !v)}
          className="text-xs text-blue-700 dark:text-blue-300 hover:underline mt-1"
        >
          {expanded ? 'Show less' : 'Read more'}
        </button>
      )}
    </li>
  );
}

function ObservationRow({ item }) {
  const subjectLabel = (item.subjects || []).map((s) => s.name).filter(Boolean).join(', ');
  return (
    <li
      data-testid={`bunk-observation-${item.id}`}
      className="rounded-lg border border-gray-200 dark:border-gray-700 px-3 py-2 text-sm hover:bg-gray-50 dark:hover:bg-gray-800/50"
    >
      <Link to={`/observations/${item.id}`} className="block">
        <div className="flex flex-wrap items-center gap-2 mb-1">
          {item.author_name && (
            <span className="font-semibold text-gray-900 dark:text-white">{item.author_name}</span>
          )}
          {item.context && (
            <span className="text-xs text-gray-400">{item.context}</span>
          )}
          {subjectLabel && (
            <span className="text-xs text-gray-500 dark:text-gray-400 ml-auto truncate max-w-[50%]">
              re: {subjectLabel}
            </span>
          )}
        </div>
        <p className="text-gray-700 dark:text-gray-200">{item.body_preview}</p>
      </Link>
    </li>
  );
}

function NotesSection({ bunkConcerns, specialistReports, observations = [], toProfile, notesLink }) {
  const today = specialistReports?.today || [];
  const recent = specialistReports?.recent || [];
  const sensitiveCounts = specialistReports?.sensitive_counts_by_camper || {};
  const sensitiveTotal = Object.values(sensitiveCounts).reduce((s, n) => s + n, 0);
  const specialistNotes = [...today, ...recent];
  const dayObservations = observations || [];
  const isEmpty =
    bunkConcerns.length === 0
    && specialistNotes.length === 0
    && sensitiveTotal === 0
    && dayObservations.length === 0;

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
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-wide text-gray-400 dark:text-gray-500 mb-2">
              Bunk concerns
            </p>
            {bunkConcerns.length === 0 ? (
              <p className="text-sm text-gray-400 dark:text-gray-500">None today.</p>
            ) : (
              <ul className="space-y-2.5">
                {bunkConcerns.map((item) => (
                  <li
                    key={item.reflection_id}
                    data-testid={`bunk-concern-${item.reflection_id}`}
                    className="rounded-lg border-l-2 border-amber-400 bg-amber-50 dark:bg-amber-900/20 px-3 py-2 text-sm"
                  >
                    <p className="font-semibold text-gray-900 dark:text-white">
                      {item.author}
                      {item.author_role && (
                        <span className="ml-1.5 text-xs font-normal text-gray-500 dark:text-gray-400">
                          · {item.author_role}
                        </span>
                      )}
                    </p>
                    {item.note && (
                      <p className="text-gray-700 dark:text-gray-200 mt-1">{item.note}</p>
                    )}
                    {item.open_concern && (
                      <p className="text-gray-600 dark:text-gray-300 mt-1 italic">
                        {item.open_concern}
                      </p>
                    )}
                  </li>
                ))}
              </ul>
            )}
          </div>
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-wide text-gray-400 dark:text-gray-500 mb-2">
              Observations
            </p>
            {dayObservations.length === 0 ? (
              <p className="text-sm text-gray-400 dark:text-gray-500">None on this date.</p>
            ) : (
              <ul className="space-y-2.5" data-testid="bunk-observations-list">
                {dayObservations.map((o) => (
                  <ObservationRow key={o.id} item={o} />
                ))}
              </ul>
            )}
          </div>
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-wide text-gray-400 dark:text-gray-500 mb-2">
              Specialist reports &amp; recent notes
            </p>
            {specialistNotes.length === 0 && sensitiveTotal === 0 ? (
              <p className="text-sm text-gray-400 dark:text-gray-500">None today.</p>
            ) : (
              <ul className="space-y-3">
                {specialistNotes.map((n) => (
                  <SpecialistNote key={n.id} note={n} toProfile={toProfile} />
                ))}
                {sensitiveTotal > 0 && (
                  <li className="text-xs text-gray-500 dark:text-gray-400 italic">
                    {sensitiveTotal} sensitive note{sensitiveTotal === 1 ? '' : 's'} not visible
                    (Camper Care).
                  </li>
                )}
              </ul>
            )}
          </div>
        </div>
      )}
    </SectionCard>
  );
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
  return (
    <>
      <OrdersSection orders={data?.orders} />
      <NotesSection
        bunkConcerns={data?.bunk_concerns || []}
        specialistReports={data?.specialist_reports}
        observations={data?.observations || []}
        toProfile={toProfile}
        notesLink={notesLink}
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
        />
      )}
    </div>
  );
}
