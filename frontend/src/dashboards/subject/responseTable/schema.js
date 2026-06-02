/**
 * Schema-aware helpers shared between the LT Responses table and the
 * per-subject dashboard form-responses widgets. Keeping these in one
 * module ensures both pages render reflections identically (column
 * derivation, flag detection, colour tiering).
 */

/** Pick the localised string for a field prompt / label / option. */
export function pickLabel(loc, language, fallback = '') {
  if (!loc) return fallback;
  if (typeof loc === 'string') return loc;
  return loc[language] ?? loc.en ?? Object.values(loc)[0] ?? fallback;
}

/** A field's option set is yes/no when it has exactly two options whose
 *  values lexically match {yes, no} (case-insensitive). */
export function isYesNoOptions(options) {
  if (!Array.isArray(options) || options.length !== 2) return false;
  const vals = new Set(options.map((o) => String(o.value ?? '').toLowerCase()));
  return vals.has('yes') && vals.has('no');
}

/**
 * Derive renderable sections from a template schema:
 *   - ratingCols: one entry per (sub-)dimension (rating_group categories
 *     expanded into siblings); used as table columns.
 *   - flagFields: yes/no single_choice fields surfaced as KPI cards +
 *     per-row flag chips.
 *   - chipFields: other single_choice / multi_choice fields, shown as
 *     small chips inside the Description cell.
 *   - descTextFields: textarea / text fields, stacked inside the
 *     Description cell.
 */
export function deriveSchemaSections(schema, language = 'en') {
  const fields = schema?.fields ?? [];
  const ratingCols = [];
  const flagFields = [];
  const chipFields = [];
  const descTextFields = [];

  for (const f of fields) {
    const label = pickLabel(f.prompts ?? f.labels, language, f.key);
    if (f.type === 'rating_group' && Array.isArray(f.categories)) {
      const scaleMax = Array.isArray(f.scale) ? Number(f.scale[1]) || 5 : 5;
      for (const cat of f.categories) {
        ratingCols.push({
          key: f.key,
          subKey: cat.key,
          label: pickLabel(cat.labels, language, cat.key),
          groupLabel: label,
          scaleMax,
        });
      }
      continue;
    }
    if (f.type === 'single_rating') {
      const scaleMax = Array.isArray(f.scale) ? Number(f.scale[1]) || 5 : 5;
      ratingCols.push({ key: f.key, label, scaleMax });
      continue;
    }
    if (f.type === 'single_choice' || f.type === 'multi_choice') {
      const options = (f.options ?? []).map((o) => ({
        value: o.value,
        label: pickLabel(o.labels ?? o.prompts, language, String(o.value)),
      }));
      if (f.type === 'single_choice' && isYesNoOptions(f.options)) {
        flagFields.push({ key: f.key, label, yesValue: 'yes', options });
      } else {
        chipFields.push({ key: f.key, label, options });
      }
      continue;
    }
    if (f.type === 'textarea' || f.type === 'text' || f.type === 'long_text') {
      descTextFields.push({ key: f.key, label });
    }
  }
  return { ratingCols, flagFields, chipFields, descTextFields };
}

const GRID_META_FIELD_TYPES = new Set(['section_header', 'instructions']);
const SCORED_FIELD_TYPES = new Set(['single_rating', 'rating_group']);

/** Short column title for table headers (e.g. rating_group category labels). */
export function shortColumnHeader(header, fieldType) {
  if (!header) return '';
  if (fieldType === 'rating_group') {
    return header.split(/\s+[—–-]\s+/)[0]?.trim() || header;
  }
  if (header.length > 28) return `${header.slice(0, 26)}…`;
  return header;
}

/**
 * Ordered grid columns mirroring ``iter_grid_fields`` / ScoreGrid: one column
 * per scored category plus every other answerable field in template order.
 */
