/**
 * LT Template Responses — Step 7_12, Story 53.
 *
 * Two tabs:
 *   • Individual — paginated rows (period, author, language, answers)
 *     with filters: date range, respondent, language, rating_le,
 *     has_free_text.
 *   • Aggregate — counts, language distribution, avg-per-dimension
 *     with version-validity markers (Story 48 c1).
 *
 * CSV download buttons hit the LT export endpoints (Story 53 c7) which
 * the browser fetches with cookie auth like other Django downloads.
 */

import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link, useParams, useSearchParams } from 'react-router-dom';
import {
  exportResponsesUrl,
  fetchResponses,
  getTemplate,
} from '../../api/leadershipTeam';
import { useAuth } from '../../auth/AuthContext';

function fmtDate(d) { return d || '—'; }

function IndividualTab({ payload, params, setParams }) {
  const rows = payload?.results ?? [];
  const page = payload?.page ?? 1;
  const pageSize = payload?.page_size ?? 25;
  const total = payload?.total ?? 0;
  const totalPages = Math.max(1, Math.ceil(total / pageSize));

  const setParam = (k, v) => {
    const next = new URLSearchParams(params);
    if (v) next.set(k, v); else next.delete(k);
    if (k !== 'page') next.delete('page');
    setParams(next, { replace: true });
  };

  return (
    <>
      <section
        className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-3 flex flex-wrap gap-2 items-end"
        aria-label="Filters"
        data-testid="lt-responses-filters"
      >
        <label className="text-xs text-gray-700 dark:text-gray-300">
          From
          <input
            type="date"
            value={params.get('date_from') || ''}
            onChange={(e) => setParam('date_from', e.target.value)}
            className="block mt-1 rounded-md border-gray-300 dark:border-gray-600 dark:bg-gray-700 text-sm"
            data-testid="lt-responses-date-from"
          />
        </label>
        <label className="text-xs text-gray-700 dark:text-gray-300">
          To
          <input
            type="date"
            value={params.get('date_to') || ''}
            onChange={(e) => setParam('date_to', e.target.value)}
            className="block mt-1 rounded-md border-gray-300 dark:border-gray-600 dark:bg-gray-700 text-sm"
          />
        </label>
        <label className="text-xs text-gray-700 dark:text-gray-300">
          Language
          <select
            value={params.get('language') || ''}
            onChange={(e) => setParam('language', e.target.value)}
            className="block mt-1 rounded-md border-gray-300 dark:border-gray-600 dark:bg-gray-700 text-sm"
            data-testid="lt-responses-lang"
          >
            <option value="">all</option>
            <option value="en">en</option>
            <option value="es">es</option>
            <option value="he">he</option>
          </select>
        </label>
        <label className="text-xs text-gray-700 dark:text-gray-300">
          Rating ≤
          <input
            type="number"
            value={params.get('rating_le') || ''}
            onChange={(e) => setParam('rating_le', e.target.value)}
            className="block mt-1 w-20 rounded-md border-gray-300 dark:border-gray-600 dark:bg-gray-700 text-sm"
            data-testid="lt-responses-rating-le"
          />
        </label>
        <label className="text-xs text-gray-700 dark:text-gray-300 flex items-center gap-1 mt-4">
          <input
            type="checkbox"
            checked={params.get('has_free_text') === '1'}
            onChange={(e) => setParam('has_free_text', e.target.checked ? '1' : '')}
            data-testid="lt-responses-free-text"
          />
          Has free text
        </label>
      </section>

      {rows.length === 0 ? (
        <p className="text-sm text-gray-500 dark:text-gray-400 text-center py-6" data-testid="lt-responses-empty">
          No reflections match these filters.
        </p>
      ) : (
        <ul className="space-y-2" data-testid="lt-responses-rows">
          {rows.map((r) => (
            <li
              key={r.id}
              className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-3"
              data-testid={`lt-responses-row-${r.id}`}
            >
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <p className="text-sm font-medium text-gray-900 dark:text-white">
                    {r.author?.name ?? 'Unknown'}{' '}
                    {r.subject?.name && r.subject?.id !== r.author?.id && (
                      <span className="text-xs text-gray-500 dark:text-gray-400">
                        about {r.subject.name}
                      </span>
                    )}
                  </p>
                  <p className="text-xs text-gray-500 dark:text-gray-400">
                    Period {fmtDate(r.period_start)} → {fmtDate(r.period_end)} · {r.language} · v{r.template_version}
                  </p>
                </div>
                <Link
                  to={`/reflections/${r.id}`}
                  className="text-xs text-indigo-600 dark:text-indigo-400 hover:underline shrink-0"
                >
                  Open →
                </Link>
              </div>
            </li>
          ))}
        </ul>
      )}

      {totalPages > 1 && (
        <div
          className="flex items-center gap-2 justify-end text-sm"
          data-testid="lt-responses-pagination"
        >
          <button
            type="button"
            disabled={page <= 1}
            onClick={() => setParam('page', String(page - 1))}
            className="rounded-md border border-gray-300 dark:border-gray-600 px-2 py-1 disabled:opacity-40 text-gray-700 dark:text-gray-300"
          >
            Prev
          </button>
          <span className="text-xs text-gray-500 dark:text-gray-400">
            Page {page} / {totalPages}
          </span>
          <button
            type="button"
            disabled={page >= totalPages}
            onClick={() => setParam('page', String(page + 1))}
            className="rounded-md border border-gray-300 dark:border-gray-600 px-2 py-1 disabled:opacity-40 text-gray-700 dark:text-gray-300"
          >
            Next
          </button>
        </div>
      )}
    </>
  );
}

