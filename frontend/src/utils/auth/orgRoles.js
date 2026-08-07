/**
 * Pure helpers for reading the per-org auth payload
 * (`user.organizations`). Kept free of React/AuthContext imports so
 * modules like api.js can use them without import cycles;
 * capability.js re-exports them for component call sites.
 */

import { resolveOrganizationSlug } from '../orgSlug';

/**
 * The user's org entry for the organization this SPA instance is
 * serving. Null when the user has no Person/Membership here (e.g. a TBE
 * user browsing clc.bunklogs.net) or when the payload predates the
 * `organizations` shape.
 */
export function currentOrgContext(user) {
  if (!user || !Array.isArray(user.organizations)) return null;
  const slug = resolveOrganizationSlug();
  if (slug) {
    return user.organizations.find((org) => org.slug === slug) || null;
  }
  return user.organizations.length === 1 ? user.organizations[0] : null;
}

/**
 * Active membership roles scoped to the current org when resolvable,
 * otherwise the flattened cross-org union (`membership_roles`) so older
 * payloads and unscoped dev hosts keep working.
 */
export function membershipRolesForUser(user) {
  const ctx = currentOrgContext(user);
  if (ctx && Array.isArray(ctx.roles)) return ctx.roles;
  return Array.isArray(user?.membership_roles) ? user.membership_roles : [];
}
