/**
 * One group (bunk / classroom) in a supervisor's grid. The card body is a
 * button that selects the group; the full-dashboard link sits beside it so
 * the two actions never nest. `averages` renders one RatingCell per
 * category and is omitted when the payload has no scores.
 */
import { Flag } from 'lucide-react';
import { Link } from 'react-router-dom';
import ProgressBar from '../ui/ProgressBar';
import RatingCell from '../ui/RatingCell';

export default function GroupCard({
  name,
  staff,
  done = 0,
  total = 0,
  averages = null,
  flags = 0,
  selected = false,
  onSelect,
  href,
  hrefLabel = 'Open dashboard',
  noTotalText = 'Nothing expected',
  testId,
}) {
  return (
    <div
      data-testid={testId}
      data-selected={selected ? 'true' : 'false'}
      className={`flex flex-col rounded-xl bg-white dark:bg-gray-900 ${
        selected ? 'border-2 border-brand' : 'border border-line m-px'
      }`}
    >
      <button
        type="button"
        onClick={onSelect}
        aria-pressed={selected}
        className="flex flex-col gap-2.5 p-4 pb-2 text-left rounded-t-xl hover:bg-line-soft/60"
      >
        <span className="flex items-center justify-between gap-2">
          <span className="text-[15px] font-bold text-ink truncate">{name}</span>
          {flags > 0 && (
            <span
              className="inline-flex items-center gap-1 text-xs font-bold text-danger-ink"
              aria-label={`${flags} flagged`}
            >
              <Flag size={13} strokeWidth={2.2} aria-hidden="true" />
              {flags}
            </span>
          )}
        </span>
        {staff && <span className="text-xs text-muted truncate">{staff}</span>}
        {total > 0 ? (
          <span className="flex items-center gap-2">
            <ProgressBar value={done} total={total} className="flex-1" aria-label={`${done} of ${total}`} />
            <span className="text-xs font-semibold tabular-nums text-ink-2">
              {done}/{total}
            </span>
          </span>
        ) : (
          <span className="text-xs text-muted">{noTotalText}</span>
        )}
        {averages && averages.length > 0 && (
          <span className="flex gap-1">
            {averages.map((a) => (
              <RatingCell
                key={a.label}
                value={a.value}
                scaleMax={a.scaleMax}
                size="sm"
                label={a.label}
                className="flex-1 h-[26px]"
              />
            ))}
          </span>
        )}
      </button>
      {href && (
        <Link
          to={href}
          className="px-4 pb-3 pt-1 text-xs font-semibold text-brand hover:text-brand-hover"
        >
          {hrefLabel} →
        </Link>
      )}
    </div>
  );
}
