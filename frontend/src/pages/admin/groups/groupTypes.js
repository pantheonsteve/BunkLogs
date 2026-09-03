/**
 * Group-type vocabulary and ordering, shared by the list and detail pages.
 *
 * The order is developmental (division holds units hold bunks), not
 * alphabetical, because that's how a director thinks about the hierarchy.
 */
export const GROUP_TYPE_LABELS = {
  bunk: 'Bunk',
  classroom: 'Classroom',
  caseload: 'Caseload',
  unit: 'Unit',
  division: 'Division',
  cohort: 'Cohort',
  team: 'Team',
  specialty: 'Specialty / Activity',
  custom: 'Custom',
};

export const GROUP_TYPE_ORDER = [
  'division', 'unit', 'bunk', 'classroom', 'caseload', 'cohort', 'team', 'specialty', 'custom',
];

/** Types that hold subjects; the rest are staff-only by design. */
export const SUBJECT_BEARING_TYPES = new Set(['bunk', 'classroom', 'caseload', 'cohort']);

/**
 * Types a camper-care caseload can point at.
 *
 * A caseload row targets any AssignmentGroup and the resolver expands a
 * unit or division to its child bunks, so the tab is worth showing on
 * containers too — not just on the leaf group.
 */
export const SUPERVISABLE_TYPES = new Set([
  'bunk', 'classroom', 'caseload', 'unit', 'division',
]);

export function groupTypeLabel(type) {
  return GROUP_TYPE_LABELS[type] || type;
}

/**
 * What the group's authors are called.
 *
 * A classroom's authors are its faculty/counselors; a team's are its staff.
 * Both resolve through the org's vocabulary, so a school reads "Faculty".
 */
export function authorTermKey(groupType) {
  return groupType === 'bunk' || groupType === 'classroom' ? 'counselor' : 'staff';
}

export function developmentalSort(groups) {
  return [...groups].sort((a, b) => {
    const ai = GROUP_TYPE_ORDER.indexOf(a.group_type);
    const bi = GROUP_TYPE_ORDER.indexOf(b.group_type);
    if (ai !== bi) return (ai < 0 ? 99 : ai) - (bi < 0 ? 99 : bi);
    if (a.display_order !== b.display_order) {
      return (a.display_order ?? 0) - (b.display_order ?? 0);
    }
    return (a.name || '').localeCompare(b.name || '');
  });
}
