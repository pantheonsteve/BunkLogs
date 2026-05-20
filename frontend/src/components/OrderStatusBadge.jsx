import { ORDER_STATES } from '../hooks/useOrderStateMachine';

/**
 * Step 7_2 — colour-distinct status pill, reusable across Camper Care orders
 * and Maintenance tickets. Status labels and colour classes intentionally
 * mirror the canonical product spec
 * (`docs/user_stories/00_cross_cutting/order_state_machine.md`).
 *
 * @param {{ status: string }} props
 */
const STATUS_LABELS = {
  [ORDER_STATES.NEW]: 'New',
  [ORDER_STATES.IN_PROGRESS]: 'In Progress',
  [ORDER_STATES.FULFILLED]: 'Fulfilled',
  [ORDER_STATES.UNABLE_TO_FULFILL]: 'Unable to Fulfill',
};

const STATUS_CLASSES = {
  [ORDER_STATES.NEW]:
    'bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-200',
  [ORDER_STATES.IN_PROGRESS]:
    'bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-200',
  [ORDER_STATES.FULFILLED]:
    'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-200',
  [ORDER_STATES.UNABLE_TO_FULFILL]:
    'bg-rose-100 text-rose-800 dark:bg-rose-900/40 dark:text-rose-200',
};

export default function OrderStatusBadge({ status }) {
  const label = STATUS_LABELS[status] || status || 'Unknown';
  const tone = STATUS_CLASSES[status] || 'bg-gray-100 text-gray-700';
  return (
    <span
      data-testid="order-status-badge"
      data-status={status || 'unknown'}
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${tone}`}
    >
      {label}
    </span>
  );
}

export const STATUS_BADGE_LABELS = STATUS_LABELS;
