import { describe, it, expect } from 'vitest';
import { canHaveParent, parentTypesFor } from '../groupHierarchy';

describe('groupHierarchy', () => {
  it('bunks can nest under units or divisions', () => {
    expect(parentTypesFor('bunk')).toEqual(['unit', 'division']);
    expect(canHaveParent('bunk')).toBe(true);
  });

  it('divisions cannot have parents', () => {
    expect(canHaveParent('division')).toBe(false);
  });
});
