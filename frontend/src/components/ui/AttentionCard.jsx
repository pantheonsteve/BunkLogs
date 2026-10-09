/**
 * "Needs attention" card: tinted icon chip, title, count, then up to
 * `maxRows` linked people (initials, name · where, age). Longer lists end
 * with "+N more", linked when `moreTo` is given. `ageTone: 'danger'` marks
 * an item that has waited too long.
 */
import { useId } from 'react';
import { Link } from 'react-router-dom';
import InitialsAvatar from './InitialsAvatar';

const TONE_CHIP = {
  warn: 'bg-warn-soft text-warn-ink',
  danger: 'bg-danger-soft text-danger-ink',
  neutral: 'bg-line-soft text-ink-2',
};

const AGE_TEXT = {
  danger: 'text-danger-ink',
  warn: 'text-warn-ink',
  neutral: 'text-muted',
};

const ROW_CLS = 'flex items-center gap-2.5 min-h-10 border-t border-line-soft text-ink';

function RowContent({ row }) {
  return (
    <>
      <InitialsAvatar name={row.name} initials={row.initials} size="sm" tone="neutral" aria-hidden="true" />
      <span className="flex-1 min-w-0 truncate text-[13px]">
        <span className="font-semibold">{row.name}</span>
        {row.where && <span className="text-muted"> · {row.where}</span>}
      </span>
      {row.age && (
        <span className={`text-xs font-semibold shrink-0 ${AGE_TEXT[row.ageTone] || AGE_TEXT.neutral}`}>
          {row.age}
        </span>
      )}
    </>
  );
}

export default function AttentionCard({
  title,
  icon: Icon,
  tone = 'neutral',
  count,
  rows = [],
  emptyText = 'None today.',
  action,
  moreTo,
  maxRows = 3,
  className = '',
  ...rest
}) {
  const headingId = useId();
  const shown = rows.slice(0, maxRows);
  const hidden = rows.length - shown.length;
  const total = count ?? rows.length;

  return (
    <section
      aria-labelledby={headingId}
      data-count={total}
      className={`flex flex-col gap-2 rounded-[14px] border border-line bg-white dark:bg-gray-900 px-5 py-[18px] ${className}`.trim()}
      {...rest}
    >
      <div className="flex items-center gap-2.5">
        {Icon && (
          <span
            className={`inline-flex items-center justify-center w-8 h-8 rounded-lg shrink-0 ${
              TONE_CHIP[tone] || TONE_CHIP.neutral
            }`}
          >
            <Icon size={18} aria-hidden="true" />
          </span>
        )}
        <h2 id={headingId} className="flex-1 min-w-0 text-[15px] font-bold text-ink">
          {title}
        </h2>
        <span className="text-xl font-bold tabular-nums text-ink">{total}</span>
      </div>

      {rows.length === 0 ? (
        <p className="text-[13px] text-muted">{emptyText}</p>
      ) : (
        <ul>
          {shown.map((row) => (
            <li key={row.id}>
              {row.to ? (
                <Link to={row.to} className={`${ROW_CLS} hover:bg-line-soft rounded-md`}>
                  <RowContent row={row} />
                </Link>
              ) : (
                <div className={ROW_CLS}>
                  <RowContent row={row} />
                </div>
              )}
            </li>
          ))}
          {hidden > 0 && (
            <li className="pt-1">
              {moreTo ? (
                <Link to={moreTo} className="inline-flex items-center min-h-10 text-[13px] font-semibold text-brand hover:text-brand-hover">
                  +{hidden} more
                </Link>
              ) : (
                <span className="text-[13px] font-semibold text-muted">+{hidden} more</span>
              )}
            </li>
          )}
        </ul>
      )}

      {action && <div className="pt-1">{action}</div>}
    </section>
  );
}
