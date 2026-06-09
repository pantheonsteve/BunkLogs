import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  listAdminPeople,
  buildAdminPeopleListParams,
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
import DedupePeopleModal from '../../components/admin/DedupePeopleModal';
import DeletePersonModal from '../../components/admin/DeletePersonModal';
import { profileLink } from '../../utils/dashboardLinks';

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

const PAGE_SIZE_OPTIONS = [25, 50, 100];
const LAST_NAME_INITIALS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'.split('');

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

function PeopleListPagination({
  offset,
  resultCount,
  totalCount,
  loading,
  onPrevious,
  onNext,
}) {
  if (totalCount === 0) return null;
  const start = offset + 1;
  const end = Math.min(offset + resultCount, totalCount);
  const hasPrevious = offset > 0;
  const hasNext = offset + Math.max(resultCount, 1) < totalCount;
  return (
    <div
      data-testid="people-list-pagination"
      className="mt-3 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between text-sm text-gray-500"
    >
      <p>
        Showing <span className="font-medium text-gray-700 dark:text-gray-300">{start}</span>
        {' '}to{' '}
        <span className="font-medium text-gray-700 dark:text-gray-300">{end}</span>
        {' '}of{' '}
        <span className="font-medium text-gray-700 dark:text-gray-300">{totalCount}</span>
        {' '}· sorted A–Z by last name
      </p>
      <div className="flex items-center gap-2">
        <button
          type="button"
          data-testid="people-page-previous"
          disabled={!hasPrevious || loading}
          onClick={onPrevious}
          className="px-3 py-1 rounded-md border border-gray-300 bg-white text-gray-700 disabled:opacity-40 dark:bg-gray-800 dark:border-gray-600 dark:text-gray-200"
        >
          Previous
        </button>
        <button
          type="button"
          data-testid="people-page-next"
          disabled={!hasNext || loading}
          onClick={onNext}
          className="px-3 py-1 rounded-md border border-gray-300 bg-white text-gray-700 disabled:opacity-40 dark:bg-gray-800 dark:border-gray-600 dark:text-gray-200"
        >
          Next
        </button>
      </div>
    </div>
  );
}

function PersonProfilePanel({
  person,
  programs,
  invitedStatus,
  onInvite,
  onDelete,
  onPersonChanged,
  onDismiss,
}) {
  return (
    <div
      className="rounded-md border border-gray-200 dark:border-gray-700 p-3 bg-gray-50/50 dark:bg-gray-900/40"
      data-testid={`person-profile-panel-${person.id}`}
    >
      <header className="flex items-start justify-between gap-2 mb-3">
        <div>
          <h2 className="text-base font-semibold">
            <Link
              to={profileLink(person.id)}
              className="text-indigo-700 dark:text-indigo-300 hover:underline"
            >
              {person.full_name}
            </Link>
          </h2>
          <p className="text-xs text-gray-500">{person.email || 'no email'}</p>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <button
            type="button"
            data-testid={`delete-person-${person.id}`}
            onClick={() => onDelete(person)}
            className="text-xs px-2 py-1 rounded-md border border-red-300 text-red-700 hover:bg-red-50"
          >
            Delete
          </button>
          <button
            type="button"
            data-testid={`invite-person-${person.id}`}
            onClick={() => onInvite(person.id)}
            disabled={!person.email || invitedStatus[person.id] === 'pending'}
            className="text-xs px-2 py-1 rounded-md border border-indigo-300 text-indigo-700 hover:bg-indigo-50 disabled:opacity-50"
          >
            {invitedStatus[person.id] === 'sent' ? 'Invitation sent' : 'Send invitation'}
          </button>
          {onDismiss && (
            <button
              type="button"
              aria-label={`Remove ${person.full_name} from selection`}
              data-testid={`dismiss-person-${person.id}`}
              onClick={() => onDismiss(person.id)}
              className="text-xs px-2 py-1 rounded-md border border-gray-300 text-gray-600 hover:bg-gray-100"
            >
              ×
            </button>
          )}
        </div>
      </header>
      <ProfileTabs
        person={person}
        programs={programs}
        onPersonChanged={onPersonChanged}
      />
    </div>
  );
}

