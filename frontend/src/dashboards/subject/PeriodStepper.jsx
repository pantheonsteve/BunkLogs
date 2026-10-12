/**
 * Preset + custom date-range picker for the subject "All entries" page.
 * The profile itself uses the This week / Last 4 weeks / Full session
 * SegmentedControl instead.
 */
import { formatShortDate } from './responseTable/schema';

const PRESET_DAYS = [7, 30, 90];

export default function PeriodStepper({ period, rangeStart, rangeEnd, onRangeChange, refreshing }) {
  if (!period) return null;

  const inputStart = rangeStart || period.start;
  const inputEnd = rangeEnd || period.end;

  const setPreset = (days) => {
    if (!onRangeChange) return;
    const end = new Date();
    const start = new Date();
    start.setDate(end.getDate() - (days - 1));
    const fmt = (d) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
    onRangeChange(fmt(start), fmt(end));
  };

  const applyRange = (nextStart, nextEnd) => {
    if (!onRangeChange || !nextStart || !nextEnd) return;
    if (nextStart > nextEnd) {
      onRangeChange(nextEnd, nextStart);
    } else {
      onRangeChange(nextStart, nextEnd);
    }
  };

  return (
    <section
      className="bg-white dark:bg-gray-800 shadow-sm rounded-xl p-4 border border-gray-200 dark:border-gray-700 mb-6 flex flex-wrap items-center gap-3"
      data-testid="subject-period-stepper"
    >
      <div>
        <p className="text-xs uppercase tracking-wide text-gray-500 dark:text-gray-400">Period</p>
        <p className="text-sm font-medium text-gray-800 dark:text-gray-100">
          {formatShortDate(inputStart)} — {formatShortDate(inputEnd)}
          {refreshing && (
            <span className="ml-2 text-xs font-normal text-gray-400 dark:text-gray-500">Updating…</span>
          )}
        </p>
      </div>
      <div className="flex flex-wrap items-center gap-2 ml-auto">
        {PRESET_DAYS.map((days) => (
          <button
            key={days}
            type="button"
            onClick={() => setPreset(days)}
            className="text-xs font-medium px-3 py-1.5 rounded-md border border-gray-200 dark:border-gray-600 text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-700"
            data-testid={`subject-period-preset-${days}`}
          >
            Last {days} days
          </button>
        ))}
        <label className="flex items-center gap-1.5 text-xs text-gray-700 dark:text-gray-300">
          <span className="sr-only">Start date</span>
          <span aria-hidden="true">From</span>
          <input
            type="date"
            value={inputStart}
            onChange={(e) => applyRange(e.target.value, inputEnd)}
            className="rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-2 py-1.5 text-xs"
            data-testid="subject-period-start"
          />
        </label>
        <label className="flex items-center gap-1.5 text-xs text-gray-700 dark:text-gray-300">
          <span className="sr-only">End date</span>
          <span aria-hidden="true">To</span>
          <input
            type="date"
            value={inputEnd}
            onChange={(e) => applyRange(inputStart, e.target.value)}
            className="rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-2 py-1.5 text-xs"
            data-testid="subject-period-end"
          />
        </label>
      </div>
    </section>
  );
}
