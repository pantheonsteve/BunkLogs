/**
 * Admin growth dashboard by grade level (/admin/reflections/growth).
 *
 * Shows what themes each grade cohort raises in their weekly 3-2-1
 * reflections, so a Director can see 8th graders wrestling with fundamentals
 * and 11th graders taking on harder challenges — and coach the gap when the
 * progression isn't there.
 *
 * Gated to religious-school orgs: grade level only exists on the Madrichim
 * roster, and a camp's unit-based roster has no equivalent.
 */
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { useSearchParams } from 'react-router-dom';
import { Chart as ChartJS } from 'chart.js';
import 'chart.js/auto';

import {
  exportAdminGrowthUrl,
  fetchAdminGrowth,
  fetchAdminGrowthExamples,
} from '../../../api/adminGrowth';
import { useAuth } from '../../../auth/AuthContext';
import { orgSurfaces } from '../../../utils/auth/orgProfile';

const GRADE_OPTIONS = [8, 9, 10, 11, 12];

// Distinct enough to read as separate cohorts at a glance, and ordered so
// older grades are visually "further along" the same hue ramp.
const GRADE_COLORS = ['#c7d2fe', '#a5b4fc', '#818cf8', '#6366f1', '#4338ca'];

const COMPLEXITY_KEY = '__concern_complexity';

// A grade with fewer reflections than this is too thin to read as signal;
// we still show it but flag it rather than letting the Director over-read it.
const THIN_COHORT_REFLECTIONS = 3;

const DIRECTION_META = {
  improving: { label: 'Rising with grade', className: 'text-green-700 dark:text-green-300' },
  flat: { label: 'Flat across grades', className: 'text-amber-700 dark:text-amber-300' },
  declining: { label: 'Falling with grade', className: 'text-red-700 dark:text-red-300' },
  insufficient_data: { label: 'Not enough data', className: 'text-gray-500 dark:text-gray-400' },
};

function gradeColor(index) {
  return GRADE_COLORS[index % GRADE_COLORS.length];
}

function formatSlope(slope) {
  if (slope == null) return '—';
  const sign = slope > 0 ? '+' : '';
  return `${sign}${slope.toFixed(2)}/grade`;
}

/**
 * Grouped bar chart: one bar group per theme, one bar per grade.
 *
 * Shows share of concerns rather than raw counts so an 8th-grade cohort of
 * 20 doesn't dwarf an 11th-grade cohort of 4 — the question is what each
 * grade talks about, not how many of them there are.
 */
function ThemesByGradeChart({ grades, taxonomy }) {
  const canvasRef = useRef(null);
  const chartRef = useRef(null);

  useEffect(() => {
    if (!canvasRef.current) return undefined;
    if (chartRef.current) chartRef.current.destroy();

    const themesWithConcerns = taxonomy.filter((theme) =>
      grades.some((grade) =>
        grade.themes.some((t) => t.theme_key === theme.key && t.open_concern_count > 0),
      ),
    );

    chartRef.current = new ChartJS(canvasRef.current.getContext('2d'), {
      type: 'bar',
      data: {
        labels: themesWithConcerns.map((t) => t.label),
        datasets: grades.map((grade, index) => ({
          label: grade.grade_level == null ? 'Unknown grade' : `Grade ${grade.grade_level}`,
          data: themesWithConcerns.map((theme) => {
            const row = grade.themes.find((t) => t.theme_key === theme.key);
            return row?.share_of_concerns != null ? Math.round(row.share_of_concerns * 100) : 0;
          }),
          backgroundColor: gradeColor(index),
          borderRadius: 4,
        })),
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { position: 'bottom' },
          tooltip: { callbacks: { label: (ctx) => `${ctx.dataset.label}: ${ctx.parsed.y}% of concerns` } },
        },
        scales: {
          y: { beginAtZero: true, ticks: { callback: (v) => `${v}%` }, title: { display: true, text: 'Share of concerns' } },
        },
      },
    });
    return () => {
      if (chartRef.current) {
        chartRef.current.destroy();
        chartRef.current = null;
      }
    };
  }, [grades, taxonomy]);

  return (
    <div className="h-80" data-testid="admin-growth-chart">
      <canvas ref={canvasRef} />
    </div>
  );
}

