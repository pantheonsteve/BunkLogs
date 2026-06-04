import { describe, expect, it } from 'vitest';
import { profileLink, resolveProfileBackGroup } from './dashboardLinks';

describe('dashboardLinks', () => {
  it('builds profile URLs with group and date query params', () => {
    expect(profileLink(330, { groupId: 12, date: '2026-06-02' })).toBe(
      '/profile/330?group=12&date=2026-06-02',
    );
  });

  it('resolves back group from query param or single bunk', () => {
    const groups = [{ id: 36, name: 'Bunk 5', group_type: 'bunk' }];
    expect(resolveProfileBackGroup('36', groups)).toEqual(groups[0]);
    expect(resolveProfileBackGroup(null, groups)).toEqual(groups[0]);
    expect(resolveProfileBackGroup(null, [...groups, { id: 37, name: 'Bunk 6', group_type: 'bunk' }])).toBeNull();
  });
});
