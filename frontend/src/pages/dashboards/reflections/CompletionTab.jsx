/**
 * Reflection completion roster. Shown on the Reflections dashboard when
 * the organization has turned on the reflection_completion setting.
 *
 * The role list is this org's enabled membership roles that have a
 * self-reflection template. The grade filter appears only when the
 * roster rows carry grades, so a camp can use the same tab.
 */
import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { CalendarCheck2, Download, GraduationCap, Users } from 'lucide-react';
import { getAdminSettings } from '../../../api/admin';
import {
  exportAdminReflectionsTeamUrl,
  fetchAdminReflectionsTeam,
} from '../../../api/adminReflections';
import { listTemplates } from '../../../api/leadershipTeam';
import { useAuth } from '../../../auth/AuthContext';
import HomeCard from '../../../components/ui/HomeCard';
import { useTerm } from '../../../context/OrgBrandingContext';

const STATUS_META = {
  submitted: {
    label: 'Submitted',
    className: 'bg-green-100 text-green-900 dark:bg-green-900/50 dark:text-green-100 ring-1 ring-inset ring-green-600/25',
    dotClassName: 'bg-green-500',
    rowClassName: 'border-l-green-500 dark:border-l-green-400',
  },
  day_off: {
    label: 'Day off',
    className: 'bg-blue-100 text-blue-900 dark:bg-blue-900/50 dark:text-blue-100 ring-1 ring-inset ring-blue-600/25',
    dotClassName: 'bg-blue-500',
    rowClassName: 'border-l-blue-500 dark:border-l-blue-400',
  },
  not_submitted: {
    label: 'Not submitted',
    className: 'bg-amber-100 text-amber-900 dark:bg-amber-900/50 dark:text-amber-100 ring-1 ring-inset ring-amber-600/25',
    dotClassName: 'bg-amber-500',
    rowClassName: 'border-l-amber-500 dark:border-l-amber-400',
  },
};

const STAT_TILES = [
  {
    key: 'submitted',
    label: 'Submitted',
    className: 'border-green-200 bg-green-50 text-green-900 dark:border-green-800 dark:bg-green-900/25 dark:text-green-100',
  },
  {
    key: 'not_submitted',
    label: 'Not submitted',
    className: 'border-amber-200 bg-amber-50 text-amber-900 dark:border-amber-800 dark:bg-amber-900/25 dark:text-amber-100',
  },
  {
    key: 'day_off',
    label: 'Day off',
    className: 'border-blue-200 bg-blue-50 text-blue-900 dark:border-blue-800 dark:bg-blue-900/25 dark:text-blue-100',
  },
  {
    key: 'total',
    label: 'Total',
    className: 'border-indigo-200 bg-indigo-50 text-indigo-900 dark:border-indigo-800 dark:bg-indigo-900/25 dark:text-indigo-100',
  },
];

function initialsFor(name) {
  const parts = String(name || '').trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return '?';
  return (parts[0][0] + (parts.length > 1 ? parts[parts.length - 1][0] : '')).toUpperCase();
}

