/**
 * Unit-level rollup dashboard.
 *
 * Renders the payload from `GET /api/v1/dashboards/group/<unit_id>/`
 * (group_type='unit'): a per-bunk completion + badge summary, plus
 * union sections for help-requested and off-camp campers across all
 * child bunks. Bunk rows link to `/dashboards/group/{bunkId}` so the
 * drill-down stays on the same universal URL.
 */

import { Link } from 'react-router-dom';

const BADGE_LABEL = Object.freeze({
  help_requested: 'help requested',
  bunk_concerns: 'bunk concerns',
  off_camp: 'off-camp',
  low_completion: 'low completion',
  cc_flagged: 'CC flagged',
  cc_pending_order: 'CC order pending',
});

function BadgePill({ code }) {
  return (
    <span
      data-testid={`badge-${code}`}
      className="inline-block text-[10px] uppercase tracking-wide font-bold px-1.5 py-0.5 rounded bg-amber-100 text-amber-900 dark:bg-amber-900/40 dark:text-amber-100 mr-1"
    >
      {BADGE_LABEL[code] || code}
    </span>
  );
}

function CamperBrief({ camper }) {
  const name = `${camper.preferred_name || camper.first_name} ${(camper.last_name || '')[0] || ''}.`;
  return (
    <li
      data-testid={`group-camper-${camper.id}`}
      className="inline-flex items-center px-2 py-1 rounded-full bg-gray-100 dark:bg-gray-800 text-sm mr-2 mb-2"
    >
      {name}
    </li>
  );
}

function CompletionBar({ submitted, expected }) {
  if (!expected) {
    return <span className="text-xs text-gray-500 dark:text-gray-400">no campers expected</span>;
  }
  const ratio = Math.min(1, submitted / expected);
  return (
    <div className="flex items-center gap-2">
      <div className="h-1.5 w-24 rounded-full bg-gray-200 dark:bg-gray-700 overflow-hidden">
        <div
          className="h-full bg-emerald-500"
          style={{ width: `${Math.round(ratio * 100)}%` }}
        />
      </div>
      <span className="text-xs text-gray-700 dark:text-gray-300 tabular-nums">
        {submitted}/{expected}
      </span>
    </div>
  );
}

export default function UnitDashboard({ data, selectedDate, onDateChange, backTo = '/dashboards' }) {
  const group = data?.header?.group || {};
  const summary = data?.summary || {};
  const bunks = data?.bunks || [];
  const helpRequested = data?.help_requested || [];
  const offCamp = data?.off_camp || [];
  const bunkConcerns = data?.bunk_concerns || [];

  return (
    <div
      data-testid="group-dashboard-unit"
      className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-[96rem] mx-auto space-y-4"
    >
      <header className="space-y-2">
        <Link
          to={backTo}
          className="text-sm text-blue-700 dark:text-blue-300 hover:underline"
        >
          ← Back
        </Link>
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <h1 className="text-2xl font-semibold text-gray-900 dark:text-white">
              {group.name || 'Unit'}
            </h1>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              Unit dashboard · {summary.bunk_count || 0} bunks
            </p>
          </div>
          <label className="text-sm text-gray-700 dark:text-gray-200">
            Date{' '}
            <input
              type="date"
              value={selectedDate || ''}
              onChange={(e) => onDateChange?.(e.target.value)}
              className="ml-2 rounded border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 px-2 py-1"
            />
          </label>
        </div>
      </header>

      <section
        data-testid="unit-summary-tiles"
        className="grid grid-cols-2 md:grid-cols-4 gap-3"
      >
        <Tile label="Submitted" value={`${summary.submitted ?? 0}/${summary.expected ?? 0}`} />
        <Tile label="Off camp" value={summary.off_camp ?? 0} />
        <Tile label="Help requested" value={summary.help_requested_count ?? 0} />
        <Tile label="Attention" value={summary.attention_bunk_count ?? 0} />
      </section>

      <section
        data-testid="section-bunks"
        className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 px-4 py-3 shadow-sm"
      >
        <h2 className="text-base font-semibold text-gray-900 dark:text-white mb-2">
          Bunks <span className="ml-2 text-xs text-gray-500 dark:text-gray-400">({bunks.length})</span>
        </h2>
        {bunks.length === 0 ? (
          <p className="text-sm text-gray-500 dark:text-gray-400">no active bunks in this unit.</p>
        ) : (
          <ul className="divide-y divide-gray-100 dark:divide-gray-800">
            {bunks.map((bunk) => (
              <li key={bunk.id} className="py-2 flex flex-wrap items-center justify-between gap-2">
                <div className="min-w-0">
                  <Link
                    to={`/dashboards/group/${bunk.id}`}
                    data-testid={`bunk-row-${bunk.id}`}
                    className="text-sm font-medium text-blue-700 dark:text-blue-300 hover:underline"
                  >
                    {bunk.name}
                  </Link>
                  {bunk.counselor_names?.length > 0 && (
                    <p className="text-xs text-gray-500 dark:text-gray-400 truncate">
                      {bunk.counselor_names.join(', ')}
                    </p>
                  )}
                  <div className="mt-1 flex flex-wrap items-center">
                    {(bunk.badges || []).map((b) => (
                      <BadgePill key={b} code={b} />
                    ))}
                  </div>
                </div>
                <CompletionBar
                  submitted={bunk.completion?.submitted ?? 0}
                  expected={bunk.completion?.expected ?? 0}
                />
              </li>
            ))}
          </ul>
        )}
      </section>

      <ListSection
        title="Help requested today"
        testid="section-help-requested"
        items={helpRequested}
        renderItem={(c) => <CamperBrief key={c.id} camper={c} />}
        emptyMessage="no help requests today."
      />

      <ListSection
        title="Off camp today"
        testid="section-off-camp"
        items={offCamp}
        renderItem={(c) => <CamperBrief key={c.id} camper={c} />}
        emptyMessage="everyone is on camp."
      />

      <ListSection
        title="Bunk concerns"
        testid="section-bunk-concerns"
        items={bunkConcerns}
        renderItem={(item) => (
          <li
            key={item.reflection_id}
            data-testid={`bunk-concern-${item.reflection_id}`}
            className="text-sm"
          >
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
        )}
        emptyMessage="no flagged bunks today."
        listClassName="space-y-2"
      />
    </div>
  );
}

function Tile({ label, value }) {
  return (
    <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 px-3 py-2 shadow-sm">
      <p className="text-xs uppercase tracking-wide text-gray-500 dark:text-gray-400">{label}</p>
      <p className="text-xl font-semibold text-gray-900 dark:text-white tabular-nums">{value}</p>
    </div>
  );
}

function ListSection({
  title, items, renderItem, emptyMessage, testid, listClassName,
}) {
  const isEmpty = !items || items.length === 0;
  return (
    <section
      data-testid={testid}
      data-state={isEmpty ? 'empty' : 'populated'}
      className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 px-4 py-3 shadow-sm"
    >
      <h2 className="text-base font-semibold text-gray-900 dark:text-white mb-2">
        {title}{' '}
        {!isEmpty && (
          <span className="ml-2 text-xs text-gray-500 dark:text-gray-400">
            ({items.length})
          </span>
        )}
      </h2>
      {isEmpty ? (
        <p className="text-sm text-gray-500 dark:text-gray-400">{emptyMessage}</p>
      ) : (
        <ul className={listClassName || 'flex flex-wrap'}>
          {items.map(renderItem)}
        </ul>
      )}
    </section>
  );
}
