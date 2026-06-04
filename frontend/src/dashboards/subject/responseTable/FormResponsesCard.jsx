/**
 * Shared per-template form-responses widget.
 *
 * Renders a collapsible card for one reflection template: KPI tiles,
 * rating-trend sparklines, and a schema-aware response table. Used by
 * the per-subject dashboard (`SubjectDetail`) and the unified group
 * dashboard (`GroupTemplateResponses`).
 *
 * The `block` shape comes from the backend dashboard payloads
 * (`api/dashboards/subject.py` and `api/dashboards/group_template_cards.py`):
 *   { template, schema_fields, summary, rating_series, reflections }
 *
 * `showSubject` adds a Subject column (group view, where each row is a
 * different person); the subject page omits it since the subject is fixed.
 */

import { useState } from 'react';
import { Link } from 'react-router-dom';
import { AlertTriangle, FileText, Users } from 'lucide-react';
import PrivacyChip from '../../../components/reflection/PrivacyChip';
import { ratingColor } from '../../colors';
import {
  deriveSchemaSections,
  formatShortDate,
  seriesDisplayLabel,
} from './schema';
import {
  DescriptionCell,
  RatingCellTd,
  SubjectCell,
} from './cells';

export function KpiTile({ icon: Icon, label, value, tone = 'neutral' }) {
  const accent = {
    neutral: 'text-blue-500',
    danger: 'text-red-500',
    warning: 'text-yellow-500',
    muted: 'text-gray-500',
  }[tone] ?? 'text-blue-500';
  return (
    <div
      className="bg-white dark:bg-gray-800 shadow-sm rounded-xl p-4 border border-gray-200 dark:border-gray-700"
      data-testid={`subject-kpi-${String(label).toLowerCase().replace(/\s+/g, '-')}`}
    >
      <div className="flex items-center">
        <Icon className={`w-6 h-6 ${accent} shrink-0`} />
        <div className="ml-3">
          <p className="text-xs uppercase tracking-wide text-gray-500 dark:text-gray-400">{label}</p>
          <p className="text-xl font-semibold text-gray-900 dark:text-white">{value}</p>
        </div>
      </div>
    </div>
  );
}

export function RatingSparkline({ points, scaleMax = 5, ariaLabel }) {
  const filtered = points.filter((p) => p.value != null);
  if (filtered.length === 0) {
    return <p className="text-xs text-gray-400 italic">No rating data in this window.</p>;
  }
  const w = 280;
  const h = 56;
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
    <svg width={w} height={h} viewBox={`0 0 ${w} ${h}`} role="img" aria-label={ariaLabel} className="block">
      {[1, Math.ceil(scaleMax / 2), scaleMax].map((v) => (
        <line key={v} x1={padX} x2={w - padX} y1={yScale(v)} y2={yScale(v)} stroke="#e5e7eb" strokeWidth="0.5" />
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
          <title>{formatShortDate(p.date)}: {Math.round(p.value)} of {scaleMax}</title>
        </circle>
      ))}
    </svg>
  );
}

