const PREFIX = 'counselorDraft';

export function camperReflectionDraftKey(subjectId, date) {
  return `${PREFIX}:camper:${subjectId}:${date}`;
}

export function selfReflectionDraftKey(date) {
  return `${PREFIX}:self:${date}`;
}

export function camperCareDraftKey(draftId) {
  return `${PREFIX}:camper-care:${draftId}`;
}

export function maintenanceDraftKey(draftId) {
  return `${PREFIX}:maintenance:${draftId}`;
}

export function loadCounselorDraft(key) {
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

export function saveCounselorDraft(key, payload) {
  try {
    localStorage.setItem(
      key,
      JSON.stringify({ ...payload, updatedAt: Date.now() }),
    );
  } catch {
    /* quota / private mode */
  }
}

export function clearCounselorDraft(key) {
  try {
    localStorage.removeItem(key);
  } catch {
    /* ignore */
  }
}
