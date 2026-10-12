/**
 * Staff view of one camper / student (`/profile/:personId`, 2027 refresh).
 *
 * Header, period toolbar, then per-category KPIs, a daily score chart, and
 * a daily logs table for the primary rating template; other templates keep
 * the shared `FormResponsesCard`. Observations sit in the right column with
 * a count-only placeholder for tiers the viewer can't read. Visibility is
 * server-side: this view renders only what the payload contains.
 * Data shape: see `GET /api/v1/dashboards/subject/<id>/`.
 */

import { useMemo, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Lock } from 'lucide-react';
import RichText from '../../components/ui/RichText';
import Badge from '../../components/ui/Badge';
import Button from '../../components/ui/Button';
import InitialsAvatar from '../../components/ui/InitialsAvatar';
import KpiTile from '../../components/ui/KpiTile';
import RatingCell from '../../components/ui/RatingCell';
import SegmentedControl from '../../components/ui/SegmentedControl';
import SensitiveNotePlaceholder from '../../components/SensitiveNotePlaceholder';
import PrivacyChip from '../../components/reflection/PrivacyChip';
import ObservationComposer, { dateOnlyToLocalDatetime } from '../../components/observations/ObservationComposer';
import { sensitivityAudience } from '../../api/observations';
import { useTerm } from '../../context/OrgBrandingContext';
import {
  groupDashboardLink,
  observationThreadLink,
  profileBackLabel,
  profileLink,
  resolveProfileBackGroup,
} from '../../utils/dashboardLinks';
import { downloadSubjectEntriesExport, subjectEntriesPageLink } from './flattenSubjectEntries';
import { deriveSchemaSections, isTruthyFlag } from './responseTable/schema';
import { SubjectCell } from './responseTable/cells';
import FormResponsesCard from './responseTable/FormResponsesCard';
import ScoreTrendChart from './ScoreTrendChart';
import {
  PERIOD_OPTIONS,
  activePeriod,
  addDays,
  computeKpi,
  dailyValues,
  dayCount,
  dayRange,
  formatDay,
  helpRequestDays,
  isCamperCareHelpField,
  isUnitHeadHelpField,
  localToday,
  periodRange,
  pickPrimaryBlock,
} from './profileStats';

const CARD = 'rounded-[14px] border border-line bg-white dark:bg-gray-900 px-5 py-5';

const SERIES_COLORS = {
  social: 'var(--color-series-social)',
  behavior: 'var(--color-series-behavior)',
  participation: 'var(--color-series-participation)',
};
const FALLBACK_COLORS = [
  SERIES_COLORS.social,
  SERIES_COLORS.behavior,
  SERIES_COLORS.participation,
  'var(--color-ink-2)',
];

const PRIOR_LABEL = { week: 'prior week', '4weeks': 'prior 4 weeks' };

function colKey(col) {
  return col.subKey ? `${col.key}__${col.subKey}` : col.key;
}

function seriesColor(col, index) {
  return SERIES_COLORS[col.subKey ?? col.key] ?? FALLBACK_COLORS[index % FALLBACK_COLORS.length];
}

function titleCase(s) {
  return String(s || '').replace(/\b\w/g, (c) => c.toUpperCase());
}

function languageName(code) {
  if (!code) return null;
  try {
    return new Intl.DisplayNames(['en'], { type: 'language' }).of(code) ?? code;
  } catch {
    return code;
  }
}

function formatObservationWhen(iso) {
  if (!iso) return '';
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? '' : d.toLocaleString();
}

// ---------------------------------------------------------------------------
// Left rail
// ---------------------------------------------------------------------------

