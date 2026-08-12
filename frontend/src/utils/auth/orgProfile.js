/**
 * Which product surfaces the current organization gets.
 *
 * Branding is slug-driven (see `context/OrgBrandingContext.jsx`); product
 * shape is driven by `program_types` on the per-org auth payload, so a
 * third tenant works without another slug check.
 *
 * Crane Lake safety: anything we can't positively identify as a religious
 * school -- missing `program_types`, an unresolvable org, or a mixed-type
 * org -- resolves to the full camp nav that shipped before this module.
 */

import { currentOrgContext } from './orgRoles';

const RELIGIOUS_SCHOOL = 'religious_school';

/** Active program types in the current org, or [] when unknown. */
export function orgProgramTypes(user) {
  const types = currentOrgContext(user)?.program_types;
  return Array.isArray(types) ? types : [];
}

/** True only when every known program in this org is a religious school. */
export function isReligiousSchoolOrg(user) {
  const types = orgProgramTypes(user);
  return types.length > 0 && types.every((t) => t === RELIGIOUS_SCHOOL);
}

/**
 * Feature surfaces keyed by what they gate:
 *
 *   campOps        Maintenance Queue, Camper Care orders, Request catalog
 *   campDashboards Group Performance, Bunk Logs, Coverage, Concerns, Authors
 *   observations   Observations inbox + its unread badge (Notes are deferred
 *                  for TBE Tier 1 -- see docs/user_stories/10_notes_platform/)
 *   gradeReflections  /admin/reflections Madrich weekly completion dashboard
 */
export function orgSurfaces(user) {
  const school = isReligiousSchoolOrg(user);
  return {
    campOps: !school,
    campDashboards: !school,
    observations: !school,
    gradeReflections: school,
  };
}
