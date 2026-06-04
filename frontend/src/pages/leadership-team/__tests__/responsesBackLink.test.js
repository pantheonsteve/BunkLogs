import { describe, expect, it } from 'vitest';
import { responsesBackLink } from '../Responses';

describe('responsesBackLink', () => {
  it('sends admins to reflections with date by default', () => {
    expect(responsesBackLink({ isAdmin: true, date: '2026-06-03' })).toEqual({
      href: '/dashboards/reflections?date=2026-06-03',
      label: '← Reflections',
    });
  });

  it('honours dashboard query param for admins', () => {
    expect(
      responsesBackLink({ dashboard: 'logs', date: '2026-06-03', isAdmin: true }),
    ).toEqual({
      href: '/dashboards/logs?date=2026-06-03',
      label: '← Bunk Logs',
    });
  });

  it('keeps non-admins on template library', () => {
    expect(responsesBackLink({ isAdmin: false, date: '2026-06-03' })).toEqual({
      href: '/admin/templates',
      label: '← Template library',
    });
  });
});
