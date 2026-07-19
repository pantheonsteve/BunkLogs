/**
 * Camper Care order detail — Step 7_8, Stories 22.4 + 23.
 *
 * Sections:
 *   Header — item, camper, bunk, submitter, status, timestamps
 *   Description — counselor's narrative when present
 *   Activity — chronological state changes + notes
 *   Actions — status transitions + 5-minute correction window (team scope)
 */

import { useCallback, useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import api from '../../api';
import {
  fetchOrderDetail,
  transitionOrder,
} from '../../api/camperCare';

const STATUS_BADGE = {
  new: 'bg-blue-100 text-blue-900 dark:bg-blue-900/40 dark:text-blue-100',
  in_progress: 'bg-amber-100 text-amber-900 dark:bg-amber-900/40 dark:text-amber-100',
  fulfilled: 'bg-green-100 text-green-900 dark:bg-green-900/40 dark:text-green-100',
  unable_to_fulfill: 'bg-gray-200 text-gray-800 dark:bg-gray-700 dark:text-gray-100',
};

const STATUS_LABEL = {
  new: 'New',
  in_progress: 'In Progress',
  fulfilled: 'Fulfilled',
  unable_to_fulfill: 'Unable to fulfill',
};

const TRANSITION_LABEL = {
  in_progress: 'Start',
  fulfilled: 'Mark fulfilled',
  unable_to_fulfill: 'Unable to fulfill',
  new: 'Reopen',
};

function camperLabel(c) {
  if (!c) return '';
  const first = c.preferred_name || c.first_name || '';
  const last = c.last_name || '';
  return `${first} ${last}`.trim();
}

function formatTime(iso) {
  if (!iso) return '';
  return new Date(iso).toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function orderTitle(order) {
  const lines = order?.line_items || [];
  if (lines.length === 0) {
    return order?.item || 'Order';
  }
  if (lines.length === 1) {
    const line = lines[0];
    const qty = line.quantity > 1 ? ` ×${line.quantity}` : '';
    return `${line.item_label}${qty}`;
  }
  return `${lines.length} requested items`;
}

function orderSubtitle(order) {
  const lines = order?.line_items || [];
  if (lines.length <= 1) {
    const note = lines[0]?.note || order?.item_note;
    return note || '';
  }
  return '';
}

function RequestedItems({ lineItems }) {
  if (!lineItems?.length) return null;
  return (
    <section data-testid="cc-order-detail-items">
      <h2 className="text-sm font-semibold text-gray-700 dark:text-gray-200 mb-2">
        Requested items
      </h2>
      <ul className="divide-y divide-gray-100 dark:divide-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
        {lineItems.map((line) => (
          <li
            key={line.id}
            data-testid={`cc-order-line-${line.id}`}
            className="px-4 py-3 bg-white dark:bg-gray-900"
          >
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <p className="text-sm font-medium text-gray-900 dark:text-white">
                  {line.item_label}
                </p>
                {line.note ? (
                  <p className="text-sm text-gray-600 dark:text-gray-300 mt-1 whitespace-pre-wrap">
                    {line.note}
                  </p>
                ) : null}
              </div>
              {line.quantity > 1 ? (
                <span className="text-sm font-semibold text-gray-700 dark:text-gray-200 shrink-0">
                  ×{line.quantity}
                </span>
              ) : null}
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
}

function ActivityEvent({ event }) {
  const isStateChange = event.event_type === 'state_change' || event.from_state || event.to_state;
  return (
    <div data-testid={`activity-${event.id}`} className="flex gap-3">
      <div className="w-1.5 flex-shrink-0 mt-1.5">
        <div className="w-1.5 h-1.5 rounded-full bg-gray-400" />
      </div>
      <div className="flex-1 min-w-0 pb-4 border-b border-gray-100 dark:border-gray-800 last:border-0">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-xs font-medium text-gray-700 dark:text-gray-200">
            {event.actor_name || 'System'}
          </span>
          <span className="text-xs text-gray-400">{formatTime(event.created_at)}</span>
          {isStateChange && event.from_state && event.to_state ? (
            <span className="text-xs text-gray-500 dark:text-gray-400">
              {STATUS_LABEL[event.from_state] || event.from_state}
              {' → '}
              {STATUS_LABEL[event.to_state] || event.to_state}
            </span>
          ) : null}
        </div>
        {event.note ? (
          <p className="text-sm text-gray-800 dark:text-gray-100 mt-1 whitespace-pre-wrap">
            {event.note}
          </p>
        ) : null}
        {event.reason ? (
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
            Reason: {event.reason}
          </p>
        ) : null}
      </div>
    </div>
  );
}

function TransitionModal({ order, toState, onClose, onSubmitted }) {
  const [note, setNote] = useState('');
  const [reason, setReason] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');

  if (!order) return null;
  const reasonRequired = toState === 'unable_to_fulfill';

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    if (reasonRequired && !reason.trim()) {
      setError('A reason is required to mark unable to fulfill.');
      return;
    }
    setSubmitting(true);
    try {
      await transitionOrder(order.id, {
        toState,
        note: note.trim() || undefined,
        reason: reason.trim() || undefined,
      });
      onSubmitted();
    } catch (err) {
      const detail = err?.response?.data?.detail
        || err?.response?.data?.to_state
        || err?.response?.data?.reason
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
      data-testid="cc-order-transition-modal"
    >
      <div className="w-full sm:max-w-md bg-white dark:bg-gray-900 rounded-t-2xl sm:rounded-2xl shadow-xl p-4">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
          {TRANSITION_LABEL[toState] || toState}
        </h2>
        <p className="text-sm text-gray-600 dark:text-gray-300 mt-1">
          {order.item} · {camperLabel(order.subject)}
        </p>
        <form onSubmit={handleSubmit} className="mt-3 space-y-3">
          <label className="block text-sm">
            <span className="text-gray-700 dark:text-gray-200">Note (optional)</span>
            <textarea
              value={note}
              onChange={(e) => setNote(e.target.value)}
              rows={3}
              data-testid="cc-order-transition-note"
              className="mt-1 block w-full rounded-md border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 px-3 py-2 text-sm"
            />
          </label>
          {reasonRequired && (
            <label className="block text-sm">
              <span className="text-gray-700 dark:text-gray-200">Reason (required)</span>
              <input
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                required
                data-testid="cc-order-transition-reason"
                className="mt-1 block w-full rounded-md border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 px-3 py-2 text-sm"
              />
            </label>
          )}
          {error && (
            <p role="alert" className="text-sm text-red-700 dark:text-red-300" data-testid="cc-order-transition-error">
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
              data-testid="cc-order-transition-submit"
              className="inline-flex items-center px-4 min-h-[40px] rounded-lg bg-blue-600 text-white text-sm font-medium hover:bg-blue-700 disabled:opacity-60"
            >
              {submitting ? 'Working…' : 'Apply'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default function CamperCareOrderDetail() {
  const { orderId } = useParams();
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [modal, setModal] = useState(null);
  const [correcting, setCorrecting] = useState(false);
  const [correctError, setCorrectError] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const result = await fetchOrderDetail(orderId);
      setData(result);
    } catch (err) {
      const status = err?.response?.status;
      const detail = err?.response?.data?.detail;
      const path = err?.config?.url || `/api/v1/camper-care/orders/${orderId}/`;
      if (status === 404 && !detail) {
        setError(
          `Order detail API is not available (${path}). `
          + 'Use local dev (make frontend-dev + make up) or deploy the backend change.',
        );
      } else {
        setError(detail || err?.message || 'Could not load order.');
      }
    } finally {
      setLoading(false);
    }
  }, [orderId]);

  useEffect(() => {
    load();
  }, [load]);

  const handleCorrectLast = async () => {
    setCorrectError('');
    setCorrecting(true);
    try {
      await api.post(`/api/v1/orders/${orderId}/correct-last/`, {});
      await load();
    } catch (err) {
      setCorrectError(
        err?.response?.data?.detail || err?.message || 'Could not undo the last transition.',
      );
    } finally {
      setCorrecting(false);
    }
  };

  if (loading && !data) {
    return (
      <div className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-[96rem] mx-auto">
        <p className="text-gray-600 dark:text-gray-400" data-testid="cc-order-detail-loading">
          Loading order…
        </p>
      </div>
    );
  }

  if (error && !data) {
    return (
      <div className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-[96rem] mx-auto">
        <Link
          to="/camper-care/orders"
          className="text-sm text-blue-600 dark:text-blue-400 hover:underline"
        >
          ← Back to orders
        </Link>
        <div
          role="alert"
          className="mt-4 rounded-xl border border-red-200 bg-red-50 dark:bg-red-900/20 px-4 py-3 text-sm text-red-800 dark:text-red-200"
          data-testid="cc-order-detail-error"
        >
          {error}
        </div>
      </div>
    );
  }

  const order = data?.order;
  const activity = data?.activity || [];
  const canManage = data?.scope === 'team';
  const camperId = order?.subject?.id;
  const camperHref = camperId ? `/camper-care/campers/${camperId}` : null;

  return (
    <div
      className="px-4 sm:px-6 lg:px-8 py-8 pb-32 w-full max-w-[96rem] mx-auto space-y-4"
      data-testid="cc-order-detail"
    >
      <header className="flex items-center gap-3 flex-wrap">
        <button
          type="button"
          onClick={() => navigate('/camper-care/orders')}
          className="text-sm text-blue-600 dark:text-blue-400 hover:underline"
          data-testid="cc-order-detail-back"
        >
          ← Back to orders
        </button>
        {order ? (
          <span
            className={`text-xs font-medium px-2 py-0.5 rounded-full ${STATUS_BADGE[order.status] || ''}`}
            data-testid="cc-order-detail-status"
          >
            {order.status_label || STATUS_LABEL[order.status] || order.status}
          </span>
        ) : null}
      </header>

      {order ? (
        <div className="space-y-4">
          <section data-testid="cc-order-detail-header">
            <p className="text-xs font-medium uppercase tracking-wide text-purple-700 dark:text-purple-300">
              Camper Care order
            </p>
            <h1 className="text-2xl font-semibold text-gray-900 dark:text-white mt-1">
              {orderTitle(order)}
              {!order.line_items?.length && order.item_note ? ` — ${order.item_note}` : ''}
            </h1>
            {orderSubtitle(order) ? (
              <p className="text-sm text-gray-700 dark:text-gray-300 mt-2 whitespace-pre-wrap">
                {orderSubtitle(order)}
              </p>
            ) : null}
            <div className="flex flex-wrap items-center gap-2 mt-2 text-sm text-gray-600 dark:text-gray-400">
              {order.bunk?.name ? (
                <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-slate-100 text-slate-800 dark:bg-slate-800 dark:text-slate-100">
                  {order.bunk.name}
                </span>
              ) : (
                <span className="text-xs italic text-gray-400">Bunk unknown</span>
              )}
              {order.subject ? (
                camperHref ? (
                  <Link
                    to={camperHref}
                    className="hover:text-blue-700 dark:hover:text-blue-300 hover:underline"
                    data-testid="cc-order-detail-camper-link"
                  >
                    For {camperLabel(order.subject)}
                  </Link>
                ) : (
                  <span>For {camperLabel(order.subject)}</span>
                )
              ) : null}
            </div>
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-2">
              {order.submitter?.name ? `Submitted by ${order.submitter.name} · ` : ''}
              {formatTime(order.created_at)}
              {order.updated_at && order.updated_at !== order.created_at
                ? ` · Updated ${formatTime(order.updated_at)}`
                : ''}
            </p>
          </section>

          <RequestedItems lineItems={order.line_items} />

          {order.description ? (
            <section data-testid="cc-order-detail-description">
              <h2 className="text-sm font-semibold text-gray-700 dark:text-gray-200 mb-1">
                Description
              </h2>
              <p className="text-sm text-gray-800 dark:text-gray-100 whitespace-pre-wrap">
                {order.description}
              </p>
            </section>
          ) : null}

          <section data-testid="cc-order-detail-activity">
            <h2 className="text-sm font-semibold text-gray-700 dark:text-gray-200 mb-2">
              Activity
            </h2>
            {activity.length === 0 ? (
              <p className="text-sm text-gray-500 dark:text-gray-400">No activity yet.</p>
            ) : (
              <div className="space-y-0">
                {activity.map((event) => (
                  <ActivityEvent key={event.id} event={event} />
                ))}
              </div>
            )}
          </section>

          {canManage && order.is_within_correction_window ? (
            <section data-testid="cc-order-detail-correction">
              <button
                type="button"
                onClick={handleCorrectLast}
                disabled={correcting}
                className="text-sm text-amber-700 dark:text-amber-300 hover:underline disabled:opacity-60"
                data-testid="cc-order-correct-last"
              >
                {correcting ? 'Undoing…' : 'Undo last status change'}
              </button>
              {correctError ? (
                <p role="alert" className="text-sm text-red-700 dark:text-red-300 mt-1">
                  {correctError}
                </p>
              ) : null}
            </section>
          ) : null}

          {canManage && order.available_transitions?.length > 0 ? (
            <section
              className="fixed bottom-0 left-0 right-0 z-40 border-t border-gray-200 dark:border-gray-700 bg-white/95 dark:bg-gray-900/95 backdrop-blur px-4 py-3"
              data-testid="cc-order-detail-actions"
            >
              <div className="max-w-[96rem] mx-auto flex flex-wrap gap-2 justify-end">
                {order.available_transitions.map((next) => (
                  <button
                    key={next}
                    type="button"
                    onClick={() => setModal({ order, toState: next })}
                    data-testid={`cc-order-action-${next}`}
                    className="inline-flex items-center px-4 min-h-[40px] rounded-lg bg-blue-600 text-white text-sm font-medium hover:bg-blue-700"
                  >
                    {TRANSITION_LABEL[next] || next}
                  </button>
                ))}
              </div>
            </section>
          ) : null}
        </div>
      ) : null}

      {modal ? (
        <TransitionModal
          order={modal.order}
          toState={modal.toState}
          onClose={() => setModal(null)}
          onSubmitted={() => {
            setModal(null);
            load();
          }}
        />
      ) : null}
    </div>
  );
}
