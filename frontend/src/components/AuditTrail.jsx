import useAuditTrail from '../hooks/useAuditTrail';
import isSuperAdmin from '../utils/auth/isSuperAdmin';

/**
 * Step 7_4 — Admin-only chronological audit trail for a content row.
 *
 * Renders nothing for non-Admin users (org admins / Super Admins only).
 * The hook is the source of truth for the data fetch; this component is
 * thin presentation + role gating.
 *
 * @param {{
 *   user: object|null,
 *   isAdmin?: boolean,
 *   contentType: string,
 *   contentId: string|number,
 *   emptyMessage?: string,
 * }} props
 *   `user` is the canonical "me" payload (used to derive Super Admin
 *   status). `isAdmin` is an explicit gate for tenant Admins detected
 *   elsewhere (e.g. via membership lookup); either flag lets the trail
 *   render. Callers in non-admin views should just omit the component.
 */
const EVENT_LABELS = Object.freeze({
  created: 'Created',
  edited: 'Edited',
  state_changed: 'State changed',
  deactivated: 'Deactivated',
  reactivated: 'Reactivated',
  override_edit: 'Admin override: edit',
  override_close: 'Admin override: close',
  override_resolve: 'Admin override: resolve',
  audit_view: 'Audit trail viewed',
  export: 'Exported',
});

function eventLabel(eventType) {
  return EVENT_LABELS[eventType] || eventType;
}

function formatTime(iso) {
  if (!iso) return '';
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return iso;
  }
}

function renderStateSummary(event) {
  const { event_type: type, before_state: before, after_state: after } = event;
  if (type === 'state_changed') {
    const from = before?.status || '—';
    const to = after?.status || '—';
    return (
      <span data-testid="audit-state-change">{from} → {to}</span>
    );
  }
  if ((type === 'edited' || type === 'override_edit') && (before || after)) {
    return (
      <details className="text-xs text-gray-600 dark:text-gray-300">
        <summary className="cursor-pointer">View diff</summary>
        <div className="mt-1 grid gap-2 text-xs sm:grid-cols-2">
          <pre className="overflow-x-auto rounded bg-gray-50 p-2 dark:bg-gray-800">
            {JSON.stringify(before ?? {}, null, 2)}
          </pre>
          <pre className="overflow-x-auto rounded bg-gray-50 p-2 dark:bg-gray-800">
            {JSON.stringify(after ?? {}, null, 2)}
          </pre>
        </div>
      </details>
    );
  }
  return null;
}

export default function AuditTrail({
  user,
  isAdmin = false,
  contentType,
  contentId,
  emptyMessage = 'No audit events yet.',
}) {
  const canSee = isAdmin || isSuperAdmin(user);
  const { events, isLoading, error } = useAuditTrail({
    contentType,
    contentId,
    autoLoad: canSee,
  });

  if (!canSee) return null;

  if (isLoading) {
    return (
      <p data-testid="audit-trail-loading" className="text-sm italic text-gray-500">
        Loading audit trail…
      </p>
    );
  }
  if (error) {
    return (
      <p data-testid="audit-trail-error" className="text-sm text-red-600">
        Failed to load audit trail.
      </p>
    );
  }
  if (!events.length) {
    return (
      <p data-testid="audit-trail-empty" className="text-sm italic text-gray-500">
        {emptyMessage}
      </p>
    );
  }

  return (
    <ol
      data-testid="audit-trail"
      data-content-type={contentType}
      data-content-id={String(contentId)}
      className="space-y-2 border-l border-gray-200 pl-4 dark:border-gray-700"
    >
      {events.map((e) => (
        <li
          key={e.id}
          data-testid="audit-event"
          data-event-type={e.event_type}
          data-admin-override={e.is_admin_override ? 'true' : 'false'}
          className="text-sm text-gray-700 dark:text-gray-200"
        >
          <div className="flex items-center justify-between gap-2">
            <span className="font-medium">{eventLabel(e.event_type)}</span>
            <time className="text-xs text-gray-500" dateTime={e.created_at}>
              {formatTime(e.created_at)}
            </time>
          </div>
          {renderStateSummary(e)}
          {e.reason_note && (
            <div className="mt-1 text-sm">
              <span className="font-medium">Reason: </span>
              {e.reason_note}
            </div>
          )}
        </li>
      ))}
    </ol>
  );
}
