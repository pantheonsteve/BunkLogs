/**
 * Frontend capability helper.
 *
 * Roles and capabilities come from active Memberships, delivered per
 * organization on the auth payload:
 *
 *   user.organizations = [
 *     { slug: 'tbe', name: 'Temple Beth-El', capability: 'participant', roles: ['madrich'] },
 *   ]
 *
 * The "current" organization is the tenant subdomain (clc.bunklogs.net ->
 * "clc") or the VITE_DEV_ORGANIZATION_SLUG dev override; when neither is
 * set and the user belongs to exactly one org we fall back to it so
 * localhost keeps working without configuration.
 *
 * `capability` mirrors backend `Membership.capability` (derived from
 * `ROLE_TO_CAPABILITY` in core/models.py): the highest tier across the
 * user's active memberships in that org.
 */

import { useAuth } from '../../auth/AuthContext';
import isSuperAdmin from './isSuperAdmin';
import { currentOrgContext, membershipRolesForUser } from './orgRoles';

export { currentOrgContext, membershipRolesForUser };

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
 * Resolve the user's capability tier in the current organization.
 * Super admins (Django is_staff/is_superuser) always come back as
 * 'admin' so the nav surfaces admin sections for them.
 *
 * Returns null when the user has no capability here and is not a
 * super admin.
 */
export function userCapability(user) {
  if (!user) return null;
  if (isSuperAdmin(user)) return 'admin';
  return currentOrgContext(user)?.capability || null;
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

/** Maintenance membership with no admin role — stripped nav + /maintenance home. */
export function isMaintenanceOnlyMember(user) {
  if (!user) return false;
  const roles = membershipRolesForUser(user);
  return (
    roles.includes('maintenance')
    && !roles.includes('admin')
    && !hasCapability(user, 'admin')
    && !isSuperAdmin(user)
  );
}

/**
 * Membership.role -> workspace home, in priority order for people who
 * hold several roles. Roles without a dedicated workspace
 * (administrative_staff) land on the dashboards hub.
 */
const MEMBERSHIP_ROLE_HOME_PATHS = Object.freeze([
  ['admin', '/admin/home'],
  ['leadership_team', '/leadership-team'],
  ['unit_head', '/unit-head'],
  ['camper_care', '/camper-care'],
  ['health_center', '/camper-care'],
  ['medical', '/camper-care'],
  ['special_diets', '/camper-care'],
  ['counselor', '/counselor'],
  ['junior_counselor', '/counselor'],
  ['general_counselor', '/counselor'],
  ['specialist', '/specialist'],
  ['madrich', '/madrich'],
  ['kitchen_staff', '/kitchen-staff'],
  ['housekeeping', '/kitchen-staff'],
  ['maintenance', '/maintenance'],
  ['faculty', '/faculty'],
  ['administrative_staff', '/dashboards'],
]);

/**
 * Post-login and logo home target for the signed-in user.
 *
 * Users with no membership in the current organization get the terminal
 * /no-access page instead of a redirect cycle through /dashboard.
 */
export function homePathForUser(user) {
  if (!user) return '/dashboard';
  if (isMaintenanceOnlyMember(user)) return '/maintenance';
  if (isSuperAdmin(user)) return '/admin/home';
  const roles = membershipRolesForUser(user);
  for (const [role, path] of MEMBERSHIP_ROLE_HOME_PATHS) {
    if (roles.includes(role)) return path;
  }
  return '/no-access';
}

/**
 * React hook flavor of {@link userCapability}. Reads from the
 * existing useAuth context so call sites stay short:
 *
 *   const cap = useCapability();
 *   if (cap === 'admin') ...
 */
export function useCapability() {
  const { user } = useAuth();
  return userCapability(user);
}

// Used by tests + ranking math; not part of the public API.
export const _RANKS = Object.freeze({
  participant: PARTICIPANT_RANK,
  supervisor: SUPERVISOR_RANK,
  program_lead: PROGRAM_LEAD_RANK,
  domain_specialist: DOMAIN_SPECIALIST_RANK,
  admin: ADMIN_RANK,
});
