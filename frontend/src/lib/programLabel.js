/**
 * A program label short enough to sit in a topbar.
 *
 * `Program.name` is required to start with the organization name, so a
 * real one reads "The Rabbi Leslie Yale Gutterman Religious School
 * 2026-2027" -- ninety characters of chrome. There is no short field on
 * the model, and stripping the org prefix leaves the same problem, so the
 * label is derived from the dates instead: a school year that crosses
 * into a second calendar year gives "2026-27", a single-summer camp
 * season gives "2026".
 */

function yearOf(ymd) {
  // 'YYYY-MM-DD' straight off the API. Parsed by hand rather than via
  // Date so a UTC-midnight start date can't slide back a year.
  const year = Number(String(ymd || '').slice(0, 4));
  return Number.isInteger(year) && year > 1900 ? year : null;
}

export function programShortLabel(program) {
  if (!program) return '';
  const start = yearOf(program.start_date);
  const end = yearOf(program.end_date);
  if (!start) return program.name || '';
  if (!end || end === start) return String(start);
  return `${start}-${String(end).slice(-2)}`;
}
