import { useCallback, useEffect, useRef, useState } from 'react';

const DEFAULT_DURATION_MS = 4000;

/**
 * Bottom-centered pill toast. Matches the style we standardized on
 * across the new admin pages (GroupList, GroupDetail, FieldKey).
 *
 * Pair with `useToast()` for the standard auto-dismiss pattern:
 *
 *   const { toast, showToast } = useToast();
 *   ...
 *   <Toast message={toast} data-testid="my-toast" />
 *
 * If `message` is empty/null/undefined the component renders nothing.
 */
export default function Toast({ message, ...rest }) {
  if (!message) return null;
  return (
    <div
      role="status"
      className="fixed bottom-6 left-1/2 -translate-x-1/2 bg-gray-900 dark:bg-gray-100 text-white dark:text-gray-900 text-sm px-5 py-2.5 rounded-full shadow-lg z-50"
      {...rest}
    >
      {message}
    </div>
  );
}

/**
 * Tiny hook that owns the "set a message, auto-hide after N ms" pattern.
 * Returns the current message and helpers to show/clear it.
 */
export function useToast(durationMs = DEFAULT_DURATION_MS) {
  const [toast, setToast] = useState('');
  const timerRef = useRef(null);

  const clearToast = useCallback(() => {
    if (timerRef.current) {
      clearTimeout(timerRef.current);
      timerRef.current = null;
    }
    setToast('');
  }, []);

  const showToast = useCallback(
    (msg) => {
      if (timerRef.current) clearTimeout(timerRef.current);
      setToast(msg);
      timerRef.current = setTimeout(() => {
        setToast('');
        timerRef.current = null;
      }, durationMs);
    },
    [durationMs],
  );

  useEffect(
    () => () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    },
    [],
  );

  return { toast, showToast, clearToast };
}
