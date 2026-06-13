export const ADMIN_PROGRAM_STORAGE_KEY = 'bunklogs.admin.selectedProgramId';

/** Resolve a program id or slug to a numeric program id string. */
export function resolveProgramId(programRef, programs) {
  if (!programRef || !programs?.length) return '';
  const ref = String(programRef).trim();
  const byId = programs.find((p) => String(p.id) === ref);
  if (byId) return String(byId.id);
  const bySlug = programs.find((p) => p.slug === ref);
  if (bySlug) return String(bySlug.id);
  return '';
}

export function readStoredProgramId() {
  try {
    return sessionStorage.getItem(ADMIN_PROGRAM_STORAGE_KEY) || '';
  } catch {
    return '';
  }
}

export function writeStoredProgramId(programId) {
  try {
    if (programId) {
      sessionStorage.setItem(ADMIN_PROGRAM_STORAGE_KEY, String(programId));
    } else {
      sessionStorage.removeItem(ADMIN_PROGRAM_STORAGE_KEY);
    }
  } catch {
    // ignore private browsing / blocked storage
  }
}

/**
 * Pick the admin program id to preselect: URL ?program=, then session
 * storage (set by other admin pages), then the newest active program.
 */
export function resolveInitialProgramId({ urlProgramId, storedProgramId, programs }) {
  const fromUrl = resolveProgramId(urlProgramId, programs);
  if (fromUrl) return fromUrl;
  const fromStorage = resolveProgramId(storedProgramId, programs);
  if (fromStorage) return fromStorage;
  const active = programs.filter((p) => p.is_active);
  const sorted = [...active].sort(
    (a, b) => (b.start_date || '').localeCompare(a.start_date || ''),
  );
  if (sorted[0]) return String(sorted[0].id);
  if (programs[0]) return String(programs[0].id);
  return '';
}
