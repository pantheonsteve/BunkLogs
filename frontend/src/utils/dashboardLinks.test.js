import { describe, expect, it } from 'vitest';
import {
  observationBackLabel,
  observationThreadLink,
  profileLink,
  resolveProfileBackGroup,
  safeInternalPath,
  subjectProfileHref,
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

  it('resolves back group from query param or single bunk', () => {
    const groups = [{ id: 36, name: 'Bunk 5', group_type: 'bunk' }];
    expect(resolveProfileBackGroup('36', groups)).toEqual(groups[0]);
    expect(resolveProfileBackGroup(null, groups)).toEqual(groups[0]);
    expect(resolveProfileBackGroup(null, [...groups, { id: 37, name: 'Bunk 6', group_type: 'bunk' }])).toBeNull();
  });
});
