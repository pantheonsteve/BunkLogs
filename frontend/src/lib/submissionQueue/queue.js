/**
 * IndexedDB-backed offline submission queue for network-tolerant writes.
 */

import api from '../../api';
import {
  BACKOFF_MS,
  DRAIN_INTERVAL_MS,
  ENTRY_STATUS,
  MAX_QUEUE_ENTRIES,
  SUBMISSION_KIND,
} from './constants';
import {
  deleteEntry,
  listEntries,
  listPendingEntries,
  putEntry,
} from './db';
import { QueuedSubmissionError } from './errors';

const listeners = new Set();
let drainTimer = null;
let draining = false;

function notify() {
  listeners.forEach((fn) => {
    try {
      fn();
    } catch (_) {
      /* ignore subscriber errors */
    }
  });
}

export function subscribe(listener) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export function isRetryableError(err) {
  if (!err) return false;
  if (err.response) {
    const status = err.response.status;
    if (status === 401 || status === 403 || status === 400 || status === 404) {
      return false;
    }
    return status >= 500 || status === 408 || status === 429;
  }
  return !err.response;
}

export function isQueuedSubmissionError(err) {
  return err?.name === 'QueuedSubmissionError' || err?.queued === true;
}

function newEntryId() {
  if (typeof crypto !== 'undefined' && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  return `q-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

async function enforceQueueCap() {
  const all = await listEntries();
  const pending = all.filter((e) => e.status === ENTRY_STATUS.PENDING);
  if (pending.length <= MAX_QUEUE_ENTRIES) return;
  pending.sort((a, b) => a.createdAt - b.createdAt);
  const overflow = pending.length - MAX_QUEUE_ENTRIES;
  for (let i = 0; i < overflow; i += 1) {
    await deleteEntry(pending[i].id);
  }
}

export async function persistPending({
  kind,
  clientSubmissionId,
  metadata = {},
  payload = null,
  photoBlobs = [],
}) {
  const entry = {
    id: newEntryId(),
    kind,
    clientSubmissionId,
    metadata,
    payload,
    photoBlobs: await serializeBlobs(photoBlobs),
    status: ENTRY_STATUS.PENDING,
    createdAt: Date.now(),
    nextRetryAt: 0,
    retryCount: 0,
    lastError: '',
  };
  await putEntry(entry);
  await enforceQueueCap();
  notify();
  return entry.id;
}

export async function markConfirmed(entryId) {
  if (!entryId) return;
  await deleteEntry(entryId);
  notify();
}

export async function discard(entryId) {
  if (!entryId) return;
  await deleteEntry(entryId);
  notify();
}

async function serializeBlobs(files) {
  if (!files?.length) return [];
  const out = [];
  for (const file of files) {
    try {
      const buffer = await file.arrayBuffer();
      out.push({
        name: file.name,
        type: file.type,
        buffer,
      });
    } catch (_) {
      /* skip unreadable blob */
    }
  }
  return out;
}

function blobsToFiles(photoBlobs) {
  if (!photoBlobs?.length) return [];
  return photoBlobs.map(({ name, type, buffer }) => new File([buffer], name, { type }));
}

export async function getPendingEntries() {
  return listPendingEntries();
}

export async function getPendingByKind(kind) {
  const pending = await listPendingEntries();
  return pending.filter((e) => e.kind === kind);
}

export function hasPendingCamperReflection(subjectId, date) {
  return listPendingEntries().then((entries) =>
    entries.some(
      (e) =>
        e.kind === SUBMISSION_KIND.CAMPER_REFLECTION
        && String(e.metadata?.subjectId) === String(subjectId)
        && e.metadata?.date === date,
    ),
  );
}

export function hasPendingSelfReflection(date) {
  return listPendingEntries().then((entries) =>
    entries.some(
      (e) => e.kind === SUBMISSION_KIND.SELF_REFLECTION && e.metadata?.date === date,
    ),
  );
}

export function listPendingRequestEntries() {
  return listPendingEntries().then((entries) =>
    entries.filter(
      (e) =>
        e.kind === SUBMISSION_KIND.CAMPER_CARE_REQUEST
        || e.kind === SUBMISSION_KIND.MAINTENANCE_TICKET,
    ),
  );
}

async function executeEntry(entry) {
  switch (entry.kind) {
    case SUBMISSION_KIND.CAMPER_REFLECTION: {
      const p = entry.payload;
      const res = await api.post('/api/v1/counselor/camper-reflections/', {
        subject_id: p.subjectId,
        assignment_group_id: p.assignmentGroupId,
        answers: p.answers,
        language: p.language,
        team_visibility: p.teamVisibility,
        client_submission_id: entry.clientSubmissionId,
      });
      return { data: res.data, status: res.status };
    }
    case SUBMISSION_KIND.SELF_REFLECTION: {
      const p = entry.payload;
      const body = {
        day_off: !!p.dayOff,
        language: p.language,
        client_submission_id: entry.clientSubmissionId,
      };
      if (!p.dayOff) body.answers = p.answers || {};
      const res = await api.post('/api/v1/counselor/self-reflection/', body);
      return { data: res.data, status: res.status };
    }
    case SUBMISSION_KIND.CAMPER_CARE_REQUEST: {
      const p = entry.payload;
      const res = await api.post('/api/v1/counselor/camper-care-requests/', {
        ...p,
        client_submission_id: entry.clientSubmissionId,
      });
      return { data: res.data, status: res.status };
    }
    case SUBMISSION_KIND.MAINTENANCE_TICKET: {
      const p = entry.payload;
      const form = new FormData();
      form.append('location', p.location);
      form.append('category', p.category);
      form.append('description', p.description || '');
      form.append('urgency', p.urgency);
      if (p.urgentReason) form.append('urgent_reason', p.urgentReason);
      form.append('client_submission_id', entry.clientSubmissionId);
      blobsToFiles(entry.photoBlobs).forEach((file) => {
        form.append('photos', file);
      });
      const res = await api.post('/api/v1/counselor/maintenance-tickets/', form, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      return { data: res.data, status: res.status };
    }
    case SUBMISSION_KIND.OBSERVATION: {
      const p = entry.payload;
      const res = await api.post('/api/v1/observations/', {
        ...p,
        client_submission_id: entry.clientSubmissionId,
      });
      return { data: res.data, status: res.status };
    }
    default:
      throw new Error(`Unknown queue kind: ${entry.kind}`);
  }
}

function successStatus(status) {
  return status === 200 || status === 201;
}

export async function drainQueue() {
  if (draining) return;
  if (typeof navigator !== 'undefined' && navigator.onLine === false) return;

  draining = true;
  try {
    const pending = await listPendingEntries();
    const now = Date.now();
    for (const entry of pending) {
      if (entry.nextRetryAt && entry.nextRetryAt > now) continue;
      try {
        const result = await executeEntry(entry);
        if (successStatus(result.status)) {
          await deleteEntry(entry.id);
          notify();
        }
      } catch (err) {
        if (!isRetryableError(err)) {
          entry.status = ENTRY_STATUS.FAILED;
          entry.lastError = err?.message || 'Submit failed';
          await putEntry(entry);
          notify();
          continue;
        }
        entry.retryCount = (entry.retryCount || 0) + 1;
        const backoff = BACKOFF_MS[
          Math.min(entry.retryCount - 1, BACKOFF_MS.length - 1)
        ];
        entry.nextRetryAt = Date.now() + backoff;
        entry.lastError = err?.message || 'Network error';
        await putEntry(entry);
        notify();
      }
    }
  } finally {
    draining = false;
  }
}

export function startQueueDrainLoop() {
  if (drainTimer) return;
  drainQueue();
  drainTimer = setInterval(drainQueue, DRAIN_INTERVAL_MS);
  if (typeof window !== 'undefined') {
    window.addEventListener('online', drainQueue);
  }
}

export function stopQueueDrainLoop() {
  if (drainTimer) {
    clearInterval(drainTimer);
    drainTimer = null;
  }
  if (typeof window !== 'undefined') {
    window.removeEventListener('online', drainQueue);
  }
}

/**
 * Persist then attempt immediate POST. On retryable failure, leave pending.
 */
export async function submitWithQueue({
  kind,
  clientSubmissionId,
  metadata = {},
  payload = null,
  photoBlobs = [],
  execute,
}) {
  const entryId = await persistPending({
    kind,
    clientSubmissionId,
    metadata,
    payload,
    photoBlobs,
  });

  try {
    const result = await execute();
    if (successStatus(result.status)) {
      await markConfirmed(entryId);
      return result;
    }
    const err = new Error(`Unexpected status ${result.status}`);
    err.response = { status: result.status };
    throw err;
  } catch (err) {
    if (err?.response?.status === 401) {
      await discard(entryId);
      throw err;
    }
    if (isRetryableError(err)) {
      drainQueue();
      throw new QueuedSubmissionError(undefined, err);
    }
    await discard(entryId);
    throw err;
  }
}

export { SUBMISSION_KIND };
