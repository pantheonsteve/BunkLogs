/**
 * Leaders strip for the top of a group dashboard.
 *
 * Reads the generic `roster` array from `GET /api/v1/dashboards/group/<id>/`
 * and shows the group's authors (counselors, faculty, madrichim, unit heads)
 * as avatar chips with their program role. Supervisory roles sort first.
 */

import { initialsFor } from './ui/InitialsAvatar';

const ROLE_STYLES = {
  faculty: {
    avatar: 'bg-indigo-100 text-indigo-800 dark:bg-indigo-900/50 dark:text-indigo-200',
    label: 'text-indigo-700 dark:text-indigo-300',
  },
  unit_head: {
    avatar: 'bg-amber-100 text-amber-800 dark:bg-amber-900/50 dark:text-amber-200',
    label: 'text-amber-700 dark:text-amber-300',
  },
  counselor: {
    avatar: 'bg-sky-100 text-sky-800 dark:bg-sky-900/50 dark:text-sky-200',
    label: 'text-sky-700 dark:text-sky-300',
  },
  madrich: {
    avatar: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/50 dark:text-emerald-200',
    label: 'text-emerald-700 dark:text-emerald-300',
  },
};

const DEFAULT_STYLE = {
  avatar: 'bg-violet-100 text-violet-800 dark:bg-violet-900/50 dark:text-violet-200',
  label: 'text-gray-600 dark:text-gray-300',
};

const ROLE_ORDER = ['faculty', 'unit_head', 'leadership_team', 'camper_care', 'counselor', 'madrich'];

function roleRank(role) {
  const i = ROLE_ORDER.indexOf(role);
  return i === -1 ? ROLE_ORDER.length : i;
}

export function prettyRole(role) {
  if (!role) return 'Leader';
  return role
    .split('_')
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(' ');
}

export default function GroupLeaders({ roster, className = '' }) {
  const leaders = (Array.isArray(roster) ? roster : [])
    .filter((m) => m.role_in_group === 'author')
    .sort((a, b) => (
      roleRank(a.membership_role) - roleRank(b.membership_role)
      || (a.name || '').localeCompare(b.name || '')
    ));
  if (leaders.length === 0) return null;

  return (
    <section
      data-testid="group-leaders"
      aria-label="Group leaders"
      className={className}
    >
      <p className="text-[11px] font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400 mb-2">
        {leaders.length === 1 ? 'Leader' : `Leaders · ${leaders.length}`}
      </p>
      <ul className="flex flex-wrap gap-2">
        {leaders.map((m) => {
          const style = ROLE_STYLES[m.membership_role] || DEFAULT_STYLE;
          return (
            <li
              key={m.person_id}
              data-testid={`group-leader-${m.person_id}`}
              className="flex items-center gap-2.5 rounded-full border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 pl-1 pr-4 py-1 shadow-sm"
            >
              <span
                aria-hidden
                className={`inline-flex items-center justify-center w-8 h-8 rounded-full text-xs font-bold shrink-0 ${style.avatar}`}
              >
                {initialsFor(m.name)}
              </span>
              <span className="flex flex-col leading-tight min-w-0">
                <span className="text-sm font-semibold text-gray-900 dark:text-white truncate">
                  {m.name}
                </span>
                <span className={`text-[11px] font-medium ${style.label}`}>
                  {prettyRole(m.membership_role)}
                </span>
              </span>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
