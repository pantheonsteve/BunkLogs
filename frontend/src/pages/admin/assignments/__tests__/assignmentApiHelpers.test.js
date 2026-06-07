import { describe, it, expect } from 'vitest';
import {
  parseListPayload,
  personFromMembership,
  mergeMembershipPeople,
} from '../assignmentApiHelpers';

describe('assignmentApiHelpers', () => {
  it('parseListPayload accepts bare arrays and paginated results', () => {
    expect(parseListPayload([{ id: 1 }])).toEqual([{ id: 1 }]);
    expect(parseListPayload({ results: [{ id: 2 }] })).toEqual([{ id: 2 }]);
    expect(parseListPayload({})).toEqual([]);
  });

  it('personFromMembership resolves numeric person id and person_name', () => {
    expect(personFromMembership({
      id: 50,
      person: 5,
      person_name: 'Sam Lee',
    })).toEqual({
      id: 5,
      first_name: 'Sam',
      last_name: 'Lee',
      full_name: 'Sam Lee',
    });
  });

  it('mergeMembershipPeople dedupes by person id', () => {
    const map = mergeMembershipPeople([
      { id: 50, person: 5, person_name: 'Sam Lee', role: 'counselor' },
      { id: 51, person: 5, person_name: 'Sam Lee', role: 'general_counselor' },
    ], 'counselor');
    expect(map.size).toBe(1);
    expect(map.get(5).roles).toEqual(['counselor']);
  });
});
