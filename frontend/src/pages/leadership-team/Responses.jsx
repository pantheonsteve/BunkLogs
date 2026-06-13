/**
 * LT Template Responses — Step 7_12 Story 53, redesigned to mirror the
 * legacy Admin Bunk Logs look-and-feel while remaining template-generic.
 *
 * Page shell wraps the standard app chrome (Sidebar + Header). The
 * Individual tab is schema-aware:
 *
 *   - single_choice yes/no     -> KPI counter card + per-row flag chip
 *   - single_choice (other)    -> chip inside Description cell
 *   - single_rating / rating_group -> full-cell colour-coded column
 *                                    (FA4 hex palette, matching
 *                                    AdminBunkLogItem)
 *   - textarea / text          -> stacked inside Description cell
 *
 * Date model: ``?date=YYYY-MM-DD`` single-day stepper (default = today).
 * Sent to the API as ``date_from=date_to=date`` -- the existing endpoint
 * already supports range filters so no backend change required. Date
 * range remains available through the Filters drawer for power users.
 *
 * Aggregate tab: pie charts per scored dimension, daily trend line, date picker.
 */

import { useEffect, useMemo, useRef, useState } from 'react';
import { Link, useParams, useSearchParams } from 'react-router-dom';
import {
  Calendar,
  ChevronLeft,
  ChevronRight,
  Download,
  FileText,
  Filter,
  Search,
  Users,
  X,
} from 'lucide-react';
import {
  exportResponsesUrl,
  fetchAllResponses,
  getTemplate,
} from '../../api/leadershipTeam';
import { useAuth } from '../../auth/AuthContext';
import isSuperAdmin from '../../utils/auth/isSuperAdmin';
import SingleDatePicker from '../../components/ui/SingleDatePicker';
import {
  deriveSchemaSections,
  formatShortDate as formatShortDateShared,
  getInitials,
  pickLabel,
  ratingTierClass,
  seriesDisplayLabel,
} from '../../dashboards/subject/responseTable/schema';
import ScorePieChart from '../../dashboards/performance/ScorePieChart';
import { ratingColor } from '../../dashboards/colors';
import {
  DescriptionCell,
  FlagChip,
  RatingCellTd,
  SubjectCell as SharedSubjectCell,
} from '../../dashboards/subject/responseTable/cells';

function formatLongDate(yyyymmdd) {
  if (!yyyymmdd) return '';
  const [y, m, d] = String(yyyymmdd).split('-').map(Number);
  if (!y || !m || !d) return yyyymmdd;
  const dt = new Date(Date.UTC(y, m - 1, d));
  return dt.toLocaleDateString('en-US', {
    weekday: 'long', year: 'numeric', month: 'long', day: 'numeric',
    timeZone: 'UTC',
  });
}

const formatShortDate = formatShortDateShared;

function todayLocalISO() {
  const now = new Date();
  const y = now.getFullYear();
  const m = String(now.getMonth() + 1).padStart(2, '0');
  const d = String(now.getDate()).padStart(2, '0');
  return `${y}-${m}-${d}`;
}

function dateFromISO(s) {
  if (!s) return null;
  const [y, m, d] = s.split('-').map(Number);
  if (!y || !m || !d) return null;
  return new Date(y, m - 1, d, 12, 0, 0, 0);
}

function isoFromDate(date) {
  if (!date) return '';
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, '0');
  const d = String(date.getDate()).padStart(2, '0');
  return `${y}-${m}-${d}`;
}

function shiftISO(iso, deltaDays) {
  const d = dateFromISO(iso);
  if (!d) return iso;
  d.setDate(d.getDate() + deltaDays);
  return isoFromDate(d);
}

const DASHBOARD_BACK_PATHS = Object.freeze({
  logs: '/dashboards/logs',
  reflections: '/dashboards/reflections',
});

/** Back link for template responses: dashboards hub (admin) or template library. */
export function responsesBackLink({ dashboard, date, isAdmin }) {
  const scope = dashboard === 'logs' || dashboard === 'reflections'
    ? dashboard
    : (isAdmin ? 'reflections' : null);
  if (!scope) return { href: '/admin/templates', label: '← Template library' };
  const base = DASHBOARD_BACK_PATHS[scope];
  const href = date ? `${base}?date=${encodeURIComponent(date)}` : base;
  const label = scope === 'logs' ? '← Bunk Logs' : '← Reflections';
  return { href, label };
}

// ---------------------------------------------------------------------------
// Row sub-components (see ../../dashboards/subject/responseTable for the
// shared cell implementations; this page only injects the LT-specific
// flag testid prefix + subject-link href).
// ---------------------------------------------------------------------------

function SubjectCell({ row, dateQs }) {
  const subjectId = row.subject?.id;
  const linkTo = subjectId
    ? `/profile/${subjectId}${dateQs ?? ''}`
    : null;
  return <SharedSubjectCell row={row} linkTo={linkTo} />;
}

