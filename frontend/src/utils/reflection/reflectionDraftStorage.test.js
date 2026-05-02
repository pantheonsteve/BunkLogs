import { describe, it, expect, beforeEach } from 'vitest';
import {
  reflectionDraftKey,
  loadReflectionDraft,
  saveReflectionDraft,
  clearReflectionDraft,
} from './reflectionDraftStorage';

describe('reflectionDraftStorage', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('save and resume round-trip', () => {
    const key = reflectionDraftKey(42, '2026-06-01', '2026-06-07');
    expect(key).toContain('42');
    saveReflectionDraft(key, { answers: { note: 'draft' } });
    const loaded = loadReflectionDraft(key);
    expect(loaded.answers.note).toBe('draft');
    clearReflectionDraft(key);
    expect(loadReflectionDraft(key)).toBeNull();
  });
});
