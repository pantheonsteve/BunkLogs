import { useCallback, useMemo } from 'react';
import api from '../api';

/**
 * Step 7_2 — React hook wrapping the shared state-machine API endpoints.
 *
 * Used by the Camper Care Orders workspace (Story 23) and the Maintenance
 * queue + ticket detail (Stories 32, 33, 34). The hook is intentionally thin:
 * UI components own the optimistic update / re-render orchestration via the
 * returned promises.
 *
 * @param {{ contentType?: 'order'|'maintenance_ticket',
 *           contentId?: string,
 *           status?: string,
 *           lastTransitionAt?: string|null,
 *           availableTransitions?: string[] }} content
 *   Snapshot of the current order/ticket. Provide `contentType` and
 *   `contentId` for instance-scoped operations; omit them for the bulk
 *   helper (which still requires `contentType`).
 *
 * @returns {{
 *   availableTransitions: string[],
 *   isWithinCorrectionWindow: boolean,
 *   transitionTo: (toState: string, opts?: {note?: string, reason?: string}) => Promise,
 *   correctLast: () => Promise,
 *   bulkTransition: (ids: string[], toState: string, opts?: {note?: string, reason?: string}) => Promise,
 * }}
 */
export const ORDER_STATES = Object.freeze({
  NEW: 'new',
  IN_PROGRESS: 'in_progress',
  FULFILLED: 'fulfilled',
  UNABLE_TO_FULFILL: 'unable_to_fulfill',
});

const PATHS = {
  order: {
    transition: (id) => `/api/v1/orders/${id}/transition/`,
    correctLast: (id) => `/api/v1/orders/${id}/correct-last/`,
    bulk: '/api/v1/orders/bulk-transition/',
  },
  maintenance_ticket: {
    transition: (id) => `/api/v1/maintenance/${id}/transition/`,
    correctLast: (id) => `/api/v1/maintenance/${id}/correct-last/`,
    bulk: '/api/v1/maintenance/bulk-transition/',
  },
};

const CORRECTION_WINDOW_MS = 5 * 60 * 1000;

export function isWithinCorrectionWindow(lastTransitionAt, { now } = {}) {
  if (!lastTransitionAt) return false;
  const last = new Date(lastTransitionAt);
  if (Number.isNaN(last.getTime())) return false;
  const reference = now ?? new Date();
  return reference.getTime() - last.getTime() <= CORRECTION_WINDOW_MS;
}

export default function useOrderStateMachine({
  contentType = 'order',
  contentId,
  status,
  lastTransitionAt,
  availableTransitions,
} = {}) {
  const paths = PATHS[contentType] || PATHS.order;

  const transitionTo = useCallback(
    (toState, { note = '', reason = '' } = {}) => {
      if (!contentId) {
        return Promise.reject(
          new Error('useOrderStateMachine: contentId required for transitionTo'),
        );
      }
      return api.post(paths.transition(contentId), {
        to_state: toState,
        note,
        reason,
      });
    },
    [contentId, paths],
  );

  const correctLast = useCallback(() => {
    if (!contentId) {
      return Promise.reject(
        new Error('useOrderStateMachine: contentId required for correctLast'),
      );
    }
    return api.post(paths.correctLast(contentId), {});
  }, [contentId, paths]);

  const bulkTransition = useCallback(
    (ids, toState, { note = '', reason = '' } = {}) => {
      return api.post(paths.bulk, {
        ids,
        to_state: toState,
        note,
        reason,
      });
    },
    [paths],
  );

  const within = useMemo(
    () => isWithinCorrectionWindow(lastTransitionAt),
    [lastTransitionAt],
  );

  return {
    availableTransitions: availableTransitions || availableTransitionsFromStatus(status),
    isWithinCorrectionWindow: within,
    transitionTo,
    correctLast,
    bulkTransition,
  };
}

const TRANSITION_TABLE = {
  [ORDER_STATES.NEW]: [
    ORDER_STATES.IN_PROGRESS,
    ORDER_STATES.FULFILLED,
    ORDER_STATES.UNABLE_TO_FULFILL,
  ],
  [ORDER_STATES.IN_PROGRESS]: [
    ORDER_STATES.FULFILLED,
    ORDER_STATES.UNABLE_TO_FULFILL,
  ],
  [ORDER_STATES.FULFILLED]: [ORDER_STATES.IN_PROGRESS],
  [ORDER_STATES.UNABLE_TO_FULFILL]: [ORDER_STATES.IN_PROGRESS],
};

function availableTransitionsFromStatus(status) {
  return TRANSITION_TABLE[status] ? [...TRANSITION_TABLE[status]].sort() : [];
}