export default function FormResponsesCard({
  block,
  language = 'en',
  testidPrefix = 'subject',
  showSubject = false,
  subjectLinkBase = null,
  subjectProfileLink = null,
}) {
  const tpl = block.template ?? {};
  const reflections = block.reflections ?? [];
  const firstDate = reflections.length > 0 ? reflections[0].date : null;
  const templateId = tpl.id;
  let responsesUrl = null;
  if (templateId) {
    responsesUrl = `/admin/templates/${templateId}/responses`;
    if (firstDate) {
      responsesUrl += `?date=${firstDate}&tab=individual`;
    }
  }
  const [open, setOpen] = useState(true);
  const schema = { fields: block.schema_fields ?? [] };
  const sections = deriveSchemaSections(schema, language);
  const { ratingCols, flagFields, chipFields, descTextFields } = sections;
  const summary = block.summary ?? { total_reflections: 0, flag_counts: {} };
  const series = block.rating_series ?? [];

  const hasRatingGroups = ratingCols.some((c) => c.subKey);
  const groupedHeader = [];
  let i = 0;
  while (i < ratingCols.length) {
    const col = ratingCols[i];
    if (col.subKey) {
      let j = i + 1;
      while (j < ratingCols.length && ratingCols[j].key === col.key && ratingCols[j].subKey) j += 1;
      groupedHeader.push({ label: col.groupLabel, span: j - i });
      i = j;
    } else {
      groupedHeader.push({ label: '', span: 1 });
      i += 1;
    }
  }
  // Date column, plus an optional Subject column on the group view.
  const leadingCols = showSubject ? 2 : 1;

  return (
    <section
      className="mb-6 bg-white dark:bg-gray-800 shadow-sm rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden"
      data-testid={`${testidPrefix}-template-card-${tpl.id}`}
    >
      <header className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
        <div>
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
            {block.assignment?.title || tpl.name}
          </h2>
          <p className="text-xs uppercase tracking-wide text-gray-400">
            {tpl.subject_mode}{tpl.slug ? ` · ${tpl.slug}` : ''}
            {block.assignment?.is_required === false ? ' · optional' : ''}
          </p>
        </div>
        <div className="flex gap-2 items-center">
          {responsesUrl && (
            <a
              href={responsesUrl}
              className="text-xs text-blue-600 dark:text-blue-400 underline hover:text-blue-800"
              target="_blank"
              rel="noopener noreferrer"
              title="Go to all form responses"
              data-testid={`${testidPrefix}-card-responses-link-${tpl.id}`}
            >
              View all responses
            </a>
          )}
          <button
            type="button"
            onClick={() => setOpen((v) => !v)}
            className="text-xs font-medium px-3 py-1.5 rounded-md border border-gray-200 dark:border-gray-600 text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700"
          >
            {open ? 'Collapse' : 'Expand'}
          </button>
        </div>
      </header>

      {open && (
        <div className="p-4 space-y-5">
          {/* KPIs */}
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3" data-testid={`${testidPrefix}-kpis-${tpl.id}`}>
            <KpiTile
              icon={FileText}
              label="Total reflections"
              value={summary.total_reflections}
              tone="neutral"
            />
            {Object.entries(summary.flag_counts ?? {}).map(([fieldKey, counts]) => {
              const flag = flagFields.find((f) => f.key === fieldKey);
              const label = flag?.label ?? fieldKey;
              const tone = counts.yes > 0
                ? (fieldKey.includes('camper_care') ? 'danger'
                  : fieldKey.includes('unit_head') ? 'warning'
                  : 'warning')
                : 'muted';
              return (
                <KpiTile
                  key={fieldKey}
                  icon={fieldKey.includes('camper_care') || fieldKey.includes('unit_head') ? AlertTriangle : Users}
                  label={label}
                  value={`${counts.yes} / ${counts.total}`}
                  tone={tone}
                />
              );
            })}
          </div>

          {/* Trends */}
          {series.length > 0 && (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4" data-testid={`${testidPrefix}-trends-${tpl.id}`}>
              {series.map((s) => {
                const displayLabel = seriesDisplayLabel(s.label, ratingCols);
                return (
                  <div key={s.label} className="rounded-lg border border-gray-200 dark:border-gray-700 p-3">
                    <p className="text-xs text-center font-medium text-gray-700 dark:text-gray-200 mb-1">{displayLabel}</p>
                    <RatingSparkline
                      points={s.points}
                      scaleMax={s.scale_max}
                      ariaLabel={`Rating trend for ${displayLabel}`}
                    />
                  </div>
                );
              })}
            </div>
          )}

          {/* Form-responses table */}
          {reflections.length === 0 ? (
            <p className="text-sm text-gray-500 dark:text-gray-400 italic">No reflections in this window.</p>
          ) : (
            <div className="overflow-x-auto">
              <table
                className="table-auto w-full text-sm dark:text-gray-300"
                data-testid={`${testidPrefix}-table-${tpl.id}`}
              >
                <thead className="text-xs uppercase text-gray-500 dark:text-gray-400 bg-gray-50 dark:bg-gray-700/50">
                  {hasRatingGroups && (
                    <tr>
                      <th colSpan={leadingCols} className="p-2 border-b border-gray-200 dark:border-gray-700" />
                      {groupedHeader.map((h, idx) => (
                        <th
                          key={`g-${idx}`}
                          colSpan={h.span}
                          className="p-2 border-b border-gray-200 dark:border-gray-700 text-center text-[10px] tracking-wide"
                        >
                          {h.label}
                        </th>
                      ))}
                      <th className="p-2 border-b border-gray-200 dark:border-gray-700" />
                    </tr>
                  )}
                  <tr>
                    <th className="p-2 text-center border-b border-gray-200 dark:border-gray-700 font-semibold">Date</th>
                    {showSubject && (
                      <th className="p-2 text-left border-b border-gray-200 dark:border-gray-700 font-semibold">Subject</th>
                    )}
                    {ratingCols.map((c, idx) => (
                      <th
                        key={`${c.key}-${c.subKey ?? ''}-${idx}`}
                        className="p-2 text-center border-b border-gray-200 dark:border-gray-700 font-semibold"
                        title={c.label}
                      >
                        <div className="truncate max-w-[8rem] mx-auto">{c.label}</div>
                      </th>
                    ))}
                    <th className="p-2 text-left border-b border-gray-200 dark:border-gray-700 font-semibold">Description</th>
                  </tr>
                </thead>
                <tbody className="text-sm font-medium divide-y divide-gray-200 dark:divide-gray-700/60">
                  {reflections.map((r) => {
                    // Re-shape per-reflection blob so DescriptionCell /
                    // SubjectCell see the same row shape the LT Responses
                    // page builds.
                    const row = {
                      ...r,
                      author: r.author_name ? { name: r.author_name } : null,
                    };
                    return (
                      <tr key={r.id} data-testid={`${testidPrefix}-row-${r.id}`}>
                        <td className="px-3 py-3 whitespace-nowrap text-center border border-gray-300 dark:border-gray-700">
                          <div className="text-sm text-gray-800 dark:text-gray-100">
                            {formatShortDate(r.date)}
                          </div>
                          <div className="text-[10px] text-gray-500 dark:text-gray-400 mt-0.5 inline-flex items-center gap-1">
                            {r.language ?? 'en'}
                            <PrivacyChip teamVisibility={r.team_visibility} size="icon" />
                          </div>
                          {r.assignment_group?.id && (
                            <Link
                              to={`/dashboards/group/${r.assignment_group.id}?date=${r.date}`}
                              className="block mt-1 text-[11px] text-indigo-600 dark:text-indigo-400 hover:underline"
                            >
                              {r.assignment_group.name ?? 'View group'} →
                            </Link>
                          )}
                        </td>
                        {showSubject && (
                          <SubjectCell
                            row={row}
                            linkTo={
                              r.subject?.id
                                ? (subjectProfileLink
                                  ? subjectProfileLink(r.subject.id)
                                  : subjectLinkBase
                                    ? `${subjectLinkBase}/${r.subject.id}`
                                    : null)
                                : null
                            }
                          />
                        )}
                        {ratingCols.map((c, idx) => (
                          <RatingCellTd
                            key={`${r.id}-${c.key}-${c.subKey ?? ''}-${idx}`}
                            col={c}
                            answers={r.answers}
                          />
                        ))}
                        <DescriptionCell
                          row={row}
                          flagFields={flagFields}
                          chipFields={chipFields}
                          descTextFields={descTextFields}
                          flagTestidPrefix={`${testidPrefix}-flag-${tpl.id}`}
                        />
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </section>
  );
}
