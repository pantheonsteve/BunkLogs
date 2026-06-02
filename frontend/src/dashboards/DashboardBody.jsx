import { useState } from 'react';
import { ChevronDown, ChevronUp } from 'lucide-react';
import { partitionFields, resolveWidgetName } from './widgetMap';
import * as Widgets from './widgets/index';

export function pct(n) {
  if (n == null || Number.isNaN(n)) return '—';
  return `${Math.round(n * 1000) / 10}%`;
}

/** Resolve a field's human-readable label from the schema (en prompt, then key). */
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
  const enriched = {
    ...field,
    scale: schemaField?.scale ?? field?.scale,
    categories: schemaField?.categories ?? field?.categories,
  };
  return <Component field={enriched} label={label} />;
}

/** SummaryBar — top header stats: completion, responses, respondents, period. */
export function SummaryBar({ summary, period }) {
  return (
    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-6">
      <div className="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900/40 px-4 py-3">
        <p className="text-xs uppercase text-gray-500 dark:text-gray-400">Completion</p>
        <p className="text-xl font-semibold text-gray-900 dark:text-white">
          {pct(summary?.completion_rate)}
        </p>
        {summary?.expected_count != null && (
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
            {summary?.submitted_count ?? 0} / {summary.expected_count} submitted
          </p>
        )}
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
 * DashboardBody — presentational renderer for an aggregation payload.
 *
 * Shared by the legacy TemplateDashboard (template-scoped) and the new
 * assignment-centric Reflections Dashboard. Renders the SummaryBar, the
 * role-tagged widget grid, and a disclosure for generic fields.
 *
 * Props:
 *   payload      {object}  - { template, period, summary, fields }
 *   language     {string}  - language code for labels (default 'en')
 *   showSummary  {boolean} - render the SummaryBar (default true). Set false
 *                            when a parent already shows summary stats.
 */
export default function DashboardBody({ payload, language = 'en', showSummary = true }) {
  const [showGeneric, setShowGeneric] = useState(false);
  if (!payload) return null;

  const schemaFields = payload?.template?.schema?.fields ?? [];
  const { tagged, generic } = partitionFields(payload?.fields ?? []);

  return (
    <>
      {showSummary && <SummaryBar summary={payload.summary} period={payload.period} />}

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
  );
}
