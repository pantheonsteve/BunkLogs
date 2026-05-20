import { STATUS_BADGE_LABELS } from './OrderStatusBadge';

/**
 * Step 7_2 — chronological activity log for an order or maintenance ticket.
 *
 * Pure presentational. Consumers pass the events array returned by the
 * transition / correct-last endpoints under `response.data.activity`.
 *
 * @param {{ events: Array<{
 *   id: string,
 *   event_type: string,
 *   from_state: string,
 *   to_state: string,
 *   note: string,
 *   reason: string,
 *   actor_name?: string|null,
 *   correction_of?: string|null,
 *   created_at: string,
 * }> }} props
 */
function formatLine(e) {
  const fromLabel = STATUS_BADGE_LABELS[e.from_state] || e.from_state;
  const toLabel = STATUS_BADGE_LABELS[e.to_state] || e.to_state;
  if (e.event_type === 'correction') {
    return `Correction: ${fromLabel} → ${toLabel}`;
  }
  if (e.event_type === 'note') {
    return 'Note added';
  }
  if (e.from_state) {
    return `${fromLabel} → ${toLabel}`;
  }
  return toLabel;
}

function formatTime(iso) {
  if (!iso) return '';
  try {
    const d = new Date(iso);
    return d.toLocaleString();
  } catch {
    return iso;
  }
}

export default function OrderActivityList({ events = [] }) {
  if (!events.length) {
    return (
      <p
        data-testid="order-activity-empty"
        className="text-sm italic text-gray-500"
      >
        No activity yet.
      </p>
    );
  }

  return (
    <ol
      data-testid="order-activity-list"
      className="space-y-2 border-l border-gray-200 pl-4 dark:border-gray-700"
    >
      {events.map((e) => (
        <li
          key={e.id}
          data-testid="order-activity-event"
          data-event-type={e.event_type}
          className="text-sm text-gray-700 dark:text-gray-200"
        >
          <div className="flex items-center justify-between gap-2">
            <span className="font-medium">{formatLine(e)}</span>
            <time className="text-xs text-gray-500" dateTime={e.created_at}>
              {formatTime(e.created_at)}
            </time>
          </div>
          {e.actor_name && (
            <div className="text-xs text-gray-500">{e.actor_name}</div>
          )}
          {e.reason && (
            <div className="mt-1 text-sm">
              <span className="font-medium">Reason: </span>
              {e.reason}
            </div>
          )}
          {e.note && (
            <div className="mt-1 text-sm">
              <span className="font-medium">Note: </span>
              {e.note}
            </div>
          )}
        </li>
      ))}
    </ol>
  );
}
