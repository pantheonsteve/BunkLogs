import { describe, it, expect } from 'vitest';
import {
  validateReflectionAnswers,
  buildDefaultAnswers,
  prepareReflectionAnswersForSubmit,
  ratingScaleValues,
  localizedOptionLabel,
} from './reflectionFormValidation';

describe('validateReflectionAnswers', () => {
  const schema = {
    fields: [
      { key: 'a', type: 'text', prompts: { en: 'A' } },
      { key: 'b', type: 'textarea', required: false, prompts: { en: 'B' } },
      {
        key: 'r',
        type: 'rating_group',
        scale_labels: { en: ['L', 'M', 'H'] },
        categories: [{ key: 'x', labels: { en: 'X' } }],
      },
    ],
  };

  it('requires present keys', () => {
    const r = validateReflectionAnswers(schema, { r: { x: 2 } });
    expect(r.ok).toBe(false);
    expect(r.errors.a).toBeDefined();
  });

  it('allows optional empty textarea', () => {
    const r = validateReflectionAnswers(schema, { a: 'hi', r: { x: 1 } });
    expect(r.ok).toBe(true);
  });

  it('rejects incomplete rating_group', () => {
    const r = validateReflectionAnswers(schema, { a: 'hi', r: {} });
    expect(r.ok).toBe(false);
    expect(r.errors.r).toBeDefined();
  });
});

describe('buildDefaultAnswers', () => {
  it('builds shapes per type', () => {
    const schema = {
      fields: [
        { key: 't', type: 'text', prompts: { en: 't' } },
        { key: 'tl', type: 'text_list', min_items: 2, prompts: { en: 'tl' } },
        { key: 'mc', type: 'multiple_choice', prompts: { en: 'm' } },
        {
          key: 'rg',
          type: 'rating_group',
          scale_labels: { en: ['a'] },
          categories: [{ key: 'c', labels: { en: 'c' } }],
        },
      ],
    };
    const a = buildDefaultAnswers(schema);
    expect(a.t).toBe('');
    expect(a.tl).toEqual(['', '']);
    expect(a.mc).toEqual([]);
    expect(a.rg).toEqual({});
  });
});

describe('ratingScaleValues', () => {
  it('uses explicit scale', () => {
    expect(ratingScaleValues({ scale: [1, 4] })).toEqual([1, 4]);
  });

  it('derives from scale_labels row length', () => {
    expect(ratingScaleValues({ scale_labels: { en: ['a', 'b', 'c'] } })).toEqual([1, 2, 3]);
  });
});

describe('localizedOptionLabel', () => {
  it('reads first label value', () => {
    expect(localizedOptionLabel({ key: 'k', labels: { en: 'Hello' } }, 'k')).toBe('Hello');
  });
});

describe('validateReflectionAnswers — extended field types', () => {
  it('accepts a valid number, date, yes_no, single_rating answer set', () => {
    const schema = {
      fields: [
        { key: 'n', type: 'number', prompts: { en: 'N' } },
        { key: 'd', type: 'date', prompts: { en: 'D' } },
        { key: 'y', type: 'yes_no', prompts: { en: 'Y' } },
        {
          key: 's',
          type: 'single_rating',
          prompts: { en: 'S' },
          scale: [1, 5],
        },
      ],
    };
    const r = validateReflectionAnswers(schema, {
      n: 7,
      d: '2026-06-01',
      y: 'yes',
      s: 4,
    });
    expect(r.ok).toBe(true);
  });

  it('rejects a non-numeric number answer', () => {
    const schema = { fields: [{ key: 'n', type: 'number', prompts: { en: 'N' } }] };
    const r = validateReflectionAnswers(schema, { n: 'abc' });
    expect(r.ok).toBe(false);
    expect(r.errors.n).toMatch(/number/i);
  });

  it('rejects a malformed date answer', () => {
    const schema = { fields: [{ key: 'd', type: 'date', prompts: { en: 'D' } }] };
    const r = validateReflectionAnswers(schema, { d: 'not-a-date' });
    expect(r.ok).toBe(false);
    expect(r.errors.d).toMatch(/date/i);
  });

  it('accepts the compound { value, follow_up } shape for yes_no', () => {
    const schema = {
      fields: [
        {
          key: 'y',
          type: 'yes_no',
          prompts: { en: 'Y' },
          follow_up_prompt: { en: 'Why?' },
        },
      ],
    };
    const r = validateReflectionAnswers(schema, { y: { value: 'yes', follow_up: 'because' } });
    expect(r.ok).toBe(true);
  });

  it('skips answer validation for section_header and instructions fields', () => {
    const schema = {
      fields: [
        { key: 'sec', type: 'section_header', prompts: { en: 'Section' }, required: true },
        { key: 'inst', type: 'instructions', prompts: { en: 'Read me' }, required: true },
      ],
    };
    const r = validateReflectionAnswers(schema, {});
    expect(r.ok).toBe(true);
  });

  it('reports missing required answer for single_rating', () => {
    const schema = {
      fields: [{ key: 's', type: 'single_rating', prompts: { en: 'S' }, scale: [1, 5] }],
    };
    const r = validateReflectionAnswers(schema, { s: '' });
    expect(r.ok).toBe(false);
    expect(r.errors.s).toMatch(/required/i);
  });
});

