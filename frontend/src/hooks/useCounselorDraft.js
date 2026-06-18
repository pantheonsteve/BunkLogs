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

  useEffect(() => {
    snapshotRef.current = getSnapshot;
  }, [getSnapshot]);

  useEffect(() => {
    if (!enabled || !draftKey) return undefined;
    const saved = loadCounselorDraft(draftKey);
    if (saved && onRestore) {
      onRestore(saved);
    }
    return undefined;
  }, [draftKey, enabled, onRestore]);

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
