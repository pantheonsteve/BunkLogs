/**
 * Shared Bunk Dashboard — Step 7_7, Story 11.
 *
 * Renders the full per-bunk payload from
 * `GET /api/v1/unit-head/bunks/<id>/`. Built as a presentational
 * component so future role flows (Camper Care, LT, Admin) can drop
 * it in once they expose a parallel endpoint.
 *
 * Section order matches the spec (criterion 1): Header → Help
 * requested → Off-camp today → Bunk concerns → Camper score grid
 * → Today's orders → Specialist reports. Empty sections collapse
 * to a single-line summary (criterion 2). The view is read-only
 * for the UH role (criterion 5).
 */

import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import ScoreGrid from './ScoreGrid';

function CollapsibleSection({
  title,
  emptyMessage,
  isEmpty,
  count,
  children,
  defaultOpen = true,
  testid,
}) {
  const [open, setOpen] = useState(defaultOpen);
  if (isEmpty) {
    return (
      <section
        data-testid={testid}
        data-state="empty"
        className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 px-4 py-3 shadow-sm"
      >
        <div className="text-sm">
          <span className="font-semibold text-gray-900 dark:text-white">{title}</span>{' '}
          <span className="text-gray-500 dark:text-gray-400">— {emptyMessage}</span>
        </div>
      </section>
    );
  }
  return (
    <section
      data-testid={testid}
      data-state="populated"
      className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 px-4 py-3 shadow-sm"
    >
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center justify-between gap-2 text-left"
        aria-expanded={open}
      >
        <h2 className="text-base font-semibold text-gray-900 dark:text-white">
          {title}
          {typeof count === 'number' && (
            <span className="ml-2 text-xs text-gray-500 dark:text-gray-400">({count})</span>
          )}
        </h2>
        <span className="text-gray-400 text-sm" aria-hidden="true">
          {open ? '–' : '+'}
        </span>
      </button>
      {open && <div className="mt-3">{children}</div>}
    </section>
  );
}

function CamperPill({ camper, dashboardPath }) {
  const name = `${camper.preferred_name || camper.first_name} ${camper.last_name?.[0] || ''}.`;
  return (
    <Link
      to={`${dashboardPath}/${camper.id}`}
      data-testid={`camper-pill-${camper.id}`}
      className="inline-flex items-center px-2 py-1 rounded-full bg-gray-100 dark:bg-gray-800 text-sm hover:bg-gray-200 dark:hover:bg-gray-700"
    >
      {name}
    </Link>
  );
}

function BunkConcernsList({ items }) {
  return (
    <ul className="space-y-2">
      {items.map((item) => (
        <li key={item.reflection_id} data-testid={`bunk-concern-${item.reflection_id}`} className="text-sm">
          <p className="font-medium text-gray-900 dark:text-white">
            {item.author}
            {item.author_role && (
              <span className="ml-2 text-xs text-gray-500 dark:text-gray-400">
                ({item.author_role})
              </span>
            )}
          </p>
          {item.note && <p className="text-gray-700 dark:text-gray-200 mt-1">{item.note}</p>}
          {item.open_concern && (
            <p className="text-gray-600 dark:text-gray-300 mt-1 italic">{item.open_concern}</p>
          )}
        </li>
      ))}
    </ul>
  );
}

function OrdersSection({ orders }) {
  const { today = [], carried_over: carriedOver = [], counts = {} } = orders || {};
  const totalCount = (today?.length || 0) + (carriedOver?.length || 0);
  return (
    <CollapsibleSection
      title="Today's orders"
      emptyMessage="none today."
      isEmpty={totalCount === 0}
      count={totalCount}
      testid="section-orders"
    >
      <p className="text-xs text-gray-500 dark:text-gray-400 mb-2">
        {counts.open || 0} open · {counts.in_progress || 0} in progress · {counts.resolved || 0} resolved
      </p>
      {carriedOver.length > 0 && (
        <div className="mb-3">
          <p className="text-xs font-medium text-gray-700 dark:text-gray-300 uppercase tracking-wide mb-1">
            Carried over from prior days
          </p>
          <ul className="space-y-1">
            {carriedOver.map((o) => (
              <OrderRow key={o.id} order={o} />
            ))}
          </ul>
        </div>
      )}
      {today.length > 0 && (
        <ul className="space-y-1">
          {today.map((o) => (
            <OrderRow key={o.id} order={o} />
          ))}
        </ul>
      )}
    </CollapsibleSection>
  );
}

function OrderRow({ order }) {
  const isMaintenance = order.kind === 'maintenance';
  const statusLabel = {
    new: 'New',
    in_progress: 'In progress',
    fulfilled: 'Fulfilled',
    unable_to_fulfill: 'Unable to fulfill',
  }[order.status] || order.status;
  return (
    <li
      data-testid={`order-${order.id}`}
      className="rounded-lg border border-gray-100 dark:border-gray-800 px-3 py-2 text-sm"
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
        <span className="text-xs text-gray-500 dark:text-gray-400">{statusLabel}</span>
      </div>
      <p className="mt-1 text-gray-900 dark:text-white">
        {isMaintenance ? order.location : order.item}
      </p>
      <p className="text-xs text-gray-600 dark:text-gray-400 mt-0.5">
        by {order.submitter || 'unknown'} · {new Date(order.submitted_at).toLocaleString()}
      </p>
    </li>
  );
}

