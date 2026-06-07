/** Resolve admin program chip/select id to API ``program`` query (slug preferred). */
export function programQueryParam(programId, programs) {
  if (!programId) return undefined;
  const match = programs.find((p) => String(p.id) === String(programId));
  return match?.slug || programId;
}
