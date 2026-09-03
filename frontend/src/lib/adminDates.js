/**
 * Date formatting for the admin dashboard.
 *
 * Everything here takes 'YYYY-MM-DD' strings straight off the API and
 * parses them as local dates. Passing those to `new Date()` treats them
 * as UTC midnight, which renders as the previous day for anyone west of
 * Greenwich -- exactly the timezones this product runs in.
 */

export function parseYmd(ymd) {
  const match = /^(\d{4})-(\d{2})-(\d{2})/.exec(String(ymd || ''));
  if (!match) return null;
  return new Date(Number(match[1]), Number(match[2]) - 1, Number(match[3]));
}

export function formatMonthDay(ymd) {
  const date = parseYmd(ymd);
  if (!date) return '';
  return date.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
}

export function formatWeekdayMonthDay(ymd) {
  const date = parseYmd(ymd);
  if (!date) return '';
  return date.toLocaleDateString(undefined, {
    weekday: 'long', month: 'long', day: 'numeric',
  });
}

export function daysBetween(fromYmd, toYmd) {
  const from = parseYmd(fromYmd);
  const to = parseYmd(toYmd);
  if (!from || !to) return null;
  return Math.round((to - from) / 86400000);
}

/** "Good morning" / "Good afternoon" / "Good evening" for the local clock. */
export function greetingFor(date = new Date()) {
  const hour = date.getHours();
  if (hour < 12) return 'Good morning';
  if (hour < 18) return 'Good afternoon';
  return 'Good evening';
}

/**
 * Coarse relative time for an activity feed: "2h ago", "3d ago".
 *
 * Minute-level precision would be noise here -- the feed is a week-long
 * lookback, and nobody acts differently on "14m" versus "18m".
 */
export function relativeTime(isoString, now = new Date()) {
  const then = new Date(isoString);
  if (Number.isNaN(then.getTime())) return '';
  const seconds = Math.max(0, Math.round((now - then) / 1000));
  if (seconds < 60) return 'just now';
  const minutes = Math.round(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.round(hours / 24)}d ago`;
}
