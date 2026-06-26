import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { Chart as ChartJS } from 'chart.js';
import 'chart.js/auto';
import { ArrowLeft, BarChart3, Download, Package, ListChecks, Boxes, ChevronUp, ChevronDown, ChevronsUpDown } from 'lucide-react';

import {
  fetchCatalogPlanning,
  fetchCatalogTree,
  downloadCatalogPlanningCsv,
} from '../../../api/admin';
import Button from '../../../components/ui/Button';
import EmptyState from '../../../components/ui/EmptyState';
import ErrorPanel from '../../../components/ui/ErrorPanel';
import LoadingState from '../../../components/ui/LoadingState';

/**
 * Catalog planning dashboard (/admin/catalog/planning). Sums requested
 * quantities (and request counts) across submitted Camper Care orders and
 * Maintenance tickets, grouped by item / request type / store, for planning.
 */

const STATUS_OPTIONS = [
  { value: 'all', label: 'All requests' },
  { value: 'fulfilled', label: 'Fulfilled only' },
  { value: 'open', label: 'Open only' },
];

const GROUP_OPTIONS = [
  { value: 'item', label: 'By item' },
  { value: 'request_type', label: 'By request type' },
  { value: 'store', label: 'By store' },
];

function isoDaysAgo(days) {
  const d = new Date();
  d.setDate(d.getDate() - days);
  return d.toISOString().slice(0, 10);
}

function todayIso() {
  return new Date().toISOString().slice(0, 10);
}

const DATE_PRESETS = [
  { id: '7', label: 'Last 7 days', range: () => ({ start: isoDaysAgo(6), end: todayIso() }) },
  { id: '30', label: 'Last 30 days', range: () => ({ start: isoDaysAgo(29), end: todayIso() }) },
  { id: '90', label: 'Last 90 days', range: () => ({ start: isoDaysAgo(89), end: todayIso() }) },
  { id: 'all', label: 'All time', range: () => ({ start: '', end: '' }) },
];

const SORTABLE_COLUMNS = [
  { key: 'label', label: 'Label', align: 'left' },
  { key: 'store', label: 'Store', align: 'left' },
  { key: 'request_type', label: 'Request type', align: 'left' },
  { key: 'quantity', label: 'Quantity', align: 'right' },
  { key: 'request_count', label: 'Requests', align: 'right' },
];

function controlClass() {
  return 'rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900 px-3 py-1.5 text-sm text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500';
}

function StatCard({ icon: Icon, label, value, iconClass, testId }) {
  return (
    <div className="flex items-center gap-3 rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 px-4 py-4">
      <span className={`inline-flex items-center justify-center w-10 h-10 rounded-lg ${iconClass}`}>
        <Icon size={20} aria-hidden="true" />
      </span>
      <div className="min-w-0">
        <p className="text-2xl font-bold leading-tight text-gray-900 dark:text-white" data-testid={testId}>{value}</p>
        <p className="text-xs text-gray-500 dark:text-gray-400 truncate">{label}</p>
      </div>
    </div>
  );
}

