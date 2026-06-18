export class QueuedSubmissionError extends Error {
  constructor(message = 'Saved on this device — we\'ll send when connected.', cause) {
    super(message);
    this.name = 'QueuedSubmissionError';
    this.cause = cause;
    this.queued = true;
  }
}

export class SessionExpiredDraftSavedError extends Error {
  constructor(message = 'Session expired — your answers are saved. Please sign in again.') {
    super(message);
    this.name = 'SessionExpiredDraftSavedError';
  }
}
