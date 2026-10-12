/**
 * Derivations over one bunk's `/dashboards/group/<id>/` payload for the
 * supervisor home. Read-only: completion counts rostered on-camp rows the
 * same way BunkDashboard does, and averages cover submitted rows only.
 */

const SCORED_TYPES = new Set(['single_rating', 'rating_group']);
const NOTE_TYPES = new Set(['textarea', 'text']);

export function camperShortName(c) {
  if (!c) return '';
  const first = c.preferred_name || c.first_name || '';
  const lastInitial = (c.last_name || '').slice(0, 1);
  return lastInitial ? `${first} ${lastInitial}.` : first;
}

export function scoredColumns(payload) {
  return (payload?.score_grid?.columns || []).filter((c) => SCORED_TYPES.has(c.field_type));
}

export function columnLabel(col) {
  if (col.header) return col.header;
  if (col.field_type === 'rating_group' && col.category_key) {
    return col.category_key.charAt(0).toUpperCase() + col.category_key.slice(1);
  }
  return col.field_key || col.label;
}

export function noteExcerpt(payload, cells, max = 160) {
  const col = (payload?.score_grid?.columns || []).find((c) => NOTE_TYPES.has(c.field_type));
  const raw = col ? cells?.[col.label] : null;
  if (raw == null || raw === '') return '';
  const text = String(raw)
    .replace(/<[^>]*>/g, ' ')
    .replace(/&nbsp;/g, ' ')
    .replace(/&amp;/g, '&')
    .replace(/\s+/g, ' ')
    .trim();
  return text.length > max ? `${text.slice(0, max - 1)}…` : text;
}

export function bunkStats(payload) {
  const rows = payload?.score_grid?.rows || [];
  const offIds = new Set((payload?.off_camp || []).map((c) => c.id));
  const expectedRows = rows.filter((r) => !offIds.has(r.camper?.id));
  const submittedRows = expectedRows.filter((r) => r.reflection_id != null);
  const averages = scoredColumns(payload).map((col) => {
    const values = submittedRows
      .map((r) => r.cells?.[col.label])
      .filter((v) => typeof v === 'number');
    const value = values.length
      ? Math.round((values.reduce((s, v) => s + v, 0) / values.length) * 10) / 10
      : null;
    return { label: columnLabel(col), value, scaleMax: col.scale_max || 5 };
  });
  const flagged = new Set([
    ...(payload?.help_requested || []).map((c) => c.id),
    ...(payload?.camper_care_help_requested || []).map((c) => c.id),
  ]);
  return {
    camperCount: rows.length,
    done: submittedRows.length,
    total: expectedRows.length,
    averages,
    flags: flagged.size,
  };
}