function ProfileRail({ backGroup, backDate, groupPayload, personId }) {
  const term = useTerm();
  const to = backGroup ? groupDashboardLink(backGroup.id, { date: backDate }) : null;
  const label = profileBackLabel(backGroup);
  const subjects = (groupPayload?.roster ?? []).filter((m) => m.role_in_group === 'subject');
  const helpIds = new Set([
    ...(groupPayload?.help_requested ?? []).map((c) => c.id),
    ...(groupPayload?.camper_care_help_requested ?? []).map((c) => c.id),
  ]);
  if (!to) return <div />;
  return (
    <nav aria-label="Group" className="mb-4 lg:mb-0 flex flex-col gap-0.5">
      <Link
        to={to}
        className="inline-flex items-center min-h-10 px-2.5 rounded-lg text-[13px] font-semibold text-ink-2 hover:bg-line-soft"
        data-testid="profile-back-to-group"
      >
        {label}
      </Link>
      {subjects.length > 0 && (
        <div className="hidden lg:flex flex-col gap-0.5" data-testid="profile-rail-roster">
          <div className="px-2.5 pt-3.5 pb-1.5 text-[11px] font-semibold tracking-wider uppercase text-muted">
            {backGroup.name ?? groupPayload?.header?.bunk?.name ?? groupPayload?.header?.group?.name} · {subjects.length} {term('camper', { plural: subjects.length !== 1 })}
          </div>
          {subjects.map((m) => {
            const current = String(m.person_id) === String(personId);
            return (
              <Link
                key={m.person_id}
                to={profileLink(m.person_id, { groupId: backGroup.id, date: backDate })}
                aria-current={current ? 'page' : undefined}
                className={`flex items-center gap-2.5 min-h-[38px] px-2.5 rounded-lg text-sm ${
                  current ? 'font-semibold bg-brand-soft text-brand' : 'font-medium text-ink-2 hover:bg-line-soft'
                }`}
              >
                <span className="flex-1 truncate">{m.name}</span>
                {helpIds.has(m.person_id) && (
                  <span
                    role="img"
                    aria-label="Help requested"
                    className="w-2 h-2 rounded-full bg-[#d97a2a]"
                    data-testid={`rail-help-dot-${m.person_id}`}
                  />
                )}
              </Link>
            );
          })}
        </div>
      )}
    </nav>
  );
}

// ---------------------------------------------------------------------------
// Header
// ---------------------------------------------------------------------------

export function ProfileHeader({
  subject,
  profile,
  help = { unitHead: 0, camperCare: 0 },
  helpWindow = 7,
  staff = [],
  staffLabel = 'Staff',
}) {
  const term = useTerm();
  const displayName = subject?.name ?? profile?.full_name ?? 'Unknown';
  const preferred = profile?.preferred_name && profile.preferred_name !== displayName
    ? ` (${profile.preferred_name})`
    : '';
  const role = profile?.primary_role;
  const programs = profile?.programs ?? [];
  const groups = profile?.assignment_groups ?? [];
  const language = languageName(profile?.preferred_language);
  const windowLabel = `of last ${helpWindow} day${helpWindow === 1 ? '' : 's'}`;
  const hasHelp = help.unitHead > 0 || help.camperCare > 0;

  return (
    <section
      className="rounded-2xl border border-line bg-white dark:bg-gray-900 px-6 py-5 flex flex-wrap items-center gap-x-5 gap-y-4"
      data-testid="subject-profile-header"
    >
      <InitialsAvatar name={displayName} size="xl" aria-hidden="true" />
      <div className="flex-1 min-w-[240px] flex flex-col gap-2">
        <h1 className="text-[28px] leading-tight font-bold tracking-tight text-ink">
          {displayName}<span className="font-normal text-muted">{preferred}</span>
        </h1>
        <div className="flex flex-wrap gap-1.5">
          {role && <Badge size="md" className="font-semibold capitalize">{role.replace(/_/g, ' ')}</Badge>}
          {programs.map((p) => (
            <Badge key={`prog-${p.id}`} size="md" className="font-semibold">{p.name}</Badge>
          ))}
          {groups.map((g) => (
            <Link key={`grp-${g.id}`} to={groupDashboardLink(g.id)} className="hover:opacity-80">
              <Badge tone="info" size="md" className="font-semibold">
                {titleCase(g.group_type)}: {g.name}
              </Badge>
            </Link>
          ))}
          {language && <Badge size="md" className="font-semibold">{language}</Badge>}
        </div>
      </div>
      {(hasHelp || staff.length > 0) && (
        <div className="flex flex-col items-start gap-1.5">
          {hasHelp && (
            <div className="flex flex-wrap gap-1.5" data-testid="subject-help-badges">
              {help.unitHead > 0 && (
                <Badge tone="warn" size="md" className="font-semibold" data-testid="subject-help-request_unit_head_help">
                  {titleCase(term('unit_head'))} help · {help.unitHead} {windowLabel}
                </Badge>
              )}
              {help.camperCare > 0 && (
                <Badge tone="danger" size="md" className="font-semibold" data-testid="subject-help-request_camper_care_help">
                  {term('camper_care')} help · {help.camperCare} {windowLabel}
                </Badge>
              )}
            </div>
          )}
          {staff.length > 0 && (
            <span className="text-xs text-muted pl-1" data-testid="subject-staff-line">
              {staffLabel}: {staff.join(', ')}
            </span>
          )}
        </div>
      )}
    </section>
  );
}

