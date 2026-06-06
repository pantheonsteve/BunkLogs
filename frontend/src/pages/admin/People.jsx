import { useCallback, useEffect, useState } from 'react';
import {
  listAdminPeople,
  getAdminPerson,
  createAdminPerson,
  patchAdminPerson,
  addAdminMembership,
  patchAdminMembership,
  deactivateAdminMembership,
  inviteAdminPerson,
  listAdminPrograms,
} from '../../api/admin';
import BulkImportModal from '../../components/admin/BulkImportModal';

/**
 * Step 7_13 PR2 — People + Memberships management (Story 55).
 *
 * Two-pane layout: filter / list on the left, profile drawer on the
 * right. Profile has Identity / Memberships / Recent activity tabs
 * per Story 55 c5.
 *
 * Bulk import affordance is added in PR3.
 */
const ROLE_OPTIONS = [
  'admin', 'leadership_team', 'unit_head', 'counselor', 'junior_counselor',
  'specialist', 'general_counselor', 'kitchen_staff', 'maintenance',
  'administrative_staff', 'housekeeping', 'camper_care', 'health_center',
  'medical', 'special_diets',
  'madrich', 'faculty', 'camper',
];

function classNames(...args) {
  return args.filter(Boolean).join(' ');
}

function Tabs({ tabs, activeTab, onChange }) {
  return (
    <nav className="border-b border-gray-200 dark:border-gray-700 flex gap-3">
      {tabs.map((t) => (
        <button
          key={t.key}
          type="button"
          data-testid={`people-tab-${t.key}`}
          onClick={() => onChange(t.key)}
          className={classNames(
            'pb-2 -mb-px text-sm font-medium border-b-2',
            activeTab === t.key
              ? 'border-indigo-500 text-indigo-700 dark:text-indigo-200'
              : 'border-transparent text-gray-500 hover:text-gray-800 dark:hover:text-gray-200',
          )}
        >
          {t.label}
        </button>
      ))}
    </nav>
  );
}

function ProfileTabs({ person, programs, onPersonChanged }) {
  const [tab, setTab] = useState('identity');
  return (
    <div className="space-y-3">
      <Tabs
        tabs={[
          { key: 'identity', label: 'Identity' },
          { key: 'memberships', label: 'Memberships' },
          { key: 'activity', label: 'Recent activity' },
        ]}
        activeTab={tab}
        onChange={setTab}
      />
      {tab === 'identity' && (
        <IdentityTab person={person} onSaved={onPersonChanged} />
      )}
      {tab === 'memberships' && (
        <MembershipsTab
          person={person}
          programs={programs}
          onChanged={onPersonChanged}
        />
      )}
      {tab === 'activity' && <ActivityTab person={person} />}
    </div>
  );
}

