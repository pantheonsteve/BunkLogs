import { describe, expect, it } from 'vitest';
import { orgSlugFromHost, resolveOrganizationSlug } from '../orgSlug';

describe('orgSlugFromHost', () => {
  it('returns tenant slug from production subdomain', () => {
    expect(orgSlugFromHost('clc.bunklogs.net')).toBe('clc');
    expect(orgSlugFromHost('tbe.bunklogs.net')).toBe('tbe');
  });

  it('returns null for reserved or non-tenant hosts', () => {
    expect(orgSlugFromHost('admin.bunklogs.net')).toBeNull();
    expect(orgSlugFromHost('www.bunklogs.net')).toBeNull();
    expect(orgSlugFromHost('localhost')).toBeNull();
    expect(orgSlugFromHost('127.0.0.1')).toBeNull();
  });
});

describe('resolveOrganizationSlug', () => {
  it('prefers VITE_DEV_ORGANIZATION_SLUG when set', () => {
    const prev = import.meta.env.VITE_DEV_ORGANIZATION_SLUG;
    import.meta.env.VITE_DEV_ORGANIZATION_SLUG = 'dev-clc';
    expect(resolveOrganizationSlug()).toBe('dev-clc');
    import.meta.env.VITE_DEV_ORGANIZATION_SLUG = prev;
  });
});