export default function AdminPeople() {
  const [people, setPeople] = useState([]);
  const [programs, setPrograms] = useState([]);
  const [search, setSearch] = useState('');
  const [roleFilter, setRoleFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('active');
  const [lastNameInitial, setLastNameInitial] = useState('');
  const [offset, setOffset] = useState(0);
  const [pageSize, setPageSize] = useState(50);
  const [totalCount, setTotalCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedIds, setSelectedIds] = useState(() => new Set());
  const [selectedPeople, setSelectedPeople] = useState(() => new Map());
  const [adding, setAdding] = useState(false);
  const [importing, setImporting] = useState(false);
  const [deduping, setDeduping] = useState(false);
  const [deletingPerson, setDeletingPerson] = useState(null);
  const [invitedStatus, setInvitedStatus] = useState({});
  const [reloadToken, setReloadToken] = useState(0);
  const reloadPeople = () => setReloadToken((token) => token + 1);

  useEffect(() => {
    const controller = new AbortController();
    let cancelled = false;

    const fetchPeople = async () => {
      setError(null);
      setLoading(true);
      try {
        const params = buildAdminPeopleListParams({
          search,
          role: roleFilter,
          status: statusFilter,
          last_name_initial: lastNameInitial,
          offset,
          page_size: pageSize,
        });
        const [list, progList] = await Promise.all([
          listAdminPeople(params, { signal: controller.signal }),
          listAdminPrograms('active'),
        ]);
        if (cancelled) return;
        setPeople(list.results || []);
        setTotalCount(list.count ?? 0);
        setPrograms(progList.results || []);
      } catch (err) {
        if (cancelled || err?.code === 'ERR_CANCELED' || err?.name === 'CanceledError') return;
        setError(err);
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    fetchPeople();
    return () => {
      cancelled = true;
      controller.abort();
    };
  }, [search, roleFilter, statusFilter, lastNameInitial, offset, pageSize, reloadToken]);

  const resetPage = () => setOffset(0);
  const updateSearch = (value) => {
    setSearch(value);
    resetPage();
  };

  useEffect(() => {
    let cancelled = false;
    const ids = Array.from(selectedIds);
    if (ids.length === 0) {
      setSelectedPeople(new Map());
      return undefined;
    }
    Promise.all(
      ids.map(async (id) => {
        try {
          const person = await getAdminPerson(id);
          return [id, person];
        } catch {
          return [id, null];
        }
      }),
    ).then((entries) => {
      if (cancelled) return;
      setSelectedPeople(new Map(entries.filter(([, person]) => person)));
    });
    return () => { cancelled = true; };
  }, [selectedIds]);

  const togglePersonSelection = (personId) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(personId)) next.delete(personId);
      else next.add(personId);
      return next;
    });
  };

  const clearSelection = () => {
    setSelectedIds(new Set());
    setSelectedPeople(new Map());
  };

  const refreshPerson = (personId) => {
    getAdminPerson(personId).then((person) => {
      setSelectedPeople((prev) => {
        const next = new Map(prev);
        next.set(personId, person);
        return next;
      });
    });
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

  const selectedCount = selectedIds.size;
  const multiSelected = selectedCount > 1;
  const selectedProfiles = Array.from(selectedIds)
    .map((id) => selectedPeople.get(id))
    .filter(Boolean);

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
      <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-5 gap-2 mb-4">
        <FieldInput label="Search name or email" value={search} onChange={updateSearch} />
        <label className="block text-xs font-medium">Role
          <select
            value={roleFilter}
            onChange={(e) => { setRoleFilter(e.target.value); resetPage(); }}
            className="mt-1 w-full rounded-md border border-gray-300 p-2 text-sm"
          >
            <option value="">Any</option>
            {ROLE_OPTIONS.map((r) => <option key={r} value={r}>{r}</option>)}
          </select>
        </label>
        <label className="block text-xs font-medium">Status
          <select
            value={statusFilter}
            onChange={(e) => { setStatusFilter(e.target.value); resetPage(); }}
            className="mt-1 w-full rounded-md border border-gray-300 p-2 text-sm"
          >
            <option value="active">Active</option>
            <option value="inactive">Inactive</option>
            <option value="">All</option>
          </select>
        </label>
        <label className="block text-xs font-medium">Last name starts with
          <select
            value={lastNameInitial}
            onChange={(e) => { setLastNameInitial(e.target.value); resetPage(); }}
            data-testid="last-name-initial-filter"
            className="mt-1 w-full rounded-md border border-gray-300 p-2 text-sm"
          >
            <option value="">Any letter</option>
            {LAST_NAME_INITIALS.map((letter) => (
              <option key={letter} value={letter}>{letter}</option>
            ))}
          </select>
        </label>
        <label className="block text-xs font-medium">Per page
          <select
            value={pageSize}
            onChange={(e) => { setPageSize(Number(e.target.value)); resetPage(); }}
            data-testid="people-page-size"
            className="mt-1 w-full rounded-md border border-gray-300 p-2 text-sm"
          >
            {PAGE_SIZE_OPTIONS.map((size) => (
              <option key={size} value={size}>{size}</option>
            ))}
          </select>
        </label>
      </div>
      {selectedCount > 0 && (
        <div
          data-testid="people-selection-toolbar"
          className="mb-4 flex flex-wrap items-center gap-3 rounded-md border border-indigo-200 bg-indigo-50 px-3 py-2 text-sm dark:border-indigo-800 dark:bg-indigo-900/20"
        >
          <span>{selectedCount} selected</span>
          <button
            type="button"
            data-testid="open-dedupe"
            disabled={selectedCount < 2}
            onClick={() => setDeduping(true)}
            className="px-3 py-1 rounded-md bg-red-600 text-white disabled:opacity-50"
          >
            Dedupe
          </button>
          <button
            type="button"
            data-testid="clear-people-selection"
            onClick={clearSelection}
            className="text-indigo-700 hover:underline dark:text-indigo-300"
          >
            Clear
          </button>
        </div>
      )}
      <div className={classNames('grid grid-cols-1 gap-4', multiSelected ? 'md:grid-cols-5' : 'md:grid-cols-2')}>
        <section data-testid="people-list" className={classNames('space-y-2', multiSelected && 'md:col-span-2')}>
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
                    'p-3 cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 flex items-start gap-3',
                    selectedIds.has(p.id) && 'bg-indigo-50 dark:bg-indigo-900/20',
                  )}
                  onClick={() => togglePersonSelection(p.id)}
                >
                  <input
                    type="checkbox"
                    checked={selectedIds.has(p.id)}
                    onChange={() => togglePersonSelection(p.id)}
                    onClick={(e) => e.stopPropagation()}
                    data-testid={`person-select-${p.id}`}
                    className="mt-1"
                    aria-label={`Select ${p.full_name}`}
                  />
                  <div className="min-w-0">
                    <Link
                      to={profileLink(p.id)}
                      onClick={(e) => e.stopPropagation()}
                      className="font-medium text-sm text-indigo-700 dark:text-indigo-300 hover:underline"
                    >
                      {p.full_name}
                    </Link>
                    <p className="text-xs text-gray-500">{p.email || 'no email'}</p>
                  </div>
                </li>
              ))}
            </ul>
          )}
          {!loading && !error && (
            <PeopleListPagination
              offset={offset}
              resultCount={people.length}
              totalCount={totalCount}
              loading={loading}
              onPrevious={() => setOffset((prev) => Math.max(0, prev - pageSize))}
              onNext={() => setOffset((prev) => prev + pageSize)}
            />
          )}
        </section>
        <aside
          data-testid="person-drawer"
          className={classNames(
            'rounded-md border bg-white dark:bg-gray-900 p-4',
            multiSelected && 'md:col-span-3',
          )}
        >
          {selectedCount === 0 ? (
            <p className="text-sm italic text-gray-500">Select a Person to view their profile.</p>
          ) : (
            <div className="max-h-[70vh] overflow-y-auto space-y-4">
              {selectedProfiles.map((person) => (
                <PersonProfilePanel
                  key={person.id}
                  person={person}
                  programs={programs}
                  invitedStatus={invitedStatus}
                  onInvite={handleInvite}
                  onDelete={setDeletingPerson}
                  onPersonChanged={() => refreshPerson(person.id)}
                  onDismiss={multiSelected ? (personId) => togglePersonSelection(personId) : null}
                />
              ))}
            </div>
          )}
        </aside>
      </div>
      {adding && (
        <AddPersonModal
          programs={programs}
          onClose={() => setAdding(false)}
          onCreated={(person) => {
            setAdding(false);
            reloadPeople();
            if (person?.id) setSelectedIds(new Set([person.id]));
          }}
        />
      )}
      {deduping && (
        <DedupePeopleModal
          selectedPeople={selectedPeople}
          onClose={() => setDeduping(false)}
          onCompleted={(result) => {
            setDeduping(false);
            reloadPeople();
            if (result?.winner_id) {
              setSelectedIds(new Set([result.winner_id]));
            } else {
              clearSelection();
            }
          }}
        />
      )}
      {deletingPerson && (
        <DeletePersonModal
          person={deletingPerson}
          onClose={() => setDeletingPerson(null)}
          onCompleted={(result) => {
            setDeletingPerson(null);
            reloadPeople();
            if (result?.person_id) {
              setSelectedIds((prev) => {
                const next = new Set(prev);
                next.delete(result.person_id);
                return next;
              });
              setSelectedPeople((prev) => {
                const next = new Map(prev);
                next.delete(result.person_id);
                return next;
              });
            }
          }}
        />
      )}
      {importing && (
        <BulkImportModal
          programs={programs}
          onClose={() => { setImporting(false); reloadPeople(); }}
        />
      )}
    </main>
  );
}
