import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  listAdminPeople,
  buildAdminPeopleListParams,
  getAdminPerson,
  createAdminPerson,
  inviteAdminPerson,
  listAdminPrograms,
} from '../../api/admin';
import BulkImportModal from '../../components/admin/BulkImportModal';
import DedupePeopleModal from '../../components/admin/DedupePeopleModal';
import DeletePersonModal from '../../components/admin/DeletePersonModal';
import PersonProfilePanel, {
  FieldInput,
  MEMBERSHIP_ROLE_OPTIONS,
  PeopleListPagination,
} from '../../components/admin/PersonProfilePanel';
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
const ROLE_OPTIONS = MEMBERSHIP_ROLE_OPTIONS;

const PAGE_SIZE_OPTIONS = [25, 50, 100];
const LAST_NAME_INITIALS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'.split('');

function classNames(...args) {
  return args.filter(Boolean).join(' ');
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
