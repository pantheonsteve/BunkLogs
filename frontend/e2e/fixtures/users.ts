/**
 * RBAC test users — mirror of the matrix seeded by
 * backend/bunk_logs/core/management/commands/seed_rbac_test_users.py.
 *
 * Capabilities are documented in docs/membership-role-vs-capability.md.
 * Run `make seed-rbac` before executing the e2e suite.
 */

export type Capability =
  | 'participant'
  | 'supervisor'
  | 'program_lead'
  | 'domain_specialist'
  | 'admin'
  | null;

export type UserKey =
  | 'counselor'
  | 'kitchen'
  | 'unit_head'
  | 'leadership'
  | 'camper_care'
  | 'health_center'
  | 'admin'
  | 'superuser'
  | 'no_membership'
  | 'tbe_admin';

export interface RbacUser {
  key: UserKey;
  email: string;
  password: string;
  /** Membership.capability (null when there is no Membership). */
  capability: Capability;
  /** Membership.role (null when there is no Membership). */
  membershipRole: string | null;
  /** Legacy User.role string (drives the existing sidebar). */
  userRole: string;
  /** Whether this user has a Person row in the clc org. */
  hasPersonInClc: boolean;
  /** Notes for the human-readable matrix in docs/rbac-test-plan.md. */
  notes: string;
}

export const SHARED_PASSWORD = 'rbacpass123';

export const RBAC_USERS: Record<UserKey, RbacUser> = {
  counselor: {
    key: 'counselor',
    email: 'rbac-counselor@example.test',
    password: SHARED_PASSWORD,
    capability: 'participant',
    membershipRole: 'counselor',
    userRole: 'Counselor',
    hasPersonInClc: true,
    notes: 'self-reflection + author on RBAC bunk',
  },
  kitchen: {
    key: 'kitchen',
    email: 'rbac-kitchen@example.test',
    password: SHARED_PASSWORD,
    capability: 'participant',
    membershipRole: 'kitchen_staff',
    userRole: 'Counselor',
    hasPersonInClc: true,
    notes: 'bilingual /reflect?language=es',
  },
  unit_head: {
    key: 'unit_head',
    email: 'rbac-unit-head@example.test',
    password: SHARED_PASSWORD,
    capability: 'supervisor',
    membershipRole: 'unit_head',
    userRole: 'Unit Head',
    hasPersonInClc: true,
    notes: 'descendant author of bunk via parent unit',
  },
  leadership: {
    key: 'leadership',
    email: 'rbac-leadership@example.test',
    password: SHARED_PASSWORD,
    capability: 'program_lead',
    membershipRole: 'leadership_team',
    userRole: 'Leadership',
    hasPersonInClc: true,
    notes: '/team/dashboard, leadership visibility',
  },
  camper_care: {
    key: 'camper_care',
    email: 'rbac-camper-care@example.test',
    password: SHARED_PASSWORD,
    capability: 'supervisor',
    membershipRole: 'camper_care',
    userRole: 'Camper Care',
    hasPersonInClc: true,
    notes: '/wellness/dashboard route gate + unit-scoped reflection feed (3.21)',
  },
  health_center: {
    key: 'health_center',
    email: 'rbac-health-center@example.test',
    password: SHARED_PASSWORD,
    capability: 'domain_specialist',
    membershipRole: 'health_center',
    userRole: 'Camper Care',
    hasPersonInClc: true,
    notes: 'second wellness specialist',
  },
  admin: {
    key: 'admin',
    email: 'rbac-admin@example.test',
    password: SHARED_PASSWORD,
    capability: 'admin',
    membershipRole: 'admin',
    userRole: 'Admin',
    hasPersonInClc: true,
    notes: 'admin via Membership only (is_staff=False)',
  },
  superuser: {
    key: 'superuser',
    email: 'rbac-superuser@example.test',
    password: SHARED_PASSWORD,
    capability: null,
    membershipRole: null,
    userRole: 'Admin',
    hasPersonInClc: false,
    notes: 'Django superuser, no Person/Membership',
  },
  no_membership: {
    key: 'no_membership',
    email: 'rbac-no-membership@example.test',
    password: SHARED_PASSWORD,
    capability: null,
    membershipRole: null,
    userRole: '',
    hasPersonInClc: false,
    notes: 'logged in but no Person profile',
  },
  tbe_admin: {
    key: 'tbe_admin',
    email: 'rbac-tbe-admin@example.test',
    password: SHARED_PASSWORD,
    capability: 'admin',
    membershipRole: 'admin',
    userRole: 'Admin',
    hasPersonInClc: false,
    notes:
      'admin in tbe-test org; the SPA always sends X-Organization-Slug=clc, so cross-tenant ' +
      'isolation manifests as empty/forbidden responses',
  },
};

export const userByKey = (k: UserKey): RbacUser => RBAC_USERS[k];
