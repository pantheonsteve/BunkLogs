/**
 * Maintenance ticket queue — Step 7_10, Stories 30-31, 34-35.
 *
 * Features:
 *  - Status filter: Open (default) / New / In Progress / Closed / All
 *  - Header counts: n new • m in progress • k urgent
 *  - Default sort: urgency (Urgent first) then age (oldest first) — enforced server-side
 *  - Bulk select + fulfill for In Progress rows (Story 23 pattern)
 *  - Closed view with date range and free-text search
 *  - Click row → navigates to /maintenance/tickets/:id
 *  - No self-reflection card (Story 30 criterion 9)
 */

import { useCallback, useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  fetchMaintenanceQueue,
  transitionTicket,
  bulkTransitionTickets,
} from '../../api/maintenance';

const STATUS_BADGE = {
  new: 'bg-blue-600 text-white',
  in_progress: 'bg-amber-400 text-amber-950 dark:bg-amber-500 dark:text-amber-950',
  fulfilled: 'bg-green-600 text-white',
  unable_to_fulfill: 'bg-gray-500 text-white',
};

const STATUS_LABEL = {
  new: 'New',
  in_progress: 'In Progress',
  fulfilled: 'Fulfilled',
  unable_to_fulfill: 'Unable to fulfill',
};

const TRANSITION_LABEL = {
  in_progress: 'Mark In Progress',
  fulfilled: 'Mark Fulfilled',
  unable_to_fulfill: 'Unable to fulfill',
  new: 'Reopen',
};

// Primary action surfaced as the prominent button per status; any remaining
// transitions render as smaller secondary actions.
const PRIMARY_TRANSITION = {
  new: 'in_progress',
  in_progress: 'fulfilled',
  fulfilled: 'in_progress',
  unable_to_fulfill: 'in_progress',
};

const AGE_THRESHOLD_SECONDS = 4 * 3600;

function formatAge(seconds) {
  if (seconds == null) return '';
  if (seconds < 60) return `${seconds}s ago`;
  const m = Math.round(seconds / 60);
  if (m < 60) return `${m}m ago`;
  const h = Math.round(m / 60);
  if (h < 48) return `${h}h ago`;
  return `${Math.round(h / 24)}d ago`;
}

function relativeFromIso(iso) {
  if (!iso) return '';
  const seconds = Math.round((Date.now() - new Date(iso).getTime()) / 1000);
  return formatAge(seconds);
}

function ClockIcon({ className = 'w-3 h-3' }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
      <circle cx="12" cy="12" r="9" />
      <path d="M12 7v5l3 2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function PersonIcon({ className = 'w-3 h-3' }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
      <circle cx="12" cy="8" r="3.5" />
      <path d="M5 20a7 7 0 0 1 14 0" strokeLinecap="round" />
    </svg>
  );
}

