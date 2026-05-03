import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { Minus, TrendingDown, TrendingUp } from 'lucide-react';

import Header from '../partials/Header';
import Sidebar from '../partials/Sidebar';
import api from '../api';

const SUB_ROLE_LABELS = {
  camper_care: 'Camper Care',
  health_center: 'Health Center',
  special_diets: 'Special Diets',
};

function trendIcon(label) {
  if (label === 'up') {
    return <TrendingUp className="inline h-4 w-4 text-emerald-600 dark:text-emerald-400" aria-hidden />;
  }
  if (label === 'down') {
    return <TrendingDown className="inline h-4 w-4 text-rose-600 dark:text-rose-400" aria-hidden />;
  }
  return <Minus className="inline h-4 w-4 text-gray-400" aria-hidden />;
}

function pct(n) {
  if (n == null || Number.isNaN(n)) return '—';
  return `${Math.round(n * 1000) / 10}%`;
}

function todayIso() {
  const d = new Date();
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${y}-${m}-${day}`;
}

export default function WellnessDashboardPage() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [payload, setPayload] = useState(null);
  const [subRole, setSubRole] = useState('');
  const [periodEnd, setPeriodEnd] = useState(todayIso);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = {
        period_end: periodEnd,
        period_days: 14,
      };
      if (subRole) params.sub_role = subRole;
      const { data } = await api.get('/api/v1/dashboards/wellness/', { params });
      setPayload(data);
    } catch (e) {
      const status = e.response?.status;
      if (status === 403) {
        setError('access');
      } else {
        setError(e.response?.data?.detail || e.message || 'Failed to load wellness dashboard');
      }
      setPayload(null);
    } finally {
      setLoading(false);
    }
  }, [periodEnd, subRole]);

  useEffect(() => {
    load();
  }, [load]);

  const totals = useMemo(() => payload?.completion ?? null, [payload]);

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} />
      <div className="relative flex flex-col flex-1 overflow-y-auto overflow-x-hidden">
        <Header sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} />
        <main className="grow px-4 sm:px-6 lg:px-8 py-8 w-full max-w-9xl mx-auto">
          <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <h1 className="text-2xl font-semibold text-gray-900 dark:text-white">Wellness team</h1>
              <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                Camper Care, Health Center, and Special Diets reflections, with cross-team patterns
                surfaced from other staff feedback.
              </p>
            </div>
            <div className="flex flex-wrap items-center gap-4">
              <label className="flex items-center gap-2 text-sm text-gray-700 dark:text-gray-300">
                <span>Sub-role</span>
                <select
                  value={subRole}
                  onChange={(ev) => setSubRole(ev.target.value)}
                  className="rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-2 py-1 text-sm"
                  aria-label="Filter by wellness sub-role"
                >
                  <option value="">All wellness roles</option>
                  <option value="camper_care">Camper Care</option>
                  <option value="health_center">Health Center</option>
                  <option value="special_diets">Special Diets</option>
                </select>
              </label>
              <label className="flex items-center gap-2 text-sm text-gray-700 dark:text-gray-300">
                <span>Period ends</span>
                <input
                  type="date"
                  value={periodEnd}
                  onChange={(ev) => setPeriodEnd(ev.target.value)}
                  className="rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-2 py-1 text-sm"
                />
              </label>
              <button
                type="button"
                onClick={load}
                className="rounded-md bg-teal-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-teal-500"
              >
                Refresh
              </button>
            </div>
          </div>

          {loading && (
            <p className="text-gray-600 dark:text-gray-400">Loading…</p>
          )}

          {!loading && error === 'access' && (
            <div className="rounded-lg border border-amber-200 dark:border-amber-900/40 bg-amber-50 dark:bg-amber-900/20 p-4 text-amber-900 dark:text-amber-100">
              <p className="font-medium">Access restricted</p>
              <p className="text-sm mt-1">
                The wellness dashboard requires a multi-tenant <strong>camper_care</strong>,{' '}
                <strong>health_center</strong>, <strong>special_diets</strong>, or{' '}
                <strong>admin</strong> program membership, or an account with the legacy{' '}
                <strong>Admin</strong> staff role.
              </p>
              <Link to="/dashboard" className="text-sm underline mt-2 inline-block">
                Back to dashboard
              </Link>
            </div>
          )}

          {!loading && error && error !== 'access' && (
            <p className="text-rose-600 dark:text-rose-400">{error}</p>
          )}

          {!loading && payload && (
            <>
              <p className="text-xs text-gray-500 dark:text-gray-400 mb-4">
                Window: {payload.period?.current_start} → {payload.period?.current_end} (prior:{' '}
                {payload.period?.prior_start} → {payload.period?.prior_end})
              </p>

              {totals && (
                <section className="mb-8 grid grid-cols-1 sm:grid-cols-3 gap-4">
                  <div className="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900/40 p-4">
                    <p className="text-xs uppercase text-gray-500 dark:text-gray-400">Wellness staff</p>
                    <p className="text-2xl font-semibold text-gray-900 dark:text-white">
                      {totals.total_staff}
                    </p>
                  </div>
                  <div className="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900/40 p-4">
                    <p className="text-xs uppercase text-gray-500 dark:text-gray-400">Reflections submitted</p>
                    <p className="text-2xl font-semibold text-gray-900 dark:text-white">
                      {totals.reflections_submitted}
                    </p>
                  </div>
                  <div className="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900/40 p-4">
                    <p className="text-xs uppercase text-gray-500 dark:text-gray-400">Completion rate</p>
                    <p className="text-2xl font-semibold text-gray-900 dark:text-white">
                      {pct(totals.completion_rate)}
                    </p>
                  </div>
                </section>
              )}

              <section className="mb-10">
                <h2 className="text-lg font-medium text-gray-900 dark:text-white mb-3">
                  Reflections by sub-role
                </h2>
                <div className="overflow-x-auto rounded-lg border border-gray-200 dark:border-gray-700">
                  <table className="min-w-full text-sm">
                    <thead className="bg-gray-50 dark:bg-gray-800/80">
                      <tr>
                        <th className="text-left px-3 py-2 font-medium">Sub-role</th>
                        <th className="text-left px-3 py-2 font-medium">Program</th>
                        <th className="text-right px-3 py-2 font-medium">Staff</th>
                        <th className="text-right px-3 py-2 font-medium">Submitted</th>
                        <th className="text-right px-3 py-2 font-medium">Completion</th>
                        <th className="text-center px-3 py-2 font-medium">Comp. trend</th>
                        <th className="text-left px-3 py-2 font-medium">Category averages</th>
                        <th className="text-center px-3 py-2 font-medium">Rating trend</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
                      {(payload.by_sub_role || []).map((row) => (
                        <tr
                          key={`${row.program_slug}-${row.role}`}
                          className="bg-white dark:bg-gray-900/40"
                        >
                          <td className="px-3 py-2 font-medium text-gray-900 dark:text-white">
                            {SUB_ROLE_LABELS[row.role] || row.role}
                          </td>
                          <td className="px-3 py-2 text-gray-600 dark:text-gray-300">{row.program_slug}</td>
                          <td className="px-3 py-2 text-right">{row.total_staff}</td>
                          <td className="px-3 py-2 text-right">{row.reflections_submitted}</td>
                          <td className="px-3 py-2 text-right">{pct(row.completion_rate)}</td>
                          <td className="px-3 py-2 text-center">
                            {trendIcon(row.completion_trend)}
                            <span className="sr-only">{row.completion_trend}</span>
                          </td>
                          <td className="px-3 py-2 text-gray-600 dark:text-gray-300 text-xs">
                            {Object.keys(row.category_averages || {}).length === 0
                              ? '—'
                              : Object.entries(row.category_averages)
                                  .map(([k, v]) => `${k}: ${v}`)
                                  .join(', ')}
                          </td>
                          <td className="px-3 py-2 text-center">
                            {trendIcon(row.rating_trend)}
                            <span className="sr-only">{row.rating_trend}</span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  {(payload.by_sub_role || []).length === 0 && (
                    <p className="p-4 text-gray-500 dark:text-gray-400 text-sm">
                      No wellness staff in scope for this filter.
                    </p>
                  )}
                </div>
              </section>

              <section className="mb-10">
                <h2 className="text-lg font-medium text-gray-900 dark:text-white mb-3">
                  Concerning ratings (≤2)
                </h2>
                <ul className="space-y-2 text-sm">
                  {(payload.by_sub_role || [])
                    .flatMap((row) =>
                      (row.concerning || []).map((c) => ({ ...c, role: row.role })),
                    )
                    .map((c, i) => (
                      <li
                        key={`${c.reflection_id}-${c.field_key}-${c.category}-${i}`}
                        className="rounded-md border border-rose-200 dark:border-rose-900/50 bg-rose-50/50 dark:bg-rose-950/30 px-3 py-2"
                      >
                        <span className="font-medium text-rose-800 dark:text-rose-200">
                          {SUB_ROLE_LABELS[c.role] || c.role} · {c.category} = {c.value}
                        </span>
                        <span className="text-gray-600 dark:text-gray-400 ml-2">
                          person {c.person_id} · {c.period_end}
                        </span>
                      </li>
                    ))}
                </ul>
                {((payload.by_sub_role || []).flatMap((r) => r.concerning || []).length === 0) && (
                  <p className="text-gray-500 dark:text-gray-400 text-sm">None in this period.</p>
                )}
              </section>

              <section className="mb-10">
                <h2 className="text-lg font-medium text-gray-900 dark:text-white mb-3">
                  Cross-team patterns
                </h2>
                <p className="text-xs text-gray-500 dark:text-gray-400 mb-3">
                  Concerns flagged in non-wellness reflections that mention wellness, camper care,
                  health center, or special diets.
                </p>
                <ul className="space-y-2 text-sm">
                  {(payload.cross_team_patterns || []).map((p, i) => (
                    <li
                      key={`${p.reflection_id}-${p.field_key}-${i}`}
                      className="rounded-md border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900/40 px-3 py-2"
                    >
                      <p className="text-gray-500 dark:text-gray-400 text-xs mb-1">
                        {p.template_role || p.template_slug} · {p.field_key} · {p.period_end}
                      </p>
                      <p className="text-gray-800 dark:text-gray-200 whitespace-pre-wrap">{p.text}</p>
                    </li>
                  ))}
                </ul>
                {(payload.cross_team_patterns || []).length === 0 && (
                  <p className="text-gray-500 dark:text-gray-400 text-sm">
                    No wellness mentions surfaced in other teams' reflections this period.
                  </p>
                )}
              </section>

              <section>
                <h2 className="text-lg font-medium text-gray-900 dark:text-white mb-3">
                  Open questions / concerns
                </h2>
                <ul className="space-y-2 text-sm">
                  {(payload.by_sub_role || [])
                    .flatMap((row) =>
                      (row.open_questions || []).map((oq) => ({ ...oq, role: row.role })),
                    )
                    .map((q) => (
                      <li
                        key={`${q.reflection_id}-${q.field_key}`}
                        className="rounded-md border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900/40 px-3 py-2"
                      >
                        <p className="text-gray-500 dark:text-gray-400 text-xs mb-1">
                          {SUB_ROLE_LABELS[q.role] || q.role} · {q.field_key} · {q.period_end}
                        </p>
                        <p className="text-gray-800 dark:text-gray-200 whitespace-pre-wrap">{q.text}</p>
                      </li>
                    ))}
                </ul>
                {((payload.by_sub_role || []).flatMap((r) => r.open_questions || []).length === 0) && (
                  <p className="text-gray-500 dark:text-gray-400 text-sm">None captured in this period.</p>
                )}
              </section>
            </>
          )}
        </main>
      </div>
    </div>
  );
}
