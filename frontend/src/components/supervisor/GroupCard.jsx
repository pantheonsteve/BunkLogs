/**
 * One group (bunk / classroom) in a supervisor's grid. The whole card links
 * to the group's full dashboard. `averages` renders one RatingCell per
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
  href,
  noTotalText = 'Nothing expected',
  testId,
}) {
  return (
    <Link
      to={href}
      data-testid={testId}
      className="flex flex-col gap-2.5 p-4 rounded-xl border border-line bg-white dark:bg-gray-900 text-left shadow-card transition-[box-shadow,border-color] hover:shadow-card-hover hover:border-brand/40 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand"
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
    </Link>
  );
}
