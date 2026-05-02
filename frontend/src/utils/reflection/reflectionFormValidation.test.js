import { describe, it, expect } from 'vitest';
import {
  validateReflectionAnswers,
  buildDefaultAnswers,
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
