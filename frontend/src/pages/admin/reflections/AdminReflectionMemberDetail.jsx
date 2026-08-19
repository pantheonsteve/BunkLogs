/**
 * Admin Reflection member detail — Step 4_4 (TBE).
 *
 * One Madrich's full reflection history (all weekly periods), reusing
 * the org-admin-gated `admin_flow/reflections.py` endpoint so it works
 * without a Supervision relationship. Answers are rendered generically
 * (no template-schema lookup) since this surface is role-parameterized —
 * `AnswerSection` special-cases a few common shapes (ratings, wins,
 * improvements, open questions) by key-name heuristics so the common
 * madrich 3-2-1 template reads like a report card, and falls back to a
 * plain key/value renderer for anything it doesn't recognize.
 *
 * Histories run long once a member has months of weekly periods, so a sticky
 * period index jumps between the entry cards already on the page, and each
 * card deep-links to the canonical `/reflections/:id` view.
 */
import { useCallback, useEffect, useState } from 'react';
import { Link, useLocation, useParams } from 'react-router-dom';
import {
  ArrowUpRight,
  CalendarDays,
  CheckCircle2,
  ClipboardList,
  MessageCircleQuestion,
  Sparkles,
  TrendingUp,
} from 'lucide-react';
import { fetchAdminReflectionMember } from '../../../api/adminReflections';
import { ratingColor, ratingTextColor } from '../../../dashboards/colors';
import { homePathForUser } from '../../../utils/auth/capability';
import { useAuth } from '../../../auth/AuthContext';
import BackLink from '../../../components/ui/BackLink';
import ErrorPanel from '../../../components/ui/ErrorPanel';
import LoadingState from '../../../components/ui/LoadingState';
import RichText from '../../../components/ui/RichText';

const STATUS_META = {
  submitted: {
    label: 'Submitted',
    className: 'bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-200',
    dotClassName: 'bg-green-500',
  },
  day_off: {
    label: 'Day off',
    className: 'bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-200',
    dotClassName: 'bg-blue-500',
  },
  not_submitted: {
    label: 'Not submitted',
    className: 'bg-gray-200 text-gray-800 dark:bg-gray-700 dark:text-gray-100',
    dotClassName: 'bg-gray-400',
  },
};

function StatusPill({ status }) {
  const meta = STATUS_META[status] ?? STATUS_META.not_submitted;
  return (
    <span className={`text-xs font-medium px-2 py-0.5 rounded-full whitespace-nowrap ${meta.className}`}>
      {meta.label}
    </span>
  );
}

function humanizeKey(key) {
  return key.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}

function getInitials(name) {
  if (!name) return '?';
  const parts = String(name).trim().split(/\s+/);
  const first = parts[0]?.[0] ?? '';
  const last = parts.length > 1 ? parts[parts.length - 1][0] : '';
  return (first + last).toUpperCase() || '?';
}

function formatDateRange(start, end) {
  const fmt = (iso) => {
    if (!iso) return '';
    const [y, m, d] = String(iso).split('-').map(Number);
    if (!y || !m || !d) return iso;
    return new Date(Date.UTC(y, m - 1, d)).toLocaleDateString('en-US', {
      month: 'short', day: 'numeric', year: 'numeric', timeZone: 'UTC',
    });
  };
  return `${fmt(start)} – ${fmt(end)}`;
}

/** Compact "Aug 3–9" / "Aug 31–Sep 6" label for the period index chips. */
function formatShortRange(start, end) {
  const parse = (iso) => {
    const [y, m, d] = String(iso ?? '').split('-').map(Number);
    return y && m && d ? new Date(Date.UTC(y, m - 1, d)) : null;
  };
  const from = parse(start);
  const to = parse(end);
  if (!from) return formatDateRange(start, end);
  const opts = { month: 'short', day: 'numeric', timeZone: 'UTC' };
  const fromLabel = from.toLocaleDateString('en-US', opts);
  if (!to) return fromLabel;
  const toLabel = to.getUTCMonth() === from.getUTCMonth()
    ? String(to.getUTCDate())
    : to.toLocaleDateString('en-US', opts);
  return `${fromLabel}–${toLabel}`;
}