// The camper's active groups for the reflection's date. ``row.groups`` is a
// list of {id, name, group_type} (id = AssignmentGroup pk). Each renders as a
// badge linking to the unified group dashboard for the same day; a camper in
// multiple groups gets multiple badges.
function BunkCell({ row }) {
  const groups = row.groups ?? [];
  const rowDate = row.period_end || row.period_start;
  if (groups.length === 0) {
    return (
      <td className="px-3 py-3 whitespace-nowrap border border-gray-300 dark:border-gray-700 text-gray-400 dark:text-gray-500">
        —
      </td>
    );
  }
  return (
    <td className="px-3 py-3 border border-gray-300 dark:border-gray-700">
      <div className="flex flex-wrap gap-1">
        {groups.map((g) => (
          <Link
            key={g.id}
            to={`/dashboards/group/${g.id}${rowDate ? `?date=${rowDate}` : ''}`}
            title={g.group_type ? `${g.name} (${g.group_type})` : g.name}
            className="inline-flex items-center px-2 py-0.5 text-xs font-medium rounded-full border border-indigo-200 bg-indigo-50 text-indigo-700 hover:bg-indigo-100 dark:border-indigo-800 dark:bg-indigo-900/30 dark:text-indigo-200"
          >
            {g.name || `Group ${g.id}`}
          </Link>
        ))}
      </div>
    </td>
  );
}

// Fixed display order for the legacy camper-score dimensions, matching
// the legacy Admin Bunk Logs table. Unknown dimensions keep their schema
// order after these.
const RATING_COLUMN_ORDER = { social: 0, behavior: 1, participation: 2 };

function orderRatingCols(cols) {
  return cols
    .map((c, idx) => ({ c, idx }))
    .sort((a, b) => {
      const ra = RATING_COLUMN_ORDER[a.c.subKey ?? a.c.key] ?? 99;
      const rb = RATING_COLUMN_ORDER[b.c.subKey ?? b.c.key] ?? 99;
      return ra - rb || a.idx - b.idx;
    })
    .map(({ c }) => c);
}

// ---------------------------------------------------------------------------
// Tabs
// ---------------------------------------------------------------------------

function KpiCard({ icon: Icon, label, value, tone = 'neutral', active = false, onClick }) {
  const accent = {
    neutral: 'text-blue-500',
    danger: 'text-red-500',
    warning: 'text-yellow-500',
    muted: 'text-gray-500',
  }[tone] ?? 'text-blue-500';
  const ring = active
    ? (tone === 'danger' ? 'border-red-400'
      : tone === 'warning' ? 'border-yellow-400'
      : 'border-blue-400')
    : 'border-transparent';
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={!onClick}
      className={`bg-white dark:bg-gray-800 shadow-sm rounded-xl p-5 border-2 ${ring} ${onClick ? 'cursor-pointer hover:border-gray-300 dark:hover:border-gray-600' : 'cursor-default'} text-left transition-colors`}
      data-testid={`lt-kpi-${(label || 'card').toString().toLowerCase().replace(/\s+/g, '-')}`}
    >
      <div className="flex items-center">
        <div className="flex-shrink-0">
          <Icon className={`w-7 h-7 ${accent}`} />
        </div>
        <div className="ml-4">
          <p className="text-sm font-medium text-gray-600 dark:text-gray-400">{label}</p>
          <p className="text-2xl font-semibold text-gray-900 dark:text-white">{value}</p>
        </div>
      </div>
    </button>
  );
}