function TicketRow({ ticket, selectable, selected, onSelectToggle, onTransition, onClick }) {
  const aged = ticket.age_seconds != null && ticket.age_seconds >= AGE_THRESHOLD_SECONDS;
  const transitions = ticket.available_transitions ?? [];
  const preferred = PRIMARY_TRANSITION[ticket.status];
  const primary = transitions.includes(preferred) ? preferred : transitions[0];
  const secondary = transitions.filter((t) => t !== primary);

  const actionButton = (next, prominent) => (
    <button
      key={next}
      type="button"
      onClick={() => onTransition(ticket, next)}
      data-testid={`ticket-action-${next}-${ticket.id}`}
      className={
        prominent
          ? 'inline-flex items-center justify-center px-4 min-h-[38px] rounded-lg border border-blue-300 dark:border-blue-700 text-sm font-medium text-blue-700 dark:text-blue-300 bg-white dark:bg-gray-900 hover:bg-blue-50 dark:hover:bg-blue-900/30 transition-colors whitespace-nowrap'
          : 'inline-flex items-center justify-center px-2 min-h-[32px] text-xs font-medium text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 hover:underline whitespace-nowrap'
      }
    >
      {TRANSITION_LABEL[next] || next}
    </button>
  );

  return (
    <li
      data-testid={`ticket-row-${ticket.id}`}
      data-status={ticket.status}
      className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 px-5 py-4 shadow-sm transition-colors cursor-pointer hover:border-blue-300 dark:hover:border-blue-600"
      onClick={() => onClick(ticket.id)}
    >
      <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3">
        {/* Left: badges, title, description, submitter */}
        <div className="flex gap-3 min-w-0">
          {selectable && (
            <input
              type="checkbox"
              checked={selected}
              onChange={(e) => { e.stopPropagation(); onSelectToggle(ticket.id); }}
              onClick={(e) => e.stopPropagation()}
              aria-label={`Select ticket at ${ticket.location}`}
              data-testid={`ticket-select-${ticket.id}`}
              className="mt-1 h-4 w-4 shrink-0 rounded border-gray-300"
            />
          )}
          <div className="min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              {ticket.urgency === 'urgent' && (
                <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-red-600 text-white">
                  Urgent
                </span>
              )}
              <span className={`text-xs font-medium px-2.5 py-0.5 rounded-full ${STATUS_BADGE[ticket.status] || ''}`}>
                {STATUS_LABEL[ticket.status] || ticket.status}
              </span>
              {ticket.status === 'new' && ticket.acknowledger == null && aged && (
                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full border border-orange-300 dark:border-orange-700 text-orange-600 dark:text-orange-300 text-[11px] font-medium">
                  <ClockIcon />
                  Aged
                </span>
              )}
            </div>
            <h3 className="font-semibold text-gray-900 dark:text-white mt-1.5">
              {ticket.location}
              {ticket.category ? ` — ${ticket.category.replace(/_/g, ' ')}` : ''}
            </h3>
            {ticket.description && (
              <p className="text-sm text-gray-600 dark:text-gray-300 mt-1 line-clamp-2">
                {ticket.description}
              </p>
            )}
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-2">
              {ticket.submitter_name ? `From ${ticket.submitter_name} · ` : ''}
              {formatAge(ticket.age_seconds)}
              {ticket.has_photos ? ' · 📎 photo' : ''}
            </p>
          </div>
        </div>

        {/* Right: status metadata + actions */}
        <div
          className="flex flex-col sm:items-end gap-2 shrink-0"
          onClick={(e) => e.stopPropagation()}
        >
          {ticket.acknowledger?.name && (
            <span className="inline-flex items-center gap-1 text-xs text-amber-700 dark:text-amber-300">
              <PersonIcon />
              In progress: {ticket.acknowledger.name}
            </span>
          )}
          {ticket.resolution?.name && (
            <span className="text-xs text-gray-500 dark:text-gray-400">
              {STATUS_LABEL[ticket.status] || ticket.status}: {relativeFromIso(ticket.resolution.at)} by {ticket.resolution.name}
            </span>
          )}
          {primary && (
            <div className="flex flex-col items-end gap-1">
              {actionButton(primary, true)}
              {secondary.length > 0 && (
                <div className="flex flex-wrap justify-end gap-1">
                  {secondary.map((next) => actionButton(next, false))}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </li>
  );
}

function TransitionModal({ ticket, toState, onClose, onSubmitted }) {
  const [note, setNote] = useState('');
  const [reason, setReason] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');

  if (!ticket) return null;
  const reasonRequired = toState === 'unable_to_fulfill';

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    if (reasonRequired && reason.trim().length < 10) {
      setError('Please provide a reason (at least 10 characters).');
      return;
    }
    setSubmitting(true);
    try {
      await transitionTicket(ticket.id, {
        toState,
        note: note.trim() || undefined,
        reason: reason.trim() || undefined,
      });
      onSubmitted();
    } catch (err) {
      const d = err?.response?.data;
      const detail = d?.detail || d?.to_state || d?.reason || err?.message || 'Could not apply transition.';
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
      data-testid="ticket-transition-modal"
    >
      <div className="w-full sm:max-w-md bg-white dark:bg-gray-900 rounded-t-2xl sm:rounded-2xl shadow-xl p-4">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
          {TRANSITION_LABEL[toState] || toState}
        </h2>
        <p className="text-sm text-gray-600 dark:text-gray-300 mt-1">
          {ticket.location}
        </p>
        <form onSubmit={handleSubmit} className="mt-3 space-y-3">
          <label className="block text-sm">
            <span className="text-gray-700 dark:text-gray-200">
              Note {reasonRequired ? '' : '(optional)'}
            </span>
            <textarea
              value={reasonRequired ? reason : note}
              onChange={(e) => reasonRequired ? setReason(e.target.value) : setNote(e.target.value)}
              rows={3}
              required={reasonRequired}
              data-testid="ticket-transition-note"
              className="mt-1 block w-full rounded-md border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 px-3 py-2 text-sm"
            />
          </label>
          {!reasonRequired && toState !== 'in_progress' && (
            <label className="block text-sm">
              <span className="text-gray-700 dark:text-gray-200">Optional closing note</span>
              <textarea
                value={note}
                onChange={(e) => setNote(e.target.value)}
                rows={2}
                data-testid="ticket-transition-closing-note"
                className="mt-1 block w-full rounded-md border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 px-3 py-2 text-sm"
              />
            </label>
          )}
          {error && (
            <p role="alert" className="text-sm text-red-700 dark:text-red-300" data-testid="ticket-transition-error">
              {error}
            </p>
          )}
          <div className="flex justify-end gap-2">
            <button
              type="button"
              onClick={onClose}
              disabled={submitting}
              className="inline-flex items-center px-3 min-h-[40px] rounded-lg border border-gray-300 dark:border-gray-700 text-sm text-gray-800 dark:text-gray-100"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={submitting}
              data-testid="ticket-transition-submit"
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

function FilterBar({ filter, search, dateFrom, dateTo, onChange }) {
  const isClosed = filter === 'closed';
  return (
    <div
      className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 px-3 py-2 shadow-sm space-y-2"
      data-testid="maint-queue-filter"
    >
      <div className="flex flex-wrap items-center gap-2">
        {['open', 'new', 'in_progress', 'closed', 'all'].map((f) => (
          <button
            key={f}
            type="button"
            onClick={() => onChange({ filter: f, search: '', dateFrom: '', dateTo: '' })}
            data-testid={`filter-${f}`}
            className={`px-3 py-1 rounded-full text-sm font-medium transition-colors ${
              filter === f
                ? 'bg-blue-600 text-white'
                : 'bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-200 hover:bg-gray-200 dark:hover:bg-gray-700'
            }`}
          >
            {f === 'in_progress' ? 'In Progress' : f.charAt(0).toUpperCase() + f.slice(1)}
          </button>
        ))}
      </div>
      {isClosed && (
        <div className="flex flex-wrap gap-2">
          <input
            type="text"
            value={search}
            onChange={(e) => onChange({ filter, search: e.target.value, dateFrom, dateTo })}
            placeholder="Search…"
            data-testid="maint-queue-search"
            className="flex-1 min-w-[120px] rounded-md border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 px-2 py-1 text-sm"
          />
          <input
            type="date"
            value={dateFrom}
            onChange={(e) => onChange({ filter, search, dateFrom: e.target.value, dateTo })}
            data-testid="maint-queue-date-from"
            className="rounded-md border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 px-2 py-1 text-sm"
          />
          <input
            type="date"
            value={dateTo}
            onChange={(e) => onChange({ filter, search, dateFrom, dateTo: e.target.value })}
            data-testid="maint-queue-date-to"
            className="rounded-md border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 px-2 py-1 text-sm"
          />
        </div>
      )}
    </div>
  );
}

export default function MaintenanceQueue() {
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [filter, setFilter] = useState('open');
  const [search, setSearch] = useState('');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [selected, setSelected] = useState(() => new Set());
  const [bulkNote, setBulkNote] = useState('');
  const [bulkSubmitting, setBulkSubmitting] = useState(false);
  const [bulkError, setBulkError] = useState('');
  const [modal, setModal] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const result = await fetchMaintenanceQueue({
        filter,
        search: search || undefined,
        dateFrom: dateFrom || undefined,
        dateTo: dateTo || undefined,
      });
      setData(result);
      setError('');
    } catch (err) {
      const detail = err?.response?.data?.detail || err?.message || 'Failed to load queue.';
      setError(typeof detail === 'string' ? detail : JSON.stringify(detail));
    } finally {
      setLoading(false);
    }
  }, [filter, search, dateFrom, dateTo]);

  useEffect(() => { load(); }, [load]);

  const handleFilterChange = ({ filter: f, search: s, dateFrom: df, dateTo: dt }) => {
    setFilter(f); setSearch(s); setDateFrom(df); setDateTo(dt);
    setSelected(new Set());
  };

  const handleTransition = (ticket, toState) => setModal({ ticket, toState });
  const handleSubmitted = () => { setModal(null); setSelected(new Set()); setBulkNote(''); load(); };

  const handleSelectToggle = (id) => {
    setSelected((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  };

  const handleBulkFulfill = async () => {
    setBulkError('');
    const ids = Array.from(selected);
    if (!ids.length) return;
    setBulkSubmitting(true);
    try {
      const result = await bulkTransitionTickets({ ids, toState: 'fulfilled', note: bulkNote.trim() || undefined });
      if (result.failed?.length) {
        setBulkError(`${result.failed.length} ticket(s) could not be transitioned.`);
      }
      handleSubmitted();
    } catch (err) {
      setBulkError(err?.response?.data?.detail || err?.message || 'Bulk update failed.');
    } finally {
      setBulkSubmitting(false);
    }
  };

  const tickets = data?.tickets ?? [];
  const counts = data?.counts ?? { new: 0, in_progress: 0, urgent_open: 0 };
  const isReadOnly = data?.scope && data.scope !== 'team';
  const inProgressTickets = tickets.filter((t) => t.status === 'in_progress');
  const eligibleSelected = useMemo(
    () => inProgressTickets.filter((t) => selected.has(t.id)),
    [inProgressTickets, selected],
  );

  if (loading && !data) {
    return (
      <div className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-[96rem] mx-auto" data-testid="maint-queue-loading">
        <p className="text-gray-600 dark:text-gray-400">Loading queue…</p>
      </div>
    );
  }

  if (error && !data) {
    return (
      <div className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-[96rem] mx-auto">
        <div role="alert" className="rounded-xl border border-amber-200 bg-amber-50 dark:border-amber-900 dark:bg-amber-900/30 px-4 py-3 text-sm text-amber-900 dark:text-amber-100" data-testid="maint-queue-error">
          {error}
        </div>
      </div>
    );
  }

  return (
    <div data-testid="maint-queue" className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-[96rem] mx-auto space-y-4">
      <header className="space-y-1">
        <h1 className="text-2xl font-semibold text-gray-900 dark:text-white">Maintenance Queue</h1>
        <p className="text-sm text-gray-600 dark:text-gray-400" data-testid="maint-queue-counts">
          {counts.new} new&nbsp;·&nbsp;{counts.in_progress} in progress&nbsp;·&nbsp;{counts.urgent_open} urgent
        </p>
        {isReadOnly && (
          <p className="text-sm text-gray-500 dark:text-gray-400" data-testid="maint-queue-readonly-note">
            Read-only view — only the maintenance team can update tickets.
          </p>
        )}
      </header>

      <FilterBar
        filter={filter}
        search={search}
        dateFrom={dateFrom}
        dateTo={dateTo}
        onChange={handleFilterChange}
      />

      {error && (
        <div role="alert" className="rounded-xl border border-amber-200 bg-amber-50 dark:border-amber-900 dark:bg-amber-900/30 px-4 py-3 text-sm text-amber-900 dark:text-amber-100">
          {error}
        </div>
      )}

      {tickets.length === 0 ? (
        <p className="text-sm text-gray-500 dark:text-gray-400" data-testid="maint-queue-empty">
          {filter === 'closed' ? 'No closed tickets match.' : 'No tickets in this view.'}
        </p>
      ) : (
        <ul className="space-y-2" data-testid="maint-queue-list">
          {tickets.map((t) => (
            <TicketRow
              key={t.id}
              ticket={t}
              selectable={!isReadOnly && t.status === 'in_progress'}
              selected={selected.has(t.id)}
              onSelectToggle={handleSelectToggle}
              onTransition={handleTransition}
              onClick={(id) => navigate(`/maintenance/tickets/${id}?from=${filter}`)}
            />
          ))}
        </ul>
      )}

      {eligibleSelected.length > 0 && (
        <div
          className="mt-3 rounded-xl border border-blue-200 dark:border-blue-700 bg-blue-50 dark:bg-blue-900/30 px-4 py-3 shadow-sm"
          data-testid="maint-queue-bulk-bar"
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
              data-testid="maint-queue-bulk-note"
              className="mt-1 block w-full rounded-md border border-blue-200 dark:border-blue-700 bg-white dark:bg-gray-900 px-3 py-2 text-sm"
            />
          </label>
          {bulkError && (
            <p role="alert" className="text-sm text-red-700 dark:text-red-300 mt-1" data-testid="maint-queue-bulk-error">
              {bulkError}
            </p>
          )}
          <div className="flex justify-end mt-3">
            <button
              type="button"
              onClick={handleBulkFulfill}
              disabled={bulkSubmitting}
              data-testid="maint-queue-bulk-submit"
              className="inline-flex items-center px-4 min-h-[40px] rounded-lg bg-blue-600 text-white text-sm font-medium hover:bg-blue-700 disabled:opacity-60"
            >
              {bulkSubmitting ? 'Working…' : 'Mark all fulfilled'}
            </button>
          </div>
        </div>
      )}

      {modal && (
        <TransitionModal
          ticket={modal.ticket}
          toState={modal.toState}
          onClose={() => setModal(null)}
          onSubmitted={handleSubmitted}
        />
      )}
    </div>
  );
}
