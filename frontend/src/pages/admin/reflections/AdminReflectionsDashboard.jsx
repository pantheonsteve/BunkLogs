/**
 * Admin Reflections dashboard — Step 4_4 (TBE).
 *
 * Weekly completion view for Madrichim with a grade-level filter
 * (8-12) and a CSV export for board reporting. Reuses the Wave-3
 * team-dashboard shape (period + submission-status + member rows) via
 * a dedicated org-admin-gated backend endpoint that doesn't require a
 * Supervision relationship (see `admin_flow/reflections.py`).
 *
 * Gated to religious-school orgs -- the grade-level model doesn't apply to
 * a camp's unit-based roster.
 */
import { useCallback, useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import {
  exportAdminReflectionsTeamUrl,
  fetchAdminReflectionsTeam,
} from '../../../api/adminReflections';
import { useAuth } from '../../../auth/AuthContext';
import { orgSurfaces } from '../../../utils/auth/orgProfile';

const ROLE = 'madrich';
const GRADE_OPTIONS = [8, 9, 10, 11, 12];

const STATUS_META = {
  submitted: {
    label: 'Submitted',
    className: 'bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-200',
  },
  day_off: {
    label: 'Day off',
    className: 'bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-200',
  },
  not_submitted: {
    label: 'Not submitted',
    className: 'bg-gray-200 text-gray-800 dark:bg-gray-700 dark:text-gray-100',
  },
};

function StatusPill({ status }) {
  const meta = STATUS_META[status] ?? STATUS_META.not_submitted;
  return (
    <span
      data-testid={`admin-reflections-status-pill-${status}`}
      className={`text-xs font-medium px-2 py-0.5 rounded-full ${meta.className}`}
    >
      {meta.label}
    </span>
  );
}

export default function AdminReflectionsDashboard() {
  const { user, loading: authLoading } = useAuth();
  const showGradeReflections = orgSurfaces(user).gradeReflections;
  const [searchParams, setSearchParams] = useSearchParams();
  const dateParam = searchParams.get('date') || '';
  const gradeParams = searchParams
    .getAll('grade')
    .map(Number)
    .filter((n) => !Number.isNaN(n));
  const gradeKey = gradeParams.slice().sort().join(',');

  const [payload, setPayload] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await fetchAdminReflectionsTeam(ROLE, {
        date: dateParam || undefined,
        gradeLevels: gradeParams,
      });
      setPayload(data);
      setError(null);
    } catch (err) {
      const status = err?.response?.status;
      if (status === 403) setError('Admin access required.');
      else if (status === 404) setError('Unknown role.');
      else setError('Failed to load the reflections dashboard.');
    } finally {
      setLoading(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dateParam, gradeKey]);

  useEffect(() => {
    if (showGradeReflections) load();
  }, [load, showGradeReflections]);

  const onDateChange = (e) => {
    const value = e.target.value;
    const next = new URLSearchParams(searchParams);
    if (value) next.set('date', value);
    else next.delete('date');
    setSearchParams(next, { replace: true });
  };

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

  if (authLoading) {
    return (
      <div className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-[96rem] mx-auto" data-testid="admin-reflections-loading">
        <p className="text-gray-500 dark:text-gray-400">Loading…</p>
      </div>
    );
  }

  if (!showGradeReflections) {
    return (
      <div className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-[96rem] mx-auto" data-testid="admin-reflections-unavailable">
        <h1 className="text-xl font-bold text-gray-900 dark:text-white">Reflections</h1>
        <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">
          The grade-level reflections dashboard isn't available for this organization yet.
        </p>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-[96rem] mx-auto" data-testid="admin-reflections-loading">
        <p className="text-gray-500 dark:text-gray-400">Loading…</p>
      </div>
    );
  }

  if (error || !payload) {
    return (
      <div className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-[96rem] mx-auto" data-testid="admin-reflections-error">
        <p className="text-red-600 dark:text-red-400">{error || 'Failed to load the reflections dashboard.'}</p>
      </div>
    );
  }

  const { header, submission_status: submissionStatus, members, template } = payload;
  const exportUrl = exportAdminReflectionsTeamUrl(ROLE, {
    date: dateParam || undefined,
    gradeLevels: gradeParams,
  });

  return (
    <div className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-[96rem] mx-auto space-y-4">
      <div>
        <div className="flex items-start justify-between gap-3">
          <div>
            <h1 className="text-xl font-bold text-gray-900 dark:text-white">
              {header.role_label} reflections
            </h1>
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
              {header.program?.name} · {header.member_count} members
            </p>
          </div>
          <a
            href={exportUrl}
            className="rounded-lg border border-gray-300 dark:border-gray-600 text-sm font-medium px-3 py-1.5 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800"
            data-testid="admin-reflections-export"
          >
            Export CSV
          </a>
        </div>

        <div className="mt-3 flex flex-wrap items-center gap-3">
          <label className="text-sm text-gray-700 dark:text-gray-300">
            Week of{' '}
            <input
              type="date"
              value={dateParam || header.date}
              onChange={onDateChange}
              max={header.date}
              className="ml-1 rounded-md border-gray-300 dark:border-gray-600 dark:bg-gray-700 text-sm"
              data-testid="admin-reflections-date"
            />
          </label>
          {header.period && (
            <span className="text-xs text-gray-500 dark:text-gray-400">
              Period {header.period.start} → {header.period.end} ({header.period.cadence})
            </span>
          )}
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
                data-testid={`admin-reflections-grade-${grade}`}
              >
                {grade}
              </button>
            );
          })}
        </div>
      </div>

      {!template ? (
        <div
          className="rounded-xl border border-dashed border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 p-4 text-sm text-gray-500 dark:text-gray-400"
          data-testid="admin-reflections-no-template"
        >
          No active reflection template is configured for this role yet.
        </div>
      ) : (
        <section
          aria-label="Submission status"
          className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-4"
          data-testid="admin-reflections-summary"
        >
          <h2 className="text-base font-semibold text-gray-900 dark:text-white mb-2">
            Submission status
          </h2>
          <div className="flex flex-wrap gap-3 text-xs text-gray-700 dark:text-gray-300">
            <span>Submitted: {submissionStatus.submitted}</span>
            <span>Not submitted: {submissionStatus.not_submitted}</span>
            <span>Day off: {submissionStatus.day_off}</span>
            <span>Total: {submissionStatus.total}</span>
          </div>
        </section>
      )}

      <section aria-label="Members" data-testid="admin-reflections-members">
        <h2 className="text-base font-semibold text-gray-900 dark:text-white mb-2">Members</h2>
        {members.length === 0 ? (
          <div className="rounded-xl border border-dashed border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 p-4 text-sm text-gray-500 dark:text-gray-400">
            No members match this filter.
          </div>
        ) : (
          <ul className="space-y-2">
            {members.map((m) => (
              <li
                key={m.membership_id}
                className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900"
                data-testid={`admin-reflections-member-${m.membership_id}`}
              >
                <Link
                  to={`/admin/reflections/${ROLE}/members/${m.membership_id}`}
                  className="block px-4 py-3 hover:bg-gray-50 dark:hover:bg-gray-800 rounded-xl"
                >
                  <div className="flex items-center justify-between gap-3">
                    <div className="min-w-0 flex items-center gap-2">
                      <p className="font-medium text-gray-900 dark:text-white truncate">
                        {m.person_name}
                      </p>
                      {m.grade_level != null && (
                        <span className="text-xs text-gray-500 dark:text-gray-400">
                          Grade {m.grade_level}
                        </span>
                      )}
                    </div>
                    <StatusPill status={m.status} />
                  </div>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
