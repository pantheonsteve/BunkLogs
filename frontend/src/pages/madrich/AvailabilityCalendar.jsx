/**
 * Madrich Sunday availability calendar — Step 4_7.
 *
 * Month-grouped list of upcoming program sessions (mobile-first; no
 * calendar-widget dependency). Each card lets the Madrich mark
 * Available / Tentative / Unavailable with an optional short note.
 * Operational scheduling signal only -- separate from the reflection
 * flow (Story 62 c3: no day-off toggle on reflections).
 *
 * Per Story 61: no other Madrichim's availability is shown here.
 */

import { useCallback, useEffect, useState } from 'react';
import { fetchAvailability, upsertAvailability } from '../../api/madrichAvailability';
import { useAuth } from '../../auth/AuthContext';

const STATUS_OPTIONS = [
  { value: 'available', label: 'Available', activeClass: 'bg-green-600 text-white border-green-600' },
  { value: 'tentative', label: 'Tentative', activeClass: 'bg-yellow-500 text-white border-yellow-500' },
  { value: 'unavailable', label: 'Unavailable', activeClass: 'bg-red-600 text-white border-red-600' },
];

function monthLabel(sessionDate) {
  const d = new Date(`${sessionDate}T00:00:00`);
  return d.toLocaleDateString(undefined, { month: 'long', year: 'numeric' });
}

function groupByMonth(sessions) {
  const groups = [];
  let current = null;
  for (const session of sessions) {
    const label = monthLabel(session.session_date);
    if (!current || current.label !== label) {
      current = { label, sessions: [] };
      groups.push(current);
    }
    current.sessions.push(session);
  }
  return groups;
}

function SessionCard({ session, orgSlug, onSaved }) {
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [noteOpen, setNoteOpen] = useState(false);
  const [noteDraft, setNoteDraft] = useState(session.commitment?.note || '');

  const status = session.commitment?.status ?? null;
  const { editable } = session;

  useEffect(() => {
    setNoteDraft(session.commitment?.note || '');
  }, [session.commitment?.note]);

  const save = async (nextStatus, nextNote) => {
    if (!editable || saving) return;
    setSaving(true);
    setError(null);
    try {
      await upsertAvailability(orgSlug, session.session_date, {
        status: nextStatus,
        note: nextNote,
      });
      await onSaved();
    } catch {
      setError('Could not save. Try again.');
    } finally {
      setSaving(false);
    }
  };

  const handleStatusChange = (nextStatus) => save(nextStatus, session.commitment?.note || '');
  const handleNoteSave = () => save(status, noteDraft).then(() => setNoteOpen(false));

  return (
    <li
      className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-4"
      data-testid={`availability-card-${session.session_date}`}
    >
      <div className="flex items-center justify-between gap-3 mb-2">
        <p className="font-medium text-gray-900 dark:text-white">{session.label}</p>
        {saving && <span className="text-xs text-gray-400 dark:text-gray-500">Saving…</span>}
      </div>

      <div className="grid grid-cols-3 gap-2" role="group" aria-label={`Status for ${session.label}`}>
        {STATUS_OPTIONS.map((opt) => {
          const active = status === opt.value;
          return (
            <button
              key={opt.value}
              type="button"
              disabled={!editable || saving}
              onClick={() => handleStatusChange(opt.value)}
              aria-pressed={active}
              className={`min-h-[44px] rounded-lg border text-sm font-medium px-2 py-2 transition-colors disabled:opacity-50 disabled:cursor-not-allowed ${
                active
                  ? opt.activeClass
                  : 'border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700'
              }`}
              data-testid={`availability-status-${session.session_date}-${opt.value}`}
            >
              {opt.label}
            </button>
          );
        })}
      </div>

      {status === null && editable && (
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-2">
          Tap a status so your Director knows your plan.
        </p>
      )}

      {!editable && (
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-2" data-testid={`availability-locked-${session.session_date}`}>
          Availability for this Sunday locked Saturday at 6:00 PM.
        </p>
      )}

      {error && <p className="text-sm text-red-600 dark:text-red-400 mt-2">{error}</p>}

      {editable && status !== null && (
        <div className="mt-2">
          {!noteOpen ? (
            <button
              type="button"
              onClick={() => setNoteOpen(true)}
              className="text-xs text-indigo-600 dark:text-indigo-400 hover:underline"
              data-testid={`availability-note-toggle-${session.session_date}`}
            >
              {session.commitment?.note ? `Note: ${session.commitment.note}` : 'Add a note'}
            </button>
          ) : (
            <div className="space-y-2">
              <textarea
                value={noteDraft}
                onChange={(e) => setNoteDraft(e.target.value.slice(0, 280))}
                maxLength={280}
                rows={2}
                placeholder="Optional note (e.g. 'Need to leave by 12:30')"
                className="w-full rounded-md border-gray-300 dark:border-gray-600 dark:bg-gray-700 text-sm"
                data-testid={`availability-note-input-${session.session_date}`}
              />
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={handleNoteSave}
                  disabled={saving}
                  className="text-xs rounded-md bg-indigo-600 hover:bg-indigo-700 text-white px-3 py-1.5"
                  data-testid={`availability-note-save-${session.session_date}`}
                >
                  Save note
                </button>
                <button
                  type="button"
                  onClick={() => setNoteOpen(false)}
                  className="text-xs text-gray-500 dark:text-gray-400 px-3 py-1.5"
                >
                  Cancel
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </li>
  );
}

export default function AvailabilityCalendar() {
  const { orgSlug } = useAuth();
  const [payload, setPayload] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await fetchAvailability(orgSlug);
      setPayload(data);
      setError(null);
    } catch {
      setError('Could not load your availability calendar.');
    } finally {
      setLoading(false);
    }
  }, [orgSlug]);

  useEffect(() => {
    load();
  }, [load]);

  if (loading) {
    return (
      <div className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-[96rem] mx-auto" data-testid="availability-loading">
        <p className="text-gray-500 dark:text-gray-400">Loading…</p>
      </div>
    );
  }

  if (error || !payload) {
    return (
      <div className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-[96rem] mx-auto" data-testid="availability-error">
        <p className="text-red-600 dark:text-red-400">{error || 'Could not load your availability calendar.'}</p>
        <button onClick={load} className="mt-3 text-sm text-indigo-600 dark:text-indigo-400 underline">
          Retry
        </button>
      </div>
    );
  }

  const sessions = Array.isArray(payload.sessions) ? payload.sessions : [];
  const groups = groupByMonth(sessions);

  return (
    <div className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-[96rem] mx-auto space-y-6">
      <div>
        <p className="text-sm text-gray-500 dark:text-gray-400">{payload.program?.name}</p>
        <h1 className="text-xl font-bold text-gray-900 dark:text-white">My availability</h1>
      </div>

      {sessions.length === 0 ? (
        <div
          className="rounded-xl border border-dashed border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 p-4 text-sm text-gray-500 dark:text-gray-400"
          data-testid="availability-empty"
        >
          No upcoming sessions are scheduled yet.
        </div>
      ) : (
        groups.map((group) => (
          <section key={group.label} aria-label={group.label}>
            <h2 className="text-sm font-semibold text-gray-500 dark:text-gray-400 mb-2 uppercase tracking-wide">
              {group.label}
            </h2>
            <ul className="space-y-3">
              {group.sessions.map((session) => (
                <SessionCard
                  key={session.session_date}
                  session={session}
                  orgSlug={orgSlug}
                  onSaved={load}
                />
              ))}
            </ul>
          </section>
        ))
      )}
    </div>
  );
}