function AggregateTab({ payload }) {
  if (!payload) return null;
  const dims = payload.avg_per_dimension ?? [];
  const langDist = payload.language_distribution ?? {};
  const volume = payload.response_volume_per_period ?? [];
  return (
    <div className="space-y-4">
      <div
        className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-4"
        data-testid="lt-responses-summary"
      >
        <p className="text-sm text-gray-700 dark:text-gray-300">
          <span className="font-semibold text-gray-900 dark:text-white">{payload.total_responses}</span> responses
        </p>
      </div>

      <div
        className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-4"
        data-testid="lt-responses-avg"
      >
        <h3 className="text-base font-semibold text-gray-900 dark:text-white mb-2">
          Average per dimension
        </h3>
        {dims.length === 0 ? (
          <p className="text-sm text-gray-500 dark:text-gray-400">No scored fields.</p>
        ) : (
          <ul className="space-y-1 text-sm">
            {dims.map((d) => (
              <li key={d.key} className="flex justify-between" data-testid={`lt-responses-dim-${d.key}`}>
                <span className="text-gray-700 dark:text-gray-300">
                  {d.key}
                  <span className="ml-2 text-xs text-gray-500 dark:text-gray-400">
                    versions: {(d.versions ?? []).join(', ') || '—'}
                  </span>
                </span>
                <span className="text-gray-900 dark:text-white font-medium">
                  {d.avg == null ? '—' : d.avg.toFixed(2)}
                  <span className="text-xs text-gray-500 dark:text-gray-400 ml-1">({d.count})</span>
                </span>
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-4">
        <h3 className="text-base font-semibold text-gray-900 dark:text-white mb-2">
          Language distribution
        </h3>
        <ul className="text-sm space-y-1">
          {Object.entries(langDist).map(([lang, count]) => (
            <li key={lang} className="flex justify-between text-gray-700 dark:text-gray-300">
              <span>{lang}</span>
              <span>{count}</span>
            </li>
          ))}
        </ul>
      </div>

      <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-4">
        <h3 className="text-base font-semibold text-gray-900 dark:text-white mb-2">
          Volume per period
        </h3>
        <ul className="text-xs space-y-0.5">
          {volume.map((v) => (
            <li key={v.period_start} className="flex justify-between text-gray-700 dark:text-gray-300">
              <span>{v.period_start}</span>
              <span>{v.count}</span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

export default function LeadershipTeamResponses() {
  const { id } = useParams();
  const { orgSlug } = useAuth();
  const [params, setParams] = useSearchParams();
  const tab = (params.get('tab') || 'individual').toLowerCase();

  const [template, setTemplate] = useState(null);
  const [payload, setPayload] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const filtersDeps = useMemo(() => params.toString(), [params]);

  useEffect(() => {
    let cancelled = false;
    async function run() {
      setLoading(true);
      setError('');
      try {
        const [tpl, data] = await Promise.all([
          getTemplate(orgSlug, id),
          fetchResponses(orgSlug, id, Object.fromEntries(new URLSearchParams(filtersDeps).entries())),
        ]);
        if (cancelled) return;
        setTemplate(tpl);
        setPayload(data);
      } catch (err) {
        if (cancelled) return;
        if (err?.response?.status === 403) setError('You cannot view these responses.');
        else if (err?.response?.status === 404) setError('Template not found.');
        else setError('Failed to load responses.');
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    run();
    return () => { cancelled = true; };
  }, [orgSlug, id, filtersDeps]);

  const switchTab = (next) => {
    const updated = new URLSearchParams(params);
    updated.set('tab', next);
    updated.delete('page');
    setParams(updated, { replace: true });
  };

  const exportHref = exportResponsesUrl(id, Object.fromEntries(params.entries()));

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <header className="bg-white dark:bg-gray-800 shadow-sm">
        <div className="max-w-5xl mx-auto px-4 py-4">
          <Link
            to="/leadership-team/templates"
            className="text-sm text-indigo-600 dark:text-indigo-400 hover:underline"
          >
            ← Template library
          </Link>
          <div className="flex items-center justify-between gap-3 mt-2">
            <div>
              <h1 className="text-xl font-bold text-gray-900 dark:text-white">
                {template?.name ?? 'Responses'}
              </h1>
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                {template?.role} · v{template?.version}
              </p>
            </div>
            <a
              href={exportHref}
              className="rounded-lg border border-gray-300 dark:border-gray-600 text-sm font-medium px-3 py-1.5 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800"
              data-testid="lt-responses-export"
            >
              Export CSV
            </a>
          </div>

          <div className="mt-3 flex gap-2 border-b border-gray-200 dark:border-gray-700">
            {['individual', 'aggregate'].map((t) => (
              <button
                key={t}
                type="button"
                onClick={() => switchTab(t)}
                aria-current={tab === t ? 'page' : undefined}
                className={`text-sm px-3 py-2 -mb-px border-b-2 ${
                  tab === t
                    ? 'border-indigo-600 text-indigo-600 dark:text-indigo-400'
                    : 'border-transparent text-gray-600 dark:text-gray-400 hover:text-gray-900'
                }`}
                data-testid={`lt-responses-tab-${t}`}
              >
                {t === 'individual' ? 'Individual' : 'Aggregate'}
              </button>
            ))}
          </div>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-4 py-6 space-y-4">
        {loading && (
          <p className="text-sm text-gray-500 dark:text-gray-400" data-testid="lt-responses-loading">
            Loading…
          </p>
        )}
        {error && (
          <p className="text-red-600 dark:text-red-400 text-sm" data-testid="lt-responses-error">
            {error}
          </p>
        )}
        {!loading && !error && tab === 'individual' && (
          <IndividualTab payload={payload} params={params} setParams={setParams} />
        )}
        {!loading && !error && tab === 'aggregate' && <AggregateTab payload={payload} />}
      </main>
    </div>
  );
}
