import { describe, it, expect, vi, beforeEach } from 'vitest';

import {
  CAPABILITIES,
  currentOrgContext,
  membershipRolesForUser,
  userCapability,
  hasCapability,
  homePathForUser,
} from '../capability';
import { resolveOrganizationSlug } from '../../orgSlug';

// The current-org resolution reads the tenant subdomain; mock it so tests
// can flip between "on clc.bunklogs.net" and "unscoped dev host".
vi.mock('../../orgSlug', () => ({
  resolveOrganizationSlug: vi.fn(() => null),
}));

const org = (slug, capability, roles, name) => ({
  slug,
  name: name || slug.toUpperCase(),
  capability,
  roles,
});

const userIn = (capability, roles = []) => ({
  organizations: [org('clc', capability, roles)],
});

beforeEach(() => {
  resolveOrganizationSlug.mockReturnValue(null);
});

describe('CAPABILITIES order', () => {
  it('orders capabilities from weakest to strongest', () => {
    expect(CAPABILITIES).toEqual([
      'participant',
      'supervisor',
      'program_lead',
      'domain_specialist',
      'admin',
    ]);
  });

  it('is frozen against mutation', () => {
    expect(() => {
      CAPABILITIES[0] = 'mutated';
    }).toThrow();
  });
});

describe('currentOrgContext', () => {
  it('returns null for null user or missing organizations payload', () => {
    expect(currentOrgContext(null)).toBe(null);
    expect(currentOrgContext({})).toBe(null);
    expect(currentOrgContext({ role: 'Admin' })).toBe(null);
  });

  it('falls back to the single org when no slug is resolvable', () => {
    const u = userIn('participant', ['madrich']);
    expect(currentOrgContext(u)?.slug).toBe('clc');
  });

  it('does not guess between multiple orgs without a slug', () => {
    const u = {
      organizations: [
        org('clc', 'admin', ['admin']),
        org('tbe', 'participant', ['madrich']),
      ],
    };
    expect(currentOrgContext(u)).toBe(null);
  });

  it('picks the org matching the tenant subdomain', () => {
    resolveOrganizationSlug.mockReturnValue('tbe');
    const u = {
      organizations: [
        org('clc', 'admin', ['admin']),
        org('tbe', 'participant', ['madrich']),
      ],
    };
    expect(currentOrgContext(u)?.capability).toBe('participant');
  });

  it('returns null when the user has no entry for the current org', () => {
    resolveOrganizationSlug.mockReturnValue('clc');
    const u = { organizations: [org('tbe', 'participant', ['madrich'])] };
    expect(currentOrgContext(u)).toBe(null);
  });
});

describe('membershipRolesForUser', () => {
  it('returns the org-scoped roles when resolvable', () => {
    resolveOrganizationSlug.mockReturnValue('tbe');
    const u = {
      membership_roles: ['admin', 'madrich'],
      organizations: [
        org('clc', 'admin', ['admin']),
        org('tbe', 'participant', ['madrich']),
      ],
    };
    expect(membershipRolesForUser(u)).toEqual(['madrich']);
  });

  it('falls back to the flattened union for older payloads', () => {
    expect(membershipRolesForUser({ membership_roles: ['counselor'] })).toEqual(['counselor']);
    expect(membershipRolesForUser({})).toEqual([]);
    expect(membershipRolesForUser(null)).toEqual([]);
  });
});

describe('userCapability', () => {
  it('returns null for null/undefined and role-less users', () => {
    expect(userCapability(null)).toBe(null);
    expect(userCapability(undefined)).toBe(null);
    expect(userCapability({})).toBe(null);
    expect(userCapability({ organizations: [] })).toBe(null);
  });

  it('returns the capability from the current org context', () => {
    expect(userCapability(userIn('participant', ['counselor']))).toBe('participant');
    expect(userCapability(userIn('supervisor', ['unit_head']))).toBe('supervisor');
    expect(userCapability(userIn('program_lead', ['leadership_team']))).toBe('program_lead');
    expect(userCapability(userIn('admin', ['admin']))).toBe('admin');
  });

  it('returns "admin" for is_staff/is_superuser regardless of memberships', () => {
    expect(userCapability({ is_staff: true })).toBe('admin');
    expect(userCapability({ is_superuser: true })).toBe('admin');
    expect(userCapability({ is_staff: true, ...userIn('participant', ['counselor']) })).toBe('admin');
  });

  it('returns null when the user has no membership in the current org', () => {
    resolveOrganizationSlug.mockReturnValue('clc');
    const tbeUser = { organizations: [org('tbe', 'participant', ['madrich'])] };
    expect(userCapability(tbeUser)).toBe(null);
  });
});

