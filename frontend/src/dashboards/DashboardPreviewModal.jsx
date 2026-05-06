import { X } from 'lucide-react';
import { useMemo } from 'react';
import { partitionFields, resolveWidgetName } from './widgetMap';
import * as Widgets from './widgets/index';

/**
 * Generate synthetic sample data for a single field so the dashboard preview
 * shows realistic widget output even before any real reflections exist.
 */
function syntheticData(field) {
  const ftype = field.type;
  const scale = field.scale ?? [1, 5];
  const scaleMin = Number(scale[0]);
  const scaleMax = Number(scale[scale.length - 1]);
  const midHigh = scaleMin + Math.round((scaleMax - scaleMin) * 0.7);
  const midLow = scaleMin + Math.round((scaleMax - scaleMin) * 0.4);

  if (ftype === 'single_rating') {
    const dist = {};
    for (let i = scaleMin; i <= scaleMax; i++) dist[String(i)] = 0;
    dist[String(midHigh)] = 4;
    dist[String(midHigh - 1)] = 2;
    dist[String(midLow)] = 1;
    return {
      mean: midHigh - 0.3,
      prior_mean: midHigh - 0.8,
      trend: 'up',
      response_count: 7,
      distribution: dist,
    };
  }

  if (ftype === 'rating_group') {
    const categories = (field.categories ?? []).map((cat) => {
      const dist = {};
      for (let i = scaleMin; i <= scaleMax; i++) dist[String(i)] = 0;
      dist[String(midHigh)] = 3;
      dist[String(midHigh - 1)] = 2;
      return {
        key: cat.key,
        mean: midHigh - 0.4,
        prior_mean: midHigh - 0.9,
        trend: 'up',
        response_count: 5,
        distribution: dist,
      };
    });
    return { categories };
  }

  if (ftype === 'text_list') {
    return {
      items: [
        { text: 'Teamwork', count: 5 },
        { text: 'Communication', count: 3 },
        { text: 'Creativity', count: 2 },
        { text: 'Punctuality', count: 1 },
      ],
      total_mentions: 11,
    };
  }

  if (ftype === 'text' || ftype === 'textarea') {
    return {
      items: [
        {
          reflection_id: 1,
          person_id: 1,
          period_end: '2026-06-14',
          text: 'Sample response text for dashboard preview.',
          is_read: false,
        },
        {
          reflection_id: 2,
          person_id: 2,
          period_end: '2026-06-13',
          text: 'Another example response shown in the preview.',
          is_read: false,
        },
      ],
      total: 2,
    };
  }

  if (ftype === 'yes_no') {
    return { yes_count: 6, no_count: 2, yes_pct: 0.75 };
  }

  if (ftype === 'single_choice' || ftype === 'multiple_choice') {
    const opts = (field.options ?? []).slice(0, 4);
    const choices =
      opts.length > 0
        ? opts.map((o, i) => ({
            option: typeof o === 'string' ? o : (o.key ?? o.label ?? `Option ${i + 1}`),
            count: Math.max(1, 5 - i),
          }))
        : [
            { option: 'Option A', count: 5 },
            { option: 'Option B', count: 3 },
            { option: 'Option C', count: 1 },
          ];
    return { choices, response_count: choices.reduce((s, c) => s + c.count, 0) };
  }

  if (ftype === 'number') {
    return { mean: 42.5, min: 30, max: 60, response_count: 8 };
  }

  if (ftype === 'date') {
    return { values: ['2026-06-10', '2026-06-11', '2026-06-12'], response_count: 3 };
  }

  return null;
}

/**
 * Build synthetic aggregated fields from a raw schema (as used in the editor,
 * with _id keys present).
 */
function buildSyntheticFields(schemaFields) {
  return (schemaFields ?? [])
    .filter((f) => f.type && f.type !== 'section_header' && f.type !== 'instructions')
    .map((f) => ({
      key: f.key || '(unnamed)',
      type: f.type,
      dashboard_role: f.dashboard_role ?? null,
      data: syntheticData(f),
    }));
}

function Widget({ widgetName, field, schemaField, schemaFields, language }) {
  const Component = Widgets[widgetName];
  if (!Component) return null;
  const prompts = schemaField?.prompts;
  const label = (prompts && (prompts[language] || prompts.en)) || field.key;
  const enriched = {
    ...field,
    scale: schemaField?.scale ?? field?.scale,
    categories: schemaField?.categories ?? field?.categories,
  };
  return <Component field={enriched} label={label} />;
}

/**
 * DashboardPreviewModal — shows what the dashboard would look like for the
 * current template schema, using synthetic sample data.
 *
 * Props:
 *   schemaFields  {Array}   raw fields from the editor (with _id, type, key, etc.)
 *   language      {string}  currently selected preview language
 *   onClose       {fn}
 */
export default function DashboardPreviewModal({ schemaFields, language = 'en', onClose }) {
  const syntheticFields = useMemo(
    () => buildSyntheticFields(schemaFields),
    [schemaFields],
  );

  const { tagged, generic } = useMemo(
    () => partitionFields(syntheticFields),
    [syntheticFields],
  );

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
      role="dialog"
      aria-modal="true"
      aria-label="Dashboard preview"
    >
      <div className="bg-white dark:bg-gray-900 rounded-2xl shadow-2xl w-full max-w-4xl max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 dark:border-gray-700">
          <div>
            <h2 className="text-base font-semibold text-gray-900 dark:text-white">Dashboard preview</h2>
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
              Synthetic sample data — shows how widgets will appear with real responses.
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="text-gray-400 hover:text-gray-700 dark:hover:text-gray-200"
            aria-label="Close preview"
          >
            <X size={20} />
          </button>
        </div>

        {/* Body */}
        <div className="overflow-y-auto p-6 space-y-6">
          {tagged.length > 0 && (
            <section>
              <p className="text-xs font-semibold uppercase tracking-wide text-gray-400 dark:text-gray-500 mb-3">
                Role-tagged widgets
              </p>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
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
            </section>
          )}

          {generic.length > 0 && (
            <section>
              <p className="text-xs font-semibold uppercase tracking-wide text-gray-400 dark:text-gray-500 mb-3">
                Generic widgets (untagged fields)
              </p>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
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
            </section>
          )}

          {tagged.length === 0 && generic.length === 0 && (
            <p className="text-sm text-gray-400 dark:text-gray-500 text-center py-8">
              Add fields to your template to see a dashboard preview.
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
