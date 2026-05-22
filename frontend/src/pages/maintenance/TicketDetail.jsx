/**
 * Maintenance ticket detail — Step 7_10, Stories 31-35.
 *
 * Sections (Story 31 criterion 1):
 *   Header  — location, category, urgency (w/ reason if Urgent), status, submitter, time
 *   Description
 *   Photos  — original submission photos
 *   Activity — chronological state changes + notes + photos added during work
 *   Actions  — pinned to bottom, vary by current status
 *
 * Notes (Story 33):
 *   Inline form (no modal). Visibility radio: Team only | Submitter and team.
 *   AudienceDisclosure updates dynamically with the radio.
 *   Author can edit own notes within 24h.
 *
 * Back nav restores prior queue filter state via query param ?from=<filter>.
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import { useNavigate, useParams, useSearchParams } from 'react-router-dom';
import {
  fetchTicketDetail,
  transitionTicket,
  correctLastTransition,
  createTicketNote,
  editTicketNote,
  fetchNoteAudience,
} from '../../api/maintenance';

const STATUS_BADGE = {
  new: 'bg-blue-100 text-blue-900 dark:bg-blue-900/40 dark:text-blue-100',
  in_progress: 'bg-amber-100 text-amber-900 dark:bg-amber-900/40 dark:text-amber-100',
  fulfilled: 'bg-green-100 text-green-900 dark:bg-green-900/40 dark:text-green-100',
  unable_to_fulfill: 'bg-gray-200 text-gray-800 dark:bg-gray-700 dark:text-gray-100',
};

const STATUS_LABEL = { new: 'New', in_progress: 'In Progress', fulfilled: 'Fulfilled', unable_to_fulfill: 'Unable to Fulfill' };
const TRANSITION_LABEL = { in_progress: 'Mark In Progress', fulfilled: 'Mark Fulfilled', unable_to_fulfill: 'Unable to Fulfill', new: 'Reopen' };
const EVENT_TYPE_LABEL = { state_change: 'Status change', correction: 'Correction', note: 'Note' };

function formatTime(iso) {
  if (!iso) return '';
  const d = new Date(iso);
  return d.toLocaleString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
}

function formatAge(seconds) {
  if (seconds == null) return '';
  const h = Math.round(seconds / 3600);
  if (h < 24) return `${h}h ago`;
  return `${Math.round(h / 24)}d ago`;
}

function ActivityEvent({ event, ticketId, onNoteUpdated }) {
  const [editing, setEditing] = useState(false);
  const [editBody, setEditBody] = useState(event.note || '');
  const [editVisibility, setEditVisibility] = useState(event.visibility || 'team_only');
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState('');

  const isNote = event.event_type === 'note';

  const handleSave = async () => {
    setSaveError('');
    if (!editBody.trim()) { setSaveError('Body required.'); return; }
    setSaving(true);
    try {
      const updated = await editTicketNote(ticketId, event.id, {
        body: editBody.trim(),
        visibility: editVisibility,
      });
      onNoteUpdated(updated);
      setEditing(false);
    } catch (err) {
      setSaveError(err?.response?.data?.detail || err?.message || 'Save failed.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div
      data-testid={`activity-${event.id}`}
      className="flex gap-3"
    >
      <div className="w-1.5 flex-shrink-0 mt-1.5">
        <div className={`w-1.5 h-1.5 rounded-full ${isNote ? 'bg-blue-400' : 'bg-gray-400'}`} />
      </div>
      <div className="flex-1 min-w-0 pb-4 border-b border-gray-100 dark:border-gray-800 last:border-0">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-xs font-medium text-gray-700 dark:text-gray-200">
            {event.actor_name || 'System'}
          </span>
          <span className="text-xs text-gray-400">{formatTime(event.created_at)}</span>
          {isNote && (
            <span className="text-xs px-1.5 py-0.5 rounded-full bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-200">
              {event.visibility === 'submitter_visible' ? 'Visible to submitter' : 'Team only'}
            </span>
          )}
          {!isNote && (
            <span className="text-xs text-gray-500 dark:text-gray-400">
              {event.from_state && event.to_state
                ? `${STATUS_LABEL[event.from_state] || event.from_state} → ${STATUS_LABEL[event.to_state] || event.to_state}`
                : EVENT_TYPE_LABEL[event.event_type] || event.event_type
              }
            </span>
          )}
        </div>

        {isNote && !editing ? (
          <>
            <p className="text-sm text-gray-800 dark:text-gray-100 mt-1 whitespace-pre-wrap">{event.note}</p>
            {event.is_within_edit_window && (
              <button
                type="button"
                onClick={() => setEditing(true)}
                className="text-xs text-blue-600 dark:text-blue-400 hover:underline mt-1"
                data-testid={`note-edit-${event.id}`}
              >
                Edit
              </button>
            )}
          </>
        ) : isNote && editing ? (
          <div className="mt-2 space-y-2">
            <textarea
              value={editBody}
              onChange={(e) => setEditBody(e.target.value)}
              rows={3}
              className="block w-full rounded-md border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 px-3 py-2 text-sm"
            />
            <div className="flex gap-4 text-sm">
              <label className="flex items-center gap-1.5 cursor-pointer">
                <input
                  type="radio"
                  name={`vis-edit-${event.id}`}
                  value="team_only"
                  checked={editVisibility === 'team_only'}
                  onChange={() => setEditVisibility('team_only')}
                />
                Team only
              </label>
              <label className="flex items-center gap-1.5 cursor-pointer">
                <input
                  type="radio"
                  name={`vis-edit-${event.id}`}
                  value="submitter_visible"
                  checked={editVisibility === 'submitter_visible'}
                  onChange={() => setEditVisibility('submitter_visible')}
                />
                Submitter and team
              </label>
            </div>
            {saveError && <p className="text-xs text-red-600 dark:text-red-400">{saveError}</p>}
            <div className="flex gap-2">
              <button
                type="button"
                onClick={handleSave}
                disabled={saving}
                className="px-3 py-1 rounded bg-blue-600 text-white text-xs hover:bg-blue-700 disabled:opacity-60"
              >
                {saving ? 'Saving…' : 'Save'}
              </button>
              <button
                type="button"
                onClick={() => { setEditing(false); setEditBody(event.note); }}
                className="px-3 py-1 rounded border text-xs"
              >
                Cancel
              </button>
            </div>
          </div>
        ) : null}

        {!isNote && event.note && (
          <p className="text-sm text-gray-600 dark:text-gray-300 mt-1 italic">{event.note}</p>
        )}
        {event.reason && (
          <p className="text-sm text-gray-600 dark:text-gray-300 mt-1">Reason: {event.reason}</p>
        )}
      </div>
    </div>
  );
}

function NoteForm({ ticketId, onNoteAdded }) {
  const [body, setBody] = useState('');
  const [visibility, setVisibility] = useState('team_only');
  const [audienceLabel, setAudienceLabel] = useState('This note will be visible to: Maintenance team, Admin.');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    fetchNoteAudience(visibility)
      .then((d) => setAudienceLabel(d.label))
      .catch(() => {});
  }, [visibility]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    if (!body.trim()) { setError('Note body is required.'); return; }
    setSubmitting(true);
    try {
      const event = await createTicketNote(ticketId, { body: body.trim(), visibility });
      onNoteAdded(event);
      setBody('');
      setVisibility('team_only');
    } catch (err) {
      setError(err?.response?.data?.body || err?.response?.data?.detail || err?.message || 'Failed to save note.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-3" data-testid="note-form">
      <textarea
        value={body}
        onChange={(e) => setBody(e.target.value)}
        rows={3}
        placeholder="Add a note…"
        data-testid="note-body"
        className="block w-full rounded-md border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 px-3 py-2 text-sm"
      />
      <div className="flex gap-4 text-sm">
        <label className="flex items-center gap-1.5 cursor-pointer">
          <input
            type="radio"
            name="visibility"
            value="team_only"
            checked={visibility === 'team_only'}
            onChange={() => setVisibility('team_only')}
          />
          Team only
        </label>
        <label className="flex items-center gap-1.5 cursor-pointer">
          <input
            type="radio"
            name="visibility"
            value="submitter_visible"
            checked={visibility === 'submitter_visible'}
            onChange={() => setVisibility('submitter_visible')}
          />
          Submitter and team
        </label>
      </div>
      <p className="text-xs text-gray-500 dark:text-gray-400 italic" data-testid="audience-disclosure">
        {audienceLabel}
      </p>
      {error && <p role="alert" className="text-sm text-red-700 dark:text-red-300">{error}</p>}
      <div className="flex justify-end">
        <button
          type="submit"
          disabled={submitting}
          data-testid="note-submit"
          className="inline-flex items-center px-4 min-h-[36px] rounded-lg bg-blue-600 text-white text-sm font-medium hover:bg-blue-700 disabled:opacity-60"
        >
          {submitting ? 'Saving…' : 'Add note'}
        </button>
      </div>
    </form>
  );
}

function TransitionActions({ ticket, onTransition, onUndo }) {
  const isTerminal = ['fulfilled', 'unable_to_fulfill'].includes(ticket.status);
  const canUndo = ticket.is_within_correction_window;

  return (
    <div
      className="sticky bottom-0 bg-white dark:bg-gray-950 border-t border-gray-200 dark:border-gray-700 px-4 py-3 flex flex-wrap gap-2 justify-between items-center"
      data-testid="ticket-actions"
    >
      <div className="flex flex-wrap gap-2">
        {ticket.available_transitions?.map((next) => (
          <button
            key={next}
            type="button"
            onClick={() => onTransition(next)}
            data-testid={`action-${next}`}
            className={`inline-flex items-center px-4 min-h-[40px] rounded-lg text-sm font-medium ${
              next === 'fulfilled'
                ? 'bg-green-600 text-white hover:bg-green-700'
                : next === 'unable_to_fulfill'
                  ? 'border border-gray-300 dark:border-gray-700 text-gray-800 dark:text-gray-100 bg-white dark:bg-gray-800 hover:bg-gray-50'
                  : next === 'in_progress'
                    ? 'bg-blue-600 text-white hover:bg-blue-700'
                    : 'border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-800 dark:text-gray-100 hover:bg-gray-50'
            }`}
          >
            {TRANSITION_LABEL[next] || next}
          </button>
        ))}
      </div>
      {canUndo && (
        <button
          type="button"
          onClick={onUndo}
          data-testid="action-undo"
          className="text-sm text-gray-500 dark:text-gray-400 hover:underline"
        >
          Undo last action
        </button>
      )}
    </div>
  );
}

function TransitionModal({ toState, ticket, onClose, onSubmitted }) {
  const [note, setNote] = useState('');
  const [reason, setReason] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');

  if (!toState) return null;
  const reasonRequired = toState === 'unable_to_fulfill' || toState === 'new';

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    const body = reasonRequired ? reason : note;
    if (reasonRequired && body.trim().length < 10) {
      setError('Please provide a reason (at least 10 characters).');
      return;
    }
    setSubmitting(true);
    try {
      await transitionTicket(ticket.id, {
        toState,
        note: !reasonRequired ? (note.trim() || undefined) : reason.trim(),
        reason: reasonRequired ? reason.trim() : undefined,
      });
      onSubmitted();
    } catch (err) {
      const d = err?.response?.data;
      setError(d?.detail || d?.to_state || d?.reason || err?.message || 'Could not apply transition.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center bg-black/40 px-4" role="dialog" aria-modal="true">
      <div className="w-full sm:max-w-md bg-white dark:bg-gray-900 rounded-t-2xl sm:rounded-2xl shadow-xl p-4">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white">{TRANSITION_LABEL[toState] || toState}</h2>
        <form onSubmit={handleSubmit} className="mt-3 space-y-3">
          <label className="block text-sm">
            <span className="text-gray-700 dark:text-gray-200">
              {reasonRequired ? 'Reason (required)' : 'Note (optional)'}
            </span>
            <textarea
              value={reasonRequired ? reason : note}
              onChange={(e) => reasonRequired ? setReason(e.target.value) : setNote(e.target.value)}
              rows={3}
              required={reasonRequired}
              className="mt-1 block w-full rounded-md border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 px-3 py-2 text-sm"
            />
          </label>
          {error && <p role="alert" className="text-sm text-red-700 dark:text-red-300">{error}</p>}
          <div className="flex justify-end gap-2">
            <button type="button" onClick={onClose} disabled={submitting} className="px-3 min-h-[40px] rounded-lg border text-sm">Cancel</button>
            <button type="submit" disabled={submitting} className="px-4 min-h-[40px] rounded-lg bg-blue-600 text-white text-sm font-medium hover:bg-blue-700 disabled:opacity-60">
              {submitting ? 'Working…' : 'Apply'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default function TicketDetail() {
  const { ticketId } = useParams();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [modal, setModal] = useState(null);
  const activityRef = useRef(null);

  const fromFilter = searchParams.get('from') || 'open';

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const result = await fetchTicketDetail(ticketId);
      setData(result);
      setError('');
    } catch (err) {
      setError(err?.response?.data?.detail || err?.message || 'Failed to load ticket.');
    } finally {
      setLoading(false);
    }
  }, [ticketId]);

  useEffect(() => { load(); }, [load]);

  const handleNoteAdded = (event) => {
    setData((prev) => ({
      ...prev,
      activity: [...(prev?.activity ?? []), event],
    }));
    activityRef.current?.lastElementChild?.scrollIntoView({ behavior: 'smooth' });
  };

  const handleNoteUpdated = (updated) => {
    setData((prev) => ({
      ...prev,
      activity: prev.activity.map((e) => (e.id === updated.id ? updated : e)),
    }));
  };

  const handleTransitionSubmitted = () => { setModal(null); load(); };

  const handleUndo = async () => {
    try {
      await correctLastTransition(ticketId);
      load();
    } catch (err) {
      alert(err?.response?.data?.detail || 'Could not undo transition.');
    }
  };

  if (loading && !data) {
    return <div className="px-4 py-6 max-w-2xl mx-auto"><p className="text-gray-500">Loading…</p></div>;
  }

  if (error && !data) {
    return (
      <div className="px-4 py-6 max-w-2xl mx-auto">
        <div role="alert" className="rounded-xl border border-red-200 bg-red-50 dark:bg-red-900/20 px-4 py-3 text-sm text-red-800 dark:text-red-200">
          {error}
        </div>
      </div>
    );
  }

  const { ticket, photos = [], activity = [] } = data || {};
  const isOpen = ticket && ['new', 'in_progress'].includes(ticket.status);

  return (
    <div className="max-w-2xl mx-auto pb-32" data-testid="ticket-detail">
      {/* Header */}
      <div className="sticky top-0 z-10 bg-white dark:bg-gray-950 border-b border-gray-200 dark:border-gray-700 px-4 py-3 flex items-center gap-3">
        <button
          type="button"
          onClick={() => navigate(`/maintenance?filter=${fromFilter}`)}
          className="text-sm text-blue-600 dark:text-blue-400 hover:underline"
          data-testid="back-button"
        >
          ← Queue
        </button>
        {ticket && (
          <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${STATUS_BADGE[ticket.status] || ''}`}>
            {STATUS_LABEL[ticket.status] || ticket.status}
          </span>
        )}
      </div>

      {ticket && (
        <div className="px-4 py-4 space-y-4">
          {/* Ticket header section */}
          <section data-testid="ticket-header">
            <div className="flex items-start justify-between gap-2 flex-wrap">
              <div>
                <h1 className="text-xl font-semibold text-gray-900 dark:text-white">
                  {ticket.location}
                </h1>
                <p className="text-sm text-gray-600 dark:text-gray-400 mt-0.5">
                  {ticket.category?.replace(/_/g, ' ')}
                  {ticket.urgency === 'urgent' && (
                    <span className="ml-2 inline-flex items-center px-2 py-0.5 rounded-full bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-100 text-xs font-semibold">
                      Urgent
                    </span>
                  )}
                </p>
                {ticket.urgency === 'urgent' && ticket.urgent_reason && (
                  <p className="text-sm text-red-700 dark:text-red-300 mt-1">
                    Reason: {ticket.urgent_reason}
                  </p>
                )}
              </div>
            </div>
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-2">
              {ticket.submitter_name ? `Submitted by ${ticket.submitter_name} · ` : ''}
              {ticket.created_at ? new Date(ticket.created_at).toLocaleString() : ''}
            </p>
          </section>

          {/* Description */}
          {ticket.description && (
            <section data-testid="ticket-description">
              <h2 className="text-sm font-semibold text-gray-700 dark:text-gray-200 mb-1">Description</h2>
              <p className="text-sm text-gray-800 dark:text-gray-100 whitespace-pre-wrap">{ticket.description}</p>
            </section>
          )}

          {/* Photos — original submission */}
          {photos.filter((p) => !p.is_followup).length > 0 && (
            <section data-testid="ticket-photos">
              <h2 className="text-sm font-semibold text-gray-700 dark:text-gray-200 mb-2">Photos</h2>
              <div className="flex flex-wrap gap-2">
                {photos.filter((p) => !p.is_followup).map((p) => (
                  <a
                    key={p.id}
                    href={p.image_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="block w-20 h-20 rounded-lg overflow-hidden border border-gray-200 dark:border-gray-700"
                  >
                    <img src={p.image_url} alt={p.caption || 'Ticket photo'} className="w-full h-full object-cover" />
                  </a>
                ))}
              </div>
            </section>
          )}

          {/* Activity */}
          <section data-testid="ticket-activity">
            <h2 className="text-sm font-semibold text-gray-700 dark:text-gray-200 mb-2">Activity</h2>
            {activity.length === 0 ? (
              <p className="text-sm text-gray-500 dark:text-gray-400">No activity yet.</p>
            ) : (
              <div ref={activityRef} className="space-y-0">
                {activity.map((e) => (
                  <ActivityEvent
                    key={e.id}
                    event={e}
                    ticketId={ticketId}
                    onNoteUpdated={handleNoteUpdated}
                  />
                ))}
              </div>
            )}

            {/* Inline note form */}
            {isOpen && (
              <div className="mt-4 rounded-xl border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900 p-3">
                <h3 className="text-sm font-medium text-gray-700 dark:text-gray-200 mb-2">Add note</h3>
                <NoteForm ticketId={ticketId} onNoteAdded={handleNoteAdded} />
              </div>
            )}
          </section>
        </div>
      )}

      {/* Actions pinned to bottom */}
      {ticket && (
        <TransitionActions
          ticket={ticket}
          onTransition={(toState) => setModal(toState)}
          onUndo={handleUndo}
        />
      )}

      {modal && (
        <TransitionModal
          toState={modal}
          ticket={ticket}
          onClose={() => setModal(null)}
          onSubmitted={handleTransitionSubmitted}
        />
      )}
    </div>
  );
}
