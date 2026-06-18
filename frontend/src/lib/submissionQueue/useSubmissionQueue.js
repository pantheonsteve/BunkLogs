import { useEffect, useState, useCallback } from 'react';
import {
  drainQueue,
  getPendingEntries,
  subscribe,
} from './queue';

export function useSubmissionQueue() {
  const [pending, setPending] = useState([]);

  const refresh = useCallback(async () => {
    const entries = await getPendingEntries();
    setPending(entries);
  }, []);

  useEffect(() => {
    refresh();
    return subscribe(refresh);
  }, [refresh]);

  return {
    pending,
    pendingCount: pending.length,
    refresh,
    drain: drainQueue,
  };
}
