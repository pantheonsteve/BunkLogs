import { useCallback, useEffect, useRef } from 'react';
import {
  clearCounselorDraft,
  loadCounselorDraft,
  saveCounselorDraft,
} from '../utils/counselor/counselorDraftStorage';

/**
 * Autosave counselor form state to localStorage (blur + interval).
 */
export function useCounselorDraft({
  draftKey,
  enabled = true,
  intervalMs = 30_000,
  getSnapshot,
  onRestore,
}) {
  const snapshotRef = useRef(getSnapshot);
  const onRestoreRef = useRef(onRestore);

  useEffect(() => {
    snapshotRef.current = getSnapshot;
  }, [getSnapshot]);

  useEffect(() => {
    onRestoreRef.current = onRestore;
  }, [onRestore]);

  // Restore once per draftKey. `onRestore` is read through a ref so an
  // inline/unstable callback from the caller does NOT enter the deps: doing
  // so re-ran this effect every render, repeatedly merging the (up to
  // intervalMs stale) saved draft over freshly typed answers — silently
  // truncating submissions and triggering React error #185.
  useEffect(() => {
    if (!enabled || !draftKey) return undefined;
    const saved = loadCounselorDraft(draftKey);
    if (saved && onRestoreRef.current) {
      onRestoreRef.current(saved);
    }
    return undefined;
  }, [draftKey, enabled]);

  const persist = useCallback(() => {
    if (!enabled || !draftKey) return;
    saveCounselorDraft(draftKey, snapshotRef.current());
  }, [draftKey, enabled]);

  useEffect(() => {
    if (!enabled || !draftKey) return undefined;
    const timer = setInterval(persist, intervalMs);
    return () => clearInterval(timer);
  }, [draftKey, enabled, intervalMs, persist]);

  const clear = useCallback(() => {
    if (draftKey) clearCounselorDraft(draftKey);
  }, [draftKey]);

  return { persistDraft: persist, clearDraft: clear };
}
