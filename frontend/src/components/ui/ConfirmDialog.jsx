import { useState } from 'react';
import Modal from './Modal';
import Button from './Button';
import Note from './Note';

/**
 * The one confirmation surface for destructive admin actions.
 *
 * Confirmation is proportional to consequence: `consequences` spells out
 * what will happen in the director's words, `reassurance` says what is
 * *not* destroyed, and `requireTypedConfirmation` gates the truly
 * irreversible ones (deleting a program) behind typing its name.
 *
 * `alternativeLabel` offers the softer action — "Set an end date instead"
 * — because removing a member is usually the wrong tool for someone
 * leaving partway through a year.
 */
export default function ConfirmDialog({
  title,
  description,
  confirmLabel = 'Confirm',
  cancelLabel = 'Cancel',
  tone = 'danger',
  consequences,
  reassurance,
  requireTypedConfirmation,
  alternativeLabel,
  onAlternative,
  onConfirm,
  onClose,
  busy = false,
  children,
  ...rest
}) {
  const [typed, setTyped] = useState('');

  const typedOk =
    !requireTypedConfirmation ||
    typed.trim().toLowerCase() === String(requireTypedConfirmation).trim().toLowerCase();

  return (
    <Modal
      title={title}
      description={description}
      onClose={onClose}
      dismissible={!busy}
      width="md"
      footer={
        <>
          <Button variant="secondary" onClick={onClose} disabled={busy}>
            {cancelLabel}
          </Button>
          <div className="flex-1" />
          {alternativeLabel && onAlternative && (
            <Button variant="secondary" onClick={onAlternative} disabled={busy}>
              {alternativeLabel}
            </Button>
          )}
          <Button
            variant={tone === 'danger' ? 'danger' : 'primary'}
            className={
              tone === 'danger'
                ? 'border border-red-200 dark:border-red-900'
                : undefined
            }
            disabled={busy || !typedOk}
            onClick={onConfirm}
            data-testid="confirm-dialog-confirm"
          >
            {busy ? 'Working…' : confirmLabel}
          </Button>
        </>
      }
      data-testid="confirm-dialog"
      {...rest}
    >
      <div className="space-y-3">
        {reassurance && (
          <Note tone="ok" data-testid="confirm-dialog-reassurance">
            {reassurance}
          </Note>
        )}
        {consequences?.length > 0 && (
          <div>
            <p className="text-sm text-gray-700 dark:text-gray-300">This will:</p>
            <ul className="mt-1.5 list-disc pl-5 space-y-1 text-sm text-gray-600 dark:text-gray-400">
              {consequences.map((line) => (
                <li key={line}>{line}</li>
              ))}
            </ul>
          </div>
        )}
        {children}
        {requireTypedConfirmation && (
          <label className="block text-sm text-gray-700 dark:text-gray-300">
            Type <strong>{requireTypedConfirmation}</strong> to confirm
            <input
              value={typed}
              onChange={(e) => setTyped(e.target.value)}
              data-testid="confirm-dialog-typed"
              autoComplete="off"
              className="mt-1 block w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm text-gray-900 dark:text-white"
            />
          </label>
        )}
      </div>
    </Modal>
  );
}
