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
 * Aggregate tab is unchanged.
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
import SingleDatePicker from '../../components/ui/SingleDatePicker';
import {
  deriveSchemaSections,
  formatShortDate as formatShortDateShared,
  getInitials,
  pickLabel,
  ratingTierClass,
} from '../../dashboards/subject/responseTable/schema';
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

function AggregateTab({ payload }) {
  if (!payload) return null;
  // Backend serializers (LT responses endpoint) emit:
  //   avg_rating_per_dimension: [{key, avg, count, versions}]
  //   language_distribution:    [{language, count}]  -- list, not dict
  //   response_volume_per_period: [{period_start, count}]
  const dims = payload.avg_rating_per_dimension ?? payload.avg_per_dimension ?? [];
  const langDistRaw = payload.language_distribution ?? [];
  const langDist = Array.isArray(langDistRaw)
    ? langDistRaw
    : Object.entries(langDistRaw).map(([language, count]) => ({ language, count }));
  const volume = payload.response_volume_per_period ?? [];
  return (
    <div className="space-y-4">
      <div
        className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-4"
        data-testid="lt-responses-summary"
      >
        <p className="text-sm text-gray-700 dark:text-gray-300">
          <span className="font-semibold text-gray-900 dark:text-white">{payload.total_responses}</span> responses
        </p>
      </div>

      <div
        className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-4"
        data-testid="lt-responses-avg"
      >
        <h3 className="text-base font-semibold text-gray-900 dark:text-white mb-2">
          Average per dimension
        </h3>
        {dims.length === 0 ? (
          <p className="text-sm text-gray-500 dark:text-gray-400">No scored fields.</p>
        ) : (
          <ul className="space-y-1 text-sm">
            {dims.map((d) => (
              <li key={d.key} className="flex justify-between" data-testid={`lt-responses-dim-${d.key}`}>
                <span className="text-gray-700 dark:text-gray-300">
                  {d.key}
                  <span className="ml-2 text-xs text-gray-500 dark:text-gray-400">
                    versions: {(d.versions ?? []).join(', ') || '—'}
                  </span>
                </span>
                <span className="text-gray-900 dark:text-white font-medium">
                  {d.avg == null ? '—' : d.avg.toFixed(2)}
                  <span className="text-xs text-gray-500 dark:text-gray-400 ml-1">({d.count})</span>
                </span>
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-4">
        <h3 className="text-base font-semibold text-gray-900 dark:text-white mb-2">
          Language distribution
        </h3>
        <ul className="text-sm space-y-1">
          {langDist.map(({ language, count }) => (
            <li key={language} className="flex justify-between text-gray-700 dark:text-gray-300">
              <span>{language}</span>
              <span>{count}</span>
            </li>
          ))}
        </ul>
      </div>

      <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-4">
        <h3 className="text-base font-semibold text-gray-900 dark:text-white mb-2">
          Volume per period
        </h3>
        <ul className="text-xs space-y-0.5">
          {volume.map((v) => (
            <li key={v.period_start} className="flex justify-between text-gray-700 dark:text-gray-300">
              <span>{v.period_start}</span>
              <span>{v.count}</span>
            </li>
          ))}
        </ul>
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
function buildApiParams(urlParams) {
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
  return out;
}

export default function LeadershipTeamResponses() {
  const { id } = useParams();
  const { orgSlug } = useAuth();
  const [params, setParams] = useSearchParams();
  const tab = (params.get('tab') || 'individual').toLowerCase();
  const language = params.get('language') || 'en';
  const dateStr = params.get('date') || todayLocalISO();
  const searchQuery = params.get('q') || '';

  const [showFilters, setShowFilters] = useState(false);
  const [template, setTemplate] = useState(null);
  const [payload, setPayload] = useState(null);
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
    const built = buildApiParams(params);
    return JSON.stringify(built);
  }, [params]);

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

  const exportHref = exportResponsesUrl(id, buildApiParams(params));

  return (
    <div className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-9xl mx-auto">
            {/* Header */}
            <div className="sm:flex sm:justify-between sm:items-center mb-6">
              <div>
                <Link
                  to="/leadership-team/templates"
                  className="text-sm text-indigo-600 dark:text-indigo-400 hover:underline"
                >
                  ← Template library
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
                {/* Search */}
                <div className="bg-white dark:bg-gray-800 shadow-sm rounded-xl p-5 mb-6">
                  <div className="relative max-w-md">
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
                </div>

                {/* Date stepper */}
                <div className="bg-white dark:bg-gray-800 shadow-sm rounded-xl p-5 mb-6">
                  <div className="flex items-center justify-between flex-wrap gap-3">
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
                    <div className="text-sm text-gray-600 dark:text-gray-400" data-testid="lt-responses-long-date">
                      {formatLongDate(dateStr)}
                    </div>
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
                    label="Total Logs"
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
                    Logs for {formatLongDate(dateStr)} ({flagFilteredRows.length} records)
                  </h2>
                </div>
              </>
            )}

            {loading && (
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
            {!loading && !error && tab === 'aggregate' && <AggregateTab payload={payload} />}
    </div>
  );
}
