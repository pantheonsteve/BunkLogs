import { Link } from 'react-router-dom';
import { ratingColor } from '../colors';
import PrivacyChip from '../../components/reflection/PrivacyChip';

function pad2(n) {
  return String(n).padStart(2, '0');
}

function formatShortDate(iso) {
  const d = new Date(iso + 'T00:00:00');
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
}

/**
 * Tiny inline SVG sparkline — we already use lightweight SVG bars elsewhere
 * (see NumberSparklineWidget); avoid adding a charting dep for one chart.
 */
function RatingSparkline({ points, scaleMax = 5, ariaLabel }) {
  const filtered = points.filter((p) => p.value != null);
  if (filtered.length === 0) {
    return (
      <p className="text-xs text-gray-400 italic">No rating data in this window.</p>
    );
  }
  const w = 320;
  const h = 64;
  const padX = 8;
  const padY = 6;
  const sorted = [...filtered].sort((a, b) => a.date.localeCompare(b.date));
  const xs = sorted.length;
  const xStep = xs > 1 ? (w - 2 * padX) / (xs - 1) : 0;
  const yScale = (v) => {
    const clamped = Math.max(1, Math.min(scaleMax, v));
    return h - padY - ((clamped - 1) / (scaleMax - 1)) * (h - 2 * padY);
  };
  const path = sorted
    .map((p, i) => `${i === 0 ? 'M' : 'L'}${padX + i * xStep},${yScale(p.value)}`)
    .join(' ');
  return (
    <svg
      width={w}
      height={h}
      viewBox={`0 0 ${w} ${h}`}
      role="img"
      aria-label={ariaLabel}
      className="block"
    >
      {/* Baseline gridlines for 1, 3, 5 */}
      {[1, Math.ceil(scaleMax / 2), scaleMax].map((v) => (
        <line
          key={v}
          x1={padX}
          x2={w - padX}
          y1={yScale(v)}
          y2={yScale(v)}
          stroke="#e5e7eb"
          strokeWidth="0.5"
        />
      ))}
      <path d={path} stroke="#1f2937" strokeWidth="1.5" fill="none" />
      {sorted.map((p, i) => (
        <circle
          key={p.date + p.reflection_id}
          cx={padX + i * xStep}
          cy={yScale(p.value)}
          r="3"
          fill={ratingColor(p.value, scaleMax) ?? '#6b7280'}
          stroke="#fff"
          strokeWidth="1"
        >
          <title>
            {formatShortDate(p.date)}: {Math.round(p.value)} of {scaleMax}
          </title>
        </circle>
      ))}
    </svg>
  );
}

function ConcernsList({ concerns }) {
  if (!concerns || concerns.length === 0) {
    return null;
  }
  return (
    <div className="mb-6 rounded-lg border border-amber-300 dark:border-amber-700 bg-amber-50 dark:bg-amber-900/20 p-4">
      <h3 className="font-medium text-amber-900 dark:text-amber-100 mb-2">
        Concerning patterns
      </h3>
      <ul className="text-sm text-amber-900 dark:text-amber-100 space-y-1">
        {concerns.map((c, i) => {
          const key = `${c.kind}-${c.field_label}-${i}`;
          if (c.kind === 'low_rating') {
            return (
              <li key={key} className="flex flex-wrap items-center gap-2">
                <span>
                  <strong>{c.field_label}</strong>: rating of {c.value} on{' '}
                  {formatShortDate(c.date)}.
                </span>
                <PrivacyChip teamVisibility={c.team_visibility} />
                {c.reflection_id && (
                  <Link
                    to={`/reflect/summary?reflection=${c.reflection_id}`}
                    className="underline"
                  >
                    View reflection
                  </Link>
                )}
              </li>
            );
          }
          if (c.kind === 'downward_trend') {
            return (
              <li key={key}>
                <strong>{c.field_label}</strong>: recent week ({c.recent_mean}) is lower
                than prior week ({c.prior_mean}) by more than 0.5.
              </li>
            );
          }
          return <li key={key}>{c.kind}: {c.field_label}</li>;
        })}
      </ul>
    </div>
  );
}

export default function SubjectDetail({ payload }) {
  if (!payload) return null;
  const { subject, period, templates, recent_texts, concerning_patterns } = payload;
  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-semibold text-gray-900 dark:text-white">
          {subject.name}
        </h1>
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-0.5">
          {period.start} → {period.end}
        </p>
      </div>

      <ConcernsList concerns={concerning_patterns} />

      {templates.length === 0 ? (
        <p className="text-sm text-gray-500 dark:text-gray-400">
          No reflections about this person in the selected window (or you don&apos;t have
          permission to view them).
        </p>
      ) : (
        <div className="space-y-6">
          {templates.map((t) => (
            <section
              key={t.template.id}
              className="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900/40 p-4"
            >
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
                {t.template.name}
              </h2>
              <p className="text-xs uppercase tracking-wide text-gray-400 mb-3">
                {t.template.subject_mode}
              </p>
              {t.rating_series.length === 0 && (
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  No rating fields on this template.
                </p>
              )}
              {t.rating_series.map((s) => (
                <div key={s.label} className="mb-4">
                  <p className="text-sm font-medium text-gray-700 dark:text-gray-200 mb-1">
                    {s.label}
                  </p>
                  <RatingSparkline
                    points={s.points}
                    scaleMax={s.scale_max}
                    ariaLabel={`Rating trend for ${s.label}`}
                  />
                </div>
              ))}
              <details className="mt-2">
                <summary className="cursor-pointer text-xs text-gray-500 dark:text-gray-400">
                  {t.reflections.length} reflection(s)
                </summary>
                <ul className="text-xs text-gray-700 dark:text-gray-300 mt-2 space-y-1">
                  {t.reflections.map((r) => (
                    <li key={r.id} className="flex flex-wrap items-center gap-2">
                      <span>
                        {r.date}
                        {r.author_name ? ` · by ${r.author_name}` : ''}
                      </span>
                      <PrivacyChip teamVisibility={r.team_visibility} />
                      <Link
                        to={`/reflect/summary?reflection=${r.id}`}
                        className="underline"
                      >
                        view
                      </Link>
                    </li>
                  ))}
                </ul>
              </details>
            </section>
          ))}
        </div>
      )}

      {recent_texts && recent_texts.length > 0 && (
        <section className="mt-6">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
            Recent text responses
          </h2>
          <ul className="space-y-2">
            {recent_texts.map((t, i) => (
              <li
                key={`${t.reflection_id}-${t.field_key}-${i}`}
                className="rounded border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900/40 p-3"
              >
                <p className="text-xs text-gray-500 dark:text-gray-400 mb-1 flex flex-wrap items-center gap-2">
                  <span>
                    {t.template_name} · {t.field_key} · {formatShortDate(t.date)}
                    {t.author_name ? ` · ${t.author_name}` : ''}
                  </span>
                  <PrivacyChip teamVisibility={t.team_visibility} />
                </p>
                <p className="text-sm text-gray-800 dark:text-gray-200 whitespace-pre-wrap">
                  {t.text}
                </p>
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}
