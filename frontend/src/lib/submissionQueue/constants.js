export const QUEUE_DB_NAME = 'bunklogs-submission-queue';
export const QUEUE_STORE = 'pending';
export const MAX_QUEUE_ENTRIES = 50;
export const DRAIN_INTERVAL_MS = 30_000;
export const BACKOFF_MS = [5_000, 30_000, 120_000];

export const SUBMISSION_KIND = Object.freeze({
  CAMPER_REFLECTION: 'camper_reflection',
  SELF_REFLECTION: 'self_reflection',
  CAMPER_CARE_REQUEST: 'camper_care_request',
  MAINTENANCE_TICKET: 'maintenance_ticket',
  OBSERVATION: 'observation',
});

export const ENTRY_STATUS = Object.freeze({
  PENDING: 'pending',
  CONFIRMED: 'confirmed',
  FAILED: 'failed',
});
