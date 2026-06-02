import { useCallback, useEffect, useState } from 'react';
import { Download } from 'lucide-react';
import api from '../api';
import DashboardBody from './DashboardBody';

function todayIso() {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}

/**
 * TemplateDashboard — fetches and renders aggregated data for a single template.
 *
 * Thin data wrapper around the shared presentational <DashboardBody>; handles
 * the period controls, fetch, and CSV export for the template-scoped endpoint.
 *
 * Props:
 *   templateId  {number}  - the template to display
 *   language    {string}  - language code for labels (default 'en')
 *   title       {string}  - optional header title override
 *   subtitle    {string}  - optional subtitle
 *   accentColor {string}  - Tailwind color prefix for the refresh button (default 'indigo')
 */
export default function TemplateDashboard({
  templateId,
  language = 'en',
  title,
  subtitle,
  accentColor = 'indigo',
}) {
  const [periodEnd, setPeriodEnd] = useState(todayIso);
  const [periodDays, setPeriodDays] = useState(14);
  const [payload, setPayload] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    if (!templateId) return;
    setLoading(true);
    setError(null);
    try {
      const { data } = await api.get(`/api/v1/dashboards/template/${templateId}/`, {
        params: { period_end: periodEnd, period_days: periodDays },
      });
      setPayload(data);
    } catch (e) {
      const status = e.response?.status;
      if (status === 403) setError('access');
      else setError(e.response?.data?.detail || e.message || 'Failed to load dashboard');
      setPayload(null);
    } finally {
      setLoading(false);
    }
  }, [templateId, periodEnd, periodDays]);

  useEffect(() => {
    load();
  }, [load]);

  const exportUrl = templateId
    ? `/api/v1/dashboards/template/${templateId}/export/?period_end=${periodEnd}&period_days=${periodDays}`
    : null;

  return (
    <div>
      {/* Controls row */}
      <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        {(title || payload?.template?.name) && (
          <div>
            <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
              {title ?? payload?.template?.name}
            </h2>
            {subtitle && (
              <p className="text-sm text-gray-500 dark:text-gray-400 mt-0.5">{subtitle}</p>
            )}
          </div>
        )}
        <div className="flex flex-wrap items-center gap-3">
          <label className="flex items-center gap-2 text-sm text-gray-700 dark:text-gray-300">
            <span>Period ends</span>
            <input
              type="date"
              value={periodEnd}
              onChange={(e) => setPeriodEnd(e.target.value)}
              className="rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-2 py-1 text-sm"
            />
          </label>
          <label className="flex items-center gap-2 text-sm text-gray-700 dark:text-gray-300">
            <span>Days</span>
            <select
              value={periodDays}
              onChange={(e) => setPeriodDays(Number(e.target.value))}
              className="rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-2 py-1 text-sm"
            >
              {[7, 14, 30, 60, 90].map((d) => (
                <option key={d} value={d}>{d}</option>
              ))}
            </select>
          </label>
          <button
            type="button"
            onClick={load}
            className={`rounded-md bg-${accentColor}-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-${accentColor}-500`}
          >
            Refresh
          </button>
          {exportUrl && payload?.summary?.response_count > 0 && (
            <a
              href={exportUrl}
              download
              className="flex items-center gap-1.5 rounded-md border border-gray-300 dark:border-gray-600 px-3 py-1.5 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800"
            >
              <Download size={14} />
              CSV
            </a>
          )}
        </div>
      </div>

      {loading && <p className="text-gray-500 dark:text-gray-400 text-sm">Loading…</p>}

      {!loading && error === 'access' && (
        <div className="rounded-lg border border-amber-200 dark:border-amber-900/40 bg-amber-50 dark:bg-amber-900/20 p-4 text-amber-900 dark:text-amber-100 text-sm">
          <p className="font-medium">Access restricted</p>
          <p className="mt-1">You do not have permission to view this dashboard.</p>
        </div>
      )}

      {!loading && error && error !== 'access' && (
        <p className="text-rose-600 dark:text-rose-400 text-sm">{error}</p>
      )}

      {!loading && payload && <DashboardBody payload={payload} language={language} />}
    </div>
  );
}
