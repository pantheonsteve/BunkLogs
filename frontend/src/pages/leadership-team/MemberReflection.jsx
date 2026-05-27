/**
 * LT Member Reflection — Step 7_12, Story 47.
 *
 * Read-only view of one team member's most recent reflection plus a
 * trend graph over the configured window. LT may mark a reflection as
 * "needs attention" but cannot edit, comment, or peek at edit history
 * (only an "Edited" indicator).
 *
 * Trend display: ASCII-style stacked bars from existing color-grid
 * conventions; per the plan we intentionally do NOT add a new chart
 * dependency in this PR.
 */

import { useCallback, useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import {
  fetchMemberReflection,
  markAttention,
  unmarkAttention,
} from '../../api/leadershipTeam';
import { useAuth } from '../../auth/AuthContext';

function FieldRow({ field }) {
  const prompt = field.prompts?.en ?? field.key;
  const answer = field.answer;
  if (field.type === 'rating_group' || field.type === 'single_rating') {
    const cells = answer && typeof answer === 'object' ? answer : {};
    return (
      <div className="space-y-1">
        <p className="text-sm font-medium text-gray-900 dark:text-white">{prompt}</p>
        <div className="flex flex-wrap gap-2 text-xs text-gray-700 dark:text-gray-300">
          {Object.entries(cells).map(([k, v]) => (
            <span key={k} className="rounded-full bg-gray-100 dark:bg-gray-800 px-2 py-0.5">
              {k}: {String(v)}
            </span>
          ))}
        </div>
      </div>
    );
  }
  if (Array.isArray(answer)) {
    return (
      <div>
        <p className="text-sm font-medium text-gray-900 dark:text-white">{prompt}</p>
        <ul className="list-disc list-inside text-sm text-gray-800 dark:text-gray-200">
          {answer.map((a, i) => <li key={i}>{String(a)}</li>)}
        </ul>
      </div>
    );
  }
  return (
    <div>
      <p className="text-sm font-medium text-gray-900 dark:text-white">{prompt}</p>
      <p className="text-sm text-gray-800 dark:text-gray-200 whitespace-pre-wrap">
        {answer === null || answer === undefined || answer === '' ? '—' : String(answer)}
      </p>
    </div>
  );
}

function TrendSeries({ series }) {
  if (!series?.length) {
    return (
      <p className="text-sm text-gray-500 dark:text-gray-400" data-testid="lt-trend-empty">
        No scored fields to plot.
      </p>
    );
  }
  return (
    <div className="space-y-3" data-testid="lt-trend">
      {series.map((s) => (
        <div key={s.label} data-testid={`lt-trend-series-${s.label}`}>
          <p className="text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
            {s.label}
          </p>
          <div className="flex items-end gap-1 h-12">
            {s.points.map((p, i) => {
              const h = p.value == null ? 0 : (p.value / s.scale_max) * 100;
              return (
                <span
                  key={`${p.period_start}-${i}`}
                  title={`${p.period_start}: ${p.value ?? '—'}`}
                  className={`flex-1 rounded-sm ${p.value == null ? 'bg-gray-200 dark:bg-gray-700' : 'bg-indigo-500 dark:bg-indigo-400'}`}
                  style={{ height: `${Math.max(h, 4)}%` }}
                  data-testid={`lt-trend-bar-${s.label}-${i}`}
                />
              );
            })}
          </div>
        </div>
      ))}
    </div>
  );
}

export default function LeadershipTeamMemberReflection() {
  const { teamRole, membershipId } = useParams();
  const { orgSlug } = useAuth();

  const [payload, setPayload] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [actionPending, setActionPending] = useState(false);
  const [showFlagForm, setShowFlagForm] = useState(false);
  const [flagNote, setFlagNote] = useState('');

  const load = useCallback(async () => {
    try {
      const data = await fetchMemberReflection(orgSlug, teamRole, membershipId);
      setPayload(data);
      setError(null);
    } catch (err) {
      const status = err?.response?.status;
      if (status === 403) setError('You cannot view this reflection.');
      else if (status === 404) setError('Member or team not found.');
      else setError('Failed to load member reflection.');
    } finally {
      setLoading(false);
    }
  }, [orgSlug, teamRole, membershipId]);

  useEffect(() => { load(); }, [load]);

  const handleMark = async () => {
    const reflectionId = payload?.metadata?.reflection_id;
    if (!reflectionId) return;
    setActionPending(true);
    try {
      await markAttention(orgSlug, reflectionId, { note: flagNote });
      setShowFlagForm(false);
      setFlagNote('');
      await load();
    } catch {
      setError('Failed to mark for attention.');
    } finally {
      setActionPending(false);
    }
  };

  const handleUnmark = async () => {
    const reflectionId = payload?.metadata?.reflection_id;
    if (!reflectionId) return;
    setActionPending(true);
    try {
      await unmarkAttention(orgSlug, reflectionId);
      await load();
    } catch {
      setError('Failed to remove your flag.');
    } finally {
      setActionPending(false);
    }
  };

  if (loading) {
    return (
      <div className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-[96rem] mx-auto" data-testid="lt-member-loading">
        <p className="text-gray-500 dark:text-gray-400">Loading…</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6" data-testid="lt-member-error">
        <p className="text-red-600 dark:text-red-400">{error}</p>
        <Link
          to={`/leadership-team/teams/${teamRole}`}
          className="mt-3 inline-block text-sm text-indigo-600 dark:text-indigo-400 underline"
        >
          Back to team
        </Link>
      </div>
    );
  }

  const { header, metadata, content, trend, attention_markers } = payload;

  return (
    <div className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-[96rem] mx-auto space-y-4">
      <div>
        <Link
          to={`/leadership-team/teams/${teamRole}`}
          className="text-sm text-indigo-600 dark:text-indigo-400 hover:underline"
        >
          ← Back to team
        </Link>
        <h1 className="text-xl font-bold text-gray-900 dark:text-white mt-2">
          {header.person.name}
        </h1>
        <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
          {header.role} ·{' '}
          {header.period ? (
            <>Period {header.period.start} → {header.period.end} ({header.period.cadence})</>
          ) : (
            'No template configured'
          )}
        </p>
      </div>
        {!metadata ? (
          <section
            className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-4"
            data-testid="lt-member-empty"
          >
            <p className="text-sm text-gray-500 dark:text-gray-400">
              No reflection has been submitted for this period.
            </p>
          </section>
        ) : (
          <>
            <section
              className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-4"
              data-testid="lt-member-metadata"
            >
              <div className="flex items-start justify-between gap-3">
                <div className="text-xs text-gray-500 dark:text-gray-400 space-y-0.5">
                  <p>Submitted {metadata.submitted_at}</p>
                  {metadata.last_edited_at && <p>Edited {metadata.last_edited_at}</p>}
                  <p>Language: {metadata.language_of_authorship}</p>
                </div>
                <div className="shrink-0">
                  {attention_markers?.length > 0 ? (
                    <button
                      type="button"
                      onClick={handleUnmark}
                      disabled={actionPending}
                      className="text-xs rounded-md border border-amber-300 dark:border-amber-700 bg-amber-50 dark:bg-amber-900/30 text-amber-800 dark:text-amber-200 px-2 py-1 hover:bg-amber-100"
                      data-testid="lt-mark-attention-toggle"
                    >
                      Clear my flag
                    </button>
                  ) : (
                    <button
                      type="button"
                      onClick={() => setShowFlagForm(true)}
                      disabled={actionPending}
                      className="text-xs rounded-md border border-amber-300 dark:border-amber-700 bg-white dark:bg-gray-900 text-amber-800 dark:text-amber-200 px-2 py-1 hover:bg-amber-50"
                      data-testid="lt-mark-attention-toggle"
                    >
                      Mark for attention
                    </button>
                  )}
                </div>
              </div>
              {showFlagForm && (
                <div
                  className="mt-3 rounded-md border border-amber-200 dark:border-amber-700 bg-amber-50 dark:bg-amber-900/20 p-3"
                  data-testid="lt-mark-attention-form"
                >
                  <textarea
                    value={flagNote}
                    onChange={(e) => setFlagNote(e.target.value)}
                    placeholder="Optional context for co-supervisors"
                    className="w-full text-sm rounded-md border-gray-300 dark:border-gray-600 dark:bg-gray-800"
                    rows={2}
                    data-testid="lt-mark-attention-note"
                  />
                  <div className="flex gap-2 mt-2 justify-end">
                    <button
                      type="button"
                      onClick={() => { setShowFlagForm(false); setFlagNote(''); }}
                      className="text-xs px-2 py-1 rounded-md border border-gray-300 dark:border-gray-600"
                    >
                      Cancel
                    </button>
                    <button
                      type="button"
                      onClick={handleMark}
                      disabled={actionPending}
                      className="text-xs px-2 py-1 rounded-md bg-amber-600 hover:bg-amber-700 text-white"
                      data-testid="lt-mark-attention-submit"
                    >
                      Mark
                    </button>
                  </div>
                </div>
              )}
              {attention_markers?.length > 0 && (
                <ul className="mt-3 space-y-1 text-xs text-gray-700 dark:text-gray-300">
                  {attention_markers.map((m) => (
                    <li key={m.id} data-testid={`lt-marker-${m.id}`}>
                      <span className="font-medium">{m.person_name}</span> flagged on {m.created_at}
                      {m.note && <span className="block text-gray-500 dark:text-gray-400">{m.note}</span>}
                    </li>
                  ))}
                </ul>
              )}
            </section>

            {content?.translation && (
              <section className="rounded-xl border border-blue-200 dark:border-blue-700 bg-blue-50 dark:bg-blue-900/20 p-3 text-xs text-blue-800 dark:text-blue-200">
                {content.translation.status === 'pending'
                  ? `Translation from ${content.translation.source_language} → en is pending.`
                  : (
                    <>
                      <p className="font-medium mb-1">
                        Translation ({content.translation.source_language} → en)
                      </p>
                      <p className="whitespace-pre-wrap">{content.translation.translated_text}</p>
                    </>
                  )}
              </section>
            )}

            <section
              className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-4 space-y-4"
              data-testid="lt-member-content"
            >
              {content?.fields?.map((f) => <FieldRow key={f.key} field={f} />)}
            </section>
          </>
        )}

        <section
          className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-4"
          data-testid="lt-member-trend"
        >
          <h2 className="text-base font-semibold text-gray-900 dark:text-white mb-2">
            Trend
          </h2>
          {trend?.period && (
            <p className="text-xs text-gray-500 dark:text-gray-400 mb-2">
              {trend.period.start} → {trend.period.end} ({trend.period.cadence})
            </p>
          )}
          <TrendSeries series={trend?.series ?? []} />
        </section>
    </div>
  );
}
