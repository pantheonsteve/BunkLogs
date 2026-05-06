/**
 * Maps dashboard_role values and generic field types to widget component names.
 *
 * Role-tagged fields get polished widgets; untagged fields get generic widgets.
 * The widget components themselves live alongside this file.
 *
 * dashboard_role → widget name
 * field type (no role) → widget name
 */

export const ROLE_WIDGET_MAP = {
  primary_rating: 'RatingHeadlineWidget',
  category_ratings: 'CategoryRadarWidget',
  wins: 'HighlightFeedWidget',
  improvements: 'ImprovementFeedWidget',
  open_concern: 'ConcernQueueWidget',
};

export const TYPE_WIDGET_MAP = {
  text: 'TextResponseListWidget',
  textarea: 'TextResponseListWidget',
  text_list: 'ItemCloudWidget',
  single_rating: 'RatingDistributionWidget',
  rating_group: 'RatingTableWidget',
  single_choice: 'ChoiceBarChartWidget',
  multiple_choice: 'ChoiceBarChartWidget',
  yes_no: 'YesNoBreakdownWidget',
  number: 'NumberSparklineWidget',
  date: 'DateHistogramWidget',
};

/** Fields that should never be rendered in dashboards. */
export const META_FIELD_TYPES = new Set(['section_header', 'instructions']);

/**
 * Given a field descriptor from the aggregation response, return the widget
 * name to use. Returns null for meta fields.
 *
 * @param {{ type: string, dashboard_role?: string|null }} field
 * @returns {string|null}
 */
export function resolveWidgetName(field) {
  if (!field) return null;
  if (META_FIELD_TYPES.has(field.type)) return null;
  if (field.dashboard_role && ROLE_WIDGET_MAP[field.dashboard_role]) {
    return ROLE_WIDGET_MAP[field.dashboard_role];
  }
  return TYPE_WIDGET_MAP[field.type] ?? 'TextResponseListWidget';
}

/**
 * Partition fields into role-tagged (to show first) and generic (to show in
 * a "More fields" disclosure).
 *
 * @param {Array} fields - array of { key, type, dashboard_role, data }
 * @returns {{ tagged: Array, generic: Array }}
 */
export function partitionFields(fields) {
  const tagged = [];
  const generic = [];
  for (const field of fields ?? []) {
    if (META_FIELD_TYPES.has(field.type)) continue;
    if (field.dashboard_role && ROLE_WIDGET_MAP[field.dashboard_role]) {
      tagged.push(field);
    } else {
      generic.push(field);
    }
  }
  return { tagged, generic };
}
