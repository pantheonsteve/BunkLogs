/**
 * Full-page, read-only view of one reflection at `/reflections/:id`.
 *
 * Built from the same primitives as the subject profile (Card, Badge,
 * InitialsAvatar, RatingCell) so ratings use the one shared 1-5 palette
 * and the page reads as part of the product. Fields the schema sections
 * don't classify fall through to "Other answers" so nothing is hidden.
 */
import { useEffect, useState } from 'react';
import { Link, useParams, useSearchParams } from 'react-router-dom';

import api from '../api';
import Header from '../partials/Header';
import Sidebar from '../partials/Sidebar';
import PrivacyChip from '../components/reflection/PrivacyChip';
import Badge from '../components/ui/Badge';
import Card, { CardBody, CardHeader } from '../components/ui/Card';
import InitialsAvatar from '../components/ui/InitialsAvatar';
import RatingCell from '../components/ui/RatingCell';
import RichText from '../components/ui/RichText';
import {
  deriveSchemaSections,
  isTruthyFlag,
  pickLabel,
} from '../dashboards/subject/responseTable/schema';
import { groupDashboardLink, profileLink } from '../utils/dashboardLinks';

const NON_ANSWER_TYPES = new Set(['section_header', 'instructions']);
// Wider than `deriveSchemaSections`' description types: this page also has
// room for short answers and `text_list` bullets, in schema order.
const TEXT_TYPES = new Set(['textarea', 'text', 'long_text', 'short_text', 'rich_text', 'text_list']);

function formatDate(iso) {
  if (!iso) return '';
  const d = new Date(`${iso}T00:00:00`);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleDateString(undefined, {
    weekday: 'short', year: 'numeric', month: 'short', day: 'numeric',
  });
}

function formatDateTime(iso) {
  if (!iso) return '';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString(undefined, {
    month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit',
  });
}

function plainAnswer(value) {
  if (value === undefined || value === null || value === '') return '—';
  if (Array.isArray(value)) return value.join(', ') || '—';
  if (typeof value === 'object') {
    return Object.entries(value).map(([k, v]) => `${k}: ${v}`).join(' · ');
  }
  return String(value);
}

function readRating(col, answers) {
  const raw = col.subKey ? (answers?.[col.key] ?? {})[col.subKey] : answers?.[col.key];
  return raw == null || raw === '' ? null : Number(raw);
}

// Same treatment as the subject profile's help badges.
function flagTone(key) {
  return String(key).toLowerCase().includes('camper_care') ? 'danger' : 'warn';
}

function ErrorPanel({ title, body, backHref, backLabel }) {
  return (
    <div className="rounded-xl border border-amber-200 bg-amber-50 dark:bg-amber-950/30 dark:border-amber-900 p-5">
      <h2 className="text-base font-semibold text-amber-900 dark:text-amber-100 mb-1">
        {title}
      </h2>
      <p className="text-sm text-amber-900 dark:text-amber-100">{body}</p>
      <div className="mt-4">
        <Link
          to={backHref}
          className="text-sm font-medium text-amber-900 dark:text-amber-100 underline"
        >
          {backLabel}
        </Link>
      </div>
    </div>
  );
}

function ScoresCard({ ratingCols, answers }) {
  const groups = [];
  for (const col of ratingCols) {
    const label = col.subKey && col.groupLabel !== col.key ? col.groupLabel : '';
    const last = groups[groups.length - 1];
    if (last && last.label === label && col.subKey) last.cols.push(col);
    else groups.push({ label, cols: [col] });
  }
  return (
    <Card as="section" data-testid="reflection-scores">
      <CardHeader title="Scores" />
      <CardBody className="space-y-4">
        {groups.map((g, gi) => (
          <div key={`${g.label}-${gi}`}>
            {g.label && (
              <p className="text-[13px] font-semibold text-muted mb-1">{g.label}</p>
            )}
            <ul className="grid grid-cols-1 sm:grid-cols-2 gap-x-8">
              {g.cols.map((col) => {
                const num = readRating(col, answers);
                return (
                  <li
                    key={`${col.key}-${col.subKey ?? ''}`}
                    data-testid={`reflection-score-${col.key}${col.subKey ? `-${col.subKey}` : ''}`}
                    className="flex items-center justify-between gap-3 py-2.5 border-b border-line-soft last:border-0 sm:[&:nth-last-child(2):nth-child(odd)]:border-0"
                  >
                    <span className="text-sm font-medium text-ink-2">{col.label}</span>
                    <span className="flex items-center gap-2">
                      <RatingCell value={num} scaleMax={col.scaleMax} label={col.label} size="lg" />
                      <span className="text-xs text-muted w-8">of {col.scaleMax}</span>
                    </span>
                  </li>
                );
              })}
            </ul>
          </div>
        ))}
      </CardBody>
    </Card>
  );
}