function MilestoneCard({ milestone }) {
  const meta = DIRECTION_META[milestone.direction] ?? DIRECTION_META.insufficient_data;
  const values = milestone.by_grade.filter((p) => p.value != null);
  const max = values.length ? Math.max(...values.map((p) => p.value)) : 0;

  return (
    <div
      className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-4"
      data-testid={`admin-growth-milestone-${milestone.metric_key}`}
    >
      <p className="text-sm font-medium text-gray-900 dark:text-white">{milestone.label}</p>
      <p className={`text-xs mt-0.5 ${meta.className}`}>
        {meta.label} · {formatSlope(milestone.slope)}
      </p>
      <div className="mt-3 flex items-end gap-1.5 h-16">
        {milestone.by_grade.map((point) => (
          <div key={point.grade_level} className="flex-1 flex flex-col items-center justify-end gap-1">
            <div
              className="w-full rounded-t bg-indigo-500 dark:bg-indigo-400 min-h-[2px]"
              style={{ height: point.value != null && max > 0 ? `${(point.value / max) * 100}%` : '2px' }}
              title={point.value != null ? String(point.value) : 'No data'}
            />
            <span className="text-[10px] text-gray-500 dark:text-gray-400">{point.grade_level}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function CoverageBanner({ coverage }) {
  const untagged = coverage.pending + coverage.failed + coverage.untagged;
  if (coverage.reflections === 0) {
    return (
      <div
        className="rounded-xl border border-dashed border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 p-4 text-sm text-gray-500 dark:text-gray-400"
        data-testid="admin-growth-coverage"
      >
        No reflections have been submitted in this window yet.
      </div>
    );
  }
  const complete = untagged === 0;
  return (
    <div
      className={`rounded-xl border p-3 text-xs ${
        complete
          ? 'border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 text-gray-600 dark:text-gray-300'
          : 'border-amber-300 dark:border-amber-700 bg-amber-50 dark:bg-amber-900/20 text-amber-800 dark:text-amber-200'
      }`}
      data-testid="admin-growth-coverage"
    >
      {coverage.tagged} of {coverage.reflections} reflections categorized
      {!complete && (
        <>
          {' '}· {untagged} still uncategorized, so a thin grade below may be a backlog rather than a real signal
        </>
      )}
    </div>
  );
}

function ExamplesPanel({ theme, items, loading, onClose }) {
  return (
    <div
      className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-4"
      data-testid="admin-growth-examples"
    >
      <div className="flex items-start justify-between gap-3">
        <p className="text-sm font-medium text-gray-900 dark:text-white">
          What they actually wrote · {theme.label}
        </p>
        <button
          type="button"
          onClick={onClose}
          className="text-xs text-gray-500 dark:text-gray-400 hover:underline"
          data-testid="admin-growth-examples-close"
        >
          Close
        </button>
      </div>
      {loading ? (
        <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">Loading…</p>
      ) : items.length === 0 ? (
        <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">No examples in this window.</p>
      ) : (
        <ul className="mt-2 space-y-2">
          {items.map((item) => (
            <li
              key={`${item.reflection_id}-${item.field_key}`}
              className="rounded-lg bg-gray-50 dark:bg-gray-800 px-3 py-2"
            >
              <p className="text-sm text-gray-800 dark:text-gray-100">{item.excerpt}</p>
              <p className="mt-1 text-[11px] text-gray-500 dark:text-gray-400">
                Grade {item.grade_level ?? '—'} · week of {item.period_start}
              </p>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export default function AdminGrowthDashboard() {
  const { user, loading: authLoading } = useAuth();
  const showGradeReflections = orgSurfaces(user).gradeReflections;
  const [searchParams, setSearchParams] = useSearchParams();

  const startParam = searchParams.get('start') || '';
  const endParam = searchParams.get('end') || '';
  const gradeParams = searchParams
    .getAll('grade')
    .map(Number)
    .filter((n) => !Number.isNaN(n));
  const gradeKey = gradeParams.slice().sort().join(',');

  const [payload, setPayload] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [examples, setExamples] = useState(null);
  const [examplesLoading, setExamplesLoading] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await fetchAdminGrowth({
        start: startParam || undefined,
        end: endParam || undefined,
        gradeLevels: gradeParams,
      });
      setPayload(data);
      setError(null);
    } catch (err) {
      const status = err?.response?.status;
      if (status === 403) setError('Admin access required.');
      else if (status === 400) setError('That date range is not valid.');
      else setError('Failed to load the growth dashboard.');
    } finally {
      setLoading(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [startParam, endParam, gradeKey]);

  useEffect(() => {
    if (showGradeReflections) load();
  }, [load, showGradeReflections]);

  const toggleGrade = (grade) => {
    const next = new URLSearchParams(searchParams);
    const current = next.getAll('grade').map(Number);
    next.delete('grade');
    const updated = current.includes(grade)
      ? current.filter((g) => g !== grade)
      : [...current, grade];
    updated.forEach((g) => next.append('grade', String(g)));
    setSearchParams(next, { replace: true });
  };

  const onDateChange = (key) => (e) => {
    const value = e.target.value;
    const next = new URLSearchParams(searchParams);
    if (value) next.set(key, value);
    else next.delete(key);
    setSearchParams(next, { replace: true });
  };

  const openExamples = async (themeKey) => {
    const theme = payload.taxonomy.find((t) => t.key === themeKey);
    setExamples({ theme, items: [] });
    setExamplesLoading(true);
    try {
      const data = await fetchAdminGrowthExamples({
        theme: themeKey,
        dashboardRole: 'open_concern',
        start: startParam || undefined,
        end: endParam || undefined,
        gradeLevels: gradeParams,
      });
      setExamples({ theme, items: data.items });
    } catch {
      setExamples({ theme, items: [] });
    } finally {
      setExamplesLoading(false);
    }
  };

  // Themes actually raised as concerns, ordered by the taxonomy's complexity
  // tier so the table itself reads as a fundamentals-to-sophisticated ramp.
  const tableThemes = useMemo(() => {
    if (!payload) return [];
    return payload.taxonomy
      .filter((theme) =>
        payload.grades.some((grade) =>
          grade.themes.some((t) => t.theme_key === theme.key && t.open_concern_count > 0),
        ),
      )
      .sort((a, b) => a.complexity_tier - b.complexity_tier || a.label.localeCompare(b.label));
  }, [payload]);

  if (authLoading) {
    return (
      <div className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-[96rem] mx-auto" data-testid="admin-growth-loading">
        <p className="text-gray-500 dark:text-gray-400">Loading…</p>
      </div>
    );
  }

  if (!showGradeReflections) {
    return (
      <div className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-[96rem] mx-auto" data-testid="admin-growth-unavailable">
        <h1 className="text-xl font-bold text-gray-900 dark:text-white">Growth by grade</h1>
        <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">
          Growth by grade level isn't available for this organization.
        </p>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-[96rem] mx-auto" data-testid="admin-growth-loading">
        <p className="text-gray-500 dark:text-gray-400">Loading…</p>
      </div>
    );
  }

  if (error || !payload) {
    return (
      <div className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-[96rem] mx-auto" data-testid="admin-growth-error">
        <p className="text-red-600 dark:text-red-400">{error || 'Failed to load the growth dashboard.'}</p>
      </div>
    );
  }

  const { header, grades, milestones, taxonomy } = payload;
  const exportUrl = exportAdminGrowthUrl({
    start: startParam || undefined,
    end: endParam || undefined,
    gradeLevels: gradeParams,
  });
  const complexity = milestones.find((m) => m.metric_key === COMPLEXITY_KEY);

  return (
    <div className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-[96rem] mx-auto space-y-4">
      <div>
        <div className="flex items-start justify-between gap-3">
          <div>
            <h1 className="text-xl font-bold text-gray-900 dark:text-white">Growth by grade</h1>
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
              What each grade is asking about · {header.program?.name} · {header.period.start} → {header.period.end}
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Link
              to="/admin/reflections"
              className="rounded-lg border border-gray-300 dark:border-gray-600 text-sm font-medium px-3 py-1.5 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800"
              data-testid="admin-growth-completion-tab"
            >
              Completion
            </Link>
            <a
              href={exportUrl}
              className="rounded-lg border border-gray-300 dark:border-gray-600 text-sm font-medium px-3 py-1.5 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800"
              data-testid="admin-growth-export"
            >
              Export CSV
            </a>
          </div>
        </div>

        <div className="mt-3 flex flex-wrap items-center gap-3">
          <label className="text-sm text-gray-700 dark:text-gray-300">
            From{' '}
            <input
              type="date"
              value={startParam || header.period.start}
              onChange={onDateChange('start')}
              className="ml-1 rounded-md border-gray-300 dark:border-gray-600 dark:bg-gray-700 text-sm"
              data-testid="admin-growth-start"
            />
          </label>
          <label className="text-sm text-gray-700 dark:text-gray-300">
            To{' '}
            <input
              type="date"
              value={endParam || header.period.end}
              onChange={onDateChange('end')}
              className="ml-1 rounded-md border-gray-300 dark:border-gray-600 dark:bg-gray-700 text-sm"
              data-testid="admin-growth-end"
            />
          </label>
        </div>

        <div className="mt-3 flex flex-wrap items-center gap-2">
          <span className="text-sm text-gray-700 dark:text-gray-300 mr-1">Grade:</span>
          {GRADE_OPTIONS.map((grade) => {
            const active = gradeParams.includes(grade);
            return (
              <button
                key={grade}
                type="button"
                onClick={() => toggleGrade(grade)}
                className={`text-xs px-2 py-1 rounded-full border ${
                  active
                    ? 'bg-indigo-600 text-white border-indigo-600'
                    : 'border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300'
                }`}
                data-testid={`admin-growth-grade-${grade}`}
              >
                {grade}
              </button>
            );
          })}
        </div>
      </div>

      <CoverageBanner coverage={header.coverage} />

      {grades.length === 0 ? (
        <div
          className="rounded-xl border border-dashed border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 p-4 text-sm text-gray-500 dark:text-gray-400"
          data-testid="admin-growth-empty"
        >
          No graded cohorts to compare yet.
        </div>
      ) : (
        <>
          {complexity && (
            <section
              aria-label="Concern sophistication"
              className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-4"
              data-testid="admin-growth-headline"
            >
              <h2 className="text-base font-semibold text-gray-900 dark:text-white">
                Are older grades taking on harder challenges?
              </h2>
              <p className="mt-1 text-sm text-gray-600 dark:text-gray-300">
                Concern complexity is{' '}
                <span className={DIRECTION_META[complexity.direction]?.className}>
                  {(DIRECTION_META[complexity.direction]?.label ?? '').toLowerCase()}
                </span>{' '}
                ({formatSlope(complexity.slope)}).{' '}
                {complexity.direction === 'improving'
                  ? 'Older Madrichim are raising more sophisticated concerns, which is the progression you want.'
                  : complexity.direction === 'insufficient_data'
                    ? 'More grades need categorized reflections before this reads as a trend.'
                    : 'Older Madrichim are not yet raising harder concerns than the younger cohort — worth coaching.'}
              </p>
            </section>
          )}

          <section aria-label="Concern themes by grade" data-testid="admin-growth-themes">
            <h2 className="text-base font-semibold text-gray-900 dark:text-white mb-2">
              Concern themes by grade
            </h2>
            <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-4">
              <ThemesByGradeChart grades={grades} taxonomy={taxonomy} />
            </div>
          </section>

          {milestones.length > 0 && (
            <section aria-label="Developmental milestones" data-testid="admin-growth-milestones">
              <h2 className="text-base font-semibold text-gray-900 dark:text-white mb-2">
                Developmental milestones
              </h2>
              <p className="text-xs text-gray-500 dark:text-gray-400 mb-2">
                Each cohort's own averages across grades 8-12. A rising line means the
                progression is happening; a flat one is where to coach.
              </p>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                {milestones.map((m) => (
                  <MilestoneCard key={m.metric_key} milestone={m} />
                ))}
              </div>
            </section>
          )}

          <section aria-label="Theme detail" data-testid="admin-growth-table">
            <h2 className="text-base font-semibold text-gray-900 dark:text-white mb-2">
              Theme detail
            </h2>
            {tableThemes.length === 0 ? (
              <div className="rounded-xl border border-dashed border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 p-4 text-sm text-gray-500 dark:text-gray-400">
                No concerns have been categorized in this window yet.
              </div>
            ) : (
              <div className="overflow-x-auto rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900">
                <table className="min-w-full text-sm">
                  <thead className="bg-gray-50 dark:bg-gray-800 text-xs uppercase text-gray-500 dark:text-gray-400">
                    <tr>
                      <th scope="col" className="px-4 py-2 text-left font-medium">Theme</th>
                      <th scope="col" className="px-4 py-2 text-left font-medium">Tier</th>
                      {grades.map((grade) => (
                        <th key={grade.grade_level} scope="col" className="px-4 py-2 text-right font-medium">
                          {grade.grade_level == null ? 'Unknown' : `Grade ${grade.grade_level}`}
                        </th>
                      ))}
                      <th scope="col" className="px-4 py-2" />
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                    {tableThemes.map((theme) => (
                      <tr key={theme.key} data-testid={`admin-growth-row-${theme.key}`}>
                        <td className="px-4 py-2 text-gray-900 dark:text-white">{theme.label}</td>
                        <td className="px-4 py-2 text-gray-500 dark:text-gray-400">{theme.complexity_tier}</td>
                        {grades.map((grade) => {
                          const row = grade.themes.find((t) => t.theme_key === theme.key);
                          return (
                            <td
                              key={grade.grade_level}
                              className="px-4 py-2 text-right text-gray-700 dark:text-gray-300"
                            >
                              {row?.open_concern_count ? row.open_concern_count : '—'}
                            </td>
                          );
                        })}
                        <td className="px-4 py-2 text-right">
                          <button
                            type="button"
                            onClick={() => openExamples(theme.key)}
                            className="text-xs text-indigo-600 dark:text-indigo-400 hover:underline"
                            data-testid={`admin-growth-examples-${theme.key}`}
                          >
                            Examples
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>

          {examples && (
            <ExamplesPanel
              theme={examples.theme}
              items={examples.items}
              loading={examplesLoading}
              onClose={() => setExamples(null)}
            />
          )}

          <section aria-label="Cohort sizes" data-testid="admin-growth-cohorts">
            <div className="flex flex-wrap gap-2 text-xs text-gray-500 dark:text-gray-400">
              {grades.map((grade) => (
                <span
                  key={grade.grade_level}
                  className="rounded-full border border-gray-200 dark:border-gray-700 px-2 py-1"
                  data-testid={`admin-growth-cohort-${grade.grade_level}`}
                >
                  {grade.grade_level == null ? 'Unknown grade' : `Grade ${grade.grade_level}`}:{' '}
                  {grade.member_count} members, {grade.reflection_count} reflections
                  {grade.reflection_count > 0 && grade.reflection_count < THIN_COHORT_REFLECTIONS && ' · thin'}
                </span>
              ))}
            </div>
          </section>
        </>
      )}
    </div>
  );
}
