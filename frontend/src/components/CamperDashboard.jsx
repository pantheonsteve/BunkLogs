/**
 * Shared Camper Dashboard — Step 7_7, Story 13.
 *
 * Presentational component rendering the role-agnostic payload from
 * any `…/campers/<id>/` endpoint (UH today, Camper Care in 7_8, LT
 * in 7_12, Admin in 7_13). Visibility is enforced server-side; this
 * view trusts what it's handed and surfaces the spec's two flavors
 * of "missing" content: empty arrays render the no-data message, and
 * `sensitive_excluded_count` renders the "1 sensitive note (Camper
 * Care)" placeholder.
 *
 * Sections (criterion 1):
 *   1. Trend graph (multi-series, toggleable)
 *   2. Today's reflection (template-ordered fields)
 *   3. Today's scores
 *   4. Today's flags (help requested, etc.)
 *   5. Specialist reports
 *   6. Camper-care notes
 */

import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { NO_DATA_FILL, ratingColor, ratingLegend, ratingTextColor } from '../dashboards/colors';

const RANGE_OPTIONS = [
  { value: 'this_week', label: 'This week' },
  { value: 'last_4_weeks', label: 'Last 4 weeks' },
  { value: 'full_session', label: 'Full session' },
];

function formatShortDate(iso) {
  const d = new Date(`${iso}T00:00:00`);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleDateString(undefined, { month: 'numeric', day: 'numeric' });
}

function formatCamperName(camper) {
  if (!camper) return '';
  const first = camper.preferred_name || camper.first_name || '';
  const last = camper.last_name || '';
  return `${first} ${last}`.trim();
}

function getEnPrompt(prompts) {
  if (!prompts) return '';
  return prompts.en || prompts.es || Object.values(prompts)[0] || '';
}

function TrendCell({ point, scaleMax, label }) {
  const dateLabel = formatShortDate(point.date);
  if (point.value == null) {
    return (
      <td
        data-testid="trend-cell-empty"
        className="border border-gray-200 dark:border-gray-700 p-0 text-center"
        style={{ backgroundColor: NO_DATA_FILL, color: '#6b7280' }}
        aria-label={`${label}, ${dateLabel}, no reflection`}
        title={`${dateLabel} — no reflection`}
      >
        <span className="block w-full h-full px-1 py-1.5 text-[10px] font-mono">—</span>
      </td>
    );
  }
  const fill = ratingColor(point.value, scaleMax);
  const text = ratingTextColor(point.value, scaleMax);
  const rounded = Math.round(point.value);
  const baseClass = 'border border-gray-200 dark:border-gray-700 p-0 text-center';
  const inner = 'block w-full h-full px-1 py-1.5 text-[10px] font-mono focus:outline-none focus:ring-2 focus:ring-indigo-400';
  const aria = `${label}, ${dateLabel}, rating ${rounded} of ${scaleMax}`;
  const tooltip = `${dateLabel} — ${rounded} of ${scaleMax}`;

  if (point.reflection_id) {
    return (
      <td className={baseClass} style={{ backgroundColor: fill, color: text }}>
        <Link
          to={`/reflections/${point.reflection_id}`}
          aria-label={aria}
          title={tooltip}
          className={inner}
          style={{ color: text }}
        >
          {rounded}
        </Link>
      </td>
    );
  }
  return (
    <td
      data-testid="trend-cell"
      data-value={point.value}
      className={baseClass}
      style={{ backgroundColor: fill, color: text }}
      aria-label={aria}
      title={tooltip}
    >
      <span className={inner}>{rounded}</span>
    </td>
  );
}

