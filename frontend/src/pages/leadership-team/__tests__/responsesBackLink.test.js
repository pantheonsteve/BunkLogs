import { describe, expect, it } from 'vitest';
import { responsesBackLink, subjectRowHref } from '../Responses';

describe('responsesBackLink', () => {
  it('sends admins to reflections with date by default', () => {
    expect(responsesBackLink({ isAdmin: true, date: '2026-06-03' })).toEqual({
      href: '/dashboards/reflections?date=2026-06-03',
      label: 'Back to Reflections',
    });
  });

  it('honours dashboard query param for admins', () => {
    expect(
      responsesBackLink({ dashboard: 'logs', date: '2026-06-03', isAdmin: true }),
    ).toEqual({
      href: '/dashboards/logs?date=2026-06-03',
      label: 'Back to Bunk Logs',
    });
  });

  it('keeps non-admins on template library', () => {
    expect(responsesBackLink({ isAdmin: false, date: '2026-06-03' })).toEqual({
      href: '/admin/templates',
      label: 'Back to template library',
    });
  });

  it('sends role-based orgs home, ignoring the dashboard hub', () => {
    expect(
      responsesBackLink({
        dashboard: 'reflections',
        date: '2026-06-03',
        isAdmin: true,
        homePath: '/admin/home',
      }),
    ).toEqual({ href: '/admin/home', label: 'Back to Admin Home' });
  });
});

describe('subjectRowHref', () => {
  const subject = { id: 88, name: 'Rose', membership_id: 3189, membership_role: 'madrich' };

  it('opens the camper profile by default', () => {
    expect(subjectRowHref(subject, { dateQs: '?date=2026-06-03' }))
      .toBe('/profile/88?date=2026-06-03');
  });

  it('opens the member reflection history for role-based orgs', () => {
    expect(subjectRowHref(subject, { dateQs: '?date=2026-06-03', memberDetail: true }))
      .toBe('/admin/reflections/madrich/members/3189');
  });

  it('falls back to the profile when the row has no membership', () => {
    expect(subjectRowHref({ id: 88, name: 'Rose' }, { memberDetail: true }))
      .toBe('/profile/88');
  });

  it('returns null without a subject', () => {
    expect(subjectRowHref(null)).toBeNull();
  });
});
