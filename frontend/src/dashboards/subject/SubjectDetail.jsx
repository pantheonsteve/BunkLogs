/**
 * Per-subject landing page (Step 7_21 follow-up; design ref:
 * docs/design/form_orchestration_reframe.md §4.1).
 *
 * Top-to-bottom sections: profile header, period stepper,
 * concerning-pattern alert, per-template form-response widgets
 * (KPI tiles + bunk-log style table + trend sparklines), and the
 * recent text-response list.
 *
 * The schema-aware table and KPI cells reuse helpers from
 * `responseTable/` so the visual treatment matches the LT Responses
 * page exactly. Data shape: see `GET /api/v1/dashboards/subject/<id>/`.
 */

import { useMemo, useState } from 'react';
import RichText from '../../components/ui/RichText';
import { Link, useNavigate } from 'react-router-dom';
import { AlertTriangle, FileText, MessageSquarePlus, Users } from 'lucide-react';
import ObservationComposer from '../../components/observations/ObservationComposer';
import PrivacyChip from '../../components/reflection/PrivacyChip';
import { ratingColor } from '../colors';
import {
  deriveSchemaSections,
  formatShortDate,
  getInitials,
  ratingTierClass,
} from './responseTable/schema';
import {
  DescriptionCell,
  RatingCellTd,
  SubjectCell,
} from './responseTable/cells';

// ---------------------------------------------------------------------------
// Small UI primitives
// ---------------------------------------------------------------------------

