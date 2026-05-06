import { useCallback, useEffect, useState } from 'react';
import { ChevronDown, ChevronUp, Download } from 'lucide-react';
import api from '../api';
import { partitionFields, resolveWidgetName } from './widgetMap';
import * as Widgets from './widgets/index';

function pct(n) {
  if (n == null || Number.isNaN(n)) return '—';
  return `${Math.round(n * 1000) / 10}%`;
}

function todayIso() {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}

/**
 * Resolve a field's human-readable label from the schema.
 * Tries en prompt, then field key.
 */
function fieldLabel(fieldKey, schemaFields, language = 'en') {
  const schemaField = (schemaFields ?? []).find((f) => f.key === fieldKey);
  if (!schemaField) return fieldKey;
  const prompts = schemaField.prompts;
  if (prompts) {
    return prompts[language] || prompts.en || fieldKey;
  }
  return schemaField.name || fieldKey;
}

/** Render a single widget by name. */
function Widget({ widgetName, field, schemaField, schemaFields, language }) {
  const Component = Widgets[widgetName];
  if (!Component) return null;
  const label = fieldLabel(field.key, schemaFields, language);

  // Pass scale info from schema if available (needed by rating widgets)
  const enriched = {
    ...field,
    scale: schemaField?.scale ?? field?.scale,
    categories: schemaField?.categories ?? field?.categories,
  };
  return <Component field={enriched} label={label} />;
}

/**
 * SummaryBar — top header stats: completion, responses, persons.
 */
function SummaryBar({ summary, period }) {
  return (
    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-6">
      <div className="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900/40 px-4 py-3">
        <p className="text-xs uppercase text-gray-500 dark:text-gray-400">Completion</p>
        <p className="text-xl font-semibold text-gray-900 dark:text-white">
          {pct(summary?.completion_rate)}
        </p>
      </div>
      <div className="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900/40 px-4 py-3">
        <p className="text-xs uppercase text-gray-500 dark:text-gray-400">Responses</p>
        <p className="text-xl font-semibold text-gray-900 dark:text-white">{summary?.response_count ?? '—'}</p>
      </div>
      <div className="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900/40 px-4 py-3">
        <p className="text-xs uppercase text-gray-500 dark:text-gray-400">Respondents</p>
        <p className="text-xl font-semibold text-gray-900 dark:text-white">{summary?.person_count ?? '—'}</p>
      </div>
      <div className="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900/40 px-4 py-3">
        <p className="text-xs uppercase text-gray-500 dark:text-gray-400">Period</p>
        <p className="text-sm font-medium text-gray-700 dark:text-gray-300 truncate">
          {period?.current_start} → {period?.current_end}
        </p>
      </div>
    </div>
  );
}

/**
 * TemplateDashboard — renders aggregated data for a single template.
 *
 * Props:
 *   templateId  {number}  - the template to display
 *   language    {string}  - language code for labels (default 'en')
 *   title       {string}  - optional header title override
 *   subtitle    {string}  - optional subtitle
 *   accentColor {string}  - Tailwind color prefix for the export button, e.g. 'indigo' (default)
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
  const [showGeneric, setShowGeneric] = useState(false);

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

  const schemaFields = payload?.template?.schema?.fields ?? [];
  const { tagged, generic } = partitionFields(payload?.fields ?? []);

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

      {!loading && payload && (
        <>
          <SummaryBar summary={payload.summary} period={payload.period} />

          {/* Role-tagged widgets */}
          {tagged.length > 0 && (
            <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4 mb-6">
              {tagged.map((field) => {
                const widgetName = resolveWidgetName(field);
                if (!widgetName) return null;
                const schemaField = schemaFields.find((f) => f.key === field.key);
                return (
                  <Widget
                    key={field.key}
                    widgetName={widgetName}
                    field={field}
                    schemaField={schemaField}
                    schemaFields={schemaFields}
                    language={language}
                  />
                );
              })}
            </div>
          )}

          {/* Generic widgets in disclosure */}
          {generic.length > 0 && (
            <div className="mt-4">
              <button
                type="button"
                className="flex items-center gap-2 text-sm font-medium text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white mb-3"
                onClick={() => setShowGeneric((v) => !v)}
                aria-expanded={showGeneric}
              >
                {showGeneric ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                {showGeneric ? 'Hide' : 'Show'} additional fields ({generic.length})
              </button>
              {showGeneric && (
                <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4">
                  {generic.map((field) => {
                    const widgetName = resolveWidgetName(field);
                    if (!widgetName) return null;
                    const schemaField = schemaFields.find((f) => f.key === field.key);
                    return (
                      <Widget
                        key={field.key}
                        widgetName={widgetName}
                        field={field}
                        schemaField={schemaField}
                        schemaFields={schemaFields}
                        language={language}
                      />
                    );
                  })}
                </div>
              )}
            </div>
          )}

          {tagged.length === 0 && generic.length === 0 && (
            <p className="text-sm text-gray-400 dark:text-gray-500">
              No field data to display for this period.
            </p>
          )}
        </>
      )}
    </div>
  );
}
