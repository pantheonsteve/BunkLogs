import { describe, expect, it, vi, beforeEach } from 'vitest';
import 'fake-indexeddb/auto';
import {
  drainQueue,
  getPendingEntries,
  isQueuedSubmissionError,
  isRetryableError,
  markConfirmed,
  persistPending,
  submitWithQueue,
  SUBMISSION_KIND,
} from '../queue';

vi.mock('../../../api', () => ({
  default: {
    post: vi.fn(),
  },
}));

describe('submissionQueue', () => {
  beforeEach(async () => {
    const entries = await getPendingEntries();
    await Promise.all(entries.map((entry) => markConfirmed(entry.id)));
  });

  it('treats network errors as retryable', () => {
    expect(isRetryableError({ message: 'Network Error' })).toBe(true);
    expect(isRetryableError({ response: { status: 503 } })).toBe(true);
    expect(isRetryableError({ response: { status: 400 } })).toBe(false);
  });

  it('persists pending entries in IndexedDB', async () => {
    const entryId = await persistPending({
      kind: SUBMISSION_KIND.SELF_REFLECTION,
      clientSubmissionId: '11111111-1111-4111-8111-111111111111',
      metadata: { date: '2026-06-05' },
      payload: { dayOff: true, language: 'en' },
    });
    const pending = await getPendingEntries();
    expect(pending.some((entry) => entry.id === entryId)).toBe(true);
  });

  it('marks queued submission errors for UX handling', async () => {
    const api = (await import('../../../api')).default;
    api.post.mockRejectedValueOnce({ message: 'Network Error' });

    let caught;
    try {
      await submitWithQueue({
        kind: SUBMISSION_KIND.SELF_REFLECTION,
        clientSubmissionId: '22222222-2222-4222-8222-222222222222',
        metadata: { date: '2026-06-05' },
        payload: { dayOff: true, language: 'en' },
        execute: () => api.post('/api/v1/counselor/self-reflection/', {}),
      });
    } catch (err) {
      caught = err;
    }
    expect(isQueuedSubmissionError(caught)).toBe(true);
  });

  it('drain retries with the same client_submission_id stored in the queue entry', async () => {
    const api = (await import('../../../api')).default;
    const clientSubmissionId = '44444444-4444-4444-8444-444444444444';
    await persistPending({
      kind: SUBMISSION_KIND.CAMPER_REFLECTION,
      clientSubmissionId,
      metadata: { subjectId: 11, date: '2026-06-05', assignmentGroupId: 100 },
      payload: {
        subjectId: 11,
        assignmentGroupId: 100,
        answers: { note: 'queued' },
        language: 'en',
        teamVisibility: 'team',
      },
    });
    api.post.mockResolvedValueOnce({ data: { id: 1 }, status: 201 });

    await drainQueue();

    expect(api.post).toHaveBeenCalledWith(
      '/api/v1/counselor/camper-reflections/',
      expect.objectContaining({ client_submission_id: clientSubmissionId }),
    );
    const pending = await getPendingEntries();
    expect(pending).toHaveLength(0);
  });
});
