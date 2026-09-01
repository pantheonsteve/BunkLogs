import { useState } from 'react';

import { createAdminPerson } from '../../../api/admin';
import Button from '../../../components/ui/Button';
import Modal from '../../../components/ui/Modal';
import Note from '../../../components/ui/Note';
import { MEMBERSHIP_ROLE_OPTIONS, SUBJECT_ROLES } from '../../../components/admin/PersonProfilePanel';

function Field({ label, value, onChange, type = 'text' }) {
  return (
    <label className="block text-xs font-medium text-gray-700 dark:text-gray-300">
      {label}
      <input
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="mt-1 w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm text-gray-900 dark:text-white"
      />
    </label>
  );
}

/**
 * Create a Person plus their first Membership.
 *
 * A duplicate email comes back as a 409 carrying the existing record, so
 * the conflict is offered as "open the person you already have" rather
 * than as an error the admin has to decode.
 */
export default function AddPersonModal({ programs, defaultProgramId, onClose, onCreated }) {
  const [draft, setDraft] = useState({
    first_name: '',
    last_name: '',
    preferred_name: '',
    email: '',
    program_id: defaultProgramId || programs[0]?.id || '',
    role: 'counselor',
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [conflict, setConflict] = useState(null);
  const isSubjectRole = SUBJECT_ROLES.includes(draft.role);

  const submit = async (e) => {
    e.preventDefault();
    setSaving(true);
    setError('');
    setConflict(null);
    try {
      const created = await createAdminPerson({
        first_name: draft.first_name,
        last_name: draft.last_name,
        preferred_name: draft.preferred_name,
        email: draft.email,
        membership: {
          program_id: Number(draft.program_id),
          role: draft.role,
        },
      });
      onCreated(created);
    } catch (err) {
      const data = err?.response?.data;
      if (err?.response?.status === 409 && data?.existing_person) {
        setConflict(data.existing_person);
      } else {
        setError(data?.detail || 'Could not create.');
      }
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal
      title="Add person"
      onClose={onClose}
      dismissible={!saving}
      data-testid="add-person-modal"
      footer={
        <>
          <Button variant="secondary" onClick={onClose} disabled={saving}>
            Cancel
          </Button>
          <div className="flex-1" />
          <Button onClick={submit} disabled={saving} data-testid="add-person-save">
            {saving ? 'Saving…' : 'Create person'}
          </Button>
        </>
      }
    >
      <form onSubmit={submit} className="space-y-3">
        <Field label="First name" value={draft.first_name} onChange={(v) => setDraft({ ...draft, first_name: v })} />
        <Field label="Last name" value={draft.last_name} onChange={(v) => setDraft({ ...draft, last_name: v })} />
        <Field label="Preferred name" value={draft.preferred_name} onChange={(v) => setDraft({ ...draft, preferred_name: v })} />
        <Field label="Email (optional)" type="email" value={draft.email} onChange={(v) => setDraft({ ...draft, email: v })} />
        <label className="block text-xs font-medium text-gray-700 dark:text-gray-300">
          Program
          <select
            value={draft.program_id}
            onChange={(e) => setDraft({ ...draft, program_id: e.target.value })}
            className="mt-1 w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm"
          >
            {programs.map((p) => (
              <option key={p.id} value={p.id}>{p.name}</option>
            ))}
          </select>
        </label>
        <label className="block text-xs font-medium text-gray-700 dark:text-gray-300">
          Initial role
          <select
            value={draft.role}
            onChange={(e) => setDraft({ ...draft, role: e.target.value })}
            className="mt-1 w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm"
          >
            {MEMBERSHIP_ROLE_OPTIONS.map((r) => <option key={r} value={r}>{r}</option>)}
          </select>
        </label>
        {isSubjectRole && (
          <Note tone="info" data-testid="add-person-subject-role-note">
            Campers and students are subjects of reflections rather than users of
            the product, so no login is created and they cannot be invited.
          </Note>
        )}
        {error && <Note tone="danger">{error}</Note>}
        {conflict && (
          <Note tone="warn" title="That email already exists" data-testid="add-person-conflict">
            <p>
              <strong>{conflict.full_name}</strong> already has a record. Add the
              new membership to them instead of creating a duplicate.
            </p>
            <Button
              size="sm"
              variant="secondary"
              className="mt-2"
              onClick={() => onCreated(conflict)}
            >
              Open existing person
            </Button>
          </Note>
        )}
      </form>
    </Modal>
  );
}
