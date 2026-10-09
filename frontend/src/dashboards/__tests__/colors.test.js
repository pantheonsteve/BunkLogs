import { describe, it, expect } from 'vitest';
import {
  COVERAGE_TIERS,
  RATING_FILLS,
  RATING_TEXT,
  RATING_TIER_CLASSES,
  ratingColor,
  ratingTierClass,
} from '../colors';

describe('rating palette', () => {
  it('covers 1–5 with fills, text colors and matching Tailwind classes', () => {
    [1, 2, 3, 4, 5].forEach((n) => {
      expect(RATING_FILLS[n]).toMatch(/^#[0-9a-f]{6}$/);
      expect(RATING_TEXT[n]).toMatch(/^#[0-9a-f]{6}$/);
      expect(RATING_TIER_CLASSES[n]).toContain(`bg-[${RATING_FILLS[n]}]`);
      expect(RATING_TIER_CLASSES[n]).toContain(RATING_TEXT[n] === '#ffffff' ? 'text-white' : 'text-ink');
    });
  });

  it('maps shorter scales so the bottom is red and the top is dark green', () => {
    expect(ratingColor(1, 3)).toBe(RATING_FILLS[1]);
    expect(ratingColor(3, 3)).toBe(RATING_FILLS[5]);
    expect(ratingTierClass(4, 4)).toBe(RATING_TIER_CLASSES[5]);
    expect(ratingTierClass(null)).toContain('bg-gray-100');
  });

  it('uses dark text on the orange coverage tier', () => {
    expect(COVERAGE_TIERS.orange.text).toBe('#1d1b2c');
  });
});
