/**
 * Shared color tokens for dashboard heatmaps, trend grids and rating cells.
 *
 * This file is the only definition of the 1-5 rating palette. Palette is
 * colorblind-aware (Okabe-Ito-leaning red/orange/yellow/light-green/dark-green)
 * and never the only signal: every cell also shows its number and an aria-label.
 */

export const COVERAGE_TIERS = {
  green:        { fill: '#1b6e3f', text: 'white',  label: '100%' },
  light_green:  { fill: '#62b372', text: '#0b1d12',label: '90–99%' },
  yellow:       { fill: '#e9c14a', text: '#3a2a05',label: '70–89%' },
  orange:       { fill: '#d97a2a', text: '#1d1b2c',label: '40–69%' },
  red:          { fill: '#c0473a', text: 'white',  label: '1–39%' },
  gray:         { fill: '#9ca3af', text: '#1f2937',label: '0%' },
  inactive:     { fill: 'transparent', text: '#6b7280', label: 'No roster' },
};

export const COVERAGE_TIER_ORDER = [
  'green', 'light_green', 'yellow', 'orange', 'red', 'gray', 'inactive',
];

/**
 * Map a numeric percentage (0-100) to a coverage tier keyword.
 * Used client-side to colorize cells when the API returned a raw percent
 * instead of a status. The backend status is preferred when present.
 */
export function coverageTier(percent, hasRoster = true) {
  if (!hasRoster) return 'inactive';
  if (percent == null) return 'gray';
  if (percent >= 100) return 'green';
  if (percent >= 90) return 'light_green';
  if (percent >= 70) return 'yellow';
  if (percent >= 40) return 'orange';
  if (percent >= 1) return 'red';
  return 'gray';
}

/** 1 = red ... 5 = dark green. Text is white on 1 and 5, ink on 2-4. */
export const RATING_FILLS = {
  1: '#c0473a',
  2: '#d97a2a',
  3: '#e9c14a',
  4: '#62b372',
  5: '#1b6e3f',
};

export const RATING_TEXT = {
  1: '#ffffff',
  2: '#1d1b2c',
  3: '#1d1b2c',
  4: '#1d1b2c',
  5: '#ffffff',
};

// Tailwind only generates classes it can find as literal strings, so these
// repeat RATING_FILLS; colors.test.js asserts they stay in sync.
export const RATING_TIER_CLASSES = {
  1: 'bg-[#c0473a] text-white',
  2: 'bg-[#d97a2a] text-ink',
  3: 'bg-[#e9c14a] text-ink',
  4: 'bg-[#62b372] text-ink',
  5: 'bg-[#1b6e3f] text-white',
};

export const RATING_EMPTY_CLASS = 'bg-gray-100 text-gray-600';

// Shorter scales map onto the 5-tier palette so a 1 is always red and the
// top score is always dark green.
const SCALE_TIERS = {
  3: [1, 3, 5],
  4: [1, 2, 3, 5],
  5: [1, 2, 3, 4, 5],
};

/** Palette tier (1-5) for a rating on a 1..scaleMax scale, or null. */
export function ratingTier(value, scaleMax = 5) {
  if (value == null || value === '' || !Number.isFinite(Number(value))) return null;
  const v = Number(value);
  const max = scaleMax || 5;
  const tiers = SCALE_TIERS[max];
  if (tiers) {
    return tiers[Math.max(0, Math.min(max - 1, Math.round(v) - 1))];
  }
  return Math.max(1, Math.min(5, Math.round((v / max) * 5)));
}

/** Hex fill for a rating, or null when there's no rating (callers show NO_DATA_FILL). */
export function ratingColor(value, scaleMax = 5) {
  const tier = ratingTier(value, scaleMax);
  return tier == null ? null : RATING_FILLS[tier];
}

export function ratingTextColor(value, scaleMax = 5) {
  const tier = ratingTier(value, scaleMax);
  return tier == null ? '#1f2937' : RATING_TEXT[tier];
}

/** Tailwind bg + text classes for a rating cell. */
export function ratingTierClass(value, scaleMax = 5) {
  const tier = ratingTier(value, scaleMax);
  return tier == null ? RATING_EMPTY_CLASS : RATING_TIER_CLASSES[tier];
}

/** Legend rows for a given scale (used by SubjectTrendGrid and ScoreGrid). */
export function ratingLegend(scaleMax = 5) {
  const max = scaleMax || 5;
  const count = SCALE_TIERS[max] ? max : 5;
  return Array.from({ length: count }, (_, i) => ({
    value: i + 1,
    fill: ratingColor(i + 1, count),
  }));
}

export const NO_DATA_FILL = '#e5e7eb';
export const INACTIVE_PATTERN_ID = 'inactiveStripes';
