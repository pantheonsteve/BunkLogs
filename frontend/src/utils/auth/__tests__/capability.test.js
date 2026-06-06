import { describe, it, expect } from 'vitest';

import {
  CAPABILITIES,
  userCapability,
  hasCapability,
  homePathForUser,
  _LEGACY_USER_ROLE_TO_CAPABILITY,
} from '../capability';

// Mirror of backend users.models.User.ROLE_CHOICES. If a new legacy
// User.role string is added on the backend, this list fails first --
// then capability.js needs an entry too.
const LEGACY_ROLES = [
  'Admin',
  'Camper Care',
  'Unit Head',
  'Counselor',
  'Leadership',
  'Kitchen Staff',
];

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

describe('LEGACY_USER_ROLE_TO_CAPABILITY coverage', () => {
  it('maps every backend User.role value', () => {
    for (const role of LEGACY_ROLES) {
      expect(
        Object.prototype.hasOwnProperty.call(
          _LEGACY_USER_ROLE_TO_CAPABILITY,
          role,
        ),
      ).toBe(true);
    }
  });

  it('does not invent new role names', () => {
    for (const role of Object.keys(_LEGACY_USER_ROLE_TO_CAPABILITY)) {
      expect(LEGACY_ROLES).toContain(role);
    }
  });
});

describe('userCapability', () => {
  it('returns null for null/undefined', () => {
    expect(userCapability(null)).toBe(null);
    expect(userCapability(undefined)).toBe(null);
  });

  it('returns null for users with no role and no super-admin flags', () => {
    expect(userCapability({})).toBe(null);
    expect(userCapability({ role: '' })).toBe(null);
    expect(userCapability({ role: null })).toBe(null);
  });

  it('returns the capability for each legacy User.role', () => {
    expect(userCapability({ role: 'Counselor' })).toBe('participant');
    expect(userCapability({ role: 'Kitchen Staff' })).toBe('participant');
    expect(userCapability({ role: 'Unit Head' })).toBe('supervisor');
    expect(userCapability({ role: 'Camper Care' })).toBe('supervisor');
    expect(userCapability({ role: 'Leadership' })).toBe('program_lead');
    expect(userCapability({ role: 'Admin' })).toBe('admin');
  });

  it('returns "admin" for is_staff users regardless of their User.role', () => {
    expect(userCapability({ is_staff: true })).toBe('admin');
    expect(userCapability({ is_staff: true, role: 'Counselor' })).toBe('admin');
  });

  it('returns "admin" for is_superuser users regardless of role', () => {
    expect(userCapability({ is_superuser: true })).toBe('admin');
    expect(userCapability({ is_superuser: true, role: 'Camper Care' })).toBe('admin');
  });

  it('returns null for unknown role strings (and does not throw)', () => {
    expect(userCapability({ role: 'Mystery Role' })).toBe(null);
  });
});

describe('hasCapability — single capability checks', () => {
  it('returns false for null user / null capability target', () => {
    expect(hasCapability(null, 'participant')).toBe(false);
    expect(hasCapability({ role: 'Counselor' }, [])).toBe(false);
  });

  it('admin matches every named capability', () => {
    const admin = { role: 'Admin' };
    expect(hasCapability(admin, 'participant')).toBe(true);
    expect(hasCapability(admin, 'supervisor')).toBe(true);
    expect(hasCapability(admin, 'program_lead')).toBe(true);
    expect(hasCapability(admin, 'domain_specialist')).toBe(true);
    expect(hasCapability(admin, 'admin')).toBe(true);
  });

  it('super admin matches every named capability (even without role)', () => {
    const root = { is_staff: true };
    expect(hasCapability(root, 'admin')).toBe(true);
    expect(hasCapability(root, 'supervisor')).toBe(true);
  });

  it('program_lead matches participant/supervisor/program_lead but not admin or domain_specialist', () => {
    const u = { role: 'Leadership' };
    expect(hasCapability(u, 'participant')).toBe(true);
    expect(hasCapability(u, 'supervisor')).toBe(true);
    expect(hasCapability(u, 'program_lead')).toBe(true);
    expect(hasCapability(u, 'domain_specialist')).toBe(false);
    expect(hasCapability(u, 'admin')).toBe(false);
  });

  it('supervisor matches participant/supervisor only', () => {
    const u = { role: 'Unit Head' };
    expect(hasCapability(u, 'participant')).toBe(true);
    expect(hasCapability(u, 'supervisor')).toBe(true);
    expect(hasCapability(u, 'program_lead')).toBe(false);
    expect(hasCapability(u, 'admin')).toBe(false);
  });

  it('participant matches only participant', () => {
    const u = { role: 'Counselor' };
    expect(hasCapability(u, 'participant')).toBe(true);
    expect(hasCapability(u, 'supervisor')).toBe(false);
    expect(hasCapability(u, 'program_lead')).toBe(false);
    expect(hasCapability(u, 'admin')).toBe(false);
  });
});

describe('hasCapability — list-of-capabilities checks', () => {
  it('matches any capability in the list (OR semantics)', () => {
    const u = { role: 'Unit Head' };
    expect(hasCapability(u, ['admin', 'supervisor'])).toBe(true);
    expect(hasCapability(u, ['admin', 'program_lead'])).toBe(false);
  });

  it('handles a single-element list the same as a bare string', () => {
    const u = { role: 'Camper Care' };
    expect(hasCapability(u, ['supervisor'])).toBe(hasCapability(u, 'supervisor'));
  });
});

describe('homePathForUser', () => {
  it('sends maintenance-only members to the queue', () => {
    expect(homePathForUser({
      role: 'Counselor',
      membership_roles: ['maintenance'],
    })).toBe('/maintenance');
  });

  it('keeps counselor home for non-maintenance counselors', () => {
    expect(homePathForUser({ role: 'Counselor', membership_roles: [] })).toBe('/counselor');
  });
});
