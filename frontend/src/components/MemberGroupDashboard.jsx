/**
 * Standard dashboard for every group type that is not a bunk, unit,
 * division, or classroom. Same chrome as those dashboards: date, leaders,
 * people grouped by role, and oversight blocks when the viewer may see them.
 */

import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import AdminGroupLink from './AdminGroupLink';
import GroupTypeIcon from './GroupTypeIcon';
import GroupLeaders from './GroupLeaders';
import ObservationComposer from './observations/ObservationComposer';
import PersonAvatar from './ui/PersonAvatar';
import {
  AvailabilitySection,
  ChallengesSection,
  CompletionSection,
} from './ClassroomDashboard';
import { useTerm } from '../context/OrgBrandingContext';
import { groupTypeLabel } from '../pages/admin/groups/groupTypes';
import { DEFAULT_TERMS } from '../utils/terminology';
import { observationThreadLink, profileLink } from '../utils/dashboardLinks';

function personName(person) {
  return `${person.preferred_name || person.first_name} ${person.last_name}`.trim();
}

function typeTitle(term, groupType) {
  if (groupType && DEFAULT_TERMS[groupType]) {
    return term(groupType, { capitalize: true });
  }
  return groupTypeLabel(groupType);
}

function roleHeading(term, role) {
  if (role && DEFAULT_TERMS[role]) {
    return term(role, { plural: true, capitalize: true });
  }
  if (!role) return 'Members';
  return role
    .split('_')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}

function peopleByRole({ subjects, authors, roster }) {
  const authorRoleById = new Map(
    (roster || [])
      .filter((row) => row.role_in_group === 'author')
      .map((row) => [row.person_id, row.membership_role]),
  );
  const byId = new Map();
  for (const subject of subjects) {
    byId.set(subject.id, {
      id: subject.id,
      name: personName(subject),
      role: subject.membership_role || '',
      isSubject: true,
    });
  }
  for (const author of authors) {
    if (byId.has(author.id)) continue;
    byId.set(author.id, {
      id: author.id,
      name: author.name,
      role: authorRoleById.get(author.id) || '',
      isSubject: false,
    });
  }
  const groups = new Map();
  for (const person of byId.values()) {
    const key = person.role || '';
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(person);
  }
  return [...groups.entries()]
    .map(([role, people]) => ({
      role,
      people: people.sort((a, b) => a.name.localeCompare(b.name)),
    }))
    .sort((a, b) => {
      const aSubject = a.people.some((person) => person.isSubject);
      const bSubject = b.people.some((person) => person.isSubject);
      if (aSubject !== bSubject) return aSubject ? -1 : 1;
      return a.role.localeCompare(b.role);
    });
}

export default function MemberGroupDashboard({
  data, selectedDate, onDateChange, backTo = '/dashboards',
}) {
  const term = useTerm();
  const group = data?.header?.group || {};
  const subjects = data?.subjects || [];
  const authors = data?.authors || [];
  const seesOperations = Boolean(data?.viewer?.sees_operations);
  const sections = peopleByRole({ subjects, authors, roster: data?.roster });
  const navigate = useNavigate();
  const [composeSubject, setComposeSubject] = useState(null);
  const returnTo = group.id ? `/dashboards/group/${group.id}` : null;
  const title = typeTitle(term, group.group_type);
  const headcount = sections.reduce((sum, section) => sum + section.people.length, 0);

  return (
    <div
      data-testid="group-dashboard-member"
      className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-[96rem] mx-auto space-y-4"
    >
      <header className="space-y-2">
        <div className="flex items-center justify-between gap-3">
          <Link
            to={backTo}
            className="text-sm text-blue-700 dark:text-blue-300 hover:underline"
          >
            ← Back
          </Link>
          <AdminGroupLink data={data} />
        </div>
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <div className="flex items-center gap-2.5">
              <GroupTypeIcon type={group.group_type} />
              <h1 className="text-2xl font-semibold text-gray-900 dark:text-white">
                {group.name || title}
              </h1>
            </div>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              {title} dashboard · {headcount} {headcount === 1 ? 'person' : 'people'}
            </p>
          </div>
          <label className="text-sm text-gray-700 dark:text-gray-200">
            Date{' '}
            <input
              type="date"
              value={selectedDate || ''}
              onChange={(e) => onDateChange?.(e.target.value)}
              className="ml-2 rounded border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 px-2 py-1"
            />
          </label>
        </div>
        <GroupLeaders roster={data?.roster} className="pt-2" />
      </header>

      {seesOperations ? (
        <>
          {data?.challenges && <ChallengesSection challenges={data.challenges} />}
          <CompletionSection
            completion={data.completion}
            returnTo={returnTo || undefined}
            emptyLabel="No one is on this roster yet."
          />
          <AvailabilitySection
            availability={data.availability}
            emptyLabel="No one is on this roster yet."
            nameHeading="Name"
          />
        </>
      ) : (
        <section
          data-testid="member-operations-note"
          className="rounded-xl border border-amber-200 dark:border-amber-900 bg-amber-50 dark:bg-amber-900/30 px-4 py-3 text-sm text-amber-900 dark:text-amber-100"
        >
          {`Reflection completion and availability are shown to people who oversee this ${term('group')}.`}
        </section>
      )}

      {sections.length === 0 ? (
        <section className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 px-4 py-3 shadow-sm">
          <p className="text-sm text-gray-500 dark:text-gray-400">
            {`No one is in this ${term('group')} yet.`}
          </p>
        </section>
      ) : sections.map((section) => (
        <section
          key={section.role || 'members'}
          data-testid={`member-role-${section.role || 'unset'}`}
          className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 px-4 py-3 shadow-sm"
        >
          <h2 className="text-base font-semibold text-gray-900 dark:text-white mb-2">
            {roleHeading(term, section.role)}{' '}
            <span className="ml-2 text-xs text-gray-500 dark:text-gray-400">
              ({section.people.length})
            </span>
          </h2>
          <ul className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-1 text-sm">
            {section.people.map((person) => (
              <li
                key={person.id}
                data-testid={`member-person-${person.id}`}
                className="flex items-center justify-between gap-2 px-2 py-1 rounded bg-gray-50 dark:bg-gray-800"
              >
                <span className="flex items-center gap-2 min-w-0">
                  <PersonAvatar id={person.id} name={person.name} />
                  <Link
                    to={profileLink(person.id, { groupId: group.id, date: selectedDate })}
                    className="truncate text-blue-700 dark:text-blue-300 hover:underline"
                  >
                    {person.name}
                  </Link>
                </span>
                {person.isSubject && (
                  <button
                    type="button"
                    onClick={() => setComposeSubject({ id: person.id, full_name: person.name })}
                    className="shrink-0 text-xs font-medium text-indigo-700 dark:text-indigo-300 hover:underline"
                    data-testid={`member-observe-${person.id}`}
                  >
                    Add observation
                  </button>
                )}
              </li>
            ))}
          </ul>
        </section>
      ))}

      {composeSubject && (
        <ObservationComposer
          initialSubjects={[composeSubject]}
          onClose={() => setComposeSubject(null)}
          onSent={(created) => {
            setComposeSubject(null);
            if (created?.id) navigate(observationThreadLink(created.id, returnTo));
          }}
        />
      )}
    </div>
  );
}
