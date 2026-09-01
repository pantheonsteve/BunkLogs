import { describe, expect, it } from 'vitest';

import { programShortLabel } from '../programLabel';

describe('programShortLabel', () => {
  it('spans two calendar years for a school year', () => {
    expect(programShortLabel({
      name: 'The Rabbi Leslie Yale Gutterman Religious School 2026-2027',
      start_date: '2026-09-13',
      end_date: '2027-05-16',
    })).toBe('2026-27');
  });

  it('is a single year for a summer season', () => {
    expect(programShortLabel({
      name: 'Crane Lake Camp Summer 2026',
      start_date: '2026-06-20',
      end_date: '2026-08-14',
    })).toBe('2026');
  });

  it('does not slide a January-1 start back a year', () => {
    expect(programShortLabel({ start_date: '2027-01-01', end_date: '2027-06-30' }))
      .toBe('2027');
  });

  it('falls back to the full name when there are no usable dates', () => {
    expect(programShortLabel({ name: 'Pilot', start_date: null })).toBe('Pilot');
    expect(programShortLabel(null)).toBe('');
  });
});
