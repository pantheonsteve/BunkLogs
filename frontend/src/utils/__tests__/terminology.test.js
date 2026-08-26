/**
 * Mirrors `backend/bunk_logs/core/test_terminology.py` — the two modules
 * implement the same fallback rules and must not drift.
 */
import { describe, expect, it } from 'vitest';
import { DEFAULT_TERMS, normalizeTerminology, resolveTerm } from '../terminology';

describe('normalizeTerminology', () => {
  it('returns camp defaults for missing or empty payloads', () => {
    expect(normalizeTerminology(undefined)).toEqual(DEFAULT_TERMS);
    expect(normalizeTerminology(null)).toEqual(DEFAULT_TERMS);
    expect(normalizeTerminology({})).toEqual(DEFAULT_TERMS);
  });

  it('applies overrides and leaves unset keys alone', () => {
    const terms = normalizeTerminology({
      cohort: { one: 'Teaching Team', other: 'Teaching Teams' },
    });

    expect(terms.cohort).toEqual({ one: 'Teaching Team', other: 'Teaching Teams' });
    expect(terms.director).toEqual(DEFAULT_TERMS.director);
  });

  it('never drops a key on partial or malformed overrides', () => {
    const terms = normalizeTerminology({
      camper: 'student',
      cohort: { other: '' },
      director: ['nonsense'],
    });

    // A bare string supplies both forms; it does not invent a plural.
    expect(terms.camper).toEqual({ one: 'student', other: 'student' });
    // An empty `other` must fall back to the default plural, not to a
    // defaulted `one` -- otherwise "cohorts" would silently become "cohort".
    expect(terms.cohort).toEqual(DEFAULT_TERMS.cohort);
    expect(terms.director).toEqual(DEFAULT_TERMS.director);
    expect(Object.keys(terms).sort()).toEqual(Object.keys(DEFAULT_TERMS).sort());
  });
});

describe('resolveTerm', () => {
  const terms = normalizeTerminology({
    camper: { one: 'student', other: 'students' },
    director: { one: 'Ed Team', other: 'Ed Team' },
  });

  it('selects the requested form', () => {
    expect(resolveTerm(terms, 'camper')).toBe('student');
    expect(resolveTerm(terms, 'camper', { plural: true })).toBe('students');
    expect(resolveTerm(terms, 'director', { plural: true })).toBe('Ed Team');
  });

  it('capitalizes only the first character', () => {
    expect(resolveTerm(terms, 'camper', { capitalize: true })).toBe('Student');
    expect(resolveTerm(terms, 'director', { capitalize: true })).toBe('Ed Team');
  });

  it('falls back to defaults, then to the key itself', () => {
    expect(resolveTerm(null, 'cohort')).toBe('cohort');
    expect(resolveTerm(terms, 'not_a_term')).toBe('not_a_term');
  });
});
