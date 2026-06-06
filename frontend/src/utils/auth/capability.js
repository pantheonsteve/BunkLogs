/**
 * Frontend capability helper (3.32).
 *
 * The backend RBAC story moved to `Membership.capability` with five
 * tiers (participant / supervisor / program_lead / domain_specialist
 * / admin), but the frontend has been gating nav on legacy
 * `User.role` strings (Title Case 'Admin' / 'Counselor' / ...). This
 * helper bridges the two so callers can write
 *
 *   if (hasCapability(user, 'supervisor')) { ... }
 *
 * today and we can swap the underlying source from `user.role` to a
 * real `Membership.capability` field in one place when the
 * `/api/v1/memberships/me/` payload lands on the auth context.
 *
 * Mirror of backend `bunk_logs.core.models.ROLE_TO_CAPABILITY`
 * (core/models.py:28-45). Kept in sync by manual review when either
 * side changes; the unit tests assert coverage of every legacy
 * User.role value enumerated in `users.models.User.ROLE_CHOICES`.
 *
 * Known limitation: today's `user.role` is Title Case and cannot
 * distinguish `health_center` from `camper_care` (both surface as
 * 'Camper Care'). That means a health_center membership renders the
 * supervisor-tier sidebar instead of the domain_specialist tier --
 * matches current behavior, fixed when memberships flow into
 * useAuth().
 */

import { useAuth } from '../../auth/AuthContext';
import isSuperAdmin from './isSuperAdmin';

/**
 * Capability tiers in order of increasing privilege. Higher tiers
 * implicitly include the entries to their left for nav purposes
 * (e.g. an admin sees supervisor sections, a program_lead sees
 * participant sections).
 */
export const CAPABILITIES = Object.freeze([
  'participant',
  'supervisor',
  'program_lead',
  'domain_specialist',
  'admin',
]);

const PARTICIPANT_RANK = CAPABILITIES.indexOf('participant');
const SUPERVISOR_RANK = CAPABILITIES.indexOf('supervisor');
const PROGRAM_LEAD_RANK = CAPABILITIES.indexOf('program_lead');
const DOMAIN_SPECIALIST_RANK = CAPABILITIES.indexOf('domain_specialist');
const ADMIN_RANK = CAPABILITIES.indexOf('admin');

/**
 * Map of legacy `User.role` (Title Case strings from
 * users.models.User.ROLE_CHOICES) to capability. The empty string and
 * missing role both surface as null.
 */
const LEGACY_USER_ROLE_TO_CAPABILITY = Object.freeze({
  Counselor: 'participant',
  'Kitchen Staff': 'participant',
  'Unit Head': 'supervisor',
  'Camper Care': 'supervisor',
  Leadership: 'program_lead',
  Admin: 'admin',
});

/**
 * Resolve the user's capability tier. Super admins (Django
 * is_staff/is_superuser) always come back as 'admin' regardless of
 * their `user.role` so the nav surfaces admin sections for them.
 *
 * Returns null when the user has no role and is not a super admin.
 */
export function userCapability(user) {
  if (!user) return null;
  if (isSuperAdmin(user)) return 'admin';
  const role = user.role;
  if (typeof role !== 'string' || role === '') return null;
  return LEGACY_USER_ROLE_TO_CAPABILITY[role] || null;
}

function rankOf(cap) {
  return CAPABILITIES.indexOf(cap);
}

/**
 * Inclusive "at least this tier" check, with one wrinkle:
 * domain_specialist is a side branch (not a strict subset of
 * program_lead). The rule is:
 *
 *   - admin matches everything except (trivially) a *strictly higher*
 *     tier (none exists).
 *   - program_lead matches participant, supervisor, program_lead.
 *   - supervisor matches participant, supervisor.
 *   - participant matches only participant.
 *   - domain_specialist matches participant, supervisor, and
 *     domain_specialist (it sits "around" the supervisor tier for
 *     nav purposes -- specialists can see specialist sections plus
 *     their own personal entries).
 *
 * `capOrList` accepts a single capability string or an array of
 * acceptable capabilities (any-match).
 */
export function hasCapability(user, capOrList) {
  const userCap = userCapability(user);
  if (!userCap) return false;
  const wanted = Array.isArray(capOrList) ? capOrList : [capOrList];
  if (wanted.length === 0) return false;
  const userRank = rankOf(userCap);
  return wanted.some((want) => {
    if (want === userCap) return true;
    if (userCap === 'admin') return true;
    if (want === 'admin') return false;
    if (userCap === 'domain_specialist') {
      return want === 'participant' || want === 'supervisor';
    }
    if (want === 'domain_specialist') return false;
    const wantRank = rankOf(want);
    if (wantRank < 0) return false;
    return userRank >= wantRank;
  });
}

/**
 * React hook flavor of {@link userCapability}. Reads from the
 * existing useAuth context so call sites stay short:
 *
 *   const cap = useCapability();
 *   if (cap === 'admin') ...
 */
/** Maintenance membership with no admin role — stripped nav + /maintenance home. */
export function isMaintenanceOnlyMember(user) {
  if (!user) return false;
  const roles = Array.isArray(user.membership_roles) ? user.membership_roles : [];
  return (
    roles.includes('maintenance')
    && !roles.includes('admin')
    && !hasCapability(user, 'admin')
    && !isSuperAdmin(user)
  );
}

const ROLE_HOME_PATHS = Object.freeze({
  Admin: '/admin/home',
  Counselor: '/counselor',
  'Unit Head': '/unit-head',
  'Camper Care': '/camper-care',
  Leadership: '/leadership-team',
  'Leadership Team': '/leadership-team',
  'Kitchen Staff': '/kitchen-staff',
  Specialist: '/specialist',
  Madrich: '/madrich',
  Maintenance: '/maintenance',
});

/** Post-login and logo home target for the signed-in user. */
export function homePathForUser(user) {
  if (!user) return '/dashboard';
  if (isMaintenanceOnlyMember(user)) return '/maintenance';
  if (isSuperAdmin(user)) return '/admin/home';
  const rolePath = user.role && ROLE_HOME_PATHS[user.role];
  return rolePath || '/dashboard';
}

export function useCapability() {
  const { user } = useAuth();
  return userCapability(user);
}

// Re-exported so tests can assert against the canonical mapping
// without reaching into a private symbol.
export const _LEGACY_USER_ROLE_TO_CAPABILITY = LEGACY_USER_ROLE_TO_CAPABILITY;

// Used by tests + ranking math; not part of the public API.
export const _RANKS = Object.freeze({
  participant: PARTICIPANT_RANK,
  supervisor: SUPERVISOR_RANK,
  program_lead: PROGRAM_LEAD_RANK,
  domain_specialist: DOMAIN_SPECIALIST_RANK,
  admin: ADMIN_RANK,
});