describe('hasCapability — single capability checks', () => {
  it('returns false for null user / empty capability list', () => {
    expect(hasCapability(null, 'participant')).toBe(false);
    expect(hasCapability(userIn('participant'), [])).toBe(false);
  });

  it('admin matches every named capability', () => {
    const admin = userIn('admin', ['admin']);
    for (const cap of CAPABILITIES) {
      expect(hasCapability(admin, cap)).toBe(true);
    }
  });

  it('super admin matches every named capability (even without memberships)', () => {
    const root = { is_staff: true };
    expect(hasCapability(root, 'admin')).toBe(true);
    expect(hasCapability(root, 'supervisor')).toBe(true);
  });

  it('program_lead matches participant/supervisor/program_lead but not admin or domain_specialist', () => {
    const u = userIn('program_lead', ['leadership_team']);
    expect(hasCapability(u, 'participant')).toBe(true);
    expect(hasCapability(u, 'supervisor')).toBe(true);
    expect(hasCapability(u, 'program_lead')).toBe(true);
    expect(hasCapability(u, 'domain_specialist')).toBe(false);
    expect(hasCapability(u, 'admin')).toBe(false);
  });

  it('supervisor matches participant/supervisor only', () => {
    const u = userIn('supervisor', ['unit_head']);
    expect(hasCapability(u, 'participant')).toBe(true);
    expect(hasCapability(u, 'supervisor')).toBe(true);
    expect(hasCapability(u, 'program_lead')).toBe(false);
    expect(hasCapability(u, 'admin')).toBe(false);
  });

  it('participant matches only participant', () => {
    const u = userIn('participant', ['counselor']);
    expect(hasCapability(u, 'participant')).toBe(true);
    expect(hasCapability(u, 'supervisor')).toBe(false);
    expect(hasCapability(u, 'program_lead')).toBe(false);
    expect(hasCapability(u, 'admin')).toBe(false);
  });

  it('domain_specialist matches participant/supervisor/domain_specialist', () => {
    const u = userIn('domain_specialist', ['health_center']);
    expect(hasCapability(u, 'participant')).toBe(true);
    expect(hasCapability(u, 'supervisor')).toBe(true);
    expect(hasCapability(u, 'domain_specialist')).toBe(true);
    expect(hasCapability(u, 'admin')).toBe(false);
  });
});

describe('hasCapability — list-of-capabilities checks', () => {
  it('matches any capability in the list (OR semantics)', () => {
    const u = userIn('supervisor', ['unit_head']);
    expect(hasCapability(u, ['admin', 'supervisor'])).toBe(true);
    expect(hasCapability(u, ['admin', 'program_lead'])).toBe(false);
  });
});

describe('homePathForUser', () => {
  it('returns /dashboard for a missing user (unauthenticated entry)', () => {
    expect(homePathForUser(null)).toBe('/dashboard');
  });

  it('sends maintenance-only members to the queue', () => {
    expect(homePathForUser(userIn('participant', ['maintenance']))).toBe('/maintenance');
  });

  it('routes each workspace role to its home', () => {
    expect(homePathForUser(userIn('admin', ['admin']))).toBe('/admin/home');
    expect(homePathForUser(userIn('participant', ['counselor']))).toBe('/counselor');
    expect(homePathForUser(userIn('supervisor', ['unit_head']))).toBe('/unit-head');
    expect(homePathForUser(userIn('supervisor', ['camper_care']))).toBe('/camper-care');
    expect(homePathForUser(userIn('program_lead', ['leadership_team']))).toBe('/leadership-team');
    expect(homePathForUser(userIn('participant', ['madrich']))).toBe('/madrich');
    expect(homePathForUser(userIn('participant', ['kitchen_staff']))).toBe('/kitchen-staff');
    expect(homePathForUser(userIn('supervisor', ['faculty']))).toBe('/faculty');
    expect(homePathForUser(userIn('supervisor', ['administrative_staff']))).toBe('/dashboards');
  });

  it('prefers admin over other roles', () => {
    expect(homePathForUser(userIn('admin', ['admin', 'counselor']))).toBe('/admin/home');
  });

  it('is terminal (/no-access) for users with no roles in the current org', () => {
    resolveOrganizationSlug.mockReturnValue('clc');
    const tbeUser = { organizations: [org('tbe', 'participant', ['madrich'])] };
    expect(homePathForUser(tbeUser)).toBe('/no-access');
    expect(homePathForUser({ organizations: [], membership_roles: [] })).toBe('/no-access');
  });

  it('sends super admins to /admin/home', () => {
    expect(homePathForUser({ is_superuser: true })).toBe('/admin/home');
  });
});
