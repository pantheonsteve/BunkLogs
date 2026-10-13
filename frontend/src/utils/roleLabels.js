/**
 * Role names come from terminology. When two roles share a word
 * (a school that calls counselors faculty, and also has a faculty role),
 * the shared description tells them apart.
 */
export function labeledRoles(roles, term, catalog = []) {
  const description = {};
  for (const entry of catalog || []) description[entry.role] = entry.description || '';
  const base = roles.map((role) => term(role, { capitalize: true }));
  const counts = {};
  for (const label of base) counts[label] = (counts[label] || 0) + 1;
  return roles.map((role, index) => {
    const label = base[index];
    const extra = description[role];
    if (counts[label] > 1 && extra) return `${label} — ${extra}`;
    return label;
  });
}
