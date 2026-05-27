/**
 * Flagged campers workspace — Step 7_8, Story 20.
 *
 * Sections, top to bottom:
 *   - Today (status active or followed_up, created today)
 *   - Carried over (status active or followed_up, created earlier)
 *   - Resolved (last 30d) — collapsed by default, revealed via toggle
 *
 * Each row supports three transitions (criterion 5):
 *   - Mark followed up (note optional)
 *   - Mark resolved (note required, terminal)
 *   - Reopen (note required, from resolved or followed_up)
 *
 * The transition prompt is a single shared modal so the note-capture
 * UX is consistent across the three actions.
 */

import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  fetchFlags, followUpFlag, resolveFlag, reopenFlag,
} from '../../api/camperCare';

const TRIGGER_LABELS = {
  specialist_note: 'Specialist note',
  camper_care_note: 'Camper Care note',
  reflection: 'Reflection',
};

function triggerLabel(kind) {
  if (!kind) return '';
  return TRIGGER_LABELS[kind] || kind.replace(/_/g, ' ');
}

const STATUS_LABELS = {
  active: { label: 'Active', cls: 'bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-200' },
  followed_up: { label: 'Followed up', cls: 'bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-200' },
  resolved: { label: 'Resolved', cls: 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-200' },
};

function StatusBadge({ status }) {
  const meta = STATUS_LABELS[status] || { label: status, cls: 'bg-gray-100 text-gray-700' };
  return (
    <span
      data-testid={`flag-status-${status}`}
      className={`text-xs font-medium px-2 py-0.5 rounded-full ${meta.cls}`}
    >
      {meta.label}
    </span>
  );
}

function camperLabel(c) {
  if (!c) return '';
  const first = c.preferred_name || c.first_name || '';
  const last = c.last_name || '';
  return `${first} ${last}`.trim();
}

function formatTimestamp(iso) {
  if (!iso) return '';
  try {
    return new Date(iso).toLocaleString();
  } catch (e) {
    return iso;
  }
}

function FlagRow({ flag, onAction }) {
  const raisedBy = flag.raised_by?.name || 'Unknown';
  const roleLabel = flag.raised_by?.role ? ` (${flag.raised_by.role})` : '';
  const camperId = flag.subject_camper?.id;
  const camperHref = camperId
    ? `/camper-care/campers/${camperId}?flagId=${encodeURIComponent(flag.id)}#flag-${flag.id}`
    : null;
  return (
    <li
      data-testid={`flag-row-${flag.id}`}
      data-status={flag.status}
      className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 px-4 py-3 shadow-sm"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          {camperHref ? (
            <Link
              to={camperHref}
              data-testid={`flag-camper-link-${flag.id}`}
              className="font-semibold text-gray-900 dark:text-white hover:text-blue-700 dark:hover:text-blue-300 hover:underline"
            >
              {camperLabel(flag.subject_camper)}
            </Link>
          ) : (
            <h3 className="font-semibold text-gray-900 dark:text-white">
              {camperLabel(flag.subject_camper)}
            </h3>
          )}
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
            Raised by {raisedBy}{roleLabel} · {formatTimestamp(flag.created_at)}
          </p>
        </div>
        <StatusBadge status={flag.status} />
      </div>
      {flag.trigger_content_type && (
        <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
          Source: {triggerLabel(flag.trigger_content_type)}
        </p>
      )}
      {flag.trigger_preview && (
        <blockquote
          data-testid={`flag-trigger-preview-${flag.id}`}
          className="text-sm text-gray-700 dark:text-gray-200 italic border-l-2 border-gray-300 dark:border-gray-600 pl-3 mt-2 line-clamp-3"
        >
          {flag.trigger_preview}
        </blockquote>
      )}
      <div className="flex flex-wrap gap-2 mt-3">
        {(flag.status === 'active' || flag.status === 'followed_up') && (
          <>
            <button
              type="button"
              onClick={() => onAction(flag, 'follow_up')}
              data-testid={`flag-action-follow-up-${flag.id}`}
              className="inline-flex items-center px-3 min-h-[36px] rounded-lg border border-amber-300 dark:border-amber-700 bg-amber-50 dark:bg-amber-900/30 text-sm text-amber-900 dark:text-amber-100 hover:bg-amber-100"
            >
              Mark followed up
            </button>
            <button
              type="button"
              onClick={() => onAction(flag, 'resolve')}
              data-testid={`flag-action-resolve-${flag.id}`}
              className="inline-flex items-center px-3 min-h-[36px] rounded-lg bg-blue-600 text-white text-sm hover:bg-blue-700"
            >
              Mark resolved
            </button>
          </>
        )}
        {(flag.status === 'resolved' || flag.status === 'followed_up') && (
          <button
            type="button"
            onClick={() => onAction(flag, 'reopen')}
            data-testid={`flag-action-reopen-${flag.id}`}
            className="inline-flex items-center px-3 min-h-[36px] rounded-lg border border-gray-300 dark:border-gray-700 text-sm text-gray-800 dark:text-gray-100 hover:bg-gray-50 dark:hover:bg-gray-800"
          >
            Reopen
          </button>
        )}
      </div>
    </li>
  );
}

