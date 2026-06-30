import { afterEach, describe, expect, it, vi } from 'vitest';
import { renderHook } from '@testing-library/react';
import { useCounselorDraft } from '../useCounselorDraft';
import { saveCounselorDraft } from '../../utils/counselor/counselorDraftStorage';

afterEach(() => {
  localStorage.clear();
});

describe('useCounselorDraft', () => {
  // Regression: an inline `onRestore` (new identity each render) must not
  // re-run the restore effect. Previously it did, repeatedly merging the
  // stale saved draft over freshly typed answers — silently truncating
  // submissions and triggering React error #185.
  it('restores exactly once even when onRestore identity changes each render', () => {
    const key = 'counselorDraft:test:1';
    saveCounselorDraft(key, { answers: { note: 'saved draft' } });

    const restoreSpy = vi.fn();
    const { rerender } = renderHook(
      ({ cb }) =>
        useCounselorDraft({
          draftKey: key,
          enabled: true,
          getSnapshot: () => ({}),
          onRestore: cb,
        }),
      { initialProps: { cb: (saved) => restoreSpy(saved) } },
    );

    expect(restoreSpy).toHaveBeenCalledTimes(1);
    expect(restoreSpy).toHaveBeenCalledWith(
      expect.objectContaining({ answers: { note: 'saved draft' } }),
    );

    // Simulate parent re-renders passing a fresh arrow each time.
    rerender({ cb: (saved) => restoreSpy(saved) });
    rerender({ cb: (saved) => restoreSpy(saved) });

    expect(restoreSpy).toHaveBeenCalledTimes(1);
  });

  it('does not restore when no draft is stored', () => {
    const restoreSpy = vi.fn();
    renderHook(() =>
      useCounselorDraft({
        draftKey: 'counselorDraft:test:empty',
        enabled: true,
        getSnapshot: () => ({}),
        onRestore: restoreSpy,
      }),
    );
    expect(restoreSpy).not.toHaveBeenCalled();
  });
});