function StatusPill({ status }) {
  const meta = STATUS_META[status] ?? STATUS_META.not_submitted;
  return (
    <span
      data-testid={`admin-reflections-status-pill-${status}`}
      className={`inline-flex items-center gap-1.5 text-xs font-semibold px-2.5 py-0.5 rounded-full ${meta.className}`}
    >
      <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${meta.dotClassName}`} aria-hidden="true" />
      {meta.label}
    </span>
  );
}

function CompletionBar({ submissionStatus }) {
  const expected = submissionStatus.total - submissionStatus.day_off;
  const pct = expected > 0 ? Math.round((submissionStatus.submitted / expected) * 100) : null;
  return (
    <div data-testid="admin-reflections-completion">
      <div className="flex items-baseline justify-between gap-3">
        <p className="text-3xl font-bold text-indigo-700 dark:text-indigo-300">
          {pct === null ? '—' : `${pct}%`}
        </p>
        <p className="text-sm text-gray-700 dark:text-gray-300">
          {submissionStatus.submitted} of {expected} expected
        </p>
      </div>
      <div
        className="mt-2 h-2.5 rounded-full bg-gray-200 dark:bg-gray-700 overflow-hidden"
        role="progressbar"
        aria-valuenow={pct ?? 0}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label="Completion rate"
      >
        <div
          className="h-full rounded-full bg-indigo-600 dark:bg-indigo-400"
          style={{ width: `${pct ?? 0}%` }}
        />
      </div>
    </div>
  );
}

export default function CompletionTab() {
  const { orgSlug } = useAuth();
  const term = useTerm();
  const [searchParams, setSearchParams] = useSearchParams();
  const dateParam = searchParams.get('date') || '';
  const roleParam = searchParams.get('role') || '';
  const gradeParams = searchParams
    .getAll('grade')
    .map(Number)
    .filter((n) => !Number.isNaN(n));
  const gradeKey = gradeParams.slice().sort().join(',');

  const [roles, setRoles] = useState(null);
  const [rolesError, setRolesError] = useState(null);
  const [payload, setPayload] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [knownGrades, setKnownGrades] = useState([]);

  useEffect(() => {
    let cancelled = false;
    Promise.all([
      getAdminSettings(),
      listTemplates(orgSlug),
    ]).then(([settings, data]) => {
      if (cancelled) return;
      const enabled = Array.isArray(settings?.enabled_roles) ? settings.enabled_roles : [];
      const withTemplate = new Set(
        (data?.templates || [])
          .filter((tpl) => tpl.subject_mode === 'self' && tpl.role)
          .map((tpl) => tpl.role),
      );
      const matched = enabled.filter((role) => withTemplate.has(role));
      setRoles(matched.length ? matched : [...withTemplate]);
      setRolesError(null);
    }).catch(() => {
      if (!cancelled) setRolesError('Could not load reflection roles.');
    });
    return () => { cancelled = true; };
  }, [orgSlug]);

  const role = roles?.includes(roleParam) ? roleParam : (roles?.[0] || '');

  const load = useCallback(async () => {
    if (!role) return;
    setLoading(true);
    try {
      const data = await fetchAdminReflectionsTeam(role, {
        date: dateParam || undefined,
        gradeLevels: gradeParams,
      });
      setPayload(data);
      setError(null);
      const found = (data?.members || [])
        .map((member) => member.grade_level)
        .filter((grade) => grade != null);
      if (found.length) {
        setKnownGrades((prev) => [...new Set([...prev, ...found])].sort((a, b) => a - b));
      }
    } catch (err) {
      const status = err?.response?.status;
      if (status === 403) setError('Admin access required.');
      else if (status === 404) setError('Unknown role.');
      else setError('Failed to load the reflections dashboard.');
    } finally {
      setLoading(false);
    }
    // gradeKey stands in for the grade list so the callback stays stable.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [role, dateParam, gradeKey]);

  useEffect(() => {
    if (role) load();
  }, [load, role]);

  const roleLabel = role ? term(role, { capitalize: true }) : '';
  const gradeOptions = useMemo(() => knownGrades, [knownGrades]);

  const setParam = (mutate) => {
    const next = new URLSearchParams(searchParams);
    mutate(next);
    setSearchParams(next, { replace: true });
  };

  const onDateChange = (e) => {
    const value = e.target.value;
    setParam((next) => {
      if (value) next.set('date', value);
      else next.delete('date');
    });
  };

  const onRoleChange = (e) => {
    const value = e.target.value;
    setKnownGrades([]);
    setParam((next) => {
      next.set('role', value);
      next.delete('grade');
    });
  };

  const toggleGrade = (grade) => {
    setParam((next) => {
      const current = next.getAll('grade').map(Number);
      next.delete('grade');
      const updated = current.includes(grade)
        ? current.filter((g) => g !== grade)
        : [...current, grade];
      updated.forEach((g) => next.append('grade', String(g)));
    });
  };

  if (rolesError) {
    return (
      <p className="text-red-600 dark:text-red-400" data-testid="admin-reflections-error">
        {rolesError}
      </p>
    );
  }

  if (!roles) {
    return (
      <p className="text-gray-500 dark:text-gray-400" data-testid="admin-reflections-loading">
        Loading…
      </p>
    );
  }

  if (roles.length === 0) {
    return (
      <p className="text-sm text-gray-600 dark:text-gray-300" data-testid="admin-reflections-no-roles">
        No self-reflection forms are set up yet. Add one under Forms.
      </p>
    );
  }

  if (loading && !payload) {
    return (
      <p className="text-gray-500 dark:text-gray-400" data-testid="admin-reflections-loading">
        Loading…
      </p>
    );
  }

  if (error || !payload) {
    return (
      <p className="text-red-600 dark:text-red-400" data-testid="admin-reflections-error">
        {error || 'Failed to load the reflections dashboard.'}
      </p>
    );
  }

  const { header, submission_status: submissionStatus, members, template } = payload;
  const exportUrl = exportAdminReflectionsTeamUrl(role, {
    date: dateParam || undefined,
    gradeLevels: gradeParams,
  });

  return (
    <div className="space-y-4" data-testid="reflections-completion">
      <div>
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="flex items-start gap-3 min-w-0">
            <span className="inline-flex items-center justify-center w-11 h-11 rounded-xl shrink-0 bg-indigo-100 text-indigo-700 dark:bg-indigo-900/50 dark:text-indigo-300">
              <GraduationCap size={22} aria-hidden="true" />
            </span>
            <div className="min-w-0">
              <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
                {roleLabel} completion
              </h2>
              <p className="text-sm text-gray-700 dark:text-gray-300 mt-0.5">
                {header.period?.cadence ? `${header.period.cadence} roster` : 'Roster'}
                {header.program?.name ? ` · ${header.program.name}` : ''}
                {` · ${header.member_count} members`}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Link
              to="/admin/reflections/availability"
              className="inline-flex items-center gap-1.5 rounded-lg border border-indigo-300 dark:border-indigo-700 text-sm font-semibold px-3 py-1.5 text-indigo-700 dark:text-indigo-300 hover:bg-indigo-50 dark:hover:bg-indigo-900/30 transition-colors"
              data-testid="admin-reflections-availability-tab"
            >
              <CalendarCheck2 size={15} aria-hidden="true" />
              Availability
            </Link>
            <a
              href={exportUrl}
              className="inline-flex items-center gap-1.5 rounded-lg border border-emerald-300 dark:border-emerald-700 text-sm font-semibold px-3 py-1.5 text-emerald-700 dark:text-emerald-300 hover:bg-emerald-50 dark:hover:bg-emerald-900/30 transition-colors"
              data-testid="admin-reflections-export"
            >
              <Download size={15} aria-hidden="true" />
              Export CSV
            </a>
          </div>
        </div>

        <div className="mt-4 rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 shadow-sm p-3 flex flex-wrap items-center gap-x-4 gap-y-3">
          {roles.length > 1 && (
            <label className="text-sm font-medium text-gray-800 dark:text-gray-200">
              Role{' '}
              <select
                value={role}
                onChange={onRoleChange}
                className="ml-1 rounded-md border-gray-300 dark:border-gray-600 dark:bg-gray-700 text-sm"
                data-testid="admin-reflections-role"
                aria-label="Role"
              >
                {roles.map((option) => (
                  <option key={option} value={option}>
                    {term(option, { capitalize: true })}
                  </option>
                ))}
              </select>
            </label>
          )}
          <label className="text-sm font-medium text-gray-800 dark:text-gray-200">
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
            <span className="text-xs font-medium px-2.5 py-1 rounded-full bg-indigo-50 text-indigo-800 ring-1 ring-inset ring-indigo-600/20 dark:bg-indigo-900/30 dark:text-indigo-200">
              {header.period.start} → {header.period.end} ({header.period.cadence})
            </span>
          )}

          {gradeOptions.length > 0 && (
            <div className="flex flex-wrap items-center gap-2 sm:ml-auto">
              <span className="text-sm font-medium text-gray-800 dark:text-gray-200">Grade:</span>
              {gradeOptions.map((grade) => {
                const active = gradeParams.includes(grade);
                return (
                  <button
                    key={grade}
                    type="button"
                    onClick={() => toggleGrade(grade)}
                    aria-pressed={active}
                    className={`text-xs font-semibold w-8 h-8 rounded-full border transition-colors ${
                      active
                        ? 'bg-violet-600 text-white border-violet-600 hover:bg-violet-700'
                        : 'border-gray-300 dark:border-gray-600 text-gray-800 dark:text-gray-200 hover:border-violet-400 hover:text-violet-700 dark:hover:text-violet-300'
                    }`}
                    data-testid={`admin-reflections-grade-${grade}`}
                  >
                    {grade}
                  </button>
                );
              })}
            </div>
          )}
        </div>
      </div>

      {!template ? (
        <div
          className="rounded-xl border border-dashed border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 p-4 text-sm text-gray-600 dark:text-gray-300"
          data-testid="admin-reflections-no-template"
        >
          No active reflection template is configured for this role yet.
        </div>
      ) : (
        <HomeCard
          title="Submission status"
          subtitle="Day off members are excluded from the completion rate."
          accent="indigo"
          icon={CalendarCheck2}
          data-testid="admin-reflections-summary"
        >
          <CompletionBar submissionStatus={submissionStatus} />
          <div className="mt-4 grid grid-cols-2 sm:grid-cols-4 gap-2">
            {STAT_TILES.map((tile) => (
              <div
                key={tile.key}
                className={`rounded-lg border px-3 py-2 ${tile.className}`}
                data-testid={`admin-reflections-stat-${tile.key}`}
              >
                <p className="text-2xl font-bold leading-tight">{submissionStatus[tile.key]}</p>
                <p className="text-xs font-medium">{tile.label}</p>
              </div>
            ))}
          </div>
        </HomeCard>
      )}

      <section aria-label="Members" data-testid="admin-reflections-members">
        <h3 className="flex items-center gap-2 text-base font-semibold text-gray-900 dark:text-white mb-2">
          <Users size={17} className="text-indigo-600 dark:text-indigo-400" aria-hidden="true" />
          Members
        </h3>
        {members.length === 0 ? (
          <div className="rounded-xl border border-dashed border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 p-4 text-sm text-gray-600 dark:text-gray-300">
            No members match this filter.
          </div>
        ) : (
          <ul className="space-y-2">
            {members.map((m) => {
              const meta = STATUS_META[m.status] ?? STATUS_META.not_submitted;
              return (
                <li
                  key={m.membership_id}
                  className={`rounded-xl border border-l-4 border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 shadow-sm ${meta.rowClassName}`}
                  data-testid={`admin-reflections-member-${m.membership_id}`}
                >
                  <Link
                    to={`/admin/reflections/${role}/members/${m.membership_id}`}
                    className="block px-4 py-3 rounded-r-xl hover:bg-indigo-50/70 dark:hover:bg-indigo-900/20 transition-colors"
                  >
                    <div className="flex items-center justify-between gap-3">
                      <div className="min-w-0 flex items-center gap-3">
                        <span className="inline-flex items-center justify-center h-9 w-9 rounded-full bg-indigo-600 text-xs font-bold text-white shrink-0">
                          {initialsFor(m.person_name)}
                        </span>
                        <p className="font-semibold text-gray-900 dark:text-white truncate">
                          {m.person_name}
                        </p>
                        {m.grade_level != null && (
                          <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-violet-100 text-violet-800 ring-1 ring-inset ring-violet-600/20 dark:bg-violet-900/40 dark:text-violet-200 shrink-0">
                            Grade {m.grade_level}
                          </span>
                        )}
                      </div>
                      <StatusPill status={m.status} />
                    </div>
                  </Link>
                </li>
              );
            })}
          </ul>
        )}
      </section>
    </div>
  );
}