// ---------------------------------------------------------------------------
// Toolbar
// ---------------------------------------------------------------------------

function Toolbar({
  start, end, logCount, periodCtx, onRangeChange, refreshing, personId, subjectName,
}) {
  const [exporting, setExporting] = useState(false);
  const [exportError, setExportError] = useState(null);
  const options = PERIOD_OPTIONS.filter((o) => periodRange(o.value, periodCtx));
  const active = activePeriod(start, end, periodCtx);

  const pick = (value) => {
    const r = periodRange(value, periodCtx);
    if (r && onRangeChange) onRangeChange(r.start, r.end);
  };

  const runExport = async () => {
    setExporting(true);
    setExportError(null);
    try {
      await downloadSubjectEntriesExport(personId, { start, end, subjectName });
    } catch (e) {
      setExportError(e.response?.data?.detail || e.message || 'Export failed');
    } finally {
      setExporting(false);
    }
  };

  return (
    <div className="flex flex-wrap items-center gap-3" data-testid="subject-period-toolbar">
      <SegmentedControl
        options={options}
        value={active}
        onChange={pick}
        ariaLabel="Period"
        testIdPrefix="subject-period-"
      />
      <span className="text-[13px] text-ink-2" data-testid="subject-period-label">
        {formatDay(start)} – {formatDay(end)} · {logCount} daily log{logCount === 1 ? '' : 's'}
        {refreshing && <span className="ml-2 text-muted">Updating…</span>}
      </span>
      {personId && (
        <div className="ml-auto flex flex-wrap items-center gap-2">
          <Button
            as={Link}
            variant="secondary"
            to={subjectEntriesPageLink(personId, { start, end })}
            data-testid="subject-all-entries-link"
          >
            All entries →
          </Button>
          <Button variant="secondary" onClick={runExport} disabled={exporting} data-testid="subject-export-btn">
            {exporting ? 'Exporting…' : 'Export'}
          </Button>
          {exportError && <span className="text-xs text-danger-ink">{exportError}</span>}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Primary template: KPIs, chart, daily logs
// ---------------------------------------------------------------------------

function KpiGrid({ cols, reflections, priorReflections, end, priorLabel }) {
  return (
    <div className="grid gap-4 grid-cols-[repeat(auto-fit,minmax(220px,1fr))]" data-testid="subject-kpis">
      {cols.map((col, i) => {
        const { avg, delta, last7 } = computeKpi(col, { reflections, priorReflections, rangeEnd: end });
        const abs = delta == null ? null : Math.abs(delta).toFixed(1);
        let direction = null;
        if (abs != null && abs !== '0.0') direction = delta > 0 ? 'up' : 'down';
        return (
          <KpiTile
            key={colKey(col)}
            data-testid={`subject-kpi-${colKey(col)}`}
            label={(
              <span className="inline-flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full" style={{ background: seriesColor(col, i) }} aria-hidden="true" />
                {col.label}
              </span>
            )}
            value={avg == null ? '—' : avg.toFixed(1)}
            delta={abs ?? undefined}
            deltaDirection={direction}
            sub={delta == null ? 'No prior data' : `vs ${priorLabel}`}
          >
            <div className="flex gap-[3px] mt-1" role="group" aria-label="Last 7 days">
              {last7.map((d) => (
                <RatingCell
                  key={d.date}
                  size="sm"
                  className="flex-1"
                  value={d.value == null ? null : Math.round(d.value * 10) / 10}
                  scaleMax={col.scaleMax}
                  label={`${col.label} ${formatDay(d.date)}`}
                />
              ))}
            </div>
          </KpiTile>
        );
      })}
    </div>
  );
}

function DailyLogs({ block, cols, flagFields, descTextFields, uhLabel, ccLabel, onAddObservation }) {
  const tplId = block.template?.id;
  const rows = [...(block.reflections ?? [])].sort(
    (a, b) => b.date.localeCompare(a.date) || (b.id ?? 0) - (a.id ?? 0),
  );
  return (
    <section className={CARD} aria-labelledby="subject-daily-logs-title" data-testid="subject-daily-logs">
      <h2 id="subject-daily-logs-title" className="text-base font-bold text-ink mb-3">Daily logs</h2>
      {rows.length === 0 ? (
        <p className="text-sm text-muted">No logs in this period.</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full min-w-[560px] text-sm" data-testid={`subject-table-${tplId}`}>
            <thead>
              <tr className="text-left text-xs text-muted">
                <th scope="col" className="font-semibold py-1.5 pr-2">Date</th>
                {cols.map((c) => (
                  <th key={colKey(c)} scope="col" className="font-semibold py-1.5 px-1 text-center w-16">{c.label}</th>
                ))}
                <th scope="col" className="font-semibold py-1.5 pl-3">Note</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => {
                const notes = descTextFields
                  .map((f) => r.answers?.[f.key])
                  .filter((v) => typeof v === 'string' && v.trim());
                const flags = flagFields.filter((f) => isTruthyFlag(r.answers?.[f.key]));
                return (
                  <tr key={r.id} data-testid={`subject-row-${r.id}`}>
                    <td className="py-2.5 pr-2 border-t border-line-soft align-top whitespace-nowrap">
                      <div className="flex items-center gap-1.5 font-semibold text-ink">
                        {formatDay(r.date)}
                        <PrivacyChip teamVisibility={r.team_visibility} size="icon" />
                      </div>
                      {onAddObservation && (
                        <button
                          type="button"
                          onClick={() => onAddObservation(r.date)}
                          className="mt-1 text-[11px] font-semibold text-brand hover:underline"
                          data-testid={`subject-add-observation-${r.id}`}
                        >
                          Note +
                        </button>
                      )}
                    </td>
                    {cols.map((c) => (
                      <td key={colKey(c)} className="py-2 px-[3px] border-t border-line-soft align-top">
                        <RatingCell
                          value={r.answers ? (c.subKey ? r.answers[c.key]?.[c.subKey] : r.answers[c.key]) : null}
                          scaleMax={c.scaleMax}
                          label={c.label}
                        />
                      </td>
                    ))}
                    <td className="py-2.5 pl-3 border-t border-line-soft align-top">
                      {notes.map((html, i) => (
                        <RichText key={i} html={html} className="text-[13px] leading-normal text-ink break-words" />
                      ))}
                      <div className="flex flex-wrap items-center gap-1.5 mt-1">
                        {r.author_name && <span className="text-xs text-muted">{r.author_name}</span>}
                        {flags.map((f) => {
                          let tone = 'neutral';
                          let text = f.label;
                          if (isUnitHeadHelpField(f)) { tone = 'warn'; text = uhLabel; }
                          else if (isCamperCareHelpField(f)) { tone = 'danger'; text = ccLabel; }
                          return (
                            <Badge
                              key={f.key}
                              tone={tone}
                              size="xs"
                              className="font-bold"
                              data-testid={`subject-flag-${tplId}-${f.key}`}
                            >
                              {text}
                            </Badge>
                          );
                        })}
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

// ---------------------------------------------------------------------------
// Observations
// ---------------------------------------------------------------------------

function ObservationsPanel({ observations = [], hidden = [], onCompose, profileReturnTo = null }) {
  const sorted = useMemo(
    () => [...observations].sort((a, b) => {
      const ta = Date.parse(a.observed_at || a.created_at || '') || 0;
      const tb = Date.parse(b.observed_at || b.created_at || '') || 0;
      return tb - ta;
    }),
    [observations],
  );

  return (
    <section className={`${CARD} flex flex-col gap-3`} aria-labelledby="subject-obs-title" data-testid="observations-panel">
      <div className="flex items-center justify-between gap-2">
        <h2 id="subject-obs-title" className="text-base font-bold text-ink">Observations</h2>
        {onCompose && (
          <Button size="sm" onClick={() => onCompose()} data-testid="observation-add-btn">
            + Add observation
          </Button>
        )}
      </div>
      {sorted.length === 0 && (
        <p className="text-sm text-muted" data-testid="observations-empty">
          No observations in this period.
        </p>
      )}
      {sorted.map((o) => {
        const whenIso = o.observed_at || o.created_at;
        const whenLabel = formatObservationWhen(whenIso);
        return (
          <Link
            key={o.id}
            to={observationThreadLink(o.id, profileReturnTo)}
            className="block border-t border-line-soft pt-3 -mx-2 px-2 rounded-md hover:bg-line-soft/60"
          >
            <RichText
              html={o.body}
              className="text-[13px] leading-normal text-ink break-words [&_p]:mb-1 last:[&_p]:mb-0"
            />
            <div className="flex flex-wrap items-center gap-x-1.5 gap-y-1 mt-1 text-xs text-muted">
              {o.author && <span>{o.author.name}</span>}
              {whenLabel && (
                <time dateTime={whenIso} data-testid={`observation-when-${o.id}`}>{whenLabel}</time>
              )}
              {o.sensitivity && o.sensitivity !== 'normal' && (
                <Badge tone="warn" size="xs">{sensitivityAudience(o.sensitivity)}</Badge>
              )}
            </div>
          </Link>
        );
      })}
      {hidden.map((h) => (
        <div
          key={h.sensitivity}
          className="flex items-center gap-2.5 rounded-[10px] bg-ground px-3 py-2.5 text-ink-2"
        >
          <Lock className="w-4 h-4 shrink-0" aria-hidden="true" />
          <SensitiveNotePlaceholder count={h.count} gatingRole={h.gating_role} />
        </div>
      ))}
    </section>
  );
}

// ---------------------------------------------------------------------------
// Root
// ---------------------------------------------------------------------------

export default function SubjectDetail({
  payload,
  priorTemplates = null,
  groupPayload = null,
  rangeStart,
  rangeEnd,
  onRangeChange,
  personId,
  onNoteCreated,
  refreshing = false,
  backGroupId = null,
  backDate = '',
  profileReturnTo = null,
}) {
  const navigate = useNavigate();
  const term = useTerm();
  const [composeObservation, setComposeObservation] = useState(null);
  if (!payload) return null;

  const {
    subject,
    subject_profile: profile,
    period,
    templates = [],
    observations,
    hidden_observations: hiddenObservations,
  } = payload;
  const language = profile?.preferred_language ?? 'en';
  const start = rangeStart || period?.start || '';
  const end = rangeEnd || period?.end || '';
  const periodCtx = { today: localToday(), programs: profile?.programs };
  const active = activePeriod(start, end, periodCtx);

  const primary = pickPrimaryBlock(templates, language);
  const others = templates.filter((t) => t !== primary);
  const sections = primary
    ? deriveSchemaSections({ fields: primary.schema_fields ?? [] }, language)
    : null;
  const cols = sections?.ratingCols ?? [];
  const priorBlock = primary
    ? (priorTemplates ?? []).find((t) => t.template?.id === primary.template?.id)
    : null;

  const helpDays = helpRequestDays(templates);
  const helpWindow = end ? Math.min(7, start ? dayCount(start, end) : 7) : 7;
  const windowStart = end ? addDays(end, -(helpWindow - 1)) : '';
  const inWindow = (d) => !end || (d >= windowStart && d <= end);
  const help = {
    unitHead: [...helpDays.unitHead].filter(inWindow).length,
    camperCare: [...helpDays.camperCare].filter(inWindow).length,
  };

  const backGroup = resolveProfileBackGroup(backGroupId, profile?.assignment_groups);
  const staff = (groupPayload?.roster ?? [])
    .filter((m) => m.role_in_group === 'author')
    .map((m) => m.name);
  const staffLabel = backGroup?.group_type === 'bunk'
    ? titleCase(term('counselor', { plural: staff.length !== 1 }))
    : 'Staff';

  const uhLabel = `${titleCase(term('unit_head'))} help`;
  const ccLabel = `${term('camper_care')} help`;
  const logCount = primary
    ? primary.reflections?.length ?? 0
    : templates.reduce((n, t) => n + (t.reflections?.length ?? 0), 0);

  const openCompose = (date) => {
    setComposeObservation({
      observedAtLocal: date ? dateOnlyToLocalDatetime(date) : null,
    });
  };
  const composeFromPanel = () => {
    openCompose(start && start === end ? end : null);
  };
  const onAddObservation = personId ? openCompose : null;

  return (
    <div className="lg:grid lg:grid-cols-[200px_minmax(0,1fr)] lg:gap-8">
      <ProfileRail
        backGroup={backGroup}
        backDate={backDate}
        groupPayload={groupPayload}
        personId={personId}
      />
      <div className="flex flex-col gap-5 min-w-0">
        <ProfileHeader
          subject={subject}
          profile={profile}
          help={help}
          helpWindow={helpWindow}
          staff={staff}
          staffLabel={staffLabel}
        />
        <Toolbar
          start={start}
          end={end}
          logCount={logCount}
          periodCtx={periodCtx}
          onRangeChange={onRangeChange}
          refreshing={refreshing}
          personId={personId}
          subjectName={subject?.name}
        />
        {primary && (
          <KpiGrid
            cols={cols}
            reflections={primary.reflections}
            priorReflections={priorBlock?.reflections}
            end={end}
            priorLabel={PRIOR_LABEL[active] ?? 'prior period'}
          />
        )}
        <div className="flex flex-col gap-5 2xl:grid 2xl:grid-cols-[minmax(0,1fr)_340px] 2xl:items-start">
          <div className="flex flex-col gap-5 min-w-0">
            {primary && (
              <>
                <section className={CARD} aria-labelledby="subject-trend-title">
                  <h2 id="subject-trend-title" className="text-base font-bold text-ink mb-3">Daily scores</h2>
                  <ScoreTrendChart
                    days={dayRange(start, end)}
                    series={cols.map((col, i) => ({
                      key: colKey(col),
                      label: col.label,
                      color: seriesColor(col, i),
                      values: dailyValues(primary.reflections, col),
                    }))}
                    helpDates={new Set([...helpDays.unitHead, ...helpDays.camperCare])}
                    scaleMax={cols[0]?.scaleMax ?? 5}
                  />
                </section>
                <DailyLogs
                  block={primary}
                  cols={cols}
                  flagFields={sections.flagFields}
                  descTextFields={sections.descTextFields}
                  uhLabel={uhLabel}
                  ccLabel={ccLabel}
                  onAddObservation={onAddObservation}
                />
              </>
            )}
            {templates.length === 0 && (
              <p className="text-sm text-muted" data-testid="subject-empty">
                No reflections about this person in the selected window (or you don&apos;t have permission to view them).
              </p>
            )}
            {others.map((t) => (
              <FormResponsesCard
                key={t.template?.id ?? t.template?.slug}
                block={t}
                language={language}
                personId={personId}
                onAddObservation={onAddObservation}
              />
            ))}
          </div>
          <aside className="flex flex-col gap-5 min-w-0">
            <ObservationsPanel
              observations={observations ?? []}
              hidden={hiddenObservations ?? []}
              onCompose={personId ? composeFromPanel : null}
              profileReturnTo={profileReturnTo}
            />
          </aside>
        </div>
      </div>
      {composeObservation && (
        <ObservationComposer
          initialSubjects={subject ? [{ id: Number(personId), full_name: subject.name }] : []}
          initialObservedAtLocal={composeObservation.observedAtLocal}
          onClose={() => setComposeObservation(null)}
          onSent={(data) => {
            setComposeObservation(null);
            if (onNoteCreated) onNoteCreated();
            if (data?.id) navigate(observationThreadLink(data.id, profileReturnTo));
          }}
        />
      )}
    </div>
  );
}

// Re-export shared cell so callers/tests can probe it without reaching
// into the responseTable module directly.
export { SubjectCell };
