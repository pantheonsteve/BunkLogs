/** DRF list endpoints return either a bare array or ``{ results: [] }``. */
export function parseListPayload(data) {
  if (Array.isArray(data?.results)) return data.results;
  if (Array.isArray(data)) return data;
  return [];
}

/** Membership list rows expose ``person`` as a numeric id, not a nested object. */
export function personFromMembership(membership) {
  if (!membership) return null;
  const raw = membership.person;
  const personId = typeof raw === 'object' && raw !== null ? raw.id : raw;
  if (!personId) return null;

  if (typeof raw === 'object' && raw !== null) {
    return {
      id: personId,
      first_name: raw.first_name || '',
      last_name: raw.last_name || '',
      full_name: `${raw.first_name || ''} ${raw.last_name || ''}`.trim() || membership.person_name || '',
    };
  }

  const fullName = (membership.person_name || '').trim();
  const space = fullName.indexOf(' ');
  const first_name = space > 0 ? fullName.slice(0, space) : fullName;
  const last_name = space > 0 ? fullName.slice(space + 1) : '';
  return {
    id: personId,
    first_name,
    last_name,
    full_name: fullName,
  };
}

/** Merge membership rows into a unique person map keyed by person id. */
export function mergeMembershipPeople(memberships, role) {
  const byPerson = new Map();
  for (const m of memberships) {
    const person = personFromMembership(m);
    if (!person) continue;
    const existing = byPerson.get(person.id) || {
      ...person,
      membershipId: m.id,
      roles: [],
    };
    if (role && !existing.roles.includes(role)) existing.roles.push(role);
    if (!existing.membershipId && m.id) existing.membershipId = m.id;
    byPerson.set(person.id, existing);
  }
  return byPerson;
}
