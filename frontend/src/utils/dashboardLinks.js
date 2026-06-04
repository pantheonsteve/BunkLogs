/**
 * Deep links between the unified group dashboard and per-person profiles.
 * `group` + `date` query params on `/profile/:id` enable a back link to
 * `/dashboards/group/:groupId`.
 */

export function profileLink(personId, { groupId, date } = {}) {
  const qs = new URLSearchParams();
  if (groupId != null && groupId !== '') qs.set('group', String(groupId));
  if (date) qs.set('date', date);
  const q = qs.toString();
  return q ? `/profile/${personId}?${q}` : `/profile/${personId}`;
}

export function groupDashboardLink(groupId, { date } = {}) {
  if (groupId == null || groupId === '') return null;
  return date
    ? `/dashboards/group/${groupId}?date=${encodeURIComponent(date)}`
    : `/dashboards/group/${groupId}`;
}

/** Resolve group metadata for the profile back link from URL + payload. */
export function resolveProfileBackGroup(groupIdParam, assignmentGroups = []) {
  const groups = assignmentGroups ?? [];
  if (groupIdParam) {
    const match = groups.find((g) => String(g.id) === String(groupIdParam));
    if (match) return match;
    return { id: groupIdParam, name: null, group_type: 'bunk' };
  }
  const bunks = groups.filter((g) => g.group_type === 'bunk');
  if (bunks.length === 1) return bunks[0];
  return null;
}

export function profileBackLabel(group) {
  if (!group) return null;
  if (group.name) return `← Back to ${group.name}`;
  if (group.group_type === 'bunk') return '← Back to bunk dashboard';
  return '← Back to group dashboard';
}
