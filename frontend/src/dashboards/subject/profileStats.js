/**
 * Pure helpers for the subject profile (8_6): period presets, the primary
 * rating template, per-category KPIs, and help-request days. Dates are
 * `YYYY-MM-DD` strings throughout; arithmetic happens in UTC so a day never
 * shifts with the browser's timezone.
 */
import { deriveSchemaSections, isTruthyFlag } from './responseTable/schema';

const MAX_WINDOW_DAYS = 90;

export const PERIOD_OPTIONS = [
  { value: 'week', label: 'This week' },
  { value: '4weeks', label: 'Last 4 weeks' },
  { value: 'session', label: 'Full session' },
];

function toIso(dt) {
  return dt.toISOString().slice(0, 10);
}

export function addDays(iso, n) {
  const [y, m, d] = iso.split('-').map(Number);
  return toIso(new Date(Date.UTC(y, m - 1, d + n)));
}

export function dayCount(start, end) {
  const ms = Date.parse(`${end}T00:00:00Z`) - Date.parse(`${start}T00:00:00Z`);
  return Math.round(ms / 86400000) + 1;
}

export function dayRange(start, end) {
  if (!start || !end || start > end) return [];
  const out = [];
  for (let d = start; d <= end; d = addDays(d, 1)) out.push(d);
  return out;
}

export function localToday() {
  const now = new Date();
  return toIso(new Date(Date.UTC(now.getFullYear(), now.getMonth(), now.getDate())));
}

function currentProgram(programs, today) {
  const dated = (programs ?? []).filter((p) => p.start_date && p.end_date);
  return dated.find((p) => p.start_date <= today && today <= p.end_date) ?? dated[0] ?? null;
}

/** `{start, end}` for a preset, or null when it can't be resolved (no session dates). */
export function periodRange(value, { today, programs } = {}) {
  if (value === 'week') return { start: addDays(today, -6), end: today };
  if (value === '4weeks') return { start: addDays(today, -27), end: today };
  if (value === 'session') {
    const program = currentProgram(programs, today);
    if (!program) return null;
    const end = program.end_date < today ? program.end_date : today;
    const floor = addDays(end, -(MAX_WINDOW_DAYS - 1));
    return { start: program.start_date > floor ? program.start_date : floor, end };
  }
  return null;
}

export function activePeriod(start, end, ctx) {
  const match = PERIOD_OPTIONS.find(({ value }) => {
    const r = periodRange(value, ctx);
    return r && r.start === start && r.end === end;
  });
  return match?.value ?? null;
}

/** The equal-length window immediately before `start..end`. */
export function priorRange(start, end) {
  const len = dayCount(start, end);
  return { start: addDays(start, -len), end: addDays(start, -1) };
}

/** The template block with rating columns and the most reflections. */
export function pickPrimaryBlock(templates, language = 'en') {
  let best = null;
  for (const block of templates ?? []) {
    const { ratingCols } = deriveSchemaSections({ fields: block.schema_fields ?? [] }, language);
    if (ratingCols.length === 0) continue;
    const count = block.reflections?.length ?? 0;
    if (!best || count > best.count) best = { block, count };
  }
  return best?.block ?? null;
}

export function ratingValue(answers, col) {
  const raw = col.subKey ? answers?.[col.key]?.[col.subKey] : answers?.[col.key];
  const n = raw == null || raw === '' ? NaN : Number(raw);
  return Number.isFinite(n) ? n : null;
}

/** date -> mean rating for that day. */
export function dailyValues(reflections, col) {
  const sums = new Map();
  for (const r of reflections ?? []) {
    const v = ratingValue(r.answers, col);
    if (v == null) continue;
    const s = sums.get(r.date) ?? { total: 0, n: 0 };
    s.total += v;
    s.n += 1;
    sums.set(r.date, s);
  }
  const out = new Map();
  for (const [date, s] of sums) out.set(date, s.total / s.n);
  return out;
}

function mean(values) {
  return values.length ? values.reduce((a, b) => a + b, 0) / values.length : null;
}

/** Period average (mean of daily means), delta vs the prior window, and the last 7 days. */
export function computeKpi(col, { reflections, priorReflections, rangeEnd }) {
  const current = dailyValues(reflections, col);
  const prior = dailyValues(priorReflections, col);
  const avg = mean([...current.values()]);
  const priorAvg = mean([...prior.values()]);
  const delta = avg != null && priorAvg != null ? avg - priorAvg : null;
  const last7 = rangeEnd
    ? dayRange(addDays(rangeEnd, -6), rangeEnd).map((date) => ({ date, value: current.get(date) ?? null }))
    : [];
  return { avg, delta, last7 };
}

export function isUnitHeadHelpField(field) {
  return field?.key === 'request_unit_head_help' || field?.dashboard_role === 'help_request_unit_head';
}

export function isCamperCareHelpField(field) {
  return field?.key === 'request_camper_care_help' || field?.dashboard_role === 'help_request_camper_care';
}

/** Dates with a Unit Head / Camper Care help request across every template. */
export function helpRequestDays(templates) {
  const unitHead = new Set();
  const camperCare = new Set();
  for (const block of templates ?? []) {
    for (const r of block.reflections ?? []) {
      for (const field of block.schema_fields ?? []) {
        if (!field?.key || !isTruthyFlag(r.answers?.[field.key])) continue;
        if (isUnitHeadHelpField(field)) unitHead.add(r.date);
        else if (isCamperCareHelpField(field)) camperCare.add(r.date);
      }
    }
  }
  return { unitHead, camperCare };
}

export function formatDay(iso) {
  if (!iso) return '';
  const [y, m, d] = iso.split('-').map(Number);
  return new Date(Date.UTC(y, m - 1, d)).toLocaleDateString('en-US', {
    month: 'short', day: 'numeric', timeZone: 'UTC',
  });
}
