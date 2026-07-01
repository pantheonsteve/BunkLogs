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

/**
 * Append/replace a `date` query param on an internal app path so the
 * selected day carries across navigation. Preserves any existing query
 * params and hash. No-op when `date` is falsy.
 */
export function withDateParam(path, date) {
  if (!path || !date) return path;
  const [beforeHash, hash] = path.split('#');
  const [base, query = ''] = beforeHash.split('?');
  const params = new URLSearchParams(query);
  params.set('date', date);
  const rebuilt = `${base}?${params.toString()}`;
  return hash ? `${rebuilt}#${hash}` : rebuilt;
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

/** Allow only same-origin app paths for observation ``from`` return links. */
export function safeInternalPath(path) {
  if (!path || typeof path !== 'string') return null;
  if (!path.startsWith('/') || path.startsWith('//')) return null;
  return path;
}

/** Link to an observation thread, optionally preserving a return URL. */
export function observationThreadLink(observationId, returnTo, { contextLabel } = {}) {
  const base = `/observations/${observationId}`;
  const back = safeInternalPath(returnTo);
  if (!back) return base;
  const params = new URLSearchParams();
  params.set('from', back);
  if (contextLabel) params.set('from_label', contextLabel);
  return `${base}?${params.toString()}`;
}

/** Label for the contextual back link on an observation thread (not the inbox). */
export function observationContextBackLabel(returnTo, fromLabel) {
  if (fromLabel) return `Back to ${fromLabel}`;
  const path = safeInternalPath(returnTo);
  if (path?.startsWith('/profile/')) return 'Back to profile';
  if (path?.startsWith('/dashboards/group/')) return 'Back to group dashboard';
  return 'Back';
}

/** @deprecated Use observationContextBackLabel for contextual nav. */
export function observationBackLabel(returnTo) {
  return observationContextBackLabel(returnTo);
}

/** Profile URL for a subject chip on an observation thread. */
export function subjectProfileHref(subjectId, { observedDate, returnTo, canViewProfile } = {}) {
  const from = safeInternalPath(returnTo);
  const mayView = canViewProfile || (from?.startsWith(`/profile/${subjectId}`) ?? false);
  if (!mayView) return null;
  if (from?.startsWith(`/profile/${subjectId}`)) return from;
  return profileLink(subjectId, observedDate ? { date: observedDate } : {});
}
