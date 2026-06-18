import { describe, expect, it } from 'vitest';
import {
  camperReflectionDraftKey,
  loadCounselorDraft,
  saveCounselorDraft,
  selfReflectionDraftKey,
} from '../counselorDraftStorage';

describe('counselorDraftStorage', () => {
  it('round-trips camper reflection drafts', () => {
    const key = camperReflectionDraftKey(42, '2026-06-05');
    saveCounselorDraft(key, {
      answers: { note: 'draft text' },
      clientSubmissionId: 'abc',
    });
    const restored = loadCounselorDraft(key);
    expect(restored?.answers?.note).toBe('draft text');
    expect(restored?.clientSubmissionId).toBe('abc');
  });

  it('round-trips self-reflection drafts', () => {
    const key = selfReflectionDraftKey('2026-06-05');
    saveCounselorDraft(key, { dayOff: true, clientSubmissionId: 'xyz' });
    const restored = loadCounselorDraft(key);
    expect(restored?.dayOff).toBe(true);
  });
});
