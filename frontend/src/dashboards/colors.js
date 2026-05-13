/**
 * Shared color tokens for dashboard heatmaps and trend grids.
 *
 * Palette is colorblind-aware: deuteranopia distinguishability tested using
 * Okabe-Ito-leaning hues for red/orange/yellow/light-green/dark-green plus a
 * neutral gray and a striped fill for "inactive" cells. Avoids relying on
 * red-vs-green contrast as the only signal — every cell also carries a numeric
 * tooltip and aria-label per the dashboards spec.
 */

export const COVERAGE_TIERS = {
  green:        { fill: '#1b6e3f', text: 'white',  label: '100%' },
  light_green:  { fill: '#62b372', text: '#0b1d12',label: '90–99%' },
  yellow:       { fill: '#e9c14a', text: '#3a2a05',label: '70–89%' },
  orange:       { fill: '#d97a2a', text: 'white',  label: '40–69%' },
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

/**
 * Rating colors. Diverging scale anchored to the template's scale_max so a
 * 1-4 template uses 4 colors and a 1-5 template uses 5 colors.
 *
 * Returns a hex fill string, or null when there's no rating that day (cells
 * fall back to gray with the "no data" label).
 */
const RATING_COLORS_5 = [
  '#c0473a', // 1 = red
  '#d97a2a', // 2 = orange
  '#e9c14a', // 3 = yellow
  '#62b372', // 4 = light green
  '#1b6e3f', // 5 = dark green
];

const RATING_COLORS_4 = [
  '#c0473a', // 1
  '#d97a2a', // 2
  '#e9c14a', // 3
  '#1b6e3f', // 4
];

const RATING_COLORS_3 = [
  '#c0473a',
  '#e9c14a',
  '#1b6e3f',
];

export function ratingColor(value, scaleMax = 5) {
  if (value == null || Number.isNaN(value)) return null;
  const palette =
    scaleMax >= 5 ? RATING_COLORS_5 :
    scaleMax === 4 ? RATING_COLORS_4 :
    scaleMax === 3 ? RATING_COLORS_3 :
    RATING_COLORS_5;
  const idx = Math.max(0, Math.min(palette.length - 1, Math.round(value) - 1));
  return palette[idx];
}

export function ratingTextColor(value, scaleMax = 5) {
  // Light text on dark cells (1, 2, 4-or-5) and dark text on yellows.
  if (value == null) return '#1f2937';
  const rounded = Math.round(value);
  if (rounded <= 2) return 'white';
  if (rounded === 3) return '#3a2a05';
  if (rounded === scaleMax) return 'white';
  return rounded === 4 && scaleMax >= 5 ? '#0b1d12' : 'white';
}

/**
 * Return the legend rows for a given scale (used by SubjectTrendGrid).
 */
export function ratingLegend(scaleMax = 5) {
  const palette =
    scaleMax >= 5 ? RATING_COLORS_5 :
    scaleMax === 4 ? RATING_COLORS_4 :
    scaleMax === 3 ? RATING_COLORS_3 :
    RATING_COLORS_5;
  return palette.map((fill, i) => ({ value: i + 1, fill }));
}

export const NO_DATA_FILL = '#e5e7eb';
export const INACTIVE_PATTERN_ID = 'inactiveStripes';
