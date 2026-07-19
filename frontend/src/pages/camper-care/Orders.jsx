/**
 * Camper Care orders workspace — Step 7_8, Stories 22-23.
 *
 * Three sections, in order:
 *   1. New (visually most prominent)
 *   2. In Progress (with bulk-fulfill action)
 *   3. Resolved (collapsed by default with count + date range filter)
 *
 * Filter chip at top: All | My caseload | By bunk (input) | By item (input).
 *
 * Bulk fulfillment (Story 23.5): the In Progress section grows a
 * checkbox per row; selecting any rows reveals the bulk action bar
 * with a closing-note input that maps to `to_state=fulfilled` on the
 * bulk endpoint.
 */

import { useCallback, useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  bulkTransitionOrders, fetchOrders, transitionOrder,
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

const AGE_THRESHOLD_SECONDS = 2 * 60 * 60; // surface "aged" pill past 2h per spec

function camperLabel(c) {
  if (!c) return '';
  const first = c.preferred_name || c.first_name || '';
  const last = c.last_name || '';
  return `${first} ${last}`.trim();
}

function formatAge(seconds) {
  if (seconds == null) return '';
  if (seconds < 60) return `${seconds}s ago`;
  const m = Math.round(seconds / 60);
  if (m < 60) return `${m}m ago`;
  const h = Math.round(m / 60);
  if (h < 48) return `${h}h ago`;
  const d = Math.round(h / 24);
  return `${d}d ago`;
}

function orderItemSummary(order) {
  const lines = order.line_items || [];
  if (lines.length > 1) {
    return lines
      .map((line) => {
        const qty = line.quantity > 1 ? ` ×${line.quantity}` : '';
        const note = line.note ? ` — ${line.note}` : '';
        return `${line.item_label}${qty}${note}`;
      })
      .join('; ');
  }
  if (lines.length === 1) {
    const line = lines[0];
    const qty = line.quantity > 1 ? ` ×${line.quantity}` : '';
    const note = line.note || order.item_note;
    return `${line.item_label}${qty}${note ? ` — ${note}` : ''}`;
  }
  return `${order.item}${order.item_note ? ` — ${order.item_note}` : ''}`;
}

function OrderRow({ order, selectable, selected, onSelectToggle, onTransition, onClick }) {
  const aged = order.age_seconds != null && order.age_seconds >= AGE_THRESHOLD_SECONDS;
  return (
    <li
      data-testid={`order-row-${order.id}`}
      data-status={order.status}
      onClick={() => onClick(order.id)}
      className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 px-4 py-3 shadow-sm cursor-pointer hover:border-blue-300 dark:hover:border-blue-700 transition-colors"
    >
      <div className="flex items-start gap-3">
        {selectable && (
          <input
            type="checkbox"
            checked={selected}
            onChange={(e) => { e.stopPropagation(); onSelectToggle(order.id); }}
            onClick={(e) => e.stopPropagation()}
            aria-label={`Select order for ${camperLabel(order.subject)}`}
            data-testid={`order-select-${order.id}`}
            className="mt-1 h-4 w-4 rounded border-gray-300"
          />
        )}
        <div className="min-w-0 flex-1">
          <div className="flex items-start justify-between gap-2">
            <div className="min-w-0">
              <h3 className="font-semibold text-gray-900 dark:text-white truncate">
                {orderItemSummary(order)}
              </h3>
              <div className="flex flex-wrap items-center gap-2 mt-1">
                {order.bunk?.name ? (
                  <span
                    className="text-xs font-semibold px-2 py-0.5 rounded-full bg-slate-100 text-slate-800 dark:bg-slate-800 dark:text-slate-100"
                    data-testid={`order-bunk-${order.id}`}
                  >
                    {order.bunk.name}
                  </span>
                ) : (
                  <span className="text-xs text-gray-400 dark:text-gray-500 italic">
                    Bunk unknown
                  </span>
                )}
                {order.subject && (
                  <span className="text-xs text-gray-600 dark:text-gray-300">
                    For {camperLabel(order.subject)}
                  </span>
                )}
              </div>
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                {order.submitter?.name ? (
                  <span>from {order.submitter.name} · </span>
                ) : null}
                {formatAge(order.age_seconds)}
                {aged && (
                  <span className="ml-2 inline-flex items-center px-1.5 py-0.5 rounded-full bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-200 text-[10px] font-medium">
                    Aged
                  </span>
                )}
              </p>
              {order.description && (
                <p className="text-sm text-gray-700 dark:text-gray-300 mt-1 whitespace-pre-wrap">
                  {order.description}
                </p>
              )}
            </div>
            <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${STATUS_BADGE[order.status] || ''}`}>
              {STATUS_LABEL[order.status] || order.status}
            </span>
          </div>
          {order.available_transitions?.length > 0 && (
            <div
              className="flex flex-wrap gap-2 mt-3"
              onClick={(e) => e.stopPropagation()}
            >
              {order.available_transitions.map((next) => (
                <button
                  key={next}
                  type="button"
                  onClick={() => onTransition(order, next)}
                  data-testid={`order-action-${next}-${order.id}`}
                  className="inline-flex items-center px-3 min-h-[36px] rounded-lg border border-gray-300 dark:border-gray-700 text-sm text-gray-900 dark:text-gray-100 bg-white dark:bg-gray-800 hover:bg-gray-50 dark:hover:bg-gray-700"
                >
                  {TRANSITION_LABEL[next] || next}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>
    </li>
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
      data-testid="order-transition-modal"
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
              data-testid="order-transition-note"
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
                data-testid="order-transition-reason"
                className="mt-1 block w-full rounded-md border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 px-3 py-2 text-sm"
              />
            </label>
          )}
          {error && (
            <p role="alert" className="text-sm text-red-700 dark:text-red-300" data-testid="order-transition-error">
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
              data-testid="order-transition-submit"
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

function FilterBar({ filter, bunkId, item, onChange, showAdvancedFilters }) {
  if (!showAdvancedFilters) return null;
  return (
    <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 px-3 py-2 shadow-sm" data-testid="cc-orders-filter">
      <div className="flex flex-wrap items-center gap-2">
        <label className="text-sm text-gray-700 dark:text-gray-200 flex items-center gap-1.5">
          <span>Show:</span>
          <select
            value={filter}
            onChange={(e) => onChange({ filter: e.target.value, bunkId: '', item: '' })}
            data-testid="cc-orders-filter-select"
            className="rounded border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 px-2 py-1 text-sm"
          >
            <option value="all">All</option>
            <option value="my_caseload">My caseload only</option>
            <option value="by_bunk">By bunk</option>
            <option value="by_item">By item</option>
          </select>
        </label>
        {filter === 'by_bunk' && (
          <input
            type="number"
            value={bunkId}
            onChange={(e) => onChange({ filter, bunkId: e.target.value, item })}
            placeholder="Bunk id"
            data-testid="cc-orders-filter-bunk"
            className="w-28 rounded border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 px-2 py-1 text-sm"
          />
        )}
        {filter === 'by_item' && (
          <input
            type="text"
            value={item}
            onChange={(e) => onChange({ filter, bunkId, item: e.target.value })}
            placeholder="Item label"
            data-testid="cc-orders-filter-item"
            className="w-40 rounded border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 px-2 py-1 text-sm"
          />
        )}
      </div>
    </div>
  );
}

export default function CamperCareOrders() {
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [filter, setFilter] = useState('all');
  const [bunkId, setBunkId] = useState('');
  const [item, setItem] = useState('');
  const [showResolved, setShowResolved] = useState(false);
  const [selected, setSelected] = useState(() => new Set());
  const [bulkNote, setBulkNote] = useState('');
  const [bulkSubmitting, setBulkSubmitting] = useState(false);
  const [bulkError, setBulkError] = useState('');
  const [modal, setModal] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const next = await fetchOrders({
        filter,
        bunkId: bunkId || undefined,
        item: item || undefined,
      });
      setData(next);
      setError('');
    } catch (err) {
      const detail = err?.response?.data?.detail
        || err?.response?.data?.bunk_id
        || err?.response?.data?.item;
      setError(typeof detail === 'string' ? detail : err?.message || 'Failed to load orders.');
    } finally {
      setLoading(false);
    }
  }, [filter, bunkId, item]);

  useEffect(() => { load(); }, [load]);

  const handleOrderClick = (id) => {
    navigate(`/camper-care/orders/${id}`);
  };

  const handleFilterChange = ({ filter: f, bunkId: b, item: i }) => {
    setFilter(f);
    setBunkId(b);
    setItem(i);
    setSelected(new Set());
  };

  const handleTransition = (order, toState) => {
    setModal({ order, toState });
  };

  const handleSubmitted = () => {
    setModal(null);
    setSelected(new Set());
    setBulkNote('');
    load();
  };

  const handleSelectToggle = (id) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const handleBulkFulfill = async () => {
    setBulkError('');
    const ids = Array.from(selected);
    if (ids.length === 0) return;
    setBulkSubmitting(true);
    try {
      const result = await bulkTransitionOrders({
        ids, toState: 'fulfilled', note: bulkNote.trim() || undefined,
      });
      if (result.failed?.length) {
        setBulkError(
          `${result.failed.length} order${result.failed.length === 1 ? '' : 's'} could not be transitioned.`,
        );
      }
      handleSubmitted();
    } catch (err) {
      const detail = err?.response?.data?.detail || err?.message || 'Bulk update failed.';
      setBulkError(typeof detail === 'string' ? detail : JSON.stringify(detail));
    } finally {
      setBulkSubmitting(false);
    }
  };

  const newItems = data?.new ?? [];
  const inProgress = data?.in_progress ?? [];
  const resolved = data?.resolved ?? [];
  const counts = data?.counts ?? { new: 0, in_progress: 0, resolved: 0 };
  const canManage = data?.scope === 'team';

  const scopeSubtitle = {
    team: 'All Camper Care orders for your program.',
    unit: 'Orders for campers and counselors in your supervised bunks.',
    viewer: 'Orders you submitted.',
  };

  const eligibleSelected = useMemo(
    () => (canManage ? inProgress.filter((o) => selected.has(o.id)) : []),
    [canManage, inProgress, selected],
  );

  if (loading && !data) {
    return (
      <div className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-[96rem] mx-auto">
        <p className="text-gray-600 dark:text-gray-400">Loading orders…</p>
      </div>
    );
  }

  if (error && !data) {
    return (
      <div className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-[96rem] mx-auto">
        <div
          role="alert"
          className="rounded-xl border border-amber-200 bg-amber-50 dark:border-amber-900 dark:bg-amber-900/30 px-4 py-3 text-sm text-amber-900 dark:text-amber-100"
          data-testid="cc-orders-error"
        >
          {error}
        </div>
      </div>
    );
  }

  return (
    <div data-testid="cc-orders" className="px-4 sm:px-6 lg:px-8 py-8 pb-24 w-full max-w-[96rem] mx-auto space-y-4">
      <header className="space-y-1">
        <h1 className="text-2xl font-semibold text-gray-900 dark:text-white">Orders</h1>
        <p className="text-sm text-gray-600 dark:text-gray-400">
          {scopeSubtitle[data?.scope] || scopeSubtitle.team}
        </p>
      </header>

      <FilterBar
        filter={filter}
        bunkId={bunkId}
        item={item}
        showAdvancedFilters={canManage}
        onChange={handleFilterChange}
      />

      {error && (
        <div
          role="alert"
          className="rounded-xl border border-amber-200 bg-amber-50 dark:border-amber-900 dark:bg-amber-900/30 px-4 py-3 text-sm text-amber-900 dark:text-amber-100"
        >
          {error}
        </div>
      )}

      <section data-testid="cc-orders-new">
        <div className="flex items-center justify-between mb-2">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">New</h2>
          <span className="text-xs text-gray-500 dark:text-gray-400" data-testid="cc-orders-new-count">
            {counts.new}
          </span>
        </div>
        {newItems.length === 0 ? (
          <p className="text-sm text-gray-500 dark:text-gray-400">No new orders.</p>
        ) : (
          <ul className="space-y-2">
            {newItems.map((o) => (
              <OrderRow
                key={o.id}
                order={o}
                selectable={false}
                onTransition={handleTransition}
                onClick={handleOrderClick}
              />
            ))}
          </ul>
        )}
      </section>

      <section data-testid="cc-orders-in-progress">
        <div className="flex items-center justify-between mb-2">
          <h2 className="text-base font-semibold text-gray-900 dark:text-white">In Progress</h2>
          <span className="text-xs text-gray-500 dark:text-gray-400">{counts.in_progress}</span>
        </div>
        {inProgress.length === 0 ? (
          <p className="text-sm text-gray-500 dark:text-gray-400">No orders in progress.</p>
        ) : (
          <>
            <ul className="space-y-2">
              {inProgress.map((o) => (
              <OrderRow
                key={o.id}
                order={o}
                selectable={canManage}
                selected={selected.has(o.id)}
                onSelectToggle={handleSelectToggle}
                onTransition={handleTransition}
                onClick={handleOrderClick}
              />
            ))}
          </ul>
          {canManage && eligibleSelected.length > 0 && (
              <div
                className="mt-3 rounded-xl border border-blue-200 dark:border-blue-700 bg-blue-50 dark:bg-blue-900/30 px-4 py-3 shadow-sm"
                data-testid="cc-orders-bulk-bar"
              >
                <p className="text-sm font-medium text-blue-900 dark:text-blue-100">
                  {eligibleSelected.length} selected
                </p>
                <label className="block text-sm mt-2">
                  <span className="text-blue-900 dark:text-blue-100">Closing note (optional)</span>
                  <textarea
                    value={bulkNote}
                    onChange={(e) => setBulkNote(e.target.value)}
                    rows={2}
                    data-testid="cc-orders-bulk-note"
                    className="mt-1 block w-full rounded-md border border-blue-200 dark:border-blue-700 bg-white dark:bg-gray-900 px-3 py-2 text-sm"
                  />
                </label>
                {bulkError && (
                  <p role="alert" className="text-sm text-red-700 dark:text-red-300 mt-1" data-testid="cc-orders-bulk-error">
                    {bulkError}
                  </p>
                )}
                <div className="flex justify-end mt-3">
                  <button
                    type="button"
                    onClick={handleBulkFulfill}
                    disabled={bulkSubmitting}
                    data-testid="cc-orders-bulk-submit"
                    className="inline-flex items-center px-4 min-h-[40px] rounded-lg bg-blue-600 text-white text-sm font-medium hover:bg-blue-700 disabled:opacity-60"
                  >
                    {bulkSubmitting ? 'Working…' : 'Mark all fulfilled'}
                  </button>
                </div>
              </div>
            )}
          </>
        )}
      </section>

      <section data-testid="cc-orders-resolved">
        <div className="flex items-center justify-between mb-2">
          <h2 className="text-base font-semibold text-gray-900 dark:text-white">Resolved</h2>
          <button
            type="button"
            onClick={() => setShowResolved((v) => !v)}
            data-testid="cc-orders-resolved-toggle"
            className="text-sm text-blue-700 dark:text-blue-300 hover:underline"
          >
            {showResolved ? 'Hide' : `Show (${counts.resolved})`}
          </button>
        </div>
        {showResolved && (
          resolved.length === 0 ? (
            <p className="text-sm text-gray-500 dark:text-gray-400">No resolved orders.</p>
          ) : (
            <ul className="space-y-2">
              {resolved.map((o) => (
                <OrderRow
                  key={o.id}
                  order={o}
                  selectable={false}
                  onTransition={handleTransition}
                  onClick={handleOrderClick}
                />
              ))}
            </ul>
          )
        )}
      </section>

      {modal && (
        <TransitionModal
          order={modal.order}
          toState={modal.toState}
          onClose={() => setModal(null)}
          onSubmitted={handleSubmitted}
        />
      )}
    </div>
  );
}
