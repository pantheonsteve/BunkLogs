/**
 * Merge subject dashboard payload reflections + observations into one list.
 */

import api from '../../api';

function entrySortKey(isoDateOrDatetime) {
  if (!isoDateOrDatetime) return 0;
  return new Date(isoDateOrDatetime).getTime();
}

export function flattenSubjectEntries(payload) {
  if (!payload) return [];
  const entries = [];

  for (const block of payload.templates ?? []) {
    const template = block.template ?? {};
    const schemaFields = block.schema_fields ?? [];
    for (const reflection of block.reflections ?? []) {
      entries.push({
        kind: 'reflection',
        id: reflection.id,
        sortKey: entrySortKey(reflection.date),
        date: reflection.date,
        template,
        schemaFields,
        reflection,
      });
    }
  }

  for (const observation of payload.observations ?? []) {
    entries.push({
      kind: 'observation',
      id: observation.id,
      sortKey: entrySortKey(observation.observed_at || observation.created_at),
      date: (observation.observed_at || observation.created_at || '').slice(0, 10),
      observation,
    });
  }

  return entries.sort((a, b) => b.sortKey - a.sortKey);
}

export function subjectEntriesExportUrl(personId, { start, end } = {}) {
  const params = new URLSearchParams();
  if (start) params.set('date_start', start);
  if (end) params.set('date_end', end);
  const qs = params.toString();
  return `/api/v1/dashboards/subject/${personId}/export/${qs ? `?${qs}` : ''}`;
}

/** Fetch CSV with JWT + org headers, then trigger a browser download. */
export async function downloadSubjectEntriesExport(
  personId,
  { start, end, subjectName } = {},
) {
  const params = {};
  if (start) params.date_start = start;
  if (end) params.date_end = end;
  let resp;
  try {
    resp = await api.get(
      `/api/v1/dashboards/subject/${personId}/export/`,
      { params, responseType: 'blob' },
    );
  } catch (e) {
    const blob = e.response?.data;
    if (blob instanceof Blob) {
      try {
        const json = JSON.parse(await blob.text());
        const err = new Error(json.detail || 'Export failed');
        err.response = { ...e.response, data: json };
        throw err;
      } catch (parseErr) {
        if (parseErr.response) throw parseErr;
      }
    }
    throw e;
  }
  const disposition = resp.headers['content-disposition'] || '';
  const match = disposition.match(/filename="([^"]+)"/);
  const slug = (subjectName || `subject_${personId}`)
    .trim()
    .replace(/[^\w\-]+/g, '_')
    .replace(/_+/g, '_')
    .replace(/^_|_$/g, '') || `subject_${personId}`;
  const rangePart = start && end ? `_${start}_${end}` : '';
  const filename = match?.[1] || `${slug}_entries${rangePart}.csv`;
  const url = window.URL.createObjectURL(resp.data);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  window.URL.revokeObjectURL(url);
}

export const downloadSubjectEntriesCsv = downloadSubjectEntriesExport;

export function subjectEntriesPageLink(personId, { start, end, extraSearch = '' } = {}) {
  const params = new URLSearchParams(extraSearch);
  if (start) params.set('date_start', start);
  else params.delete('date_start');
  if (end) params.set('date_end', end);
  else params.delete('date_end');
  const qs = params.toString();
  return `/profile/${personId}/entries${qs ? `?${qs}` : ''}`;
}
