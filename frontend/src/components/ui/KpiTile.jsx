/**
 * Headline number tile: label, big value with unit, then one line of
 * context. A directional delta is colored by direction (▲ ok, ▼ danger);
 * an undirected delta (e.g. a count of overdue items) takes `tone`.
 */

const TONE_TEXT = {
  ok: 'text-ok-ink',
  warn: 'text-warn-ink',
  danger: 'text-danger-ink',
  neutral: 'text-ink-2',
};

const DIRECTION = {
  up: { arrow: '▲', word: 'up', cls: 'text-ok-ink' },
  down: { arrow: '▼', word: 'down', cls: 'text-danger-ink' },
};

export default function KpiTile({
  label,
  value,
  unit,
  sub,
  delta,
  deltaDirection = null,
  tone = 'neutral',
  className = '',
  ...rest
}) {
  const dir = DIRECTION[deltaDirection];
  const deltaCls = dir ? dir.cls : TONE_TEXT[tone] || TONE_TEXT.neutral;
  const hasFooter = (delta != null && delta !== '') || sub;

  return (
    <div
      className={`flex flex-col gap-1.5 rounded-[14px] border border-line bg-white dark:bg-gray-900 px-5 py-[18px] ${className}`.trim()}
      {...rest}
    >
      <div className="text-[13px] font-semibold text-ink-2">{label}</div>
      <div className="flex items-baseline gap-1.5">
        <span className="text-[30px] leading-tight font-bold tracking-tight tabular-nums text-ink">
          {value}
        </span>
        {unit && <span className="text-sm text-muted">{unit}</span>}
      </div>
      {hasFooter && (
        <div className="flex flex-wrap items-center gap-1.5 text-[13px]">
          {delta != null && delta !== '' && (
            <span data-testid="kpi-delta" className={`font-semibold tabular-nums ${deltaCls}`}>
              {dir && (
                <>
                  <span aria-hidden="true">{dir.arrow} </span>
                  <span className="sr-only">{dir.word} </span>
                </>
              )}
              {delta}
            </span>
          )}
          {sub && <span className="text-muted">{sub}</span>}
        </div>
      )}
    </div>
  );
}