function IdentityTab({ person, onSaved }) {
  const [draft, setDraft] = useState({
    first_name: person.first_name || '',
    last_name: person.last_name || '',
    preferred_name: person.preferred_name || '',
    email: person.email || '',
    preferred_language: person.preferred_language || 'en',
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const handleSubmit = async (e) => {
    e.preventDefault();
    setSaving(true);
    setError('');
    try {
      const updated = await patchAdminPerson(person.id, draft);
      onSaved(updated);
    } catch (err) {
      setError(err?.response?.data?.detail || 'Could not save.');
    } finally {
      setSaving(false);
    }
  };
  return (
    <form onSubmit={handleSubmit} className="space-y-2" data-testid="identity-tab">
      <FieldInput
        label="First name"
        value={draft.first_name}
        onChange={(v) => setDraft({ ...draft, first_name: v })}
      />
      <FieldInput
        label="Last name"
        value={draft.last_name}
        onChange={(v) => setDraft({ ...draft, last_name: v })}
      />
      <FieldInput
        label="Preferred name"
        value={draft.preferred_name}
        onChange={(v) => setDraft({ ...draft, preferred_name: v })}
      />
      <FieldInput
        label="Email"
        type="email"
        value={draft.email}
        onChange={(v) => setDraft({ ...draft, email: v })}
      />
      <label className="block text-xs font-medium text-gray-700">
        Preferred language
        <select
          value={draft.preferred_language}
          onChange={(e) => setDraft({ ...draft, preferred_language: e.target.value })}
          className="mt-1 w-full rounded-md border border-gray-300 bg-white p-2 text-sm"
        >
          <option value="en">English</option>
          <option value="es">Spanish</option>
          <option value="he">Hebrew</option>
        </select>
      </label>
      {error && <p className="text-sm text-red-700">{error}</p>}
      <button
        type="submit"
        disabled={saving}
        data-testid="identity-save"
        className="px-3 py-1.5 rounded-md text-sm bg-indigo-600 text-white disabled:opacity-60"
      >
        {saving ? 'Saving…' : 'Save identity'}
      </button>
    </form>
  );
}

function MembershipsTab({ person, programs, onChanged }) {
  const [adding, setAdding] = useState(false);
  return (
    <div className="space-y-3" data-testid="memberships-tab">
      <ul className="divide-y border rounded-md bg-white dark:bg-gray-900">
        {(person.memberships || []).length === 0 && (
          <li className="p-3 text-sm italic text-gray-500">No memberships yet.</li>
        )}
        {(person.memberships || []).map((m) => (
          <MembershipRow key={m.id} membership={m} onChanged={onChanged} />
        ))}
      </ul>
      <button
        type="button"
        data-testid="add-membership"
        onClick={() => setAdding((v) => !v)}
        className="px-3 py-1.5 rounded-md text-sm border border-indigo-200 text-indigo-700 hover:bg-indigo-50"
      >
        {adding ? 'Cancel' : 'Add membership'}
      </button>
      {adding && (
        <AddMembershipForm
          person={person}
          programs={programs}
          onAdded={() => {
            setAdding(false);
            onChanged();
          }}
        />
      )}
    </div>
  );
}

function MembershipRow({ membership, onChanged }) {
  const [deactivating, setDeactivating] = useState(false);
  const [reason, setReason] = useState('');
  const [saving, setSaving] = useState(false);
  const handleDeactivate = async () => {
    if (!reason.trim()) return;
    setSaving(true);
    try {
      await deactivateAdminMembership(membership.id, reason);
      onChanged();
    } finally {
      setSaving(false);
      setDeactivating(false);
      setReason('');
    }
  };
  return (
    <li className="p-3 text-sm flex flex-col gap-1" data-testid={`membership-row-${membership.id}`}>
      <div className="flex items-center justify-between">
        <span>
          <span className="font-medium">{membership.role}</span>
          <span className="ml-2 text-xs text-gray-500">{membership.program_name || '—'}</span>
        </span>
        <span className={classNames(
          'text-xs px-2 py-0.5 rounded-full',
          membership.is_active
            ? 'bg-emerald-100 text-emerald-800'
            : 'bg-gray-200 text-gray-700',
        )}>
          {membership.is_active ? 'active' : 'inactive'}
        </span>
      </div>
      {membership.tags?.length > 0 && (
        <p className="text-xs text-gray-500">Tags: {membership.tags.join(', ')}</p>
      )}
      {membership.is_active && (
        <div className="mt-1 flex items-center gap-2">
          {!deactivating ? (
            <button
              type="button"
              data-testid={`membership-deactivate-${membership.id}`}
              onClick={() => setDeactivating(true)}
              className="text-xs text-red-700 underline"
            >
              Deactivate
            </button>
          ) : (
            <>
              <input
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                placeholder="Reason"
                className="rounded-md border border-gray-300 p-1 text-xs flex-1"
              />
              <button
                type="button"
                disabled={!reason.trim() || saving}
                onClick={handleDeactivate}
                className="text-xs px-2 py-1 rounded-md bg-red-600 text-white disabled:opacity-60"
              >
                {saving ? '…' : 'Confirm'}
              </button>
            </>
          )}
        </div>
      )}
    </li>
  );
}

function AddMembershipForm({ person, programs, onAdded }) {
  const [draft, setDraft] = useState({
    program_id: programs[0]?.id || '',
    role: 'counselor',
    grade_level: '',
    tags: '',
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const submit = async (e) => {
    e.preventDefault();
    setSaving(true);
    setError('');
    try {
      const tags = draft.tags
        .split(',').map((t) => t.trim()).filter(Boolean);
      await addAdminMembership(person.id, {
        program_id: Number(draft.program_id),
        role: draft.role,
        grade_level: draft.grade_level ? Number(draft.grade_level) : null,
        tags,
      });
      onAdded();
    } catch (err) {
      setError(err?.response?.data?.detail || 'Could not add.');
    } finally {
      setSaving(false);
    }
  };
  return (
    <form onSubmit={submit} className="rounded-md border border-gray-200 p-3 bg-gray-50 space-y-2" data-testid="add-membership-form">
      <label className="block text-xs font-medium">Program
        <select
          value={draft.program_id}
          onChange={(e) => setDraft({ ...draft, program_id: e.target.value })}
          className="mt-1 w-full rounded-md border border-gray-300 p-2 text-sm"
        >
          {programs.map((p) => (
            <option key={p.id} value={p.id}>{p.name}</option>
          ))}
        </select>
      </label>
      <label className="block text-xs font-medium">Role
        <select
          value={draft.role}
          onChange={(e) => setDraft({ ...draft, role: e.target.value })}
          className="mt-1 w-full rounded-md border border-gray-300 p-2 text-sm"
        >
          {ROLE_OPTIONS.map((r) => (
            <option key={r} value={r}>{r}</option>
          ))}
        </select>
      </label>
      <FieldInput label="Grade level" value={draft.grade_level} onChange={(v) => setDraft({ ...draft, grade_level: v })} />
      <FieldInput label="Tags (comma-separated)" value={draft.tags} onChange={(v) => setDraft({ ...draft, tags: v })} />
      {error && <p className="text-sm text-red-700">{error}</p>}
      <button
        type="submit"
        disabled={saving}
        data-testid="add-membership-save"
        className="px-3 py-1.5 rounded-md text-sm bg-indigo-600 text-white disabled:opacity-60"
      >
        {saving ? 'Adding…' : 'Add membership'}
      </button>
    </form>
  );
}

function ActivityTab({ person }) {
  const events = person.recent_activity || [];
  if (!events.length) {
    return <p className="text-sm italic text-gray-500" data-testid="activity-empty">No recent activity in the last 30 days.</p>;
  }
  return (
    <ul className="space-y-1.5 text-sm" data-testid="activity-tab">
      {events.map((ev) => (
        <li key={ev.id} className="rounded-md border border-gray-200 p-2 bg-white dark:bg-gray-900">
          <p className="font-medium">{ev.event_type} · {ev.content_type}</p>
          <p className="text-xs text-gray-500">{new Date(ev.created_at).toLocaleString()}</p>
          {ev.reason_note && <p className="text-xs">{ev.reason_note}</p>}
        </li>
      ))}
    </ul>
  );
}

function FieldInput({ label, value, onChange, type = 'text' }) {
  return (
    <label className="block text-xs font-medium text-gray-700">
      {label}
      <input
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="mt-1 w-full rounded-md border border-gray-300 bg-white p-2 text-sm"
      />
    </label>
  );
}

function AddPersonModal({ programs, onClose, onCreated }) {
  const [draft, setDraft] = useState({
    first_name: '',
    last_name: '',
    preferred_name: '',
    email: '',
    program_id: programs[0]?.id || '',
    role: 'counselor',
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [conflict, setConflict] = useState(null);
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
    <div
      role="dialog"
      data-testid="add-person-modal"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
    >
      <form
        onSubmit={submit}
        className="w-full max-w-md rounded-xl bg-white p-5 shadow-lg space-y-2 dark:bg-gray-900"
      >
        <h2 className="text-base font-semibold">Add Person</h2>
        <FieldInput label="First name" value={draft.first_name} onChange={(v) => setDraft({ ...draft, first_name: v })} />
        <FieldInput label="Last name" value={draft.last_name} onChange={(v) => setDraft({ ...draft, last_name: v })} />
        <FieldInput label="Preferred name" value={draft.preferred_name} onChange={(v) => setDraft({ ...draft, preferred_name: v })} />
        <FieldInput label="Email" type="email" value={draft.email} onChange={(v) => setDraft({ ...draft, email: v })} />
        <label className="block text-xs font-medium">Program
          <select
            value={draft.program_id}
            onChange={(e) => setDraft({ ...draft, program_id: e.target.value })}
            className="mt-1 w-full rounded-md border border-gray-300 p-2 text-sm"
          >
            {programs.map((p) => (
              <option key={p.id} value={p.id}>{p.name}</option>
            ))}
          </select>
        </label>
        <label className="block text-xs font-medium">Initial role
          <select
            value={draft.role}
            onChange={(e) => setDraft({ ...draft, role: e.target.value })}
            className="mt-1 w-full rounded-md border border-gray-300 p-2 text-sm"
          >
            {ROLE_OPTIONS.map((r) => <option key={r} value={r}>{r}</option>)}
          </select>
        </label>
        {error && <p className="text-sm text-red-700">{error}</p>}
        {conflict && (
          <div className="rounded-md border border-amber-300 bg-amber-50 p-2 text-sm space-y-1" data-testid="add-person-conflict">
            <p>A Person with this email already exists: <strong>{conflict.full_name}</strong>.</p>
            <p className="text-xs">Add a new membership to the existing record instead?</p>
            <button
              type="button"
              onClick={() => onCreated(conflict)}
              className="px-2 py-1 rounded-md text-xs bg-amber-600 text-white"
            >
              Open existing
            </button>
          </div>
        )}
        <div className="flex items-center justify-end gap-2 pt-1">
          <button type="button" onClick={onClose} className="text-sm text-gray-600 hover:underline">Cancel</button>
          <button
            type="submit"
            disabled={saving}
            data-testid="add-person-save"
            className="px-3 py-1.5 rounded-md text-sm bg-indigo-600 text-white disabled:opacity-60"
          >
            {saving ? 'Saving…' : 'Create Person'}
          </button>
        </div>
      </form>
    </div>
  );
}

export default function AdminPeople() {
  const [people, setPeople] = useState([]);
  const [programs, setPrograms] = useState([]);
  const [search, setSearch] = useState('');
  const [roleFilter, setRoleFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('active');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedId, setSelectedId] = useState(null);
  const [selectedPerson, setSelectedPerson] = useState(null);
  const [adding, setAdding] = useState(false);
  const [importing, setImporting] = useState(false);
  const [invitedStatus, setInvitedStatus] = useState({});

  const load = useCallback(async () => {
    setError(null);
    setLoading(true);
    try {
      const [list, progList] = await Promise.all([
        listAdminPeople({
          search,
          role: roleFilter,
          status: statusFilter,
          page_size: 100,
        }),
        listAdminPrograms('active'),
      ]);
      setPeople(list.results || []);
      setPrograms(progList.results || []);
    } catch (err) {
      setError(err);
    } finally {
      setLoading(false);
    }
  }, [search, roleFilter, statusFilter]);

  useEffect(() => { load(); }, [load]);

  useEffect(() => {
    if (selectedId == null) {
      setSelectedPerson(null);
      return;
    }
    getAdminPerson(selectedId).then(setSelectedPerson).catch(() => setSelectedPerson(null));
  }, [selectedId]);

  const refreshSelected = () => {
    if (selectedId == null) return;
    getAdminPerson(selectedId).then(setSelectedPerson);
  };

  const handleInvite = async (personId) => {
    setInvitedStatus({ ...invitedStatus, [personId]: 'pending' });
    try {
      await inviteAdminPerson(personId);
      setInvitedStatus({ ...invitedStatus, [personId]: 'sent' });
    } catch {
      setInvitedStatus({ ...invitedStatus, [personId]: 'error' });
    }
  };

  return (
    <main className="grow px-4 sm:px-6 lg:px-8 py-6 w-full max-w-6xl mx-auto" data-testid="admin-people">
      <header className="flex items-center justify-between mb-4">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">People</h1>
        <div className="flex items-center gap-2">
          <button
            type="button"
            data-testid="open-bulk-import"
            onClick={() => setImporting(true)}
            className="px-3 py-1.5 rounded-md text-sm border border-indigo-300 text-indigo-700 hover:bg-indigo-50"
          >
            Bulk import
          </button>
          <button
            type="button"
            data-testid="open-add-person"
            onClick={() => setAdding(true)}
            className="px-3 py-1.5 rounded-md text-sm bg-indigo-600 text-white"
          >
            Add Person
          </button>
        </div>
      </header>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-2 mb-4">
        <FieldInput label="Search name or email" value={search} onChange={setSearch} />
        <label className="block text-xs font-medium">Role
          <select
            value={roleFilter}
            onChange={(e) => setRoleFilter(e.target.value)}
            className="mt-1 w-full rounded-md border border-gray-300 p-2 text-sm"
          >
            <option value="">Any</option>
            {ROLE_OPTIONS.map((r) => <option key={r} value={r}>{r}</option>)}
          </select>
        </label>
        <label className="block text-xs font-medium">Status
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="mt-1 w-full rounded-md border border-gray-300 p-2 text-sm"
          >
            <option value="active">Active</option>
            <option value="inactive">Inactive</option>
            <option value="">All</option>
          </select>
        </label>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <section data-testid="people-list" className="space-y-2">
          {loading ? (
            <p className="text-sm text-gray-500">Loading…</p>
          ) : error ? (
            <p className="text-sm text-red-700">Could not load people.</p>
          ) : (
            <ul className="divide-y rounded-md border bg-white dark:bg-gray-900">
              {people.length === 0 && (
                <li className="p-3 text-sm italic text-gray-500">No people match those filters.</li>
              )}
              {people.map((p) => (
                <li
                  key={p.id}
                  data-testid={`person-row-${p.id}`}
                  className={classNames(
                    'p-3 cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800',
                    selectedId === p.id && 'bg-indigo-50 dark:bg-indigo-900/20',
                  )}
                  onClick={() => setSelectedId(p.id)}
                >
                  <p className="font-medium text-sm">{p.full_name}</p>
                  <p className="text-xs text-gray-500">{p.email || 'no email'}</p>
                </li>
              ))}
            </ul>
          )}
        </section>
        <aside data-testid="person-drawer" className="rounded-md border bg-white dark:bg-gray-900 p-4">
          {!selectedPerson ? (
            <p className="text-sm italic text-gray-500">Select a Person to view their profile.</p>
          ) : (
            <>
              <header className="flex items-center justify-between mb-3">
                <h2 className="text-lg font-semibold">{selectedPerson.full_name}</h2>
                <button
                  type="button"
                  data-testid="invite-person"
                  onClick={() => handleInvite(selectedPerson.id)}
                  disabled={!selectedPerson.email || invitedStatus[selectedPerson.id] === 'pending'}
                  className="text-xs px-2 py-1 rounded-md border border-indigo-300 text-indigo-700 hover:bg-indigo-50 disabled:opacity-50"
                >
                  {invitedStatus[selectedPerson.id] === 'sent' ? 'Invitation sent' : 'Send invitation'}
                </button>
              </header>
              <ProfileTabs
                person={selectedPerson}
                programs={programs}
                onPersonChanged={refreshSelected}
              />
            </>
          )}
        </aside>
      </div>
      {adding && (
        <AddPersonModal
          programs={programs}
          onClose={() => setAdding(false)}
          onCreated={(person) => {
            setAdding(false);
            load();
            if (person?.id) setSelectedId(person.id);
          }}
        />
      )}
      {importing && (
        <BulkImportModal
          programs={programs}
          onClose={() => { setImporting(false); load(); }}
        />
      )}
    </main>
  );
}
