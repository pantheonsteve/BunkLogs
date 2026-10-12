/**
 * Title block for supervisor homes and the bunk drill-down: eyebrow (role or
 * unit), page title, one summary line, and a compact "Logs today N / M" bar
 * on the right.
 */
import ProgressBar from '../ui/ProgressBar';

export default function SupervisorHeading({
  eyebrow,
  title,
  summary,
  progressLabel = 'Logs today',
  done,
  total,
  progressText,
  progressTestId,
  children,
}) {
  const showProgress = typeof total === 'number' && total > 0;
  return (
    <div className="flex flex-wrap items-end justify-between gap-4">
      <div className="min-w-0">
        {eyebrow && <p className="text-[13px] font-semibold text-muted">{eyebrow}</p>}
        <h1 className="mt-1 text-[28px] leading-tight font-bold tracking-tight text-ink">{title}</h1>
        {summary && <p className="mt-1.5 text-[15px] text-ink-2">{summary}</p>}
        {children}
      </div>
      {showProgress && (
        <div
          className="flex items-center gap-3 rounded-xl shadow-card border border-line bg-white dark:bg-gray-900 px-4 py-2.5"
          data-testid={progressTestId}
        >
          <span className="text-[13px] text-ink-2">{progressLabel}</span>
          <span className="text-xl font-bold tabular-nums text-ink">
            {done} / {total}
          </span>
          <ProgressBar
            value={done}
            total={total}
            className="h-2 w-[120px]"
            aria-label={`${done} of ${total} logged`}
          />
          {progressText && <span className="sr-only">{progressText}</span>}
        </div>
      )}
    </div>
  );
}
