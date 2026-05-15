import { describe, it, expect } from 'vitest';
import isSuperAdmin from './isSuperAdmin';

describe('isSuperAdmin', () => {
  it('returns false for null / undefined', () => {
    expect(isSuperAdmin(null)).toBe(false);
    expect(isSuperAdmin(undefined)).toBe(false);
  });

  it('returns false when neither flag is set', () => {
    expect(isSuperAdmin({})).toBe(false);
    expect(isSuperAdmin({ is_staff: false, is_superuser: false })).toBe(false);
    expect(isSuperAdmin({ role: 'Counselor' })).toBe(false);
  });

  it('returns true when only is_staff is set', () => {
    expect(isSuperAdmin({ is_staff: true })).toBe(true);
    expect(isSuperAdmin({ is_staff: true, is_superuser: false })).toBe(true);
  });

  it('returns true when only is_superuser is set', () => {
    expect(isSuperAdmin({ is_superuser: true })).toBe(true);
    expect(isSuperAdmin({ is_staff: false, is_superuser: true })).toBe(true);
  });

  it('returns true when both flags are set', () => {
    expect(isSuperAdmin({ is_staff: true, is_superuser: true })).toBe(true);
  });
});
