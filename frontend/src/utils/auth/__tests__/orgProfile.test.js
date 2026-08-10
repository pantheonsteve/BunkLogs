import { describe, it, expect, vi, beforeEach } from 'vitest';

import {
  isReligiousSchoolOrg,
  orgProgramTypes,
  orgSurfaces,
} from '../orgProfile';
import { resolveOrganizationSlug } from '../../orgSlug';

// Current-org resolution reads the tenant subdomain; mock it so tests can
// place the viewer on a specific tenant.
vi.mock('../../orgSlug', () => ({
  resolveOrganizationSlug: vi.fn(() => null),
}));

const org = (slug, programTypes) => ({
  slug,
  name: slug.toUpperCase(),
  capability: 'participant',
  roles: [],
  ...(programTypes === undefined ? {} : { program_types: programTypes }),
});

beforeEach(() => {
  resolveOrganizationSlug.mockReturnValue(null);
});

describe('orgProgramTypes', () => {
  it('reads program_types from the current org entry', () => {
    const user = { organizations: [org('tbe', ['religious_school'])] };
    expect(orgProgramTypes(user)).toEqual(['religious_school']);
  });

  it('returns an empty list when the org entry predates program_types', () => {
    expect(orgProgramTypes({ organizations: [org('clc')] })).toEqual([]);
  });

  it('returns an empty list when there is no resolvable org', () => {
    expect(orgProgramTypes(null)).toEqual([]);
    expect(orgProgramTypes({})).toEqual([]);
  });
});

describe('isReligiousSchoolOrg', () => {
  it('is true for an org whose only program type is religious_school', () => {
    const user = { organizations: [org('tbe', ['religious_school'])] };
    expect(isReligiousSchoolOrg(user)).toBe(true);
  });

  it('is false for a camp org', () => {
    const user = { organizations: [org('clc', ['summer_camp'])] };
    expect(isReligiousSchoolOrg(user)).toBe(false);
  });

  it('is false for a mixed-type org so camp surfaces stay available', () => {
    const user = {
      organizations: [org('mixed', ['religious_school', 'summer_camp'])],
    };
    expect(isReligiousSchoolOrg(user)).toBe(false);
  });

  it('is false when program_types is missing or empty', () => {
    expect(isReligiousSchoolOrg({ organizations: [org('clc')] })).toBe(false);
    expect(isReligiousSchoolOrg({ organizations: [org('clc', [])] })).toBe(false);
  });

  it('resolves against the tenant the SPA is serving for multi-org users', () => {
    const user = {
      organizations: [org('clc', ['summer_camp']), org('tbe', ['religious_school'])],
    };
    resolveOrganizationSlug.mockReturnValue('tbe');
    expect(isReligiousSchoolOrg(user)).toBe(true);

    resolveOrganizationSlug.mockReturnValue('clc');
    expect(isReligiousSchoolOrg(user)).toBe(false);
  });
});

describe('orgSurfaces', () => {
  it('gives a religious school its reflections dashboard and no camp surfaces', () => {
    const user = { organizations: [org('tbe', ['religious_school'])] };
    expect(orgSurfaces(user)).toEqual({
      campOps: false,
      campDashboards: false,
      observations: false,
      gradeReflections: true,
    });
  });

  it('gives a camp every camp surface and no grade reflections', () => {
    const user = { organizations: [org('clc', ['summer_camp'])] };
    expect(orgSurfaces(user)).toEqual({
      campOps: true,
      campDashboards: true,
      observations: true,
      gradeReflections: false,
    });
  });

  it('falls back to camp surfaces when the org shape is unknown', () => {
    expect(orgSurfaces(null)).toEqual({
      campOps: true,
      campDashboards: true,
      observations: true,
      gradeReflections: false,
    });
  });
});