function ReflectionBody({ reflection }) {
  const schema = reflection.localized_schema;
  const fields = Array.isArray(schema?.fields) ? schema.fields : [];
  const language = reflection.language || 'en';
  const answers = reflection.answers || {};
  const sections = deriveSchemaSections(schema, language);
  const { ratingCols, flagFields, chipFields } = sections;
  const descTextFields = fields
    .filter((f) => TEXT_TYPES.has(f.type))
    .map((f) => ({ key: f.key, type: f.type, label: pickLabel(f.prompts ?? f.labels, language, f.key) }));

  const covered = new Set([
    ...ratingCols.map((c) => c.key),
    ...flagFields.map((f) => f.key),
    ...chipFields.map((f) => f.key),
    ...descTextFields.map((f) => f.key),
  ]);
  const otherFields = fields.filter((f) => !covered.has(f.key) && !NON_ANSWER_TYPES.has(f.type));
  const answeredChips = chipFields.filter((f) => {
    const v = answers[f.key];
    return v != null && v !== '' && !(Array.isArray(v) && v.length === 0);
  });
  const unraisedFlags = flagFields.filter((f) => !isTruthyFlag(answers[f.key]));

  if (fields.length === 0) {
    return (
      <p className="text-sm text-muted italic">
        This reflection&apos;s template has no fields to display.
      </p>
    );
  }

  const firstScored = fields.findIndex((f) => f.type === 'rating_group' || f.type === 'single_rating');
  const firstText = fields.findIndex((f) => TEXT_TYPES.has(f.type));
  const scoresFirst = firstScored !== -1 && (firstText === -1 || firstScored < firstText);
  const scores = ratingCols.length > 0 && <ScoresCard ratingCols={ratingCols} answers={answers} />;

  return (
    <div className="space-y-5">
      {scoresFirst && scores}

      {descTextFields.length > 0 && (
        <Card as="section" data-testid="reflection-text-answers">
          <CardHeader title="Responses" />
          <div className="divide-y divide-line-soft">
            {descTextFields.map((f) => {
              const value = answers[f.key];
              const items = Array.isArray(value) ? value.filter((v) => String(v ?? '').trim()) : null;
              const empty = items ? items.length === 0 : value == null || value === '';
              return (
                <div key={f.key} className="px-[18px] py-4">
                  <h3 className="text-[13px] font-semibold text-ink-2 mb-1.5">{f.label}</h3>
                  {empty ? (
                    <p className="text-sm italic text-muted">No answer</p>
                  ) : items ? (
                    <ul className="space-y-1.5">
                      {items.map((item, i) => (
                        <li key={i} className="flex gap-2.5 text-[15px] leading-relaxed text-ink">
                          <span className="mt-[9px] w-1.5 h-1.5 rounded-full bg-brand shrink-0" aria-hidden="true" />
                          <span>{String(item)}</span>
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <RichText
                      html={String(value)}
                      className="text-[15px] leading-relaxed text-ink whitespace-pre-line prose prose-sm dark:prose-invert max-w-none"
                    />
                  )}
                </div>
              );
            })}
          </div>
        </Card>
      )}

      {!scoresFirst && scores}

      {(answeredChips.length > 0 || unraisedFlags.length > 0) && (
        <Card as="section" data-testid="reflection-choice-answers">
          <CardHeader title="Answers" />
          <CardBody>
            <dl className="grid grid-cols-1 sm:grid-cols-2 gap-x-8 gap-y-4">
              {answeredChips.map((f) => {
                const v = answers[f.key];
                const values = Array.isArray(v) ? v : [v];
                return (
                  <div key={f.key}>
                    <dt className="text-[13px] font-semibold text-ink-2">{f.label}</dt>
                    <dd className="mt-1.5 flex flex-wrap gap-1.5">
                      {values.map((val) => {
                        const match = f.options.find((o) => String(o.value) === String(val));
                        return (
                          <Badge key={String(val)} tone="info" size="md" className="font-semibold">
                            {match ? match.label : String(val)}
                          </Badge>
                        );
                      })}
                    </dd>
                  </div>
                );
              })}
              {unraisedFlags.map((f) => (
                <div key={f.key}>
                  <dt className="text-[13px] font-semibold text-ink-2">{f.label}</dt>
                  <dd className="mt-1.5">
                    <Badge size="md" className="font-semibold">
                      {answers[f.key] == null || answers[f.key] === '' ? '—' : 'No'}
                    </Badge>
                  </dd>
                </div>
              ))}
            </dl>
          </CardBody>
        </Card>
      )}

      {otherFields.length > 0 && (
        <Card as="section" data-testid="reflection-other-answers">
          <CardHeader title="Other answers" />
          <CardBody>
            <dl className="space-y-3">
              {otherFields.map((f) => (
                <div key={f.key}>
                  <dt className="text-[13px] font-semibold text-ink-2">
                    {pickLabel(f.prompts ?? f.labels, language, f.key)}
                  </dt>
                  <dd className="mt-0.5 text-sm text-ink whitespace-pre-wrap">
                    {plainAnswer(answers[f.key])}
                  </dd>
                </div>
              ))}
            </dl>
          </CardBody>
        </Card>
      )}
    </div>
  );
}

function ReflectionHeader({ reflection }) {
  const schema = reflection.localized_schema;
  const language = reflection.language || 'en';
  const answers = reflection.answers || {};
  const { flagFields } = deriveSchemaSections(schema, language);
  const raisedFlags = flagFields.filter((f) => isTruthyFlag(answers[f.key]));

  const templateName = reflection.template_meta?.name;
  const { subject_name: subjectName, author_name: authorName, group_name: groupName } = reflection;
  const { period_start: periodStart, period_end: periodEnd } = reflection;
  const title = subjectName || templateName || 'Reflection';
  const groupId = reflection.assignment_group ?? reflection.subject_group;
  const dateLabel = periodStart
    ? `${formatDate(periodStart)}${periodEnd && periodEnd !== periodStart ? ` – ${formatDate(periodEnd)}` : ''}`
    : null;

  return (
    <Card
      as="header"
      className="rounded-2xl px-6 py-5 flex flex-wrap items-center gap-x-5 gap-y-4"
      data-testid="reflection-header"
    >
      {subjectName && <InitialsAvatar name={subjectName} size="xl" aria-hidden="true" />}
      <div className="flex-1 min-w-[240px] flex flex-col gap-2">
        {subjectName && templateName && (
          <p className="text-[13px] font-semibold text-muted">{templateName}</p>
        )}
        <h1 className="text-[28px] leading-tight font-bold tracking-tight text-ink">
          {subjectName && reflection.subject ? (
            <Link
              to={profileLink(reflection.subject, { groupId, date: periodStart })}
              className="hover:text-brand"
              data-testid="reflection-subject-link"
            >
              {title}
            </Link>
          ) : title}
        </h1>
        <div className="flex flex-wrap gap-1.5">
          {dateLabel && <Badge size="md" className="font-semibold">{dateLabel}</Badge>}
          {groupName && (groupId ? (
            <Link to={groupDashboardLink(groupId, { date: periodStart })} className="hover:opacity-80">
              <Badge tone="info" size="md" className="font-semibold">{groupName}</Badge>
            </Link>
          ) : (
            <Badge tone="info" size="md" className="font-semibold">{groupName}</Badge>
          ))}
          <PrivacyChip teamVisibility={reflection.team_visibility} />
        </div>
      </div>
      <div className="flex flex-col items-start gap-1.5">
        {raisedFlags.length > 0 && (
          <div className="flex flex-wrap gap-1.5" data-testid="reflection-flags">
            {raisedFlags.map((f) => (
              <Badge
                key={f.key}
                tone={flagTone(f.key)}
                size="md"
                className="font-semibold"
                data-testid={`reflection-flag-${f.key}`}
              >
                {f.label}
              </Badge>
            ))}
          </div>
        )}
        {authorName && (
          <span className="text-xs text-muted pl-1">Written by {authorName}</span>
        )}
        <span className="text-xs text-muted pl-1">
          #{reflection.id}
          {reflection.language && ` · ${reflection.language}`}
          {reflection.submitted_at && ` · Submitted ${formatDateTime(reflection.submitted_at)}`}
        </span>
      </div>
    </Card>
  );
}

export default function ReflectionDetailPage() {
  const { id } = useParams();
  const [searchParams] = useSearchParams();
  const returnTo = searchParams.get('returnTo') || '/my-reflections';

  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [reflection, setReflection] = useState(null);
  const [loading, setLoading] = useState(true);
  const [errorState, setErrorState] = useState(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setErrorState(null);
    api
      .get(`/api/v1/reflections/${id}/`)
      .then((r) => {
        if (cancelled) return;
        setReflection(r.data);
      })
      .catch((err) => {
        if (cancelled) return;
        const httpStatus = err.response?.status;
        if (httpStatus === 404) {
          setErrorState({
            title: 'Reflection not found',
            body:
              "We couldn't find that reflection. It may have been deleted, or you may have followed a stale link.",
          });
        } else if (httpStatus === 403) {
          setErrorState({
            title: 'You don\u2019t have access',
            body:
              'You do not have permission to view this reflection. If you think this is wrong, ask an admin.',
          });
        } else {
          setErrorState({
            title: 'Something went wrong',
            body:
              err.response?.data?.detail
              || 'Could not load this reflection. Please try again.',
          });
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [id]);

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} />
      <div className="relative flex flex-col flex-1 overflow-y-auto overflow-x-hidden">
        <Header sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} />
        <main className="grow px-4 sm:px-6 lg:px-8 py-6 w-full max-w-5xl mx-auto">
          <div className="mb-4">
            <Link
              to={returnTo}
              className="text-sm font-semibold text-brand hover:text-brand-hover"
            >
              ← Back
            </Link>
          </div>

          {loading && (
            <p className="text-sm text-muted">Loading reflection…</p>
          )}

          {!loading && errorState && (
            <ErrorPanel
              title={errorState.title}
              body={errorState.body}
              backHref={returnTo}
              backLabel="Back to where I was"
            />
          )}

          {!loading && !errorState && reflection && (
            <div className="space-y-5" data-testid="reflection-detail">
              <ReflectionHeader reflection={reflection} />
              <ReflectionBody reflection={reflection} />
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
