const STORAGE_KEY = 'postAuthRedirect';

export function safeNextPath(next) {
  if (next == null || typeof next !== 'string') return '/dashboard';
  const trimmed = next.trim();
  if (!trimmed.startsWith('/') || trimmed.startsWith('//')) return '/dashboard';
  if (trimmed.includes('://') || trimmed.includes('\\')) return '/dashboard';
  return trimmed;
}

/** Remember intended path when user leaves for OAuth (Google) from sign-in. */
export function persistNextForOAuth(searchString) {
  try {
    const raw = new URLSearchParams(searchString || '').get('next');
    if (raw) sessionStorage.setItem(STORAGE_KEY, raw);
  } catch {
    /* quota / private mode */
  }
}

/**
 * Prefer ?next= from current URL (password login); otherwise use sessionStorage (OAuth return).
 * Clears stored value after read.
 */
export function consumePostLoginPath(searchString) {
  try {
    const q = new URLSearchParams(searchString || '').get('next');
    if (q) {
      sessionStorage.removeItem(STORAGE_KEY);
      return safeNextPath(q);
    }
    const stored = sessionStorage.getItem(STORAGE_KEY);
    sessionStorage.removeItem(STORAGE_KEY);
    return safeNextPath(stored);
  } catch {
    return '/dashboard';
  }
}