describe('prepareReflectionAnswersForSubmit', () => {
  it('drops empty yes_no values and omitted keys', () => {
    const schema = {
      fields: [
        { key: 'day_off', type: 'yes_no', required: false, prompts: { en: 'Off?' } },
        { key: 'note', type: 'textarea', required: false, prompts: { en: 'N' } },
      ],
    };
    const out = prepareReflectionAnswersForSubmit(
      schema,
      { day_off: '', note: 'hello' },
      { omitKeys: ['day_off'] },
    );
    expect(out).toEqual({ note: 'hello' });
  });

  it('sends day-off shortcut payload when dayOff is true', () => {
    const schema = {
      fields: [
        { key: 'day_off', type: 'yes_no', required: true, prompts: { en: 'Off?' } },
        { key: 'note', type: 'textarea', required: true, prompts: { en: 'N' } },
      ],
    };
    const out = prepareReflectionAnswersForSubmit(
      schema,
      { note: 'ignored' },
      { dayOff: true, omitKeys: ['day_off'] },
    );
    expect(out).toEqual({ day_off: true });
  });

  it('adds day_off=no when submitting a normal payload', () => {
    const schema = {
      fields: [
        { key: 'day_off', type: 'yes_no', required: true, prompts: { en: 'Off?' } },
        { key: 'note', type: 'textarea', required: false, prompts: { en: 'N' } },
      ],
    };
    const out = prepareReflectionAnswersForSubmit(
      schema,
      { note: 'hello' },
      { dayOff: false, omitKeys: ['day_off'] },
    );
    expect(out).toEqual({ note: 'hello', day_off: 'no' });
  });
});

describe('validateReflectionAnswers omitKeys', () => {
  it('skips omitted fields such as day_off quick actions', () => {
    const schema = {
      fields: [
        { key: 'day_off', type: 'yes_no', required: true, prompts: { en: 'Off?' } },
        { key: 'note', type: 'text', required: true, prompts: { en: 'Note' } },
      ],
    };
    const r = validateReflectionAnswers(schema, { note: 'ok' }, { omitKeys: ['day_off'] });
    expect(r.ok).toBe(true);
  });
});

describe('buildDefaultAnswers — extended field types', () => {
  it('seeds empty defaults for new types and skips meta fields', () => {
    const schema = {
      fields: [
        { key: 'n', type: 'number', prompts: { en: 'N' } },
        { key: 'd', type: 'date', prompts: { en: 'D' } },
        { key: 'y', type: 'yes_no', prompts: { en: 'Y' } },
        { key: 's', type: 'single_rating', prompts: { en: 'S' }, scale: [1, 5] },
        { key: 'sec', type: 'section_header', prompts: { en: 'Section' } },
        { key: 'inst', type: 'instructions', prompts: { en: 'Read me' } },
      ],
    };
    const a = buildDefaultAnswers(schema);
    expect(a.n).toBe('');
    expect(a.d).toBe('');
    expect(a.y).toBeUndefined();
    expect(a.s).toBe('');
    expect(a.sec).toBeUndefined();
    expect(a.inst).toBeUndefined();
  });
});
