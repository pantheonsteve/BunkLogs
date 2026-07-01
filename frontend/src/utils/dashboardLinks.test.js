import { describe, expect, it } from 'vitest';
import {
  observationBackLabel,
  observationThreadLink,
  profileLink,
  resolveProfileBackGroup,
  safeInternalPath,
  subjectProfileHref,
  withDateParam,
} from './dashboardLinks';

describe('dashboardLinks', () => {
  it('builds profile URLs with group and date query params', () => {
    expect(profileLink(330, { groupId: 12, date: '2026-06-02' })).toBe(
      '/profile/330?group=12&date=2026-06-02',
    );
  });

  it('subjectProfileHref prefers returnTo when it matches the subject profile', () => {
    const ret = '/profile/221?date_start=2026-05-21&date_end=2026-05-23';
    expect(subjectProfileHref(221, { returnTo: ret, canViewProfile: false })).toBe(ret);
    expect(subjectProfileHref(221, { observedDate: '2026-06-02', canViewProfile: true })).toBe(
      '/profile/221?date=2026-06-02',
    );
    expect(subjectProfileHref(99, { canViewProfile: false })).toBeNull();
  });

  it('builds observation links with encoded return path', () => {
    const ret = '/profile/221?date_start=2026-05-21&date_end=2026-05-23';
    expect(observationThreadLink(9, ret)).toBe(
      `/observations/9?from=${encodeURIComponent(ret)}`,
    );
    expect(observationBackLabel(ret)).toBe('Back to profile');
    expect(safeInternalPath('//evil.com')).toBeNull();
  });

  it('builds observation links with a contextual label for group dashboards', () => {
    const ret = '/dashboards/group/78?date=2026-06-03';
    expect(observationThreadLink(9, ret, { contextLabel: 'Cabin Birch' })).toBe(
      `/observations/9?from=${encodeURIComponent(ret)}&from_label=Cabin+Birch`,
    );
    expect(observationBackLabel(ret)).toBe('Back to group dashboard');
  });

  it('withDateParam appends, replaces, and no-ops correctly', () => {
    expect(withDateParam('/camper-care', '2026-06-30')).toBe('/camper-care?date=2026-06-30');
    expect(withDateParam('/camper-care', '')).toBe('/camper-care');
    expect(withDateParam('/camper-care', undefined)).toBe('/camper-care');
    // Preserves existing params and replaces an existing date.
    expect(withDateParam('/x?foo=1&date=2026-01-01', '2026-06-30')).toBe(
      '/x?foo=1&date=2026-06-30',
    );
    // Preserves a hash fragment.
    expect(withDateParam('/camper-care/campers/5?flagId=9#flag-9', '2026-06-30')).toBe(
      '/camper-care/campers/5?flagId=9&date=2026-06-30#flag-9',
    );
  });

  it('resolves back group from query param or single bunk', () => {
    const groups = [{ id: 36, name: 'Bunk 5', group_type: 'bunk' }];
    expect(resolveProfileBackGroup('36', groups)).toEqual(groups[0]);
    expect(resolveProfileBackGroup(null, groups)).toEqual(groups[0]);
    expect(resolveProfileBackGroup(null, [...groups, { id: 37, name: 'Bunk 6', group_type: 'bunk' }])).toBeNull();
  });
});
