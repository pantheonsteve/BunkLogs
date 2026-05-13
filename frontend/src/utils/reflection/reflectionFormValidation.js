const FIELD_TYPES = new Set([
  'text',
  'textarea',
  'text_list',
  'rating_group',
  'multiple_choice',
  'single_choice',
  'number',
  'date',
  'yes_no',
  'single_rating',
  'section_header',
  'instructions',
]);

const META_FIELD_TYPES = new Set(['section_header', 'instructions']);

/**
 * Client-side validation aligned with backend validate_reflection_answers.
 * @returns {{ ok: boolean, errors: Record<string, string> }}
 */
export function validateReflectionAnswers(schema, answers) {
  const errors = {};
  if (!answers || typeof answers !== 'object' || Array.isArray(answers)) {
    return { ok: false, errors: { form: 'Answers must be an object.' } };
  }
  const fields = schema?.fields;
  if (!Array.isArray(fields)) {
    return { ok: false, errors: { form: 'Invalid template schema.' } };
  }

  for (let i = 0; i < fields.length; i++) {
    const field = fields[i];
    if (!field || typeof field !== 'object') {
      errors[`field_${i}`] = 'Invalid field definition.';
      continue;
    }
    const key = field.key;
    const ftype = field.type;
    const required = field.required !== false;

    if (typeof key !== 'string' || !key.trim()) {
      errors[`field_${i}`] = 'Invalid field key.';
      continue;
    }
    if (!FIELD_TYPES.has(ftype)) {
      errors[key] = 'Unknown field type.';
      continue;
    }

    if (META_FIELD_TYPES.has(ftype)) {
      continue;
    }

    if (!(key in answers)) {
      if (!required) continue;
      errors[key] = 'This field is required.';
      continue;
    }

    const value = answers[key];
    if (ftype === 'text' || ftype === 'textarea' || ftype === 'single_choice') {
      if (typeof value !== 'string') {
        errors[key] = 'Must be text.';
        continue;
      }
      if (required && !value.trim()) {
        errors[key] = 'This field is required.';
        continue;
      }
      const max = field.max_length;
      if (typeof max === 'number' && value.length > max) {
        errors[key] = `Max ${max} characters.`;
      }
    } else if (ftype === 'text_list') {
      if (!Array.isArray(value) || !value.every((x) => typeof x === 'string')) {
        errors[key] = 'Must be a list of text lines.';
        continue;
      }
      const nonEmpty = value.filter((x) => x.trim()).length;
      const minItems = field.min_items;
      const maxItems = field.max_items;
      if (typeof minItems === 'number' && nonEmpty < minItems) {
        errors[key] = `Enter at least ${minItems} items.`;
      }
      if (typeof maxItems === 'number' && value.length > maxItems) {
        errors[key] = `At most ${maxItems} items.`;
      }
      if (required && nonEmpty === 0) {
        errors[key] = 'This field is required.';
      }
    } else if (ftype === 'multiple_choice') {
      if (!Array.isArray(value)) {
        errors[key] = 'Select one or more options.';
        continue;
      }
      if (required && value.length === 0) {
        errors[key] = 'Select at least one option.';
      }
    } else if (ftype === 'rating_group') {
      if (!value || typeof value !== 'object' || Array.isArray(value)) {
        errors[key] = 'Ratings must be provided for each category.';
        continue;
      }
      const cats = field.categories;
      if (!Array.isArray(cats)) {
        errors[key] = 'Invalid template categories.';
        continue;
      }
      const catKeys = new Set(
        cats.filter((c) => c && typeof c === 'object' && typeof c.key === 'string').map((c) => c.key),
      );
      for (const ck of Object.keys(value)) {
        if (!catKeys.has(ck)) {
          errors[key] = `Unknown category: ${ck}`;
          break;
        }
        const r = value[ck];
        if (typeof r === 'boolean' || (typeof r !== 'number' && typeof r !== 'string')) {
          errors[key] = 'Each rating must be a number.';
          break;
        }
        const num = typeof r === 'string' ? Number(r) : r;
        if (!Number.isFinite(num)) {
          errors[key] = 'Each rating must be a number.';
          break;
        }
      }
      if (errors[key]) continue;
      if (required) {
        for (const ck of catKeys) {
          if (!(ck in value)) {
            errors[key] = 'Rate every category.';
            break;
          }
        }
      }
    } else if (ftype === 'number') {
      if (value === '' || value === null || value === undefined) {
        if (required) errors[key] = 'This field is required.';
        continue;
      }
      const num = typeof value === 'string' ? Number(value) : value;
      if (typeof num !== 'number' || !Number.isFinite(num)) {
        errors[key] = 'Must be a number.';
      }
    } else if (ftype === 'date') {
      if (typeof value !== 'string' || !value.trim()) {
        if (required) errors[key] = 'This field is required.';
        continue;
      }
      if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) {
        errors[key] = 'Use the date picker to choose a valid date.';
      }
    } else if (ftype === 'yes_no') {
      let raw = value;
      if (raw && typeof raw === 'object' && !Array.isArray(raw)) {
        raw = raw.value;
      }
      if (raw === undefined || raw === null || raw === '') {
        if (required) errors[key] = 'This field is required.';
        continue;
      }
      if (raw !== 'yes' && raw !== 'no' && raw !== true && raw !== false) {
        errors[key] = 'Answer must be Yes or No.';
      }
    } else if (ftype === 'single_rating') {
      if (value === '' || value === null || value === undefined) {
        if (required) errors[key] = 'This field is required.';
        continue;
      }
      const num = typeof value === 'string' ? Number(value) : value;
      if (typeof num !== 'number' || !Number.isFinite(num)) {
        errors[key] = 'Rating must be a number.';
      }
    }
  }

  return { ok: Object.keys(errors).length === 0, errors };
}

export function buildDefaultAnswers(schema) {
  const out = {};
  const fields = schema?.fields;
  if (!Array.isArray(fields)) return out;
  for (const field of fields) {
    if (!field?.key) continue;
    const { key, type: ftype } = field;
    if (META_FIELD_TYPES.has(ftype)) continue;
    if (
      ftype === 'text' ||
      ftype === 'textarea' ||
      ftype === 'single_choice' ||
      ftype === 'date'
    ) {
      out[key] = '';
    } else if (ftype === 'text_list') {
      const n = Math.max(1, field.min_items || 1);
      const cap = typeof field.max_items === 'number' ? field.max_items : n;
      out[key] = Array.from({ length: Math.min(n, cap) }, () => '');
    } else if (ftype === 'multiple_choice') {
      out[key] = [];
    } else if (ftype === 'rating_group') {
      out[key] = {};
    } else if (ftype === 'number' || ftype === 'single_rating') {
      out[key] = '';
    } else if (ftype === 'yes_no') {
      out[key] = '';
    }
  }
  return out;
}

export function ratingScaleValues(field) {
  if (Array.isArray(field.scale) && field.scale.length > 0) {
    return field.scale.map((x) => Number(x));
  }
  const labels = field.scale_labels && typeof field.scale_labels === 'object'
    ? Object.values(field.scale_labels)[0]
    : null;
  if (Array.isArray(labels) && labels.length > 0) {
    return labels.map((_, i) => i + 1);
  }
  return [1, 2, 3, 4];
}

export function localizedOptionLabel(option, fallback = '') {
  if (!option?.labels || typeof option.labels !== 'object') return fallback;
  const first = Object.values(option.labels)[0];
  return typeof first === 'string' ? first : fallback;
}