function IndividualTab({
  payload, template, language, filteredRows, sections, dateStr,
}) {
  const { ratingCols: rawRatingCols, flagFields, chipFields, descTextFields } = sections;
  const ratingCols = orderRatingCols(rawRatingCols);
  const dateQs = dateStr ? `?date=${dateStr}` : '';

  if (filteredRows.length === 0) {
    return (
      <div className="bg-white dark:bg-gray-800 shadow-sm rounded-xl">
        <div className="flex items-center justify-center py-12 text-center">
          <div>
            <FileText className="w-12 h-12 text-gray-400 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
              No logs found
            </h3>
            <p className="text-gray-600 dark:text-gray-400" data-testid="lt-responses-empty">
              {payload?.total === 0
                ? 'No reflections were submitted for this date.'
                : 'No logs match your current filters.'}
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white dark:bg-gray-800 shadow-sm rounded-xl overflow-hidden">
      <div className="overflow-x-auto">
        <table className="table-auto w-full text-sm dark:text-gray-300" data-testid="lt-responses-rows">
          <thead className="text-xs uppercase text-gray-500 dark:text-gray-400 bg-gray-50 dark:bg-gray-700/50">
            <tr>
              <th className="p-2 text-left border-b border-gray-200 dark:border-gray-700 font-semibold">Name</th>
              <th className="p-2 text-left border-b border-gray-200 dark:border-gray-700 font-semibold">Bunk</th>
              <th className="p-2 text-center border-b border-gray-200 dark:border-gray-700 font-semibold">Date</th>
              {ratingCols.map((c, idx) => (
                <th
                  key={`${c.key}-${c.subKey ?? ''}-${idx}`}
                  className="p-2 text-center border-b border-gray-200 dark:border-gray-700 font-semibold"
                  title={c.label}
                >
                  <div className="truncate max-w-[8rem] mx-auto">{c.label}</div>
                </th>
              ))}
              <th className="p-2 text-left border-b border-gray-200 dark:border-gray-700 font-semibold">Description</th>
            </tr>
          </thead>
          <tbody className="text-sm font-medium divide-y divide-gray-200 dark:divide-gray-700/60">
            {filteredRows.map((r) => (
              <tr key={r.id} data-testid={`lt-responses-row-${r.id}`}>
                <SubjectCell row={r} dateQs={dateQs} />
                <BunkCell row={r} />
                <td className="px-3 py-3 whitespace-nowrap text-center border border-gray-300 dark:border-gray-700">
                  <div className="text-sm text-gray-800 dark:text-gray-100">
                    {formatShortDate(r.period_end || r.period_start)}
                  </div>
                  <div className="text-[10px] text-gray-500 dark:text-gray-400 mt-0.5">
                    {r.language} · v{r.template_version}
                  </div>
                  <Link
                    to={`/reflections/${r.id}`}
                    className="block mt-1 text-[11px] text-indigo-600 dark:text-indigo-400 hover:underline"
                  >
                    Open →
                  </Link>
                </td>
                {ratingCols.map((c, idx) => (
                  <RatingCellTd
                    key={`${r.id}-${c.key}-${c.subKey ?? ''}-${idx}`}
                    col={c}
                    answers={r.answers}
                  />
                ))}
                <DescriptionCell
                  row={r}
                  flagFields={flagFields}
                  chipFields={chipFields}
                  descTextFields={descTextFields}
                />
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function orderRatingDims(dims, ratingCols) {
  const orderIndex = (key) => {
    const col = ratingCols.find((c) =>
      (c.subKey ? `${c.key}__${c.subKey}` : c.key) === key,
    );
    const sortKey = col?.subKey ?? col?.key ?? key;
    return RATING_COLUMN_ORDER[sortKey] ?? 99;
  };
  return [...dims].sort((a, b) => {
    const ra = orderIndex(a.key);
    const rb = orderIndex(b.key);
    if (ra !== rb) return ra - rb;
    return a.key.localeCompare(b.key);
  });
}

function emptyDistribution(scaleMax = 5) {
  const dist = {};
  for (let i = 1; i <= scaleMax; i += 1) dist[String(i)] = 0;
  return dist;
}

/** Merge API aggregate dimensions with schema rating columns so every scored field gets a card. */
function buildAggregateDims(apiDims, ratingCols) {
  const byKey = Object.fromEntries((apiDims ?? []).map((d) => [d.key, d]));
  const orderedCols = orderRatingCols(ratingCols);
  const fromSchema = orderedCols.map((col) => {
    const key = col.subKey ? `${col.key}__${col.subKey}` : col.key;
    const scaleMax = col.scaleMax ?? 5;
    const fromApi = byKey[key];
    if (fromApi) {
      return {
        ...fromApi,
        scale_max: fromApi.scale_max ?? scaleMax,
        distribution: fromApi.distribution ?? emptyDistribution(fromApi.scale_max ?? scaleMax),
      };
    }
    return {
      key,
      avg: null,
      count: 0,
      scale_max: scaleMax,
      distribution: emptyDistribution(scaleMax),
      versions: [],
    };
  });
  const schemaKeys = new Set(fromSchema.map((d) => d.key));
  const extras = orderRatingDims(
    (apiDims ?? []).filter((d) => !schemaKeys.has(d.key)),
    ratingCols,
  );
  return [...fromSchema, ...extras];
}

function distributionLegend(distribution) {
  return Object.entries(distribution)
    .filter(([, count]) => Number(count) > 0)
    .sort(([a], [b]) => Number(a) - Number(b))
    .map(([value, count]) => `${value}: ${count}`)
    .join(' · ');
}

function DateStepperBar({ dateStr, setSingleDate, stepDate, embedded = false }) {
  const controls = (
    <div className="flex flex-wrap items-center gap-3 shrink-0">
      <div className="flex items-center space-x-3">
        <button
          type="button"
          onClick={() => stepDate(-1)}
          className="p-2 rounded-lg border border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700"
          aria-label="Previous day"
          data-testid="lt-responses-prev-day"
        >
          <ChevronLeft className="w-4 h-4" />
        </button>
        <div className="flex items-center space-x-2">
          <Calendar className="w-5 h-5 text-gray-400" />
          <SingleDatePicker
            date={dateFromISO(dateStr)}
            setDate={(d) => d && setSingleDate(isoFromDate(d))}
          />
        </div>
        <button
          type="button"
          onClick={() => stepDate(1)}
          className="p-2 rounded-lg border border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700"
          aria-label="Next day"
          data-testid="lt-responses-next-day"
        >
          <ChevronRight className="w-4 h-4" />
        </button>
      </div>
      <div
        className="text-sm text-gray-600 dark:text-gray-400 whitespace-nowrap"
        data-testid="lt-responses-long-date"
      >
        {formatLongDate(dateStr)}
      </div>
    </div>
  );

  if (embedded) return controls;

  return (
    <div className="bg-white dark:bg-gray-800 shadow-sm rounded-xl p-5 mb-6">
      {controls}
    </div>
  );
}

function AggregateTrendChart({ series, selectedDate, scaleMax = 5, onSelectDate }) {
  const containerRef = useRef(null);
  const [chartWidth, setChartWidth] = useState(0);
  const [hoveredDate, setHoveredDate] = useState(null);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return undefined;
    const update = () => setChartWidth(el.clientWidth);
    update();
    if (typeof ResizeObserver === 'undefined') return undefined;
    const ro = new ResizeObserver(update);
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  const selectDate = (date) => {
    if (!onSelectDate || !date || date === selectedDate) return;
    onSelectDate(date);
  };

  const points = (series ?? []).filter((p) => p.avg != null);
  if (points.length === 0) {
    return (
      <p className="text-sm text-gray-500 dark:text-gray-400 italic">
        No rating history yet.
      </p>
    );
  }
  const w = chartWidth || 640;
  const h = 160;
  const padX = 36;
  const padY = 20;
  const sorted = [...points].sort((a, b) => a.date.localeCompare(b.date));
  const xs = sorted.length;
  const xStep = xs > 1 ? (w - 2 * padX) / (xs - 1) : 0;
  const yScale = (v) => {
    const clamped = Math.max(1, Math.min(scaleMax, v));
    return h - padY - ((clamped - 1) / (scaleMax - 1)) * (h - 2 * padY);
  };
  const path = sorted
    .map((p, i) => `${i === 0 ? 'M' : 'L'}${padX + i * xStep},${yScale(p.avg)}`)
    .join(' ');

  return (
    <div ref={containerRef} className="w-full">
      <svg
        width="100%"
        height={h}
        viewBox={`0 0 ${w} ${h}`}
        aria-label="Average score over time. Click a point to view that day."
        className="block w-full"
        data-testid="lt-responses-trend-chart"
      >
        {[1, Math.ceil(scaleMax / 2), scaleMax].map((v) => (
          <g key={v}>
            <line
              x1={padX}
              x2={w - padX}
              y1={yScale(v)}
              y2={yScale(v)}
              stroke="#e5e7eb"
              strokeWidth="0.5"
            />
            <text x={4} y={yScale(v) + 4} className="fill-gray-400 text-[10px]">{v}</text>
          </g>
        ))}
        <path d={path} stroke="#4f46e5" strokeWidth="2" fill="none" />
        {sorted.map((p, i) => {
          const selected = p.date === selectedDate;
          const hovered = p.date === hoveredDate;
          const cx = padX + i * xStep;
          const cy = yScale(p.avg);
          const dotR = selected ? 5 : hovered ? 5 : 3.5;
          return (
            <g
              key={p.date}
              className="cursor-pointer"
              data-testid={`lt-responses-trend-point-${p.date}`}
              onMouseEnter={() => setHoveredDate(p.date)}
              onMouseLeave={() => setHoveredDate((cur) => (cur === p.date ? null : cur))}
              onClick={() => selectDate(p.date)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault();
                  selectDate(p.date);
                }
              }}
              role="button"
              tabIndex={0}
              aria-label={`View ${formatLongDate(p.date)}, average ${p.avg.toFixed(2)}`}
              aria-current={selected ? 'date' : undefined}
            >
              <title>{`${formatLongDate(p.date)} · avg ${p.avg.toFixed(2)} · click to view`}</title>
              <circle
                cx={cx}
                cy={cy}
                r={14}
                fill="transparent"
              />
              {hovered && (
                <g pointerEvents="none" data-testid={`lt-responses-trend-tooltip-${p.date}`}>
                  <rect
                    x={cx - 72}
                    y={cy - 30}
                    width={144}
                    height={20}
                    rx={4}
                    className="fill-gray-900 dark:fill-gray-700"
                    opacity={0.92}
                  />
                  <text
                    x={cx}
                    y={cy - 16}
                    textAnchor="middle"
                    className="fill-white text-[10px]"
                  >
                    {formatLongDate(p.date)}
                  </text>
                </g>
              )}
              <circle
                cx={cx}
                cy={cy}
                r={dotR}
                fill={selected || hovered ? '#4f46e5' : (ratingColor(p.avg, scaleMax) ?? '#6b7280')}
                stroke="#fff"
                strokeWidth="1.5"
                pointerEvents="none"
              />
              <text
                x={cx}
                y={h - 4}
                textAnchor="middle"
                pointerEvents="none"
                className={`text-[9px] ${
                  selected || hovered
                    ? 'fill-indigo-600 font-semibold'
                    : 'fill-gray-500'
                }`}
              >
                {formatShortDate(p.date)}
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}

function AggregateRatingCard({ dim, ratingCols }) {
  const displayLabel = seriesDisplayLabel(dim.key, ratingCols) || dim.key;
  const scaleMax = dim.scale_max ?? 5;
  const distribution = dim.distribution ?? emptyDistribution(scaleMax);
  const total = Object.values(distribution).reduce((sum, count) => sum + Number(count), 0);

  return (
    <div
      className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-4 flex flex-col items-center text-center"
      data-testid={`lt-responses-dim-${dim.key}`}
    >
      <h4 className="text-sm font-semibold text-gray-900 dark:text-white mb-3">
        {displayLabel}
      </h4>
      {total === 0 ? (
        <p className="text-xs text-gray-400 italic py-8">No ratings for this day.</p>
      ) : (
        <div className="flex flex-col items-center gap-2" aria-label={`${displayLabel} score distribution`}>
          <ScorePieChart distribution={distribution} scaleMax={scaleMax} size={96} />
          <p className="text-[10px] text-gray-500 dark:text-gray-400 text-center">
            {distributionLegend(distribution)}
          </p>
        </div>
      )}
      <p className="mt-3 text-2xl font-semibold tabular-nums text-gray-900 dark:text-white">
        {dim.avg == null ? '—' : dim.avg.toFixed(2)}
      </p>
      <p className="text-xs text-gray-500 dark:text-gray-400">
        average · {dim.count ?? 0} rating{(dim.count ?? 0) === 1 ? '' : 's'}
      </p>
    </div>
  );
}

function AggregateTab({ payload, dateStr, ratingCols, onSelectDate, loading = false }) {
  if (!payload) return null;
  const ratingColsOrdered = orderRatingCols(ratingCols);
  const dims = buildAggregateDims(
    payload.avg_rating_per_dimension ?? payload.avg_per_dimension ?? [],
    ratingColsOrdered,
  );
  const trend = payload.avg_rating_over_time ?? [];
  const trendScaleMax = dims.reduce(
    (max, d) => Math.max(max, d.scale_max ?? 5),
    5,
  );

  return (
    <div className="space-y-6">
      {loading && (
        <p className="text-xs text-gray-500 dark:text-gray-400" data-testid="lt-responses-aggregate-loading">
          Updating…
        </p>
      )}
      <div
        className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-4"
        data-testid="lt-responses-summary"
      >
        <p className="text-sm text-gray-700 dark:text-gray-300">
          <span className="font-semibold text-gray-900 dark:text-white">
            {payload.total_responses}
          </span>
          {' '}
          response{payload.total_responses === 1 ? '' : 's'} on {formatLongDate(dateStr)}
        </p>
      </div>

      {dims.length === 0 ? (
        <div
          className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-6"
          data-testid="lt-responses-avg"
        >
          <p className="text-sm text-gray-500 dark:text-gray-400">No scored fields on this template.</p>
        </div>
      ) : (
        <div
          className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4"
          data-testid="lt-responses-avg"
        >
          {dims.map((d) => (
            <AggregateRatingCard
              key={d.key}
              dim={d}
              ratingCols={ratingColsOrdered}
            />
          ))}
        </div>
      )}

      <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-4">
        <h3 className="text-base font-semibold text-gray-900 dark:text-white mb-1">
          Average score over time
        </h3>
        <p className="text-xs text-gray-500 dark:text-gray-400 mb-4">
          Composite average across all rating fields for each day. Hover to preview a date; click to view that day.
        </p>
        <AggregateTrendChart
          series={trend}
          selectedDate={dateStr}
          scaleMax={trendScaleMax}
          onSelectDate={onSelectDate}
        />
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

/**
 * Build the API params we send to ``/templates/<id>/responses/``. The
 * single-day stepper (``?date=``) wins over an explicit range — if the
 * user steps to a new day we send ``date_from=date_to=date`` and ignore
 * any stale range in the URL. The Filters drawer clears ``?date=`` when
 * the user picks a range, so the two never conflict in practice.
 */
function buildApiParams(urlParams, activeTab) {
  const out = {};
  for (const [k, v] of urlParams.entries()) {
    if (k === 'q' || k === 'date') continue;
    out[k] = v;
  }
  const single = urlParams.get('date');
  if (single) {
    out.date_from = single;
    out.date_to = single;
  }
  out.tab = activeTab;
  return out;
}

export default function LeadershipTeamResponses() {
  const { id } = useParams();
  const { orgSlug, user } = useAuth();
  const isAdmin = isSuperAdmin(user) || user?.role?.toLowerCase() === 'admin';
  const [params, setParams] = useSearchParams();
  const tab = (params.get('tab') || 'individual').toLowerCase();
  const language = params.get('language') || 'en';
  const dateStr = params.get('date') || todayLocalISO();
  const searchQuery = params.get('q') || '';

  const [showFilters, setShowFilters] = useState(false);
  const [template, setTemplate] = useState(null);
  const [payload, setPayload] = useState(null);
  const lastAggregatePayloadRef = useRef(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  // Default URL to today's date if absent so the stepper renders a
  // selection on first load. Keep this idempotent so it doesn't bounce
  // the user back when they explicitly clear ``?date=`` via the Filters
  // drawer (in which case they will have set date_from/date_to instead).
  const didDefaultDate = useRef(false);
  useEffect(() => {
    if (didDefaultDate.current) return;
    if (!params.get('date') && !params.get('date_from')) {
      const next = new URLSearchParams(params);
      next.set('date', todayLocalISO());
      setParams(next, { replace: true });
    }
    didDefaultDate.current = true;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const apiParamsKey = useMemo(() => {
    const built = buildApiParams(params, tab);
    return JSON.stringify(built);
  }, [params, tab]);

  useEffect(() => {
    let cancelled = false;
    async function run() {
      setLoading(true);
      setError('');
      try {
        const [tpl, data] = await Promise.all([
          getTemplate(orgSlug, id),
          fetchAllResponses(orgSlug, id, JSON.parse(apiParamsKey)),
        ]);
        if (cancelled) return;
        setTemplate(tpl);
        setPayload(data);
        if (data?.tab === 'aggregate') lastAggregatePayloadRef.current = data;
      } catch (err) {
        if (cancelled) return;
        if (err?.response?.status === 403) setError('You cannot view these responses.');
        else if (err?.response?.status === 404) setError('Template not found.');
        else setError('Failed to load responses.');
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    run();
    return () => { cancelled = true; };
  }, [orgSlug, id, apiParamsKey]);

  const setParam = (k, v) => {
    const next = new URLSearchParams(params);
    if (v == null || v === '') next.delete(k); else next.set(k, v);
    if (k !== 'page') next.delete('page');
    setParams(next, { replace: true });
  };

  const switchTab = (next) => {
    const updated = new URLSearchParams(params);
    updated.set('tab', next);
    updated.delete('page');
    setParams(updated, { replace: true });
  };

  // Date stepper handlers. Switching the stepper clears any explicit
  // range filter so the two date controls don't fight each other.
  const setSingleDate = (nextISO) => {
    const next = new URLSearchParams(params);
    next.set('date', nextISO);
    next.delete('date_from');
    next.delete('date_to');
    next.delete('page');
    setParams(next, { replace: true });
  };

  const stepDate = (delta) => setSingleDate(shiftISO(dateStr, delta));

  const sections = useMemo(
    () => deriveSchemaSections(template?.schema, language),
    [template?.schema, language],
  );

  const rawRows = payload?.results ?? [];
  // Client-side name search across author + subject. Cheap because the
  // server already paginates at 25 rows per page; if a single-day query
  // ever returns more, server-side ``q=`` is the follow-up.
  const filteredRows = useMemo(() => {
    const q = searchQuery.trim().toLowerCase();
    if (!q) return rawRows;
    return rawRows.filter((r) => {
      const a = (r.author?.name ?? '').toLowerCase();
      const s = (r.subject?.name ?? '').toLowerCase();
      return a.includes(q) || s.includes(q);
    });
  }, [rawRows, searchQuery]);

  // KPI card filtering: clicking a yes/no flag card flips a URL flag
  // (``?flag_<key>=yes``) which we apply client-side. Lean: no server
  // round-trip needed for what's already paginated.
  const flagFilter = (key) => params.get(`flag_${key}`) === 'yes';
  const toggleFlagFilter = (key) => {
    const next = new URLSearchParams(params);
    if (flagFilter(key)) next.delete(`flag_${key}`); else next.set(`flag_${key}`, 'yes');
    setParams(next, { replace: true });
  };

  const flagFilteredRows = useMemo(() => {
    let rows = filteredRows;
    for (const f of sections.flagFields) {
      if (flagFilter(f.key)) {
        rows = rows.filter((r) =>
          String(r.answers?.[f.key] ?? '').toLowerCase() === 'yes',
        );
      }
    }
    return rows;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filteredRows, sections.flagFields, params]);

  const exportHref = exportResponsesUrl(id, buildApiParams(params, tab));

  const aggregatePayload = payload?.tab === 'aggregate'
    ? payload
    : lastAggregatePayloadRef.current;

  const { href: backHref, label: backLabel } = responsesBackLink({
    dashboard: params.get('dashboard'),
    date: dateStr,
    isAdmin,
  });

  return (
    <div className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-9xl mx-auto">
            {/* Header */}
            <div className="sm:flex sm:justify-between sm:items-center mb-6">
              <div>
                <Link
                  to={backHref}
                  className="text-sm text-indigo-600 dark:text-indigo-400 hover:underline"
                  data-testid="lt-responses-back"
                >
                  {backLabel}
                </Link>
                <h1 className="text-2xl md:text-3xl text-gray-800 dark:text-gray-100 font-bold mt-1">
                  {template?.name ?? 'Responses'}
                </h1>
                <p className="text-gray-600 dark:text-gray-400 text-sm">
                  {template?.role ? `${template.role} · ` : ''}v{template?.version ?? '?'}
                </p>
              </div>

              <div className="grid grid-flow-col sm:auto-cols-max justify-start sm:justify-end gap-2 mt-3 sm:mt-0">
                <button
                  type="button"
                  onClick={() => setShowFilters((s) => !s)}
                  className="btn bg-white dark:bg-gray-800 border-gray-200 dark:border-gray-700/60 hover:border-gray-300 dark:hover:border-gray-600 text-gray-800 dark:text-gray-300"
                  data-testid="lt-responses-toggle-filters"
                >
                  <Filter className="w-4 h-4 mr-2" />
                  Filters
                </button>
                <a
                  href={exportHref}
                  className="btn bg-white dark:bg-gray-800 border-gray-200 dark:border-gray-700/60 hover:border-gray-300 dark:hover:border-gray-600 text-gray-800 dark:text-gray-300"
                  data-testid="lt-responses-export"
                >
                  <Download className="w-4 h-4 mr-2" />
                  Export CSV
                </a>
              </div>
            </div>

            {/* Tabs */}
            <div className="mb-6 flex gap-2 border-b border-gray-200 dark:border-gray-700">
              {['individual', 'aggregate'].map((t) => (
                <button
                  key={t}
                  type="button"
                  onClick={() => switchTab(t)}
                  aria-current={tab === t ? 'page' : undefined}
                  className={`text-sm px-3 py-2 -mb-px border-b-2 ${
                    tab === t
                      ? 'border-indigo-600 text-indigo-600 dark:text-indigo-400'
                      : 'border-transparent text-gray-600 dark:text-gray-400 hover:text-gray-900'
                  }`}
                  data-testid={`lt-responses-tab-${t}`}
                >
                  {t === 'individual' ? 'Individual' : 'Aggregate'}
                </button>
              ))}
            </div>

            {tab === 'individual' && (
              <>
                {/* Search + date */}
                <div className="bg-white dark:bg-gray-800 shadow-sm rounded-xl p-5 mb-6">
                  <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
                    <div className="relative min-w-0 flex-1 lg:max-w-md">
                      <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                        <Search className="h-5 w-5 text-gray-400" />
                      </div>
                      <input
                        type="text"
                        placeholder="Search by name..."
                        value={searchQuery}
                        onChange={(e) => setParam('q', e.target.value)}
                        className="block w-full pl-10 pr-10 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                        data-testid="lt-responses-search"
                      />
                      {searchQuery && (
                        <button
                          type="button"
                          onClick={() => setParam('q', '')}
                          className="absolute inset-y-0 right-0 pr-3 flex items-center text-gray-400 hover:text-gray-600"
                          aria-label="Clear search"
                        >
                          <X className="h-4 w-4" />
                        </button>
                      )}
                    </div>
                    <DateStepperBar
                      dateStr={dateStr}
                      setSingleDate={setSingleDate}
                      stepDate={stepDate}
                      embedded
                    />
                  </div>
                </div>

                {/* Filters drawer */}
                {showFilters && (
                  <div className="bg-white dark:bg-gray-800 shadow-sm rounded-xl p-5 mb-6" data-testid="lt-responses-filters">
                    <div className="flex items-center justify-between mb-3">
                      <h3 className="text-base font-medium text-gray-900 dark:text-white">Filters</h3>
                      <button
                        type="button"
                        onClick={() => setShowFilters(false)}
                        className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
                        aria-label="Close filters"
                      >
                        <X className="w-4 h-4" />
                      </button>
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                      <label className="text-xs text-gray-700 dark:text-gray-300">
                        From
                        <input
                          type="date"
                          value={params.get('date_from') || ''}
                          onChange={(e) => {
                            const next = new URLSearchParams(params);
                            if (e.target.value) {
                              next.set('date_from', e.target.value);
                              next.delete('date');
                            } else {
                              next.delete('date_from');
                            }
                            next.delete('page');
                            setParams(next, { replace: true });
                          }}
                          className="block mt-1 w-full rounded-md border-gray-300 dark:border-gray-600 dark:bg-gray-700 text-sm"
                          data-testid="lt-responses-date-from"
                        />
                      </label>
                      <label className="text-xs text-gray-700 dark:text-gray-300">
                        To
                        <input
                          type="date"
                          value={params.get('date_to') || ''}
                          onChange={(e) => {
                            const next = new URLSearchParams(params);
                            if (e.target.value) {
                              next.set('date_to', e.target.value);
                              next.delete('date');
                            } else {
                              next.delete('date_to');
                            }
                            next.delete('page');
                            setParams(next, { replace: true });
                          }}
                          className="block mt-1 w-full rounded-md border-gray-300 dark:border-gray-600 dark:bg-gray-700 text-sm"
                          data-testid="lt-responses-date-to"
                        />
                      </label>
                      <label className="text-xs text-gray-700 dark:text-gray-300">
                        Language
                        <select
                          value={params.get('language') || ''}
                          onChange={(e) => setParam('language', e.target.value)}
                          className="block mt-1 w-full rounded-md border-gray-300 dark:border-gray-600 dark:bg-gray-700 text-sm"
                          data-testid="lt-responses-lang"
                        >
                          <option value="">all</option>
                          <option value="en">en</option>
                          <option value="es">es</option>
                          <option value="he">he</option>
                        </select>
                      </label>
                      <label className="text-xs text-gray-700 dark:text-gray-300">
                        Rating ≤
                        <input
                          type="number"
                          value={params.get('rating_le') || ''}
                          onChange={(e) => setParam('rating_le', e.target.value)}
                          className="block mt-1 w-full rounded-md border-gray-300 dark:border-gray-600 dark:bg-gray-700 text-sm"
                          data-testid="lt-responses-rating-le"
                        />
                      </label>
                      <label className="text-xs text-gray-700 dark:text-gray-300 flex items-center gap-2 mt-5">
                        <input
                          type="checkbox"
                          checked={params.get('has_free_text') === '1'}
                          onChange={(e) => setParam('has_free_text', e.target.checked ? '1' : '')}
                          data-testid="lt-responses-free-text"
                        />
                        Has free text
                      </label>
                    </div>
                  </div>
                )}

                {/* KPI cards */}
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6" data-testid="lt-kpis">
                  <KpiCard
                    icon={Users}
                    label="Total Log Entries"
                    value={flagFilteredRows.length}
                  />
                  {sections.flagFields.map((f) => {
                    const tone = f.key.toLowerCase().includes('camper_care')
                      ? 'danger'
                      : f.key.toLowerCase().includes('unit_head')
                      ? 'warning'
                      : f.key.toLowerCase().includes('not_on_camp')
                      ? 'muted'
                      : 'neutral';
                    const count = filteredRows.filter(
                      (r) => String(r.answers?.[f.key] ?? '').toLowerCase() === 'yes',
                    ).length;
                    return (
                      <KpiCard
                        key={f.key}
                        icon={FileText}
                        label={f.label}
                        value={count}
                        tone={tone}
                        active={flagFilter(f.key)}
                        onClick={() => toggleFlagFilter(f.key)}
                      />
                    );
                  })}
                </div>

                {/* Table */}
                <div className="mb-3">
                  <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
                    Log entries for {formatLongDate(dateStr)} ({flagFilteredRows.length} records)
                  </h2>
                </div>
              </>
            )}

            {tab === 'aggregate' && (
              <DateStepperBar
                dateStr={dateStr}
                setSingleDate={setSingleDate}
                stepDate={stepDate}
              />
            )}

            {loading && tab !== 'aggregate' && (
              <p className="text-sm text-gray-500 dark:text-gray-400" data-testid="lt-responses-loading">
                Loading…
              </p>
            )}
            {error && (
              <p className="text-red-600 dark:text-red-400 text-sm" data-testid="lt-responses-error">
                {error}
              </p>
            )}

            {!loading && !error && tab === 'individual' && (
              <IndividualTab
                payload={payload}
                template={template}
                language={language}
                filteredRows={flagFilteredRows}
                sections={sections}
                dateStr={dateStr}
              />
            )}
            {!error && tab === 'aggregate' && aggregatePayload && (
              <AggregateTab
                payload={aggregatePayload}
                dateStr={dateStr}
                ratingCols={sections.ratingCols}
                onSelectDate={setSingleDate}
                loading={loading}
              />
            )}
    </div>
  );
}
