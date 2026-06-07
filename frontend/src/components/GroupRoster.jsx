/**
 * Full member roster for a group dashboard.
 *
 * Renders the `roster` array from `GET /api/v1/dashboards/group/<id>/`
 * (authors first, then subjects). Each member shows their program role
 * (membership_role) and how they participate in the group (role_in_group).
 */

import { useState } from 'react';
import { ChevronDown } from 'lucide-react';

const ROLE_IN_GROUP_LABELS = {
  author: 'Author',
  subject: 'Member',
};

function prettyRole(role) {
  if (!role) return '\u2014';
  return role
    .split('_')
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(' ');
}

function RosterTable({ members }) {
  return (
    <div className="overflow-x-auto">
      <table className="min-w-full text-sm">
        <thead>
          <tr className="text-left text-xs uppercase text-gray-500 dark:text-gray-400">
            <th className="py-1.5 pr-4 font-medium">Name</th>
            <th className="py-1.5 pr-4 font-medium">Role</th>
            <th className="py-1.5 font-medium">In group as</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100 dark:divide-gray-800">
          {members.map((m) => (
            <tr key={`${m.person_id}-${m.role_in_group}`}>
              <td className="py-1.5 pr-4 text-gray-900 dark:text-gray-100 whitespace-nowrap">
                {m.name}
              </td>
              <td className="py-1.5 pr-4 text-gray-700 dark:text-gray-300 whitespace-nowrap">
                {prettyRole(m.membership_role)}
              </td>
              <td className="py-1.5 whitespace-nowrap">
                <span className="inline-flex items-center rounded-full bg-gray-100 dark:bg-gray-800 px-2 py-0.5 text-xs font-medium text-gray-700 dark:text-gray-300">
                  {ROLE_IN_GROUP_LABELS[m.role_in_group] || prettyRole(m.role_in_group)}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function RosterBody({ roster, compact }) {
  const members = Array.isArray(roster) ? roster : [];
  if (members.length === 0) {
    return (
      <p className="text-sm italic text-gray-500 dark:text-gray-400">
        No active members in this group.
      </p>
    );
  }

  if (compact) {
    const authors = members.filter((m) => m.role_in_group === 'author');
    const subjects = members.filter((m) => m.role_in_group !== 'author');
    return (
      <div className="space-y-3 text-sm">
        {authors.length > 0 && (
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400 mb-1">
              Authors ({authors.length})
            </p>
            <ul className="space-y-1">
              {authors.map((m) => (
                <li key={`${m.person_id}-author`} className="flex items-center justify-between gap-2">
                  <span className="text-gray-900 dark:text-gray-100">{m.name}</span>
                  <span className="text-xs text-gray-500">{prettyRole(m.membership_role)}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
        {subjects.length > 0 && (
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400 mb-1">
              Members ({subjects.length})
            </p>
            <ul className="space-y-1">
              {subjects.map((m) => (
                <li key={`${m.person_id}-subject`} className="flex items-center justify-between gap-2">
                  <span className="text-gray-900 dark:text-gray-100">{m.name}</span>
                  <span className="text-xs text-gray-500">{prettyRole(m.membership_role)}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    );
  }

  return <RosterTable members={members} />;
}

export default function GroupRoster({
  roster,
  collapsible = false,
  defaultExpanded = true,
  compact = false,
  className = '',
}) {
  const members = Array.isArray(roster) ? roster : [];
  const [expanded, setExpanded] = useState(defaultExpanded);

  const sectionClass = [
    'rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900/40',
    compact ? 'px-3 py-2' : 'px-4 py-4 mb-6',
    className,
  ].filter(Boolean).join(' ');

  if (collapsible) {
    return (
      <section data-testid="group-roster" className={sectionClass}>
        <button
          type="button"
          onClick={() => setExpanded((v) => !v)}
          aria-expanded={expanded}
          data-testid="group-roster-toggle"
          className="w-full flex items-center justify-between gap-2 text-left"
        >
          <h2 className="text-sm font-semibold uppercase tracking-wide text-gray-600 dark:text-gray-300">
            Roster ({members.length})
          </h2>
          <ChevronDown
            className={`h-4 w-4 text-gray-500 transition-transform ${expanded ? 'rotate-180' : ''}`}
            aria-hidden
          />
        </button>
        {expanded && (
          <div className="mt-3">
            <RosterBody roster={roster} compact={compact} />
          </div>
        )}
      </section>
    );
  }

  return (
    <section data-testid="group-roster" className={sectionClass}>
      <h2 className="text-sm font-semibold uppercase tracking-wide text-gray-600 dark:text-gray-300 mb-3">
        Roster ({members.length})
      </h2>
      <RosterBody roster={roster} compact={compact} />
    </section>
  );
}
