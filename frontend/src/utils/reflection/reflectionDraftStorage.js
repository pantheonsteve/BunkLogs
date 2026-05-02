export function reflectionDraftKey(templateId, periodStart, periodEnd) {
  return `reflectionDraft:${templateId}:${periodStart}:${periodEnd}`;
}

export function loadReflectionDraft(key) {
  try {
    const raw = localStorage.getItem(key);
    if (!raw) return null;
    const data = JSON.parse(raw);
    if (!data || typeof data !== 'object') return null;
    return data;
  } catch {
    return null;
  }
}

export function saveReflectionDraft(key, payload) {
  try {
    localStorage.setItem(key, JSON.stringify(payload));
  } catch {
    /* quota / private mode */
  }
}

export function clearReflectionDraft(key) {
  try {
    localStorage.removeItem(key);
  } catch {
    /* ignore */
  }
}
