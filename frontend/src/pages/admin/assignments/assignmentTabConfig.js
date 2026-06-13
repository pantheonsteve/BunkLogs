export const SUB_TABS = [
  {
    key: 'counselor_bunk',
    label: 'Counselor → Bunk',
    subtitle: 'Counselors as bunk authors',
    kind: 'group_membership',
    groupTypes: ['bunk'],
    eligibleRoles: ['counselor', 'junior_counselor', 'general_counselor', 'specialist'],
    roleInGroup: 'author',
    leftLabel: 'Bunks',
  },
  {
    key: 'staff_team',
    label: 'Staff → Team',
    subtitle: 'Staff authors on team groups',
    kind: 'group_membership',
    groupTypes: ['team'],
    eligibleRoles: [
      'kitchen_staff', 'maintenance', 'housekeeping', 'health_center',
      'administrative_staff', 'specialist',
    ],
    roleInGroup: 'author',
    leftLabel: 'Teams',
  },
  {
    key: 'uh_unit',
    label: 'Unit Head → Unit',
    subtitle: 'Unit heads on units; counselors in child bunks are supervised by proxy',
    kind: 'group_membership',
    groupTypes: ['unit'],
    eligibleRoles: ['unit_head'],
    roleInGroup: 'author',
    leftLabel: 'Units',
  },
  {
    key: 'cc_caseload',
    label: 'Camper Care → Caseload',
    subtitle: 'Caseload bunk supervision',
    kind: 'supervision',
    groupTypes: ['bunk'],
    supervisorRoles: ['camper_care'],
    leftLabel: 'Caseload bunks',
  },
  {
    key: 'lt_team',
    label: 'Leadership → Team',
    subtitle: 'LT supervision by program role',
    kind: 'supervision',
    supervisorRoles: ['leadership_team'],
    targetRoleOptions: [
      'counselor', 'unit_head', 'kitchen_staff', 'maintenance', 'camper_care',
    ],
    leftLabel: 'Program roles',
  },
  {
    key: 'camper_bunk',
    label: 'Camper → Bunk / Student → Grade',
    subtitle: 'Subjects placed in bunks or classrooms',
    kind: 'group_membership',
    groupTypes: ['bunk', 'classroom'],
    eligibleRoles: ['camper', 'student'],
    roleInGroup: 'subject',
    leftLabel: 'Groups',
  },
];

export function tabConfigFor(key) {
  return SUB_TABS.find((t) => t.key === key) ?? SUB_TABS[0];
}