function Chip({ children, tone = 'neutral' }) {
  const palette = {
    neutral: 'bg-gray-100 text-gray-700 border-gray-200 dark:bg-gray-800 dark:text-gray-200 dark:border-gray-600',
    role: 'bg-indigo-100 text-indigo-800 border-indigo-200 dark:bg-indigo-900/30 dark:text-indigo-200 dark:border-indigo-800',
    program: 'bg-emerald-100 text-emerald-800 border-emerald-200 dark:bg-emerald-900/30 dark:text-emerald-200 dark:border-emerald-800',
    bunk: 'bg-sky-100 text-sky-800 border-sky-200 dark:bg-sky-900/30 dark:text-sky-200 dark:border-sky-800',
  }[tone] ?? 'bg-gray-100 text-gray-700 border-gray-200';
  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 text-xs font-medium rounded-full border ${palette}`}>
      {children}
    </span>
  );
}

function KpiTile({ icon: Icon, label, value, tone = 'neutral' }) {
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

// ---------------------------------------------------------------------------
// Header
// ---------------------------------------------------------------------------

function ProfileHeader({ subject, profile }) {
  const displayName = subject?.name ?? profile?.full_name ?? 'Unknown';
  const preferred = profile?.preferred_name && profile.preferred_name !== displayName
    ? ` (${profile.preferred_name})`
    : '';
  const role = profile?.primary_role;
  const programs = profile?.programs ?? [];
  const groups = profile?.assignment_groups ?? [];
  const language = profile?.preferred_language;
  return (
    <header
      className="bg-white dark:bg-gray-800 shadow-sm rounded-xl p-5 border border-gray-200 dark:border-gray-700 mb-6"
      data-testid="subject-profile-header"
    >
      <div className="flex items-start gap-4">
        <div className="w-14 h-14 shrink-0 rounded-full bg-gradient-to-br from-indigo-200 to-indigo-400 dark:from-indigo-700 dark:to-indigo-900 flex items-center justify-center text-lg font-semibold text-white">
          {getInitials(displayName)}
        </div>
        <div className="flex-1 min-w-0">
          <h1 className="text-2xl font-semibold text-gray-900 dark:text-white">
            {displayName}<span className="text-gray-500 dark:text-gray-400 font-normal">{preferred}</span>
          </h1>
          <div className="flex flex-wrap gap-2 mt-2">
            {role && <Chip tone="role">{role.replace(/_/g, ' ')}</Chip>}
            {programs.map((p) => (
              <Chip key={`prog-${p.id}`} tone="program">{p.name}</Chip>
            ))}
            {groups.map((g) => (
              <Link key={`grp-${g.id}`} to={`/dashboards/group/${g.id}`}>
                <Chip tone="bunk">{g.group_type}: {g.name}</Chip>
              </Link>
            ))}
            {language && <Chip>lang: {language}</Chip>}
          </div>
        </div>
      </div>
    </header>
  );
}

// ---------------------------------------------------------------------------
// Period stepper
// ---------------------------------------------------------------------------

const PRESET_DAYS = [7, 30, 90];

function PeriodStepper({ period, onRangeChange }) {
  if (!period) return null;
  const setPreset = (days) => {
    if (!onRangeChange) return;
    const end = new Date();
    const start = new Date();
    start.setDate(end.getDate() - (days - 1));
    const fmt = (d) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
    onRangeChange(fmt(start), fmt(end));
  };
  return (
    <section
      className="bg-white dark:bg-gray-800 shadow-sm rounded-xl p-4 border border-gray-200 dark:border-gray-700 mb-6 flex flex-wrap items-center gap-3"
      data-testid="subject-period-stepper"
    >
      <div>
        <p className="text-xs uppercase tracking-wide text-gray-500 dark:text-gray-400">Period</p>
        <p className="text-sm font-medium text-gray-800 dark:text-gray-100">
          {formatShortDate(period.start)} — {formatShortDate(period.end)}
        </p>
      </div>
      <div className="flex gap-2 ml-auto">
        {PRESET_DAYS.map((days) => (
          <button
            key={days}
            type="button"
            onClick={() => setPreset(days)}
            className="text-xs font-medium px-3 py-1.5 rounded-md border border-gray-200 dark:border-gray-600 text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-700"
            data-testid={`subject-period-preset-${days}`}
          >
            Last {days} days
          </button>
        ))}
      </div>
    </section>
  );
}

// ---------------------------------------------------------------------------
// Concerns
// ---------------------------------------------------------------------------

function ConcernsAlert({ concerns }) {
  if (!concerns || concerns.length === 0) return null;
  return (
    <section
      className="mb-6 rounded-lg border border-amber-300 dark:border-amber-700 bg-amber-50 dark:bg-amber-900/20 p-4"
      data-testid="subject-concerns"
    >
      <div className="flex items-start gap-2">
        <AlertTriangle className="w-5 h-5 text-amber-600 dark:text-amber-300 shrink-0 mt-0.5" />
        <div className="flex-1">
          <h3 className="font-medium text-amber-900 dark:text-amber-100 mb-2">
            Concerning patterns ({concerns.length})
          </h3>
          <ul className="text-sm text-amber-900 dark:text-amber-100 space-y-1">
            {concerns.map((c, i) => {
              const key = `${c.kind}-${c.field_label}-${i}`;
              if (c.kind === 'low_rating') {
                return (
                  <li key={key} className="flex flex-wrap items-center gap-2">
                    <span>
                      <strong>{c.field_label}</strong>: rating of {c.value} on {formatShortDate(c.date)}.
                    </span>
                    <PrivacyChip teamVisibility={c.team_visibility} />
                    {c.reflection_id && (
                      <Link to={`/reflections/${c.reflection_id}`} className="underline">
                        View reflection
                      </Link>
                    )}
                  </li>
                );
              }
              if (c.kind === 'downward_trend') {
                return (
                  <li key={key}>
                    <strong>{c.field_label}</strong>: recent week ({c.recent_mean}) is lower than prior week ({c.prior_mean}) by more than 0.5.
                  </li>
                );
              }
              return <li key={key}>{c.kind}: {c.field_label}</li>;
            })}
          </ul>
        </div>
      </div>
    </section>
  );
}

// ---------------------------------------------------------------------------
// Trend sparkline
// ---------------------------------------------------------------------------

function RatingSparkline({ points, scaleMax = 5, ariaLabel }) {
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

// ---------------------------------------------------------------------------
// Per-template form-responses widget
// ---------------------------------------------------------------------------

function FormResponsesCard({ block, language = 'en' }) {
  // Compute canonical link to the full response list for this template & date
  // E.g.: /leadership-team/templates/39/responses?date=2026-05-25&tab=individual
  // Pick first date in reflections if any, else leave off date
  const tpl = block.template ?? {};
  const reflections = block.reflections ?? [];
  const firstDate = reflections.length > 0 ? reflections[0].date : null;
  // Route: role segment is guessed as leadership-team for now; adapt as necessary
  const templateId = tpl.id;
  let responsesUrl = null;
  if (templateId) {
    responsesUrl = `/leadership-team/templates/${templateId}/responses`;
    if (firstDate) {
      // ISO format, but truncate to YYYY-MM-DD if needed
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
  const leadingCols = 1; // Date column only — subject is fixed for the page

  return (
    <section
      className="mb-6 bg-white dark:bg-gray-800 shadow-sm rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden"
      data-testid={`subject-template-card-${tpl.id}`}
    >
      <header className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
        <div>
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">{tpl.name}</h2>
          <p className="text-xs uppercase tracking-wide text-gray-400">
            {tpl.subject_mode}{tpl.slug ? ` · ${tpl.slug}` : ''}
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
              data-testid={`subject-card-responses-link-${tpl.id}`}
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
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3" data-testid={`subject-kpis-${tpl.id}`}>
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
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4" data-testid={`subject-trends-${tpl.id}`}>
              {series.map((s) => (
                <div key={s.label} className="rounded-lg border border-gray-200 dark:border-gray-700 p-3">
                  <p className="text-xs font-medium text-gray-700 dark:text-gray-200 mb-1">{s.label}</p>
                  <RatingSparkline
                    points={s.points}
                    scaleMax={s.scale_max}
                    ariaLabel={`Rating trend for ${s.label}`}
                  />
                </div>
              ))}
            </div>
          )}

          {/* Form-responses table */}
          {reflections.length === 0 ? (
            <p className="text-sm text-gray-500 dark:text-gray-400 italic">No reflections in this window.</p>
          ) : (
            <div className="overflow-x-auto">
              <table
                className="table-auto w-full text-sm dark:text-gray-300"
                data-testid={`subject-table-${tpl.id}`}
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
                    // Re-shape per-reflection blob so DescriptionCell sees
                    // the same row shape it gets on the LT Responses page.
                    const row = {
                      ...r,
                      author: r.author_name ? { name: r.author_name } : null,
                    };
                    return (
                      <tr key={r.id} data-testid={`subject-row-${r.id}`}>
                        <td className="px-3 py-3 whitespace-nowrap text-center border border-gray-300 dark:border-gray-700">
                          <div className="text-sm text-gray-800 dark:text-gray-100">
                            {formatShortDate(r.date)}
                          </div>
                          <div className="text-[10px] text-gray-500 dark:text-gray-400 mt-0.5 inline-flex items-center gap-1">
                            {r.language ?? 'en'}
                            <PrivacyChip teamVisibility={r.team_visibility} size="icon" />
                          </div>
                          <Link
                            to={`/reflections/${r.id}`}
                            className="block mt-1 text-[11px] text-indigo-600 dark:text-indigo-400 hover:underline"
                          >
                            Open →
                          </Link>
                        </td>
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
                          flagTestidPrefix={`subject-flag-${tpl.id}`}
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

// ---------------------------------------------------------------------------
// Recent text responses
// ---------------------------------------------------------------------------

function RecentTexts({ texts }) {
  if (!texts || texts.length === 0) return null;
  return (
    <section className="mb-6" data-testid="subject-recent-texts">
      <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
        Recent text responses
      </h2>
      <ul className="space-y-2">
        {texts.map((t, i) => (
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
            <RichText
              html={t.text}
              className="text-sm text-gray-800 dark:text-gray-200"
            />
      
          </li>
        ))}
      </ul>
    </section>
  );
}

// ---------------------------------------------------------------------------
// Root
// ---------------------------------------------------------------------------

const SENSITIVITY_LABEL = {
  normal: 'Normal',
  sensitive: 'Sensitive',
  domain: 'Domain',
  confidential: 'Confidential',
};

function ObservationsPanel({ observations = [], subject, personId, onCreated }) {
  const navigate = useNavigate();
  const [open, setOpen] = useState(true);
  const [composing, setComposing] = useState(false);

  const sorted = useMemo(
    () => [...observations].sort((a, b) => {
      const ta = a.created_at ? new Date(a.created_at).getTime() : 0;
      const tb = b.created_at ? new Date(b.created_at).getTime() : 0;
      return tb - ta;
    }),
    [observations],
  );

  return (
    <section
      className="mb-6 bg-white dark:bg-gray-800 shadow-sm rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden"
      data-testid="observations-panel"
    >
      <header className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center gap-2">
          <MessageSquarePlus className="w-5 h-5 text-indigo-500" />
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Observations</h2>
          {observations.length > 0 && (
            <span className="text-xs font-medium px-2 py-0.5 rounded-full bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300">
              {observations.length}
            </span>
          )}
        </div>
        <div className="flex gap-2 items-center">
          {personId && (
            <button
              type="button"
              onClick={() => setComposing(true)}
              className="text-xs font-medium px-3 py-1.5 rounded-md bg-indigo-50 dark:bg-indigo-900/30 border border-indigo-200 dark:border-indigo-800 text-indigo-700 dark:text-indigo-200 hover:bg-indigo-100 dark:hover:bg-indigo-900/50"
              data-testid="observation-add-btn"
            >
              + Add observation
            </button>
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
        <div className="p-4">
          {sorted.length === 0 ? (
            <p className="text-sm text-gray-500 dark:text-gray-400 italic" data-testid="observations-empty">
              No observations yet.
            </p>
          ) : (
            <ul className="space-y-3">
              {sorted.map((o) => (
                <li key={o.id}>
                  <Link
                    to={`/observations/${o.id}`}
                    className="block rounded-lg border border-gray-200 dark:border-gray-700 p-3 hover:bg-gray-50 dark:hover:bg-gray-700/40"
                  >
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-xs rounded-full bg-amber-50 dark:bg-amber-900/20 px-2 py-0.5 text-amber-800 dark:text-amber-200">
                        {SENSITIVITY_LABEL[o.sensitivity] ?? o.sensitivity}
                      </span>
                      {o.context && (
                        <span className="text-xs text-gray-400">{o.context}</span>
                      )}
                      {o.author && (
                        <span className="text-xs text-gray-400 ml-auto">{o.author.name}</span>
                      )}
                    </div>
                    <RichText
                      html={o.body}
                      className="text-sm text-gray-800 dark:text-gray-200 break-words [&_p]:mb-1 last:[&_p]:mb-0"
                    />
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      {composing && (
        <ObservationComposer
          initialSubjects={subject ? [{ id: personId, full_name: subject.name }] : []}
          onClose={() => setComposing(false)}
          onSent={(data) => {
            setComposing(false);
            if (onCreated) onCreated();
            if (data?.id) navigate(`/observations/${data.id}`);
          }}
        />
      )}
    </section>
  );
}

export default function SubjectDetail({ payload, onRangeChange, personId, onNoteCreated }) {
  if (!payload) return null;
  const {
    subject,
    subject_profile: profile,
    period,
    templates,
    recent_texts: recentTexts,
    concerning_patterns: concerns,
    observations,
  } = payload;
  const language = profile?.preferred_language ?? 'en';
  return (
    <div>
      <ProfileHeader subject={subject} profile={profile} />
      <PeriodStepper period={period} onRangeChange={onRangeChange} />
      <ConcernsAlert concerns={concerns} />

      {(!templates || templates.length === 0) ? (
        <p className="text-sm text-gray-500 dark:text-gray-400" data-testid="subject-empty">
          No reflections about this person in the selected window (or you don&apos;t have permission to view them).
        </p>
      ) : (
        templates.map((t) => (
          <FormResponsesCard
            key={t.template?.id ?? t.template?.slug}
            block={t}
            language={language}
          />
        ))
      )}

      {/*<RecentTexts texts={recentTexts} />*/} 
      <ObservationsPanel
        observations={observations ?? []}
        subject={subject}
        personId={personId}
        onCreated={onNoteCreated}
      />
      {/* TODO(7_23): legacy SubjectNote panel removed in 7_24 */}
    </div>
  );
}

// Re-export shared cell so callers/tests can probe it without reaching
// into the responseTable module directly.
export { SubjectCell };