export function deriveGridColumns(schema, language = 'en') {
  const columns = [];
  for (const f of schema?.fields ?? []) {
    if (!f || GRID_META_FIELD_TYPES.has(f.type)) continue;
    const fkey = f.key;
    if (!fkey) continue;
    if (f.type === 'rating_group' && Array.isArray(f.categories)) {
      const scaleMax = Array.isArray(f.scale) ? Number(f.scale[1]) || 5 : 5;
      for (const cat of f.categories) {
        const header = pickLabel(cat.labels, language, cat.key);
        columns.push({
          label: `${fkey}__${cat.key}`,
          field_key: fkey,
          field_type: 'rating_group',
          category_key: cat.key,
          scale_max: scaleMax,
          header,
        });
      }
      continue;
    }
    if (f.type === 'single_rating') {
      const header = pickLabel(f.prompts ?? f.labels, language, fkey);
      columns.push({
        label: fkey,
        field_key: fkey,
        field_type: 'single_rating',
        category_key: null,
        scale_max: Array.isArray(f.scale) ? Number(f.scale[1]) || 5 : 5,
        header,
      });
      continue;
    }
    const header = pickLabel(f.prompts ?? f.labels, language, fkey);
    columns.push({
      label: fkey,
      field_key: fkey,
      field_type: f.type,
      category_key: null,
      scale_max: null,
      header,
    });
  }
  return columns;
}

/** Read one grid cell from a reflection answers blob. */
export function gridCellValue(answers, col) {
  if (!answers || !col) return null;
  if (col.field_type === 'rating_group' && col.category_key) {
    const block = answers[col.field_key];
    if (block && typeof block === 'object') return block[col.category_key] ?? null;
    return null;
  }
  return answers[col.field_key] ?? null;
}

export function formatGridDisplayValue(value, fieldType) {
  if (value == null || value === '') return null;
  if (fieldType === 'yes_no' || fieldType === 'single_choice') {
    const s = String(value).toLowerCase();
    if (s === 'yes' || s === 'true') return 'Yes';
    if (s === 'no' || s === 'false') return 'No';
  }
  if (Array.isArray(value)) {
    return value.map((v) => String(v).trim()).filter(Boolean).join(', ') || null;
  }
  if (typeof value === 'boolean') return value ? 'Yes' : 'No';
  return String(value);
}

export function isScoredGridColumn(col) {
  return SCORED_FIELD_TYPES.has(col?.field_type);
}

/** Map a ``rating_series`` API label (field key or ``field__category``) to a
 *  short display name, e.g. ``camper_scores__behavior`` → ``Behavior``. */
export function seriesDisplayLabel(seriesLabel, ratingCols) {
  const col = ratingCols.find((c) =>
    c.subKey ? `${c.key}__${c.subKey}` === seriesLabel : c.key === seriesLabel,
  );
  if (!col) return seriesLabel;
  const short = col.label.split(/\s+[—–-]\s+/)[0]?.trim();
  return short || col.label;
}

/**
 * FA4 rating palette (decisions.md). Inline hex matches the per-row
 * implementation in ``components/bunklogs/AdminBunkLogItem.jsx`` so the
 * LT responses page reads consistently with the legacy bunk-log view.
 *
 * Non-5-point scales are normalised onto the 5-tier palette by ratio
 * (e.g. value 2 on a 4-point scale -> tier 3 / yellow) so a colour-blind
 * user can compare across templates with different scale lengths.
 */
export function ratingTierClass(value, scaleMax = 5) {
  if (value == null || !Number.isFinite(Number(value))) return 'bg-gray-100 text-gray-600';
  const ratio = Number(value) / (scaleMax || 5);
  const tier = Math.max(1, Math.min(5, Math.round(ratio * 5)));
  if (tier === 1) return 'bg-[#e86946] text-white';
  if (tier === 2) return 'bg-[#de8d6f] text-white';
  if (tier === 3) return 'bg-[#e5e825] text-black';
  if (tier === 4) return 'bg-[#90d258] text-white';
  return 'bg-[#18d128] text-white';
}

export function getInitials(name) {
  if (!name) return '?';
  const parts = String(name).trim().split(/\s+/);
  const first = parts[0]?.[0] ?? '';
  const last = parts.length > 1 ? parts[parts.length - 1][0] : '';
  return (first + last).toUpperCase() || '?';
}

export function formatShortDate(yyyymmdd) {
  if (!yyyymmdd) return '';
  const [y, m, d] = String(yyyymmdd).split('-').map(Number);
  if (!y || !m || !d) return yyyymmdd;
  const dt = new Date(Date.UTC(y, m - 1, d));
  return dt.toLocaleDateString('en-US', {
    year: 'numeric', month: 'long', day: 'numeric', timeZone: 'UTC',
  });
}
