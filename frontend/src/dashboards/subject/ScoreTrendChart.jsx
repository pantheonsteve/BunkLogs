/**
 * Multi-series daily score chart for the subject profile. Y axis is fixed to
 * the rating scale so periods compare at a glance; lines break on days with
 * no log rather than interpolating. Days with a help request get a warn band.
 */
import { useEffect, useState } from 'react';
import { formatDay } from './profileStats';

const W = 760;
const H = 230;
const PAD = { left: 36, right: 16, top: 12, bottom: 30 };
const MAX_X_LABELS = 10;

export default function ScoreTrendChart({ days, series, helpDates, scaleMax = 5 }) {
  const keysSig = series.map((s) => s.key).join('|');
  const [hidden, setHidden] = useState(() => new Set());
  useEffect(() => setHidden(new Set()), [keysSig]);

  if (days.length === 0 || series.length === 0) {
    return <p className="text-sm text-muted">No scores in this period.</p>;
  }

  const plotW = W - PAD.left - PAD.right;
  const plotH = H - PAD.top - PAD.bottom;
  const step = days.length > 1 ? plotW / (days.length - 1) : 0;
  const X = (i) => PAD.left + (days.length > 1 ? i * step : plotW / 2);
  const Y = (v) => PAD.top + ((scaleMax - v) / (scaleMax - 1)) * plotH;
  const band = Math.max(Math.min(step || plotW, 40), 10);
  const labelEvery = Math.ceil(days.length / MAX_X_LABELS);
  const ticks = Array.from({ length: scaleMax }, (_, i) => i + 1);

  const toggle = (key) => setHidden((prev) => {
    const next = new Set(prev);
    if (next.has(key)) next.delete(key);
    else next.add(key);
    return next;
  });

  const pathFor = (values) => {
    let d = '';
    let pen = false;
    days.forEach((day, i) => {
      const v = values.get(day);
      if (v == null) {
        pen = false;
        return;
      }
      d += `${pen ? 'L' : 'M'}${X(i).toFixed(1)},${Y(v).toFixed(1)} `;
      pen = true;
    });
    return d.trim();
  };

  const visible = series.filter((s) => !hidden.has(s.key));

  return (
    <div className="flex flex-col gap-3" data-testid="subject-trend-chart">
      <div className="flex flex-wrap items-center gap-2">
        {series.map((s) => {
          const on = !hidden.has(s.key);
          return (
            <button
              key={s.key}
              type="button"
              aria-pressed={on}
              onClick={() => toggle(s.key)}
              data-testid={`trend-toggle-${s.key}`}
              className={`inline-flex items-center gap-1.5 min-h-8 px-2.5 rounded-full border border-line text-xs font-semibold ${
                on ? 'text-ink bg-white dark:bg-gray-900' : 'text-muted bg-line-soft line-through'
              }`}
            >
              <span className="w-3.5 h-[3px] rounded-sm" style={{ background: s.color }} aria-hidden="true" />
              {s.label}
            </button>
          );
        })}
        {helpDates.size > 0 && (
          <span className="inline-flex items-center gap-1.5 text-xs text-ink-2">
            <span className="w-2.5 h-2.5 rounded-sm bg-warn-soft border border-warn-ink/40" aria-hidden="true" />
            Help requested
          </span>
        )}
      </div>
      <svg
        viewBox={`0 0 ${W} ${H}`}
        className="w-full h-auto block"
        role="img"
        aria-label={`${visible.map((s) => s.label).join(', ')} scores, ${formatDay(days[0])} to ${formatDay(days[days.length - 1])}`}
      >
        {days.map((day, i) => (helpDates.has(day) ? (
          <rect
            key={`band-${day}`}
            data-testid="trend-help-band"
            x={X(i) - band / 2}
            y={PAD.top}
            width={band}
            height={plotH}
            style={{ fill: 'var(--color-warn-soft)' }}
          />
        ) : null))}
        {ticks.map((v) => (
          <g key={`grid-${v}`}>
            <line x1={PAD.left} x2={W - PAD.right} y1={Y(v)} y2={Y(v)} style={{ stroke: 'var(--color-line)' }} strokeWidth="1" />
            <text x={PAD.left - 10} y={Y(v) + 4} textAnchor="end" fontSize="11" style={{ fill: 'var(--color-muted)' }}>{v}</text>
          </g>
        ))}
        {days.map((day, i) => (i % labelEvery === 0 || i === days.length - 1 ? (
          <text key={`x-${day}`} x={X(i)} y={H - 8} textAnchor="middle" fontSize="11" style={{ fill: 'var(--color-muted)' }}>
            {formatDay(day)}
          </text>
        ) : null))}
        {visible.map((s) => (
          <g key={s.key}>
            <path d={pathFor(s.values)} fill="none" strokeWidth="2.5" strokeLinejoin="round" style={{ stroke: s.color }} />
            {days.map((day, i) => {
              const v = s.values.get(day);
              return v == null ? null : (
                <circle key={day} cx={X(i)} cy={Y(v)} r="3.5" style={{ fill: s.color }}>
                  <title>{`${s.label}, ${formatDay(day)}: ${Number.isInteger(v) ? v : v.toFixed(1)}`}</title>
                </circle>
              );
            })}
          </g>
        ))}
      </svg>
    </div>
  );
}
