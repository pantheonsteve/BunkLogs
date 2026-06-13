import { useState } from 'react';
import { Link } from 'react-router-dom';
import {
  patchAdminPerson,
  addAdminMembership,
  deactivateAdminMembership,
} from '../../api/admin';
import { profileLink } from '../../utils/dashboardLinks';

export const MEMBERSHIP_ROLE_OPTIONS = [
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
          {MEMBERSHIP_ROLE_OPTIONS.map((r) => (
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

export function FieldInput({ label, value, onChange, type = 'text' }) {
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

export function PeopleListPagination({
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

export default function PersonProfilePanel({
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