function SpecialistReportsSection({ reports, dashboardPath }) {
  const today = reports?.today || [];
  const recent = reports?.recent || [];
  const sensitiveCounts = reports?.sensitive_counts_by_camper || {};
  const sensitiveTotal = Object.values(sensitiveCounts).reduce((s, n) => s + n, 0);
  const totalVisible = today.length + recent.length;
  const isEmpty = totalVisible === 0 && sensitiveTotal === 0;

  return (
    <CollapsibleSection
      title="Specialist reports"
      emptyMessage="none today."
      isEmpty={isEmpty}
      count={totalVisible || undefined}
      testid="section-specialist-reports"
    >
      {sensitiveTotal > 0 && (
        <p className="text-xs text-gray-500 dark:text-gray-400 mb-2 italic">
          {sensitiveTotal} sensitive note{sensitiveTotal === 1 ? '' : 's'} not visible (Camper Care).
        </p>
      )}
      {today.length > 0 && (
        <div className="mb-3">
          <p className="text-xs font-medium text-gray-700 dark:text-gray-300 uppercase tracking-wide mb-1">
            Today
          </p>
          <ul className="space-y-2">
            {today.map((n) => (
              <SpecialistNote key={n.id} note={n} dashboardPath={dashboardPath} />
            ))}
          </ul>
        </div>
      )}
      {recent.length > 0 && (
        <div>
          <p className="text-xs font-medium text-gray-700 dark:text-gray-300 uppercase tracking-wide mb-1">
            Recent
          </p>
          <ul className="space-y-2">
            {recent.map((n) => (
              <SpecialistNote key={n.id} note={n} dashboardPath={dashboardPath} />
            ))}
          </ul>
        </div>
      )}
    </CollapsibleSection>
  );
}

function SpecialistNote({ note, dashboardPath }) {
  const [expanded, setExpanded] = useState(false);
  const camperName = `${note.subject.preferred_name || note.subject.first_name} ${note.subject.last_name?.[0] || ''}.`;
  return (
    <li data-testid={`specialist-note-${note.id}`} className="text-sm">
      <p>
        <Link
          to={`${dashboardPath}/${note.subject.id}`}
          className="font-medium hover:underline text-blue-700 dark:text-blue-300"
        >
          {camperName}
        </Link>{' '}
        <span className="text-xs text-gray-500 dark:text-gray-400">
          · {note.author} · {new Date(note.created_at).toLocaleDateString()}
        </span>
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

export default function BunkDashboard({
  data,
  selectedDate,
  onDateChange,
  camperDashboardPath = '/unit-head/campers',
  backTo = '/unit-head',
}) {
  const today = data?.header?.today;
  const date = data?.header?.date;
  const helpRequested = data?.help_requested || [];
  const offCamp = data?.off_camp || [];
  const bunkConcerns = data?.bunk_concerns || [];
  const scoreGrid = useMemo(() => data?.score_grid || { columns: [], rows: [] }, [data]);

  return (
    <div data-testid="bunk-dashboard" className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-[96rem] mx-auto space-y-4">
      <header className="space-y-2">
        <Link
          to={backTo}
          className="text-sm text-blue-700 dark:text-blue-300 hover:underline"
        >
          ← Back
        </Link>
        <div>
          <h1 className="text-2xl font-semibold text-gray-900 dark:text-white">
            {data?.header?.bunk?.name}
          </h1>
          {data?.header?.bunk?.unit_name && (
            <p className="text-sm text-gray-600 dark:text-gray-400">
              {data.header.bunk.unit_name}
            </p>
          )}
        </div>
        <div className="flex items-center gap-3 flex-wrap">
          <label className="text-sm text-gray-700 dark:text-gray-200 flex items-center gap-2">
            <span>Date:</span>
            <input
              type="date"
              value={selectedDate || date || ''}
              max={today}
              onChange={(e) => onDateChange?.(e.target.value)}
              data-testid="bunk-dashboard-date"
              className="rounded border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 px-2 py-1 text-sm"
            />
          </label>
          {data?.header?.counselor_names?.length > 0 && (
            <p className="text-xs text-gray-600 dark:text-gray-400">
              Counselors: {data.header.counselor_names.join(' · ')}
            </p>
          )}
        </div>
      </header>

      <CollapsibleSection
        title="Help requested"
        emptyMessage="none today."
        isEmpty={helpRequested.length === 0}
        count={helpRequested.length}
        testid="section-help-requested"
      >
        <div className="flex flex-wrap gap-2">
          {helpRequested.map((c) => (
            <CamperPill key={c.id} camper={c} dashboardPath={camperDashboardPath} />
          ))}
        </div>
      </CollapsibleSection>

      <CollapsibleSection
        title="Off-camp today"
        emptyMessage="none today."
        isEmpty={offCamp.length === 0}
        count={offCamp.length}
        testid="section-off-camp"
      >
        <div className="flex flex-wrap gap-2">
          {offCamp.map((c) => (
            <CamperPill key={c.id} camper={c} dashboardPath={camperDashboardPath} />
          ))}
        </div>
      </CollapsibleSection>

      <CollapsibleSection
        title="Bunk concerns"
        emptyMessage="none today."
        isEmpty={bunkConcerns.length === 0}
        count={bunkConcerns.length}
        testid="section-bunk-concerns"
      >
        <BunkConcernsList items={bunkConcerns} />
      </CollapsibleSection>

      <CollapsibleSection
        title="Camper score grid"
        emptyMessage="no reflections submitted today."
        isEmpty={scoreGrid.rows.length === 0 && scoreGrid.columns.length === 0}
        testid="section-score-grid"
      >
        <ScoreGrid
          columns={scoreGrid.columns}
          rows={scoreGrid.rows}
          camperLinkPrefix={camperDashboardPath}
        />
      </CollapsibleSection>

      <OrdersSection orders={data?.orders} />
      <SpecialistReportsSection
        reports={data?.specialist_reports}
        dashboardPath={camperDashboardPath}
      />
    </div>
  );
}
