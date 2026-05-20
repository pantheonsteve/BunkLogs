import isSuperAdmin from '../utils/auth/isSuperAdmin';

/**
 * Step 7_4 — "Edited [time]" indicator for content read views.
 *
 * Per the canonical spec:
 * - Authors / supervisors / co-counselors see *only* the timestamp (no editor
 *   identity, no prior version).
 * - Admins / Super Admins also see the editor's name when known, and the
 *   indicator becomes a clickable affordance the caller can link to the full
 *   <AuditTrail/> (rendered via the `onOpenAuditTrail` callback).
 *
 * Renders nothing when no edit metadata is available, so it's safe to drop
 * into any read view unconditionally.
 *
 * @param {{
 *   user?: object|null,
 *   isAdmin?: boolean,
 *   editedAt?: string|null,
 *   editorName?: string|null,
 *   onOpenAuditTrail?: () => void,
 *   showEditor?: boolean,
 * }} props
 *   `showEditor` defaults to true for Admin / Super Admin viewers and false
 *   for everyone else. Pass it explicitly to override (e.g. UH viewing
 *   their own team's reflections).
 */
function formatTime(iso) {
  if (!iso) return '';
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return iso;
  }
}

export default function EditedIndicator({
  user,
  isAdmin = false,
  editedAt,
  editorName,
  onOpenAuditTrail,
  showEditor,
}) {
  if (!editedAt) return null;
  const adminViewer = isAdmin || isSuperAdmin(user);
  const reveal = showEditor === undefined ? adminViewer : Boolean(showEditor);

  const label = reveal && editorName
    ? `Edited ${formatTime(editedAt)} by ${editorName}`
    : `Edited ${formatTime(editedAt)}`;

  if (adminViewer && typeof onOpenAuditTrail === 'function') {
    return (
      <button
        type="button"
        data-testid="edited-indicator"
        data-admin-viewer="true"
        onClick={onOpenAuditTrail}
        className="text-xs italic text-gray-500 underline-offset-2 hover:underline dark:text-gray-400"
      >
        {label}
      </button>
    );
  }

  return (
    <span
      data-testid="edited-indicator"
      data-admin-viewer={adminViewer ? 'true' : 'false'}
      className="text-xs italic text-gray-500 dark:text-gray-400"
    >
      {label}
    </span>
  );
}
