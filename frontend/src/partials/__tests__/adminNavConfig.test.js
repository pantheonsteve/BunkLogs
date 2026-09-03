import { describe, expect, it } from 'vitest';
import {
  adminFormLinks,
  adminNavItems,
  adminReportLinks,
  adminSetupLinks,
  leadershipNavItems,
} from '../adminNavConfig';
import { DEFAULT_TERMS, resolveTerm } from '../../utils/terminology';

const campTerm = (key, opts) => resolveTerm(DEFAULT_TERMS, key, opts);
const schoolTerm = (key, opts) => resolveTerm(
  {
    ...DEFAULT_TERMS,
    group: { one: 'class', other: 'classes' },
    program: { one: 'school year', other: 'school years' },
  },
  key,
  opts,
);

const CAMP = { campOps: true, gradeReflections: false };
const SCHOOL = { campOps: false, gradeReflections: true };
const BARE = { campOps: false, gradeReflections: false };

const paths = (items) => items.map((i) => i.to);

describe('adminNavItems', () => {
  it('is the prototype seven, in order', () => {
    expect(paths(adminNavItems(CAMP, campTerm))).toEqual([
      '/admin/home',
      '/admin/people',
      '/admin/groups',
      '/admin/forms',
      '/admin/reports',
      '/admin/setup',
      '/admin/settings',
    ]);
  });

  it('names Groups with the tenant vocabulary', () => {
    const label = (surfaces, term) => adminNavItems(surfaces, term)
      .find((i) => i.to === '/admin/groups').label;
    expect(label(CAMP, campTerm)).toBe('Groups');
    expect(label(SCHOOL, schoolTerm)).toBe('Classes');
  });

  it('hides Reports when the org has none to show', () => {
    expect(paths(adminNavItems(BARE, campTerm))).not.toContain('/admin/reports');
  });

  it('badges only People and Groups', () => {
    const badged = adminNavItems(CAMP, campTerm).filter((i) => i.badge);
    expect(badged.map((i) => [i.to, i.badge])).toEqual([
      ['/admin/people', 'peopleNeverInvited'],
      ['/admin/groups', 'groupsNeedingAttention'],
    ]);
  });

  it('gives every item an icon key', () => {
    expect(adminNavItems(SCHOOL, schoolTerm).every((i) => i.icon)).toBe(true);
  });

  it('gives Leadership Team templates only', () => {
    expect(paths(leadershipNavItems())).toEqual(['/admin/templates']);
  });
});

describe('hub contents', () => {
  it('splits reports by surface', () => {
    expect(paths(adminReportLinks(CAMP))).toEqual(['/admin/catalog/planning']);
    expect(paths(adminReportLinks(SCHOOL))).toEqual([
      '/admin/reflections',
      '/admin/reflections/growth',
      '/admin/reflections/availability',
    ]);
    expect(adminReportLinks(BARE)).toEqual([]);
  });

  it('always offers templates and field keys', () => {
    expect(paths(adminFormLinks())).toEqual(['/admin/templates', '/admin/field-keys']);
  });

  it('offers the request catalog only to a camp', () => {
    expect(paths(adminSetupLinks(CAMP, campTerm))).toContain('/admin/catalog');
    expect(paths(adminSetupLinks(SCHOOL, schoolTerm))).not.toContain('/admin/catalog');
  });
});
