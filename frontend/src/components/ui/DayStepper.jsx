/**
 * Previous / date / next day control shared by the role homes. The middle
 * label is a transparent native date input so tapping it opens the picker;
 * "next" disables at `todayIso` because future days have no data.
 * `testIdPrefix` namespaces the test ids per page.
 */
import { ChevronLeft, ChevronRight } from 'lucide-react';
import { twMerge } from 'tailwind-merge';

function parseIso(iso) {
  const parsed = new Date(`${iso}T00:00:00`);
  return Number.isNaN(parsed.getTime()) ? null : parsed;
}

export function shiftIso(iso, days) {
  const d = parseIso(iso);
  if (!d) return iso;
  d.setDate(d.getDate() + days);
  const mm = String(d.getMonth() + 1).padStart(2, '0');
  const dd = String(d.getDate()).padStart(2, '0');
  return `${d.getFullYear()}-${mm}-${dd}`;
}

function formatStepperDate(iso) {
  const d = iso ? parseIso(iso) : null;
  if (!d) return iso || '';
  return d.toLocaleDateString(undefined, { weekday: 'long', month: 'short', day: 'numeric' });
}

function relativeDayLabel(selectedIso, todayIso) {
  if (!selectedIso || !todayIso || selectedIso === todayIso) return 'Today';
  if (shiftIso(todayIso, -1) === selectedIso) return 'Yesterday';
  return 'Past day · read-only';
}

export default function DayStepper({
  selectedIso,
  todayIso,
  onChange,
  refreshing = false,
  testIdPrefix = 'day',
  className = '',
}) {
  const atToday = !selectedIso || !todayIso || selectedIso >= todayIso;
  const stepBtn =
    'w-11 h-11 shrink-0 rounded-[10px] flex items-center justify-center bg-line-soft text-ink hover:bg-line disabled:bg-transparent disabled:text-muted/50 disabled:cursor-not-allowed transition-colors';
  return (
    <div className={twMerge('flex items-center gap-1.5', className)} data-testid={`${testIdPrefix}-day-stepper`}>
      <button
        type="button"
        aria-label="Previous day"
        className={stepBtn}
        onClick={() => onChange(shiftIso(selectedIso, -1))}
        data-testid={`${testIdPrefix}-day-prev`}
      >
        <ChevronLeft className="w-[18px] h-[18px]" aria-hidden="true" />
      </button>
      <label className="relative flex-1 text-center min-h-11 flex flex-col justify-center cursor-pointer px-2">
        <span className="text-[17px] font-bold text-ink whitespace-nowrap">{formatStepperDate(selectedIso)}</span>
        <span className="text-xs text-muted">
          {refreshing ? 'Refreshing…' : relativeDayLabel(selectedIso, todayIso)}
        </span>
        <input
          type="date"
          aria-label="Pick a date"
          value={selectedIso || ''}
          max={todayIso}
          onChange={(e) => e.target.value && onChange(e.target.value)}
          className="absolute inset-0 opacity-0 cursor-pointer"
          data-testid={`${testIdPrefix}-date-picker`}
        />
      </label>
      <button
        type="button"
        aria-label="Next day"
        className={stepBtn}
        disabled={atToday}
        onClick={() => onChange(shiftIso(selectedIso, 1))}
        data-testid={`${testIdPrefix}-day-next`}
      >
        <ChevronRight className="w-[18px] h-[18px]" aria-hidden="true" />
      </button>
    </div>
  );
}