function TrendGrid({ trend }) {
  const { series = [], scale_max: scaleMax = 5, period } = trend || {};
  const labelsKey = series.map((s) => s.label).join('|');
  const [visibleSeries, setVisibleSeries] = useState(() => new Set(series.map((s) => s.label)));

  useEffect(() => {
    setVisibleSeries(new Set(labelsKey ? labelsKey.split('|') : []));
  }, [labelsKey]);

  const days = series[0]?.points?.map((p) => p.date) || [];

  if (series.length === 0 || days.length === 0) {
    return (
      <p data-testid="trend-empty" className="text-sm text-gray-600 dark:text-gray-400">
        No reflections in this range yet.
      </p>
    );
  }

  const toggle = (label) => {
    setVisibleSeries((prev) => {
      const next = new Set(prev);
      if (next.has(label)) next.delete(label);
      else next.add(label);
      return next;
    });
  };

  const filteredSeries = series.filter((s) => visibleSeries.has(s.label));

  return (
    <div data-testid="trend-grid" className="space-y-2">
      <div className="flex flex-wrap gap-1.5" data-testid="trend-legend">
        {series.map((s) => {
          const active = visibleSeries.has(s.label);
          const swatch = ratingColor(s.scale_max || scaleMax, s.scale_max || scaleMax);
          return (
            <button
              key={s.label}
              type="button"
              onClick={() => toggle(s.label)}
              data-testid={`trend-toggle-${s.label}`}
              aria-pressed={active}
              className={`inline-flex items-center gap-1.5 text-xs px-2 py-1 rounded-full border ${
                active
                  ? 'border-blue-300 bg-blue-50 dark:border-blue-700 dark:bg-blue-900/30 text-blue-900 dark:text-blue-100'
                  : 'border-gray-200 dark:border-gray-700 text-gray-500 dark:text-gray-400'
              }`}
            >
              <span
                className="inline-block w-3 h-3 rounded"
                style={{ backgroundColor: active ? swatch || NO_DATA_FILL : NO_DATA_FILL }}
                aria-hidden="true"
              />
              {s.label}
            </button>
          );
        })}
      </div>
      <div className="overflow-x-auto rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900">
        <table className="min-w-full border-collapse text-sm">
          <thead>
            <tr>
              <th
                scope="col"
                className="sticky left-0 z-10 bg-white dark:bg-gray-900 px-3 py-2 text-left font-medium text-gray-700 dark:text-gray-200 border-b border-gray-200 dark:border-gray-700"
              >
                Dimension
              </th>
              {days.map((d) => (
                <th
                  key={d}
                  scope="col"
                  className="px-1 py-2 text-[10px] font-mono text-gray-500 dark:text-gray-400 border-b border-gray-200 dark:border-gray-700 text-center"
                >
                  {formatShortDate(d)}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {filteredSeries.map((s) => (
              <tr key={s.label}>
                <th
                  scope="row"
                  className="sticky left-0 z-10 bg-white dark:bg-gray-900 px-3 py-1.5 text-left text-gray-800 dark:text-gray-200 border-b border-gray-200 dark:border-gray-700 whitespace-nowrap font-normal"
                >
                  {s.label}
                </th>
                {s.points.map((p) => (
                  <TrendCell
                    key={p.date}
                    point={p}
                    scaleMax={s.scale_max || scaleMax}
                    label={s.label}
                  />
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {period && (
        <p className="text-xs text-gray-500 dark:text-gray-400">
          {period.start} → {period.end}
        </p>
      )}
      <Legend scaleMax={scaleMax} />
    </div>
  );
}

function Legend({ scaleMax }) {
  const rows = ratingLegend(scaleMax);
  return (
    <div className="flex items-center gap-2 flex-wrap text-xs text-gray-600 dark:text-gray-300">
      <span className="font-medium">Scale:</span>
      {rows.map(({ value, fill }) => (
        <span key={value} className="inline-flex items-center gap-1">
          <span
            className="inline-block h-3 w-4 rounded"
            style={{ backgroundColor: fill }}
            aria-hidden="true"
          />
          <span>{value}</span>
        </span>
      ))}
    </div>
  );
}

function ReflectionField({ field }) {
  const prompt = getEnPrompt(field.prompts);
  const value = field.answer;
  let rendered;
  switch (field.type) {
    case 'textarea':
    case 'short_text':
      rendered = value ? (
        <p className="whitespace-pre-wrap text-gray-900 dark:text-white">{value}</p>
      ) : (
        <p className="italic text-gray-500 dark:text-gray-400">(no answer)</p>
      );
      break;
    case 'yes_no':
      rendered = (
        <p className="text-gray-900 dark:text-white">{value === true ? 'Yes' : value === false ? 'No' : '—'}</p>
      );
      break;
    case 'single_choice':
      rendered = <p className="text-gray-900 dark:text-white">{value || '—'}</p>;
      break;
    case 'multiple_choice':
      rendered = Array.isArray(value) && value.length > 0 ? (
        <ul className="list-disc list-inside text-gray-900 dark:text-white">
          {value.map((v) => (
            <li key={v}>{v}</li>
          ))}
        </ul>
      ) : (
        <p className="italic text-gray-500 dark:text-gray-400">(none)</p>
      );
      break;
    case 'single_rating':
      rendered = (
        <p className="text-gray-900 dark:text-white">
          {typeof value === 'number' ? `${value} / ${field.scale?.max || 5}` : '—'}
        </p>
      );
      break;
    case 'rating_group': {
      const entries = value && typeof value === 'object' ? Object.entries(value) : [];
      rendered = entries.length > 0 ? (
        <ul className="text-gray-900 dark:text-white space-y-0.5">
          {entries.map(([k, v]) => (
            <li key={k} className="text-sm">
              <span className="font-medium">{k}:</span> {v ?? '—'}
            </li>
          ))}
        </ul>
      ) : (
        <p className="italic text-gray-500 dark:text-gray-400">(no ratings)</p>
      );
      break;
    }
    default:
      rendered = (
        <pre className="text-xs whitespace-pre-wrap text-gray-700 dark:text-gray-300">
          {JSON.stringify(value, null, 2)}
        </pre>
      );
  }
  return (
    <div data-testid={`reflection-field-${field.key}`} className="text-sm">
      <p className="font-medium text-gray-700 dark:text-gray-200">{prompt}</p>
      <div className="mt-1">{rendered}</div>
    </div>
  );
}

function NoteListItem({ note }) {
  const [expanded, setExpanded] = useState(false);
  return (
    <li
      data-testid={`note-${note.id}`}
      data-sensitive={note.is_sensitive ? 'true' : 'false'}
      className="rounded-lg border border-gray-100 dark:border-gray-800 px-3 py-2 text-sm"
    >
      <div className="flex items-center justify-between gap-2">
        <p className="font-medium text-gray-900 dark:text-white">{note.author}</p>
        <span className="text-xs text-gray-500 dark:text-gray-400">
          {new Date(note.created_at).toLocaleString()}
        </span>
      </div>
      {note.is_sensitive && (
        <p className="text-[10px] uppercase font-semibold tracking-wide text-amber-700 dark:text-amber-300 mt-0.5">
          Sensitive
        </p>
      )}
      <p className="text-gray-800 dark:text-gray-200 whitespace-pre-wrap mt-1">
        {expanded || !note.is_long ? note.body : note.preview}
      </p>
      {note.is_long && (
        <button
          type="button"
          onClick={() => setExpanded((v) => !v)}
          className="text-xs text-blue-700 dark:text-blue-300 hover:underline mt-1"
        >
          {expanded ? 'Show less' : 'Read more'}
        </button>
      )}
    </li>
  );
}

function NotesSection({ title, payload, testid }) {
  const items = payload?.items || [];
  const sensitiveExcluded = payload?.sensitive_excluded_count || 0;
  const isEmpty = items.length === 0 && sensitiveExcluded === 0;
  return (
    <section
      data-testid={testid}
      className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 px-4 py-3 shadow-sm"
    >
      <h2 className="text-base font-semibold text-gray-900 dark:text-white">{title}</h2>
      {isEmpty ? (
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">— none.</p>
      ) : (
        <>
          {sensitiveExcluded > 0 && (
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1 italic">
              {sensitiveExcluded} sensitive note{sensitiveExcluded === 1 ? '' : 's'} not visible.
            </p>
          )}
          {items.length > 0 && (
            <ul className="space-y-2 mt-2">
              {items.map((n) => (
                <NoteListItem key={n.id} note={n} />
              ))}
            </ul>
          )}
        </>
      )}
    </section>
  );
}

function ScoresSection({ scores }) {
  if (!scores || scores.length === 0) {
    return (
      <section
        data-testid="section-today-scores"
        className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 px-4 py-3 shadow-sm"
      >
        <h2 className="text-base font-semibold text-gray-900 dark:text-white">Today's scores</h2>
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">— no scores in today's reflection.</p>
      </section>
    );
  }
  return (
    <section
      data-testid="section-today-scores"
      className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 px-4 py-3 shadow-sm"
    >
      <h2 className="text-base font-semibold text-gray-900 dark:text-white">Today's scores</h2>
      <div className="flex flex-wrap gap-2 mt-2">
        {scores.map((cell) => {
          const fill = cell.value == null ? NO_DATA_FILL : ratingColor(cell.value, cell.scale_max || 5);
          const text = ratingTextColor(cell.value, cell.scale_max || 5);
          return (
            <div
              key={cell.label}
              data-testid={`score-pill-${cell.label}`}
              className="inline-flex items-center gap-2 rounded-full px-3 py-1"
              style={{ backgroundColor: fill || NO_DATA_FILL, color: text }}
            >
              <span className="text-xs font-medium">{cell.label}</span>
              <span className="font-semibold">
                {cell.value == null ? '—' : cell.value}
              </span>
            </div>
          );
        })}
      </div>
    </section>
  );
}

function FlagsSection({ flags }) {
  if (!flags || flags.length === 0) return null;
  return (
    <section
      data-testid="section-today-flags"
      className="rounded-xl border border-amber-200 dark:border-amber-800 bg-amber-50 dark:bg-amber-900/30 px-4 py-3 shadow-sm"
    >
      <h2 className="text-base font-semibold text-amber-900 dark:text-amber-100">Flagged in today's reflection</h2>
      <ul className="list-disc list-inside mt-2 text-sm text-amber-900 dark:text-amber-100">
        {flags.map((f) => (
          <li key={f.key} data-testid={`flag-${f.key}`}>
            {getEnPrompt(f.prompts) || f.key}
          </li>
        ))}
      </ul>
    </section>
  );
}

function ReflectionSection({ reflection }) {
  if (!reflection) {
    return (
      <section
        data-testid="section-today-reflection"
        className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 px-4 py-3 shadow-sm"
      >
        <h2 className="text-base font-semibold text-gray-900 dark:text-white">Today's reflection</h2>
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">— not submitted yet.</p>
      </section>
    );
  }
  return (
    <section
      data-testid="section-today-reflection"
      className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 px-4 py-3 shadow-sm"
    >
      <div className="flex items-center justify-between gap-2">
        <h2 className="text-base font-semibold text-gray-900 dark:text-white">Today's reflection</h2>
        <p className="text-xs text-gray-500 dark:text-gray-400">
          by {reflection.author}
        </p>
      </div>
      <div className="mt-2 space-y-3">
        {(reflection.fields || []).map((f) => (
          <ReflectionField key={f.key} field={f} />
        ))}
      </div>
    </section>
  );
}

export default function CamperDashboard({
  data,
  selectedDate,
  onDateChange,
  selectedRange,
  onRangeChange,
  backTo,
}) {
  const header = data?.header;

  return (
    <div data-testid="camper-dashboard" className="px-4 py-6 pb-24 max-w-3xl mx-auto space-y-4">
      <header className="space-y-2">
        {backTo && (
          <Link to={backTo} className="text-sm text-blue-700 dark:text-blue-300 hover:underline">
            ← Back
          </Link>
        )}
        <div>
          <h1 className="text-2xl font-semibold text-gray-900 dark:text-white">
            {formatCamperName(header?.camper)}
          </h1>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <label className="text-sm text-gray-700 dark:text-gray-200 flex items-center gap-2">
            <span>Date:</span>
            <input
              type="date"
              value={selectedDate || header?.date || ''}
              onChange={(e) => onDateChange?.(e.target.value)}
              data-testid="camper-dashboard-date"
              className="rounded border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 px-2 py-1 text-sm"
            />
          </label>
          <label className="text-sm text-gray-700 dark:text-gray-200 flex items-center gap-2">
            <span>Range:</span>
            <select
              value={selectedRange || 'last_4_weeks'}
              onChange={(e) => onRangeChange?.(e.target.value)}
              data-testid="camper-dashboard-range"
              className="rounded border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 px-2 py-1 text-sm"
            >
              {RANGE_OPTIONS.map((r) => (
                <option key={r.value} value={r.value}>{r.label}</option>
              ))}
            </select>
          </label>
        </div>
      </header>

      <section
        data-testid="section-trend"
        className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 px-4 py-3 shadow-sm"
      >
        <h2 className="text-base font-semibold text-gray-900 dark:text-white mb-2">
          Trend
        </h2>
        <TrendGrid trend={data?.trend} />
      </section>

      <FlagsSection flags={data?.today_flags} />
      <ScoresSection scores={data?.today_scores} />
      <ReflectionSection reflection={data?.today_reflection} />
      <NotesSection
        title="Specialist reports"
        payload={data?.specialist_reports}
        testid="section-specialist-reports"
      />
      <NotesSection
        title="Camper care notes"
        payload={data?.camper_care_notes}
        testid="section-camper-care-notes"
      />
    </div>
  );
}
