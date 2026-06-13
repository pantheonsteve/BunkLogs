import { useEffect, useState } from 'react';
import {
  createAdminProgram,
  endAdminProgram,
  getAdminProgram,
  patchAdminProgram,
} from '../../api/admin';
import Button from '../ui/Button';

function FieldInput({ label, value, onChange, type = 'text', readOnly = false }) {
  return (
    <label className="block text-xs font-medium text-gray-700 dark:text-gray-300">
      {label}
      <input
        type={type}
        value={value}
        readOnly={readOnly}
        onChange={(e) => onChange(e.target.value)}
        className="mt-1 w-full rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 p-2 text-sm text-gray-900 dark:text-white read-only:bg-gray-50 dark:read-only:bg-gray-900/50"
      />
    </label>
  );
}

function ModalShell({ title, onClose, children, testId }) {
  return (
    <div
      role="dialog"
      data-testid={testId}
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
    >
      <div className="w-full max-w-md rounded-xl bg-white dark:bg-gray-900 p-5 shadow-lg space-y-3">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white">{title}</h2>
        {children}
      </div>
    </div>
  );
}

export function AddProgramModal({ onClose, onCreated }) {
  const [draft, setDraft] = useState({
    name: '',
    slug: '',
    program_type: '',
    start_date: '',
    end_date: '',
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  const submit = async (e) => {
    e.preventDefault();
    setSaving(true);
    setError('');
    try {
      const created = await createAdminProgram(draft);
      onCreated(created);
    } catch (err) {
      setError(err?.response?.data?.detail || 'Could not create program.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <ModalShell title="Add program" onClose={onClose} testId="add-program-modal">
      <form onSubmit={submit} className="space-y-2" data-testid="program-add-form">
        <FieldInput label="Name" value={draft.name} onChange={(v) => setDraft({ ...draft, name: v })} />
        <FieldInput label="Slug" value={draft.slug} onChange={(v) => setDraft({ ...draft, slug: v })} />
        <FieldInput label="Program type (e.g. summer_camp)" value={draft.program_type} onChange={(v) => setDraft({ ...draft, program_type: v })} />
        <FieldInput label="Start date (yyyy-mm-dd)" value={draft.start_date} onChange={(v) => setDraft({ ...draft, start_date: v })} />
        <FieldInput label="End date (yyyy-mm-dd, optional)" value={draft.end_date} onChange={(v) => setDraft({ ...draft, end_date: v })} />
        {error && <p className="text-sm text-red-700">{error}</p>}
        <div className="flex justify-end gap-2 pt-1">
          <Button type="button" variant="secondary" size="sm" onClick={onClose}>Cancel</Button>
          <Button type="submit" size="sm" disabled={saving}>
            {saving ? 'Creating…' : 'Create program'}
          </Button>
        </div>
      </form>
    </ModalShell>
  );
}

export function EditProgramModal({ programId, onClose, onSaved }) {
  const [draft, setDraft] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    getAdminProgram(programId)
      .then((program) => {
        if (cancelled || !program) return;
        setDraft({
          name: program.name || '',
          slug: program.slug || '',
          program_type: program.program_type || '',
          start_date: program.start_date || '',
          end_date: program.end_date || '',
        });
      })
      .catch(() => {
        if (!cancelled) setError('Could not load program.');
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => { cancelled = true; };
  }, [programId]);

  const submit = async (e) => {
    e.preventDefault();
    if (!draft) return;
    setSaving(true);
    setError('');
    try {
      const updated = await patchAdminProgram(programId, draft);
      onSaved(updated);
    } catch (err) {
      setError(err?.response?.data?.detail || 'Could not save program.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <ModalShell title="Edit program" onClose={onClose} testId="edit-program-modal">
      {loading ? (
        <p className="text-sm text-gray-500">Loading…</p>
      ) : !draft ? (
        <p className="text-sm text-red-700">{error || 'Program not found.'}</p>
      ) : (
        <form onSubmit={submit} className="space-y-2">
          <FieldInput label="Name" value={draft.name} onChange={(v) => setDraft({ ...draft, name: v })} />
          <FieldInput label="Slug" value={draft.slug} onChange={(v) => setDraft({ ...draft, slug: v })} />
          <FieldInput label="Program type" value={draft.program_type} onChange={(v) => setDraft({ ...draft, program_type: v })} />
          <FieldInput label="Start date (yyyy-mm-dd)" value={draft.start_date} onChange={(v) => setDraft({ ...draft, start_date: v })} />
          <FieldInput label="End date (yyyy-mm-dd, optional)" value={draft.end_date} onChange={(v) => setDraft({ ...draft, end_date: v })} />
          {error && <p className="text-sm text-red-700">{error}</p>}
          <div className="flex justify-end gap-2 pt-1">
            <Button type="button" variant="secondary" size="sm" onClick={onClose}>Cancel</Button>
            <Button type="submit" size="sm" disabled={saving}>
              {saving ? 'Saving…' : 'Save changes'}
            </Button>
          </div>
        </form>
      )}
    </ModalShell>
  );
}

export function ViewProgramModal({ programId, onClose }) {
  const [program, setProgram] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    getAdminProgram(programId)
      .then((data) => {
        if (!cancelled) setProgram(data);
      })
      .catch(() => {
        if (!cancelled) setError('Could not load program.');
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => { cancelled = true; };
  }, [programId]);

  return (
    <ModalShell title="View program" onClose={onClose} testId="view-program-modal">
      {loading ? (
        <p className="text-sm text-gray-500">Loading…</p>
      ) : error || !program ? (
        <p className="text-sm text-red-700">{error || 'Program not found.'}</p>
      ) : (
        <div className="space-y-2 text-sm" data-testid="view-program-details">
          <FieldInput label="Name" value={program.name || ''} onChange={() => {}} readOnly />
          <FieldInput label="Slug" value={program.slug || ''} onChange={() => {}} readOnly />
          <FieldInput label="Program type" value={program.program_type || ''} onChange={() => {}} readOnly />
          <FieldInput label="Start date" value={program.start_date || '—'} onChange={() => {}} readOnly />
          <FieldInput label="End date" value={program.end_date || '—'} onChange={() => {}} readOnly />
          <p className="text-xs text-gray-500 dark:text-gray-400">
            Status: {program.is_active ? 'Active' : 'Ended'}
          </p>
          <div className="flex justify-end pt-1">
            <Button type="button" size="sm" onClick={onClose}>Close</Button>
          </div>
        </div>
      )}
    </ModalShell>
  );
}

export function EndProgramModal({ program, onClose, onEnded }) {
  const [typed, setTyped] = useState('');
  const [reason, setReason] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [summary, setSummary] = useState(null);
  const expected = program.slug || program.name;
  const canSubmit = typed === expected && reason.trim();

  const submit = async (e) => {
    e.preventDefault();
    if (!canSubmit) return;
    setSubmitting(true);
    setError('');
    try {
      const data = await endAdminProgram(program.id, reason);
      setSummary(data?.summary || null);
    } catch (err) {
      setError(err?.response?.data?.detail || 'Could not end program.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <ModalShell title={`Delete program: ${program.name}`} onClose={onClose} testId="end-program-modal">
      {summary ? (
        <div className="space-y-2 text-sm" data-testid="end-program-summary">
          <p>This action ran in a single transaction.</p>
          <ul className="list-disc pl-5">
            <li>{summary.memberships_deactivated} memberships deactivated</li>
            <li>{summary.orders_closed} Camper Care orders closed</li>
            <li>{summary.maintenance_tickets_closed} maintenance tickets closed</li>
            <li>Ended at {summary.ended_at}</li>
          </ul>
          <div className="flex justify-end pt-1">
            <Button type="button" size="sm" onClick={onEnded}>Done</Button>
          </div>
        </div>
      ) : (
        <form onSubmit={submit} className="space-y-2">
          <p className="text-sm text-gray-600 dark:text-gray-300">
            This will deactivate all memberships in this program and close any open orders/tickets.
            Type <strong>{expected}</strong> to confirm.
          </p>
          <FieldInput label="Type to confirm" value={typed} onChange={setTyped} />
          <label className="block text-xs font-medium text-gray-700 dark:text-gray-300">Reason
            <textarea
              rows={3}
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              className="mt-1 w-full rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 p-2 text-sm text-gray-900 dark:text-white"
            />
          </label>
          {error && <p className="text-sm text-red-700">{error}</p>}
          <div className="flex justify-end gap-2 pt-1">
            <Button type="button" variant="secondary" size="sm" disabled={submitting} onClick={onClose}>Cancel</Button>
            <Button type="submit" size="sm" variant="danger" disabled={!canSubmit || submitting} data-testid="end-program-confirm">
              {submitting ? 'Ending…' : 'Delete program'}
            </Button>
          </div>
        </form>
      )}
    </ModalShell>
  );
}
