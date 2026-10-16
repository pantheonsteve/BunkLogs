import { describe, expect, it } from 'vitest';
import { responsesBackLink, subjectRowHref } from '../Responses';

describe('responsesBackLink', () => {
  it('sends everyone to reflections with date by default', () => {
    expect(responsesBackLink({ date: '2026-06-03' })).toEqual({
      href: '/dashboards/reflections?date=2026-06-03',
      label: 'Back to Reflections',
    });
  });

  it('honours dashboard query param for admins', () => {
    expect(
      responsesBackLink({ dashboard: 'logs', date: '2026-06-03' }),
    ).toEqual({
      href: '/dashboards/logs?date=2026-06-03',
      label: 'Back to Bunk Logs',
    });
  });

  it('reads the logs dashboard from the path when the query omits it', () => {
    expect(responsesBackLink({
      date: '2026-06-03',
      pathname: '/dashboards/logs/9',
    })).toEqual({
      href: '/dashboards/logs?date=2026-06-03',
      label: 'Back to Bunk Logs',
    });
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