function formatDateTime(iso) {
  if (!iso) return '';
  const d = new Date(iso);
  return Number.isNaN(d.getTime())
    ? iso
    : d.toLocaleString('en-US', { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' });
}

/** Mean of a rating object's numeric values, or null when there are none. */
function averageRating(ratings) {
  if (!ratings || typeof ratings !== 'object') return null;
  const values = Object.values(ratings).filter((v) => typeof v === 'number');
  if (values.length === 0) return null;
  return values.reduce((a, b) => a + b, 0) / values.length;
}

function RatingGrid({ ratings }) {
  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
      {Object.entries(ratings).map(([key, value]) => {
        const numeric = typeof value === 'number' ? value : null;
        const bg = numeric != null ? ratingColor(numeric, 5) : '#e5e7eb';
        const fg = numeric != null ? ratingTextColor(numeric, 5) : '#374151';
        return (
          <div
            key={key}
            className="flex items-center justify-between gap-2 rounded-lg px-3 py-2"
            style={{ backgroundColor: bg }}
          >
            <span className="text-xs font-medium" style={{ color: fg }}>
              {humanizeKey(key)}
            </span>
            <span className="text-sm font-bold" style={{ color: fg }}>
              {numeric ?? '—'}
            </span>
          </div>
        );
      })}
    </div>
  );
}

function BulletSection({ icon: Icon, iconClass, items }) {
  return (
    <ul className="space-y-1.5">
      {items.map((item, i) => (
        <li key={i} className="flex items-start gap-2 text-sm text-gray-800 dark:text-gray-200">
          <Icon className={`w-4 h-4 mt-0.5 shrink-0 ${iconClass}`} aria-hidden="true" />
          <span>{String(item)}</span>
        </li>
      ))}
    </ul>
  );
}

function Callout({ icon: Icon, children }) {
  return (
    <div className="flex items-start gap-2 rounded-lg bg-indigo-50 dark:bg-indigo-900/20 border border-indigo-100 dark:border-indigo-800/50 px-3 py-2.5">
      <Icon className="w-4 h-4 mt-0.5 shrink-0 text-indigo-500 dark:text-indigo-300" aria-hidden="true" />
      <RichText html={children} as="div" className="text-sm text-indigo-900 dark:text-indigo-100" />
    </div>
  );
}

function GenericAnswerValue({ value }) {
  if (Array.isArray(value)) {
    return (
      <ul className="list-disc list-inside text-sm text-gray-800 dark:text-gray-200">
        {value.map((item, i) => <li key={i}>{String(item)}</li>)}
      </ul>
    );
  }
  if (value !== null && typeof value === 'object') {
    return (
      <div className="flex flex-wrap gap-2 text-xs text-gray-700 dark:text-gray-300">
        {Object.entries(value).map(([k, v]) => (
          <span key={k} className="rounded-full bg-gray-100 dark:bg-gray-800 px-2 py-0.5">
            {humanizeKey(k)}: {String(v)}
          </span>
        ))}
      </div>
    );
  }
  if (value === null || value === undefined || value === '') {
    return <p className="text-sm text-gray-800 dark:text-gray-200">—</p>;
  }
  return (
    <RichText html={String(value)} as="div" className="text-sm text-gray-800 dark:text-gray-200" />
  );
}

function AnswerSection({ fieldKey, value }) {
  if (fieldKey === 'ratings' && value && typeof value === 'object' && !Array.isArray(value)) {
    return <RatingGrid ratings={value} />;
  }
  if (Array.isArray(value) && value.length > 0) {
    if (/win/i.test(fieldKey)) {
      return <BulletSection icon={CheckCircle2} iconClass="text-green-500" items={value} />;
    }
    if (/improve|growth/i.test(fieldKey)) {
      return <BulletSection icon={TrendingUp} iconClass="text-amber-500" items={value} />;
    }
  }
  if (typeof value === 'string' && value.trim() && /concern|question|help/i.test(fieldKey)) {
    return <Callout icon={MessageCircleQuestion}>{value}</Callout>;
  }
  return <GenericAnswerValue value={value} />;
}

/**
 * Sticky index of every period on the page. Anchors stay real hrefs so
 * keyboard and open-in-new-tab work; the click handler adds smooth scrolling.
 */
function EntryIndex({ history, activeId, onJump }) {
  return (
    <nav
      aria-label="Reflection entries"
      data-testid="admin-reflection-member-index"
      className="sticky top-16 z-20 -mx-4 sm:-mx-6 lg:-mx-8 px-4 sm:px-6 lg:px-8 py-2 bg-gray-50/95 dark:bg-gray-950/95 backdrop-blur border-y border-gray-200 dark:border-gray-800"
    >
      <div className="flex items-center gap-2 overflow-x-auto">
        <span className="text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400 shrink-0">
          Jump to
        </span>
        {history.map((entry) => {
          const meta = STATUS_META[entry.status] ?? STATUS_META.not_submitted;
          const isActive = activeId === entry.reflection_id;
          return (
            <a
              key={entry.reflection_id}
              href={`#entry-${entry.reflection_id}`}
              onClick={(event) => onJump(event, entry.reflection_id)}
              aria-current={isActive ? 'true' : undefined}
              data-testid={`admin-reflection-member-index-${entry.reflection_id}`}
              className={`shrink-0 inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-medium transition-colors ${
                isActive
                  ? 'border-indigo-400 bg-indigo-50 text-indigo-800 dark:border-indigo-500 dark:bg-indigo-900/40 dark:text-indigo-100'
                  : 'border-gray-200 bg-white text-gray-700 hover:border-indigo-300 hover:text-indigo-700 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-200 dark:hover:border-indigo-500 dark:hover:text-indigo-200'
              }`}
            >
              <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${meta.dotClassName}`} aria-hidden="true" />
              {formatShortRange(entry.period_start, entry.period_end)}
            </a>
          );
        })}
      </div>
    </nav>
  );
}

export default function AdminReflectionMemberDetail() {
  const { role, membershipId } = useParams();
  const { user } = useAuth();
  const location = useLocation();
  const [payload, setPayload] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeId, setActiveId] = useState(null);

  // Today this page is admin-gated, so this resolves to Admin Home; going
  // through the shared role map keeps it right if the route ever opens up.
  const backTo = homePathForUser(user);
  const backLabel = backTo === '/admin/home' ? 'Back to Admin Home' : 'Back to home';

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await fetchAdminReflectionMember(role, membershipId);
      setPayload(data);
      setError(null);
    } catch (err) {
      const status = err?.response?.status;
      if (status === 403) setError('Admin access required.');
      else if (status === 404) setError('Member not found.');
      else setError('Failed to load this member.');
    } finally {
      setLoading(false);
    }
  }, [role, membershipId]);

  useEffect(() => { load(); }, [load]);

  const handleJump = useCallback((event, reflectionId) => {
    event.preventDefault();
    setActiveId(reflectionId);
    const target = document.getElementById(`entry-${reflectionId}`);
    if (!target) return;
    target.scrollIntoView?.({ behavior: 'smooth', block: 'start' });
    target.focus?.({ preventScroll: true });
  }, []);

  if (loading) {
    return (
      <div className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-[96rem] mx-auto" data-testid="admin-reflection-member-loading">
        <LoadingState>Loading…</LoadingState>
      </div>
    );
  }

  if (error || !payload) {
    return (
      <div className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-[96rem] mx-auto space-y-3" data-testid="admin-reflection-member-error">
        <ErrorPanel>{error || 'Failed to load this member.'}</ErrorPanel>
        <BackLink to={backTo} label={backLabel} />
      </div>
    );
  }

  const { person_name: personName, grade_level: gradeLevel, role_label: roleLabel, history } = payload;
  const latestWithRatings = history.find((h) => h.answers?.ratings && typeof h.answers.ratings === 'object');
  const overallAvg = averageRating(latestWithRatings?.answers?.ratings);
  const submittedCount = history.filter((h) => h.status === 'submitted').length;

  return (
    <div className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-[96rem] mx-auto space-y-6">
      <BackLink to={backTo} label={backLabel} />

      <header className="bg-white dark:bg-gray-800 shadow-sm rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
        <div className="flex items-center gap-4 p-5">
          <div className="w-14 h-14 shrink-0 rounded-full bg-gradient-to-br from-indigo-200 to-indigo-400 dark:from-indigo-700 dark:to-indigo-900 flex items-center justify-center text-lg font-semibold text-white">
            {getInitials(personName)}
          </div>
          <div className="min-w-0">
            <h1 className="text-2xl font-semibold text-gray-900 dark:text-white truncate">{personName}</h1>
            <div className="flex flex-wrap gap-2 mt-2">
              {roleLabel && (
                <span className="inline-flex items-center px-2.5 py-0.5 text-xs font-medium rounded-full border bg-indigo-100 text-indigo-800 border-indigo-200 dark:bg-indigo-900/30 dark:text-indigo-200 dark:border-indigo-800">
                  {roleLabel}
                </span>
              )}
              {gradeLevel != null && (
                <span className="inline-flex items-center px-2.5 py-0.5 text-xs font-medium rounded-full border bg-sky-100 text-sky-800 border-sky-200 dark:bg-sky-900/30 dark:text-sky-200 dark:border-sky-800">
                  Grade {gradeLevel}
                </span>
              )}
            </div>
          </div>
        </div>

        <div
          className="grid border-t border-gray-200 dark:border-gray-700 divide-x divide-gray-200 dark:divide-gray-700"
          style={{ gridTemplateColumns: `repeat(${overallAvg != null ? 3 : 2}, minmax(0, 1fr))` }}
        >
          <div className="text-center py-3">
            <p className="text-2xl font-bold text-gray-900 dark:text-white">{history.length}</p>
            <p className="text-xs text-gray-500 dark:text-gray-400">Total entries</p>
          </div>
          <div className="text-center py-3">
            <p className="text-2xl font-bold text-gray-900 dark:text-white">{submittedCount}</p>
            <p className="text-xs text-gray-500 dark:text-gray-400">Submitted</p>
          </div>
          {overallAvg != null && (
            <div className="text-center py-3">
              <p className="text-2xl font-bold" style={{ color: ratingColor(overallAvg, 5) }}>
                {overallAvg.toFixed(1)}
              </p>
              <p className="text-xs text-gray-500 dark:text-gray-400">Latest avg rating</p>
            </div>
          )}
        </div>
      </header>

      {history.length > 1 && (
        <EntryIndex history={history} activeId={activeId} onJump={handleJump} />
      )}

      <section aria-label="Reflection history" data-testid="admin-reflection-member-history">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-3">History</h2>
        {history.length === 0 ? (
          <div className="rounded-xl border border-dashed border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 p-8 text-center">
            <ClipboardList className="w-8 h-8 mx-auto text-gray-300 dark:text-gray-600 mb-2" aria-hidden="true" />
            <p className="text-sm text-gray-500 dark:text-gray-400">No reflections submitted yet.</p>
          </div>
        ) : (
          <ul className="space-y-4">
            {history.map((entry) => {
              const visibleAnswers = Object.entries(entry.answers || {}).filter(([key]) => key !== 'day_off');
              return (
                <li
                  key={entry.reflection_id}
                  id={`entry-${entry.reflection_id}`}
                  tabIndex={-1}
                  className={`scroll-mt-36 rounded-xl border bg-white dark:bg-gray-800 shadow-sm overflow-hidden focus:outline-none ${
                    activeId === entry.reflection_id
                      ? 'border-indigo-400 dark:border-indigo-500 ring-1 ring-indigo-300 dark:ring-indigo-700'
                      : 'border-gray-200 dark:border-gray-700'
                  }`}
                  data-testid={`admin-reflection-member-entry-${entry.reflection_id}`}
                >
                  <div className="flex items-center justify-between gap-3 px-4 py-3 bg-gray-50 dark:bg-gray-900/40 border-b border-gray-200 dark:border-gray-700">
                    <div className="flex items-center gap-2 min-w-0">
                      <CalendarDays className="w-4 h-4 shrink-0 text-gray-400 dark:text-gray-500" aria-hidden="true" />
                      <p className="text-sm font-semibold text-gray-900 dark:text-white truncate">
                        {formatDateRange(entry.period_start, entry.period_end)}
                      </p>
                    </div>
                    <div className="flex items-center gap-2 shrink-0">
                      {entry.submitted_at && (
                        <span className="text-xs text-gray-500 dark:text-gray-400 hidden sm:inline">
                          {formatDateTime(entry.submitted_at)}
                        </span>
                      )}
                      <StatusPill status={entry.status} />
                      <Link
                        to={`/reflections/${entry.reflection_id}?returnTo=${encodeURIComponent(`${location.pathname}${location.search}`)}`}
                        className="inline-flex items-center gap-1 text-xs font-medium text-indigo-700 dark:text-indigo-300 hover:underline"
                        aria-label={`Open entry for ${formatDateRange(entry.period_start, entry.period_end)}`}
                        data-testid={`admin-reflection-member-open-${entry.reflection_id}`}
                      >
                        <span className="hidden sm:inline">Open entry</span>
                        <ArrowUpRight className="w-3.5 h-3.5" aria-hidden="true" />
                      </Link>
                    </div>
                  </div>
                  {visibleAnswers.length > 0 && (
                    <div className="p-4 space-y-4">
                      {visibleAnswers.map(([key, value]) => (
                        <div key={key}>
                          <p className="text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400 mb-1.5 flex items-center gap-1.5">
                            {key === 'ratings' && <Sparkles className="w-3.5 h-3.5" aria-hidden="true" />}
                            {humanizeKey(key)}
                          </p>
                          <AnswerSection fieldKey={key} value={value} />
                        </div>
                      ))}
                    </div>
                  )}
                </li>
              );
            })}
          </ul>
        )}
      </section>
    </div>
  );
}
