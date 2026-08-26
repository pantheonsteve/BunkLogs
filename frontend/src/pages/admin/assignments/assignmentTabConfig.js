/**
 * Sub-tab definitions for the admin Assignments screen.
 *
 * Behavioural fields (`groupTypes`, `eligibleRoles`, ...) hold canonical slugs
 * and never vary per tenant. User-facing copy lives in `copy(t)`, which is
 * resolved against the org's vocabulary by `localizeSubTab` — a school renders
 * "Madrich → Class" off the same `counselor` / `bunk` keys the camp does.
 */
export const SUB_TABS = [
  {
    key: 'counselor_bunk',
    kind: 'group_membership',
    // A school's faculty-on-classroom is the same relationship as a camp's
    // counselor-on-bunk: whoever authors reflections about the group.
    groupTypes: ['bunk', 'classroom'],
    eligibleRoles: [
      'counselor', 'junior_counselor', 'general_counselor', 'specialist', 'faculty',
    ],
    roleInGroup: 'author',
    copy: (t) => ({
      label: `${t('counselor', { capitalize: true })} → ${t('bunk', { capitalize: true })}`,
      subtitle: `${t('counselor', { plural: true, capitalize: true })} as ${t('bunk')} authors`,
      leftLabel: t('bunk', { plural: true, capitalize: true }),
      leftLabelSingular: t('bunk'),
    }),
  },
  {
    key: 'staff_team',
    kind: 'group_membership',
    groupTypes: ['team'],
    eligibleRoles: [
      'kitchen_staff', 'maintenance', 'housekeeping', 'health_center',
      'administrative_staff', 'specialist',
    ],
    roleInGroup: 'author',
    copy: (t) => ({
      label: `${t('staff', { capitalize: true })} → ${t('team', { capitalize: true })}`,
      subtitle: `${t('staff', { capitalize: true })} authors on ${t('team')} groups`,
      leftLabel: t('team', { plural: true, capitalize: true }),
      leftLabelSingular: t('team'),
    }),
  },
  {
    key: 'uh_unit',
    kind: 'group_membership',
    groupTypes: ['unit'],
    eligibleRoles: ['unit_head'],
    roleInGroup: 'author',
    copy: (t) => ({
      label: `${t('unit_head', { capitalize: true })} → ${t('unit', { capitalize: true })}`,
      subtitle: `${t('unit_head', { plural: true, capitalize: true })} on ${t('unit', { plural: true })}; ${t('counselor', { plural: true })} in child ${t('bunk', { plural: true })} are supervised by proxy`,
      leftLabel: t('unit', { plural: true, capitalize: true }),
      leftLabelSingular: t('unit'),
    }),
  },
  {
    key: 'cc_caseload',
    kind: 'supervision',
    groupTypes: ['bunk'],
    supervisorRoles: ['camper_care'],
    copy: (t) => ({
      label: `${t('camper_care', { capitalize: true })} → ${t('caseload', { capitalize: true })}`,
      subtitle: `${t('caseload', { capitalize: true })} ${t('bunk')} supervision`,
      leftLabel: `${t('caseload', { capitalize: true })} ${t('bunk', { plural: true })}`,
      leftLabelSingular: `${t('caseload')} ${t('bunk')}`,
    }),
  },
  {
    key: 'lt_team',
    kind: 'supervision',
    supervisorRoles: ['leadership_team'],
    targetRoleOptions: [
      'counselor', 'unit_head', 'kitchen_staff', 'maintenance', 'camper_care',
    ],
    copy: (t) => ({
      label: `${t('leadership', { capitalize: true })} → ${t('team', { capitalize: true })}`,
      subtitle: `${t('leadership', { capitalize: true })} supervision by program role`,
      leftLabel: 'Program roles',
      leftLabelSingular: 'program role',
    }),
  },
  {
    key: 'camper_bunk',
    kind: 'group_membership',
    groupTypes: ['bunk', 'classroom'],
    // Madrichim are placed in a classroom as subjects, the way campers are
    // placed in a bunk -- they are also authors of their own self-reflections.
    eligibleRoles: ['camper', 'student', 'madrich'],
    roleInGroup: 'subject',
    copy: (t) => ({
      label: `${t('camper', { capitalize: true })} → ${t('bunk', { capitalize: true })}`,
      subtitle: `${t('camper', { plural: true, capitalize: true })} placed in ${t('bunk', { plural: true })}`,
      leftLabel: t('bunk', { plural: true, capitalize: true }),
      leftLabelSingular: t('bunk'),
    }),
  },
  {
    key: 'supervisor_status',
    kind: 'supervisor_status',
    copy: () => ({
      label: 'Supervisor status',
      subtitle: 'Who a person supervises + reflection visibility',
      leftLabel: 'People',
      leftLabelSingular: 'person',
    }),
  },
];

/** Resolve one tab's copy against the tenant's vocabulary. */
export function localizeSubTab(tab, term) {
  return { ...tab, ...tab.copy(term) };
}

function tabMatchesOrg(tab, roles, groupTypes) {
  // The inspector works off people alone, so it applies to every org.
  if (tab.kind === 'supervisor_status') return true;
  const tabRoles = tab.eligibleRoles || tab.supervisorRoles;
  if (tabRoles && !tabRoles.some((r) => roles.has(r))) return false;
  if (tab.groupTypes && !tab.groupTypes.some((g) => groupTypes.has(g))) return false;
  return true;
}

/**
 * Narrow the sub-tabs to the relationship shapes this org actually has.
 *
 * A religious school has no bunks or unit heads, so those tabs can only ever
 * render an empty three-pane screen. Pass `null` to opt out of filtering.
 */
export function visibleSubTabs(facets) {
  if (!facets) return SUB_TABS;
  const roles = new Set(facets.roles || []);
  const groupTypes = new Set(facets.group_types || []);
  const matched = SUB_TABS.filter((t) => tabMatchesOrg(t, roles, groupTypes));
  // An org part-way through onboarding matches nothing yet; hiding every tab
  // would leave no way to make the first assignment.
  return matched.some((t) => t.kind !== 'supervisor_status') ? matched : SUB_TABS;
}
