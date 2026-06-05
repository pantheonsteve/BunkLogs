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
import { AlertTriangle, MessageSquarePlus } from 'lucide-react';
import {
  groupDashboardLink,
  observationThreadLink,
  profileBackLabel,
  resolveProfileBackGroup,
} from '../../utils/dashboardLinks';
import ObservationComposer, { dateOnlyToLocalDatetime } from '../../components/observations/ObservationComposer';
import PrivacyChip from '../../components/reflection/PrivacyChip';
import {
  formatShortDate,
  getInitials,
  isTruthyFlag,
  pickLabel,
} from './responseTable/schema';
import { FlagChip } from './responseTable/cells';
import { SubjectCell } from './responseTable/cells';
import FormResponsesCard from './responseTable/FormResponsesCard';

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

// ---------------------------------------------------------------------------
// Header
// ---------------------------------------------------------------------------

function ProfileBackLink({ groupIdParam, backDate, profile }) {
  const group = resolveProfileBackGroup(
    groupIdParam,
    profile?.assignment_groups,
  );
  const to = group ? groupDashboardLink(group.id, { date: backDate }) : null;
  const label = profileBackLabel(group);
  if (!to || !label) return null;
  return (
    <Link
      to={to}
      className="text-sm font-semibold text-blue-700 dark:text-blue-300 hover:underline mb-4 inline-block"
      data-testid="profile-back-to-group"
    >
      {label}
    </Link>
  );
}

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

function isUnitHeadHelpField(field) {
  if (!field) return false;
  if (field.key === 'request_unit_head_help') return true;
  return field.dashboard_role === 'help_request_unit_head';
}

function isCamperCareHelpField(field) {
  if (!field) return false;
  if (field.key === 'request_camper_care_help') return true;
  return field.dashboard_role === 'help_request_camper_care';
}

function collectHelpRequests(templates) {
  const unitHead = [];
  const camperCare = [];
  for (const block of templates ?? []) {
    for (const r of block.reflections ?? []) {
      const answers = r.answers ?? {};
      for (const field of block.schema_fields ?? []) {
        const key = field?.key;
        if (!key || !isTruthyFlag(answers[key])) continue;
        const entry = { date: r.date, reflectionId: r.id, group: r.assignment_group };
        if (isUnitHeadHelpField(field)) unitHead.push(entry);
        else if (isCamperCareHelpField(field)) camperCare.push(entry);
      }
    }
  }
  return { unitHead, camperCare };
}

