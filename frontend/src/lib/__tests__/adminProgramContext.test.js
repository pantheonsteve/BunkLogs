import { describe, it, expect, beforeEach } from 'vitest';
import {
  ADMIN_PROGRAM_STORAGE_KEY,
  resolveProgramId,
  resolveInitialProgramId,
  readStoredProgramId,
  writeStoredProgramId,
} from '../adminProgramContext';

const programs = [
  { id: 1, name: 'Summer 2026', slug: 'summer-2026', is_active: true, start_date: '2026-06-01' },
  { id: 2, name: 'Summer 2025', slug: 'summer-2025', is_active: false, start_date: '2025-06-01' },
];

beforeEach(() => {
  sessionStorage.clear();
});

describe('adminProgramContext', () => {
  it('resolves program by id or slug', () => {
    expect(resolveProgramId('1', programs)).toBe('1');
    expect(resolveProgramId('summer-2025', programs)).toBe('2');
    expect(resolveProgramId('missing', programs)).toBe('');
  });

  it('prefers URL program over storage and defaults', () => {
    writeStoredProgramId('2');
    expect(resolveInitialProgramId({
      urlProgramId: 'summer-2026',
      storedProgramId: readStoredProgramId(),
      programs,
    })).toBe('1');
  });

  it('falls back to stored program then newest active', () => {
    writeStoredProgramId('2');
    expect(resolveInitialProgramId({
      urlProgramId: '',
      storedProgramId: readStoredProgramId(),
      programs,
    })).toBe('2');

    sessionStorage.removeItem(ADMIN_PROGRAM_STORAGE_KEY);
    expect(resolveInitialProgramId({
      urlProgramId: '',
      storedProgramId: '',
      programs,
    })).toBe('1');
  });
});