function PlanningChart({ rows }) {
  const canvasRef = useRef(null);
  const chartRef = useRef(null);

  useEffect(() => {
    if (!canvasRef.current) return undefined;
    if (chartRef.current) chartRef.current.destroy();
    const top = rows.slice(0, 20);
    chartRef.current = new ChartJS(canvasRef.current.getContext('2d'), {
      type: 'bar',
      data: {
        labels: top.map((r) => r.label),
        datasets: [{
          label: 'Quantity requested',
          data: top.map((r) => r.quantity),
          backgroundColor: '#6366f1',
          borderRadius: 4,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: { y: { beginAtZero: true, ticks: { precision: 0 } } },
      },
    });
    return () => {
      if (chartRef.current) {
        chartRef.current.destroy();
        chartRef.current = null;
      }
    };
  }, [rows]);

  return (
    <div className="h-72" data-testid="planning-chart">
      <canvas ref={canvasRef} />
    </div>
  );
}

export default function PlanningDashboard() {
  const [data, setData] = useState({ rows: [], totals: {} });
  const [stores, setStores] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [filters, setFilters] = useState({
    start: '', end: '', status: 'all', store: '', groupBy: 'item',
  });
  const [sort, setSort] = useState({ key: 'quantity', dir: 'desc' });

  useEffect(() => {
    fetchCatalogTree()
      .then((d) => setStores(d.stores || []))
      .catch(() => setStores([]));
  }, []);

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const res = await fetchCatalogPlanning(filters);
      setData(res);
    } catch (e) {
      setError(e?.response?.data?.detail || 'Failed to load planning data.');
    } finally {
      setLoading(false);
    }
  }, [filters]);

  useEffect(() => { load(); }, [load]);

  const setFilter = (k, v) => setFilters((f) => ({ ...f, [k]: v }));

  const applyPreset = (preset) => {
    const { start, end } = preset.range();
    setFilters((f) => ({ ...f, start, end }));
  };

  const activePreset = useMemo(() => {
    const match = DATE_PRESETS.find((p) => {
      const r = p.range();
      return r.start === filters.start && r.end === filters.end;
    });
    return match?.id || null;
  }, [filters.start, filters.end]);

  const toggleSort = (key) => {
    setSort((s) => {
      if (s.key !== key) {
        // Default to descending for numeric columns, ascending for text.
        return { key, dir: key === 'quantity' || key === 'request_count' ? 'desc' : 'asc' };
      }
      return { key, dir: s.dir === 'asc' ? 'desc' : 'asc' };
    });
  };

  const totals = data.totals || {};
  const rows = useMemo(() => {
    const base = data.rows || [];
    const dir = sort.dir === 'asc' ? 1 : -1;
    const numeric = sort.key === 'quantity' || sort.key === 'request_count';
    return [...base].sort((a, b) => {
      if (numeric) return dir * ((a[sort.key] ?? 0) - (b[sort.key] ?? 0));
      return dir * String(a[sort.key] ?? '').localeCompare(String(b[sort.key] ?? ''));
    });
  }, [data, sort]);

  return (
    <main className="grow px-4 sm:px-6 lg:px-8 py-6 w-full">
      <Link to="/admin/catalog" className="inline-flex items-center gap-1 text-sm text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 mb-4">
        <ArrowLeft size={14} /> Catalog
      </Link>

      <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between mb-6 gap-4">
        <div className="flex items-start gap-3">
          <span className="inline-flex items-center justify-center w-11 h-11 shrink-0 rounded-xl bg-violet-100 text-violet-700 dark:bg-violet-900/40 dark:text-violet-300">
            <BarChart3 size={22} aria-hidden="true" />
          </span>
          <div>
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
              Planning dashboard
            </h1>
            <p className="text-sm text-gray-500 dark:text-gray-400 mt-1 max-w-2xl">
              Quantities requested across Camper Care and Maintenance requests, for
              purchasing and staffing planning.
            </p>
          </div>
        </div>
        <Button
          variant="secondary"
          className="shrink-0"
          onClick={() => downloadCatalogPlanningCsv(filters)}
          data-testid="planning-export"
        >
          <Download size={16} /> Export CSV
        </Button>
      </div>

      <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-4 mb-6">
        <div className="flex flex-wrap items-center gap-2 mb-4">
          <span className="text-xs font-medium text-gray-500 dark:text-gray-400 mr-1">Range</span>
          {DATE_PRESETS.map((p) => (
            <button
              key={p.id}
              type="button"
              onClick={() => applyPreset(p)}
              data-testid={`planning-preset-${p.id}`}
              aria-pressed={activePreset === p.id}
              className={`px-3 py-1 rounded-full text-sm font-medium transition-colors ${
                activePreset === p.id
                  ? 'bg-blue-600 text-white'
                  : 'bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700'
              }`}
            >
              {p.label}
            </button>
          ))}
        </div>
        <div className="flex flex-wrap items-end gap-3">
          <div>
            <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">From</label>
            <input type="date" className={controlClass()} value={filters.start}
              onChange={(e) => setFilter('start', e.target.value)} data-testid="planning-start" />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">To</label>
            <input type="date" className={controlClass()} value={filters.end}
              onChange={(e) => setFilter('end', e.target.value)} data-testid="planning-end" />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">Status</label>
            <select className={controlClass()} value={filters.status}
              onChange={(e) => setFilter('status', e.target.value)} data-testid="planning-status">
              {STATUS_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">Group by</label>
            <select className={controlClass()} value={filters.groupBy}
              onChange={(e) => setFilter('groupBy', e.target.value)} data-testid="planning-groupby">
              {GROUP_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">Store</label>
            <select className={controlClass()} value={filters.store}
              onChange={(e) => setFilter('store', e.target.value)} data-testid="planning-store">
              <option value="">All stores</option>
              {stores.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
            </select>
          </div>
        </div>
      </div>

      {error && <div className="mb-4"><ErrorPanel>{error}</ErrorPanel></div>}

      {loading ? (
        <LoadingState>Loading planning data…</LoadingState>
      ) : rows.length === 0 ? (
        <div className="rounded-xl border border-dashed border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900">
          <EmptyState icon={BarChart3} title="No request data" data-testid="planning-empty">
            No requests match the current filters yet.
          </EmptyState>
        </div>
      ) : (
        <>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-6">
            <StatCard
              icon={Package}
              label="Total quantity requested"
              value={totals.quantity ?? 0}
              iconClass="bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300"
              testId="planning-total-qty"
            />
            <StatCard
              icon={ListChecks}
              label="Requests"
              value={totals.request_count ?? 0}
              iconClass="bg-sky-100 text-sky-700 dark:bg-sky-900/40 dark:text-sky-300"
            />
            <StatCard
              icon={Boxes}
              label="Groups"
              value={totals.group_count ?? rows.length}
              iconClass="bg-indigo-100 text-indigo-700 dark:bg-indigo-900/40 dark:text-indigo-300"
            />
          </div>

          <div className="grid grid-cols-1 xl:grid-cols-5 gap-6">
            <div className="xl:col-span-2 rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-4">
              <h2 className="text-sm font-semibold text-gray-900 dark:text-white mb-3">
                Top {Math.min(rows.length, 20)} by quantity
              </h2>
              <PlanningChart rows={rows} />
            </div>

            <div className="xl:col-span-3 bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full text-sm" data-testid="planning-table">
                  <thead className="bg-gray-50 dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
                    <tr>
                      {SORTABLE_COLUMNS.map((col) => {
                        const active = sort.key === col.key;
                        return (
                          <th
                            key={col.key}
                            scope="col"
                            aria-sort={active ? (sort.dir === 'asc' ? 'ascending' : 'descending') : 'none'}
                            className={`px-3 py-2 text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide cursor-pointer select-none hover:text-gray-900 dark:hover:text-gray-100 ${col.align === 'right' ? 'text-right' : 'text-left'}`}
                            onClick={() => toggleSort(col.key)}
                            data-testid={`planning-sort-${col.key}`}
                          >
                            <span className={`inline-flex items-center gap-1 ${col.align === 'right' ? 'flex-row-reverse' : ''}`}>
                              {col.label}
                              {active ? (
                                sort.dir === 'asc' ? <ChevronUp size={12} /> : <ChevronDown size={12} />
                              ) : (
                                <ChevronsUpDown size={12} className="opacity-30" />
                              )}
                            </span>
                          </th>
                        );
                      })}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100 dark:divide-gray-800">
                    {rows.map((r) => (
                      <tr key={r.key} className="hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors">
                        <td className="px-3 py-2.5 font-medium text-gray-900 dark:text-white">{r.label}</td>
                        <td className="px-3 py-2.5 text-gray-600 dark:text-gray-400">{r.store || '—'}</td>
                        <td className="px-3 py-2.5 text-gray-600 dark:text-gray-400">{r.request_type || '—'}</td>
                        <td className="px-3 py-2.5 text-right font-semibold text-gray-900 dark:text-white tabular-nums">{r.quantity}</td>
                        <td className="px-3 py-2.5 text-right text-gray-600 dark:text-gray-400 tabular-nums">{r.request_count}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </>
      )}
    </main>
  );
}