const ACTION_META = {
  follow_up: { title: 'Mark followed up', noteRequired: false, submit: 'Mark followed up' },
  resolve: { title: 'Resolve flag', noteRequired: true, submit: 'Resolve' },
  reopen: { title: 'Reopen flag', noteRequired: true, submit: 'Reopen' },
};

function TransitionModal({ flag, action, onClose, onSubmitted }) {
  const meta = ACTION_META[action];
  const [note, setNote] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');

  if (!flag || !meta) return null;

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    if (meta.noteRequired && !note.trim()) {
      setError('A note is required for this action.');
      return;
    }
    setSubmitting(true);
    try {
      if (action === 'follow_up') {
        await followUpFlag(flag.id, { note: note.trim() });
      } else if (action === 'resolve') {
        await resolveFlag(flag.id, { note: note.trim() });
      } else if (action === 'reopen') {
        await reopenFlag(flag.id, { note: note.trim() });
      }
      onSubmitted();
    } catch (err) {
      const detail = err?.response?.data?.detail
        || err?.response?.data?.note
        || err?.message
        || 'Could not apply the transition.';
      setError(typeof detail === 'string' ? detail : JSON.stringify(detail));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-end sm:items-center justify-center bg-black/40 px-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="flag-modal-title"
      data-testid="flag-transition-modal"
    >
      <div className="w-full sm:max-w-md bg-white dark:bg-gray-900 rounded-t-2xl sm:rounded-2xl shadow-xl p-4">
        <h2 id="flag-modal-title" className="text-lg font-semibold text-gray-900 dark:text-white">
          {meta.title}
        </h2>
        <p className="text-sm text-gray-600 dark:text-gray-300 mt-1">
          {camperLabel(flag.subject_camper)}
        </p>
        <form onSubmit={handleSubmit} className="mt-3 space-y-3">
          <label className="block text-sm">
            <span className="text-gray-700 dark:text-gray-200">
              {meta.noteRequired ? 'Note (required)' : 'Note (optional)'}
            </span>
            <textarea
              value={note}
              onChange={(e) => setNote(e.target.value)}
              rows={4}
              required={meta.noteRequired}
              data-testid="flag-transition-note"
              className="mt-1 block w-full rounded-md border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:ring-2 focus:ring-blue-200"
            />
          </label>
          {error && (
            <p role="alert" className="text-sm text-red-700 dark:text-red-300" data-testid="flag-transition-error">
              {error}
            </p>
          )}
          <div className="flex items-center justify-end gap-2">
            <button
              type="button"
              onClick={onClose}
              className="inline-flex items-center px-3 min-h-[40px] rounded-lg border border-gray-300 dark:border-gray-700 text-sm text-gray-800 dark:text-gray-100"
              disabled={submitting}
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={submitting}
              data-testid="flag-transition-submit"
              className="inline-flex items-center px-4 min-h-[40px] rounded-lg bg-blue-600 text-white text-sm font-medium hover:bg-blue-700 disabled:opacity-60"
            >
              {submitting ? 'Working…' : meta.submit}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default function CamperCareFlags() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showResolved, setShowResolved] = useState(false);
  const [resolvedData, setResolvedData] = useState(null);
  const [resolvedLoading, setResolvedLoading] = useState(false);
  const [modal, setModal] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const next = await fetchFlags();
      setData(next);
      setError('');
    } catch (err) {
      const detail = err?.response?.data?.detail;
      setError(typeof detail === 'string' ? detail : err?.message || 'Failed to load flags.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const loadResolved = useCallback(async () => {
    setResolvedLoading(true);
    try {
      const next = await fetchFlags({ status: 'resolved' });
      setResolvedData(next);
    } finally {
      setResolvedLoading(false);
    }
  }, []);

  useEffect(() => {
    if (showResolved && !resolvedData) {
      loadResolved();
    }
  }, [showResolved, resolvedData, loadResolved]);

  const handleAction = (flag, action) => setModal({ flag, action });
  const handleClose = () => setModal(null);
  const handleSubmitted = () => {
    setModal(null);
    load();
    if (showResolved) loadResolved();
  };

  if (loading && !data) {
    return (
      <div className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-[96rem] mx-auto">
        <p className="text-gray-600 dark:text-gray-400">Loading flags…</p>
      </div>
    );
  }

  if (error && !data) {
    return (
      <div className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-[96rem] mx-auto">
        <div
          role="alert"
          className="rounded-xl border border-amber-200 bg-amber-50 dark:border-amber-900 dark:bg-amber-900/30 px-4 py-3 text-sm text-amber-900 dark:text-amber-100"
          data-testid="cc-flags-error"
        >
          {error}
        </div>
      </div>
    );
  }

  const items = data?.items ?? [];
  const today = data?.today;
  const todays = items.filter((f) => f.is_today);
  const carried = items.filter((f) => !f.is_today);
  const resolved = resolvedData?.items ?? [];

  return (
    <div data-testid="cc-flags" className="px-4 sm:px-6 lg:px-8 py-8 pb-24 w-full max-w-[96rem] mx-auto space-y-4">
      <header className="space-y-1">
        <h1 className="text-2xl font-semibold text-gray-900 dark:text-white">Flagged campers</h1>
        <p className="text-sm text-gray-600 dark:text-gray-400">
          Active flags routed to Camper Care across your program.
        </p>
      </header>

      <section data-testid="cc-flags-today">
        <div className="flex items-center justify-between mb-2">
          <h2 className="text-base font-semibold text-gray-900 dark:text-white">Today</h2>
          <span className="text-xs text-gray-500 dark:text-gray-400">{todays.length} active</span>
        </div>
        {todays.length === 0 ? (
          <p className="text-sm text-gray-500 dark:text-gray-400" data-testid="cc-flags-today-empty">
            No new flags today{today ? ` (${today})` : ''}.
          </p>
        ) : (
          <ul className="space-y-2">
            {todays.map((f) => (
              <FlagRow key={f.id} flag={f} onAction={handleAction} />
            ))}
          </ul>
        )}
      </section>

      <section data-testid="cc-flags-carried">
        <div className="flex items-center justify-between mb-2">
          <h2 className="text-base font-semibold text-gray-900 dark:text-white">Carried over</h2>
          <span className="text-xs text-gray-500 dark:text-gray-400">{carried.length}</span>
        </div>
        {carried.length === 0 ? (
          <p className="text-sm text-gray-500 dark:text-gray-400">No older active flags.</p>
        ) : (
          <ul className="space-y-2">
            {carried.map((f) => (
              <FlagRow key={f.id} flag={f} onAction={handleAction} />
            ))}
          </ul>
        )}
      </section>

      <section data-testid="cc-flags-resolved">
        <div className="flex items-center justify-between mb-2">
          <h2 className="text-base font-semibold text-gray-900 dark:text-white">Resolved</h2>
          <button
            type="button"
            onClick={() => setShowResolved((v) => !v)}
            data-testid="cc-flags-resolved-toggle"
            className="text-sm text-blue-700 dark:text-blue-300 hover:underline"
          >
            {showResolved ? 'Hide' : 'Show resolved'}
          </button>
        </div>
        {showResolved && (
          resolvedLoading ? (
            <p className="text-sm text-gray-500 dark:text-gray-400">Loading resolved…</p>
          ) : resolved.length === 0 ? (
            <p className="text-sm text-gray-500 dark:text-gray-400">No resolved flags.</p>
          ) : (
            <ul className="space-y-2">
              {resolved.map((f) => (
                <FlagRow key={f.id} flag={f} onAction={handleAction} />
              ))}
            </ul>
          )
        )}
      </section>

      {modal && (
        <TransitionModal
          flag={modal.flag}
          action={modal.action}
          onClose={handleClose}
          onSubmitted={handleSubmitted}
        />
      )}
    </div>
  );
}