function HelpRequestBadges({ templates, language = 'en' }) {
  const { unitHead, camperCare } = useMemo(
    () => collectHelpRequests(templates),
    [templates],
  );
  if (unitHead.length === 0 && camperCare.length === 0) return null;

  const uhLabel = pickLabel(
    { en: 'Unit Head Help Requested' },
    language,
    'Unit Head Help Requested',
  );
  const ccLabel = pickLabel(
    { en: 'Camper Care Help Requested' },
    language,
    'Camper Care Help Requested',
  );

  return (
    <div
      className="mb-6 flex flex-wrap items-center gap-2"
      data-testid="subject-help-badges"
    >
      {unitHead.length > 0 && (
        <FlagChip
          field={{
            key: 'request_unit_head_help',
            label: `${uhLabel} · ${unitHead.length} day${unitHead.length === 1 ? '' : 's'}`,
          }}
          testidPrefix="subject-help"
        />
      )}
      {camperCare.length > 0 && (
        <FlagChip
          field={{
            key: 'request_camper_care_help',
            label: `${ccLabel} · ${camperCare.length} day${camperCare.length === 1 ? '' : 's'}`,
          }}
          testidPrefix="subject-help"
        />
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Period stepper
// ---------------------------------------------------------------------------

const PRESET_DAYS = [7, 30, 90];

function PeriodStepper({ period, rangeStart, rangeEnd, onRangeChange, refreshing }) {
  if (!period) return null;

  const inputStart = rangeStart || period.start;
  const inputEnd = rangeEnd || period.end;

  const setPreset = (days) => {
    if (!onRangeChange) return;
    const end = new Date();
    const start = new Date();
    start.setDate(end.getDate() - (days - 1));
    const fmt = (d) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
    onRangeChange(fmt(start), fmt(end));
  };

  const applyRange = (nextStart, nextEnd) => {
    if (!onRangeChange || !nextStart || !nextEnd) return;
    if (nextStart > nextEnd) {
      onRangeChange(nextEnd, nextStart);
    } else {
      onRangeChange(nextStart, nextEnd);
    }
  };

  return (
    <section
      className="bg-white dark:bg-gray-800 shadow-sm rounded-xl p-4 border border-gray-200 dark:border-gray-700 mb-6 flex flex-wrap items-center gap-3"
      data-testid="subject-period-stepper"
    >
      <div>
        <p className="text-xs uppercase tracking-wide text-gray-500 dark:text-gray-400">Period</p>
        <p className="text-sm font-medium text-gray-800 dark:text-gray-100">
          {formatShortDate(inputStart)} — {formatShortDate(inputEnd)}
          {refreshing && (
            <span className="ml-2 text-xs font-normal text-gray-400 dark:text-gray-500">Updating…</span>
          )}
        </p>
      </div>
      <div className="flex flex-wrap items-center gap-2 ml-auto">
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
        <label className="flex items-center gap-1.5 text-xs text-gray-700 dark:text-gray-300">
          <span className="sr-only">Start date</span>
          <span aria-hidden="true">From</span>
          <input
            type="date"
            value={inputStart}
            onChange={(e) => applyRange(e.target.value, inputEnd)}
            className="rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-2 py-1.5 text-xs"
            data-testid="subject-period-start"
          />
        </label>
        <label className="flex items-center gap-1.5 text-xs text-gray-700 dark:text-gray-300">
          <span className="sr-only">End date</span>
          <span aria-hidden="true">To</span>
          <input
            type="date"
            value={inputEnd}
            onChange={(e) => applyRange(inputStart, e.target.value)}
            className="rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-2 py-1.5 text-xs"
            data-testid="subject-period-end"
          />
        </label>
      </div>
    </section>
  );
}

// ---------------------------------------------------------------------------
// Concerns
// ---------------------------------------------------------------------------

/** Map reflection id → assignment group (+ row date) from template blocks. */
function buildReflectionGroupById(templates) {
  const map = new Map();
  for (const t of templates ?? []) {
    for (const r of t.reflections ?? []) {
      if (r.assignment_group?.id) {
        map.set(r.id, r.assignment_group);
      }
    }
  }
  return map;
}

function ConcernsAlert({ concerns, reflectionGroupById }) {
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
                const ag = c.reflection_id ? reflectionGroupById?.get(c.reflection_id) : null;
                return (
                  <li key={key} className="flex flex-wrap items-center gap-2">
                    <span>
                      <strong>{c.field_label}</strong>: rating of {c.value} on {formatShortDate(c.date)}.
                    </span>
                    <PrivacyChip teamVisibility={c.team_visibility} />
                    {ag?.id && (
                      <Link
                        to={`/dashboards/group/${ag.id}?date=${c.date}`}
                        className="underline"
                      >
                        View {ag.name ?? 'group'}
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

function ObservationsPanel({ observations = [], onCompose, profileReturnTo = null }) {
  const [open, setOpen] = useState(true);

  const sorted = useMemo(
    () => [...observations].sort((a, b) => {
      const ta = (a.observed_at || a.created_at)
        ? new Date(a.observed_at || a.created_at).getTime()
        : 0;
      const tb = (b.observed_at || b.created_at)
        ? new Date(b.observed_at || b.created_at).getTime()
        : 0;
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
          {onCompose && (
            <button
              type="button"
              onClick={() => onCompose()}
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
                    to={observationThreadLink(o.id, profileReturnTo)}
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

    </section>
  );
}

export default function SubjectDetail({
  payload,
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
  const reflectionGroupById = useMemo(
    () => buildReflectionGroupById(templates),
    [templates],
  );
  const navigate = useNavigate();
  const [composeObservation, setComposeObservation] = useState(null);

  const openCompose = (date) => {
    setComposeObservation({
      observedAtLocal: date ? dateOnlyToLocalDatetime(date) : null,
    });
  };

  return (
    <div>
      <ProfileBackLink
        groupIdParam={backGroupId}
        backDate={backDate}
        profile={profile}
      />
      <ProfileHeader subject={subject} profile={profile} />
      <HelpRequestBadges templates={templates} language={language} />
      <PeriodStepper
        period={period}
        rangeStart={rangeStart}
        rangeEnd={rangeEnd}
        onRangeChange={onRangeChange}
        refreshing={refreshing}
      />
      <ConcernsAlert concerns={concerns} reflectionGroupById={reflectionGroupById} />

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
            personId={personId}
            onAddObservation={personId ? openCompose : null}
          />
        ))
      )}

      {/*<RecentTexts texts={recentTexts} />*/}
      <ObservationsPanel
        observations={observations ?? []}
        onCompose={personId ? () => openCompose() : null}
        profileReturnTo={profileReturnTo}
      />
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
      {/* TODO(7_23): legacy SubjectNote panel removed in 7_24 */}
    </div>
  );
}

// Re-export shared cell so callers/tests can probe it without reaching
// into the responseTable module directly.
export { SubjectCell };
