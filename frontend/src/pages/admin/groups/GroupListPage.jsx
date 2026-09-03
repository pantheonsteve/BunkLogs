/**
 * Groups — the merged list that replaced Assignments.
 *
 * Assignments existed because the group list couldn't answer "who writes
 * logs here and who are they about". It can now: one request returns
 * subject and author counts plus this week's submissions, so the two
 * problems that stop a group from working — no author, no subjects — are
 * warnings on the row rather than a separate screen you have to know to
 * visit. The dashboard links here with `?warning=` to narrow to them.
 */
import { useCallback, useEffect, useMemo, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { AlertTriangle, Users } from 'lucide-react';

import api from '../../../api';
import { listAdminGroupsOverview } from '../../../api/admin';
import GroupBulkImportPanel from '../../../components/admin/GroupBulkImportPanel';
import Badge from '../../../components/ui/Badge';
import Button from '../../../components/ui/Button';
import DataTable from '../../../components/ui/DataTable';
import EmptyState from '../../../components/ui/EmptyState';
import ErrorPanel from '../../../components/ui/ErrorPanel';
import FilterBar, { FilterChips, FilterSelect, SearchInput } from '../../../components/ui/FilterBar';
import LoadingState from '../../../components/ui/LoadingState';
import Modal from '../../../components/ui/Modal';
import Note from '../../../components/ui/Note';
import ProgressBar from '../../../components/ui/ProgressBar';
import Toast, { useToast } from '../../../components/ui/Toast';
import PageHeader from '../../../components/ui/PageHeader';
import { useAdminProgram } from '../../../context/AdminProgramContext';
import { useTerm } from '../../../context/OrgBrandingContext';
import { canHaveParent, parentTypesFor } from '../../../lib/groupHierarchy';
import {
  GROUP_TYPE_LABELS,
  SUBJECT_BEARING_TYPES,
  developmentalSort,
  groupTypeLabel,
} from './groupTypes';

const STATUS_FILTERS = [
  { value: 'active', label: 'Active' },
  { value: 'inactive', label: 'Inactive' },
  { value: 'all', label: 'All' },
];

function formatApiError(data, fallback = 'Request failed.') {
  if (!data) return fallback;
  if (typeof data.detail === 'string') return data.detail;
  if (Array.isArray(data.non_field_errors) && data.non_field_errors.length) {
    return data.non_field_errors.join(' ');
  }
  const fieldMsgs = Object.entries(data)
    .filter(([, v]) => Array.isArray(v) && v.length)
    .map(([k, v]) => `${k}: ${v.join(', ')}`);
  return fieldMsgs.length ? fieldMsgs.join('; ') : fallback;
}

function warningsFor(group) {
  const out = [];
  if (group.author_count === 0) out.push('no_author');
  if (SUBJECT_BEARING_TYPES.has(group.group_type) && group.subject_count === 0) {
    out.push('no_subjects');
  }
  return out;
}

function CreateGroupModal({ programId, onClose, onCreated, showToast }) {
  const [draft, setDraft] = useState({ name: '', group_type: 'bunk', parent: '' });
  const [parentOptions, setParentOptions] = useState([]);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!programId || !canHaveParent(draft.group_type)) {
      setParentOptions([]);
      return undefined;
    }
    let cancelled = false;
    Promise.all(
      parentTypesFor(draft.group_type).map((groupType) => api.get('/api/v1/assignment-groups/', {
        params: { program: programId, group_type: groupType, is_active: 'true', page_size: 500 },
      })),
    )
      .then((responses) => {
        if (cancelled) return;
        const byId = new Map();
        for (const r of responses) {
          for (const g of (Array.isArray(r.data?.results) ? r.data.results : r.data || [])) {
            byId.set(g.id, g);
          }
        }
        setParentOptions([...byId.values()].sort((a, b) => a.name.localeCompare(b.name)));
      })
      .catch(() => { if (!cancelled) setParentOptions([]); });
    return () => { cancelled = true; };
  }, [programId, draft.group_type]);

  const submit = async (e) => {
    e?.preventDefault();
    setSaving(true);
    setError('');
    try {
      const payload = {
        name: draft.name.trim(),
        group_type: draft.group_type,
        program: Number(programId),
      };
      if (draft.parent) payload.parent = Number(draft.parent);
      const { data } = await api.post('/api/v1/assignment-groups/', payload);
      showToast(`Created "${data.name}"`);
      onCreated(data);
    } catch (err) {
      setError(formatApiError(err.response?.data, 'Create failed.'));
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal
      title="New group"
      onClose={onClose}
      dismissible={!saving}
      data-testid="create-group-modal"
      footer={(
        <>
          <Button variant="secondary" onClick={onClose} disabled={saving}>Cancel</Button>
          <div className="flex-1" />
          <Button
            onClick={submit}
            disabled={saving || !draft.name.trim() || !programId}
            data-testid="create-group-save"
          >
            {saving ? 'Creating…' : 'Create'}
          </Button>
        </>
      )}
    >
      <form onSubmit={submit} className="space-y-3">
        <label className="block text-xs font-medium text-gray-700 dark:text-gray-300">
          Name
          <input
            value={draft.name}
            onChange={(e) => setDraft({ ...draft, name: e.target.value })}
            placeholder="e.g. Bunk Aleph"
            data-testid="create-group-name"
            className="mt-1 w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm"
          />
        </label>
        <label className="block text-xs font-medium text-gray-700 dark:text-gray-300">
          Type
          <select
            value={draft.group_type}
            onChange={(e) => setDraft({ ...draft, group_type: e.target.value, parent: '' })}
            data-testid="create-group-type"
            className="mt-1 w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm"
          >
            {Object.entries(GROUP_TYPE_LABELS).map(([v, l]) => (
              <option key={v} value={v}>{l}</option>
            ))}
          </select>
        </label>
        {canHaveParent(draft.group_type) && (
          <label className="block text-xs font-medium text-gray-700 dark:text-gray-300">
            Part of
            <select
              value={draft.parent}
              onChange={(e) => setDraft({ ...draft, parent: e.target.value })}
              data-testid="create-group-parent"
              className="mt-1 w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm"
            >
              <option value="">Nothing</option>
              {parentOptions.map((g) => (
                <option key={g.id} value={String(g.id)}>
                  {g.name} ({groupTypeLabel(g.group_type)})
                </option>
              ))}
            </select>
          </label>
        )}
        {!programId && (
          <Note tone="warn">Pick a program in the header before creating a group.</Note>
        )}
        {error && <Note tone="danger">{error}</Note>}
      </form>
    </Modal>
  );
}

export default function GroupListPage() {
  const navigate = useNavigate();
  const term = useTerm();
  const [searchParams, setSearchParams] = useSearchParams();
  const {
    programId,
    program: selectedProgram,
    ready: programsReady,
  } = useAdminProgram();

  const [groups, setGroups] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [typeFilter, setTypeFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('active');
  const [search, setSearch] = useState('');
  const [creating, setCreating] = useState(false);
  const [showImport, setShowImport] = useState(false);
  const { toast, showToast } = useToast(3000);

  const warningFilter = searchParams.get('warning') || '';
  const setWarningFilter = (value) => {
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev);
      if (value) next.set('warning', value);
      else next.delete('warning');
      return next;
    });
  };

  const groupsLo = term('group', { plural: true });
  const groupsCap = term('group', { plural: true, capitalize: true });
  const authorsLo = term('counselor', { plural: true });
  const subjectsLo = term('camper', { plural: true });

  const load = useCallback(async () => {
    if (!programsReady) return;
    setLoading(true);
    setError('');
    try {
      const data = await listAdminGroupsOverview({
        program: programId || undefined,
        group_type: typeFilter || undefined,
        include_inactive: statusFilter === 'active' ? undefined : 'true',
      });
      setGroups(data.results || []);
    } catch (err) {
      setError(formatApiError(err.response?.data, `Failed to load ${groupsLo}.`));
    } finally {
      setLoading(false);
    }
  }, [programId, typeFilter, statusFilter, programsReady, groupsLo]);

  useEffect(() => { load(); }, [load]);

  const rows = useMemo(() => {
    const q = search.trim().toLowerCase();
    const filtered = groups.filter((g) => {
      if (statusFilter === 'active' && !g.is_active) return false;
      if (statusFilter === 'inactive' && g.is_active) return false;
      if (warningFilter && !warningsFor(g).includes(warningFilter)) return false;
      if (q && !`${g.name} ${g.parent_name || ''}`.toLowerCase().includes(q)) return false;
      return true;
    });
    return developmentalSort(filtered);
  }, [groups, search, statusFilter, warningFilter]);

  const needsAuthor = groups.filter((g) => warningsFor(g).includes('no_author')).length;
  const needsSubjects = groups.filter((g) => warningsFor(g).includes('no_subjects')).length;

  const columns = [
    {
      key: 'name',
      header: 'Name',
      render: (g) => (
        <div className="min-w-0">
          <p className="font-semibold text-gray-900 dark:text-white">{g.name}</p>
          <p className="text-xs text-gray-500 dark:text-gray-400">
            {groupTypeLabel(g.group_type)}
            {g.parent_name ? ` · part of ${g.parent_name}` : ''}
          </p>
        </div>
      ),
    },
    {
      key: 'people',
      header: 'People',
      render: (g) => {
        const warnings = warningsFor(g);
        if (warnings.length === 0) {
          return (
            <span className="text-xs text-gray-600 dark:text-gray-400 tabular-nums">
              {g.subject_count} {subjectsLo} · {g.author_count} {authorsLo}
            </span>
          );
        }
        return (
          <div className="flex flex-wrap gap-1.5">
            {warnings.includes('no_author') && (
              <Badge tone="warn" dot data-testid={`group-warning-no-author-${g.id}`}>
                No {term('counselor')} yet
              </Badge>
            )}
            {warnings.includes('no_subjects') && (
              <Badge tone="warn" dot data-testid={`group-warning-no-subjects-${g.id}`}>
                No {subjectsLo}
              </Badge>
            )}
            {!warnings.includes('no_author') && (
              <span className="text-xs text-gray-500 tabular-nums">
                {g.author_count} {authorsLo}
              </span>
            )}
          </div>
        );
      },
    },
    {
      key: 'week',
      header: 'Logs this week',
      width: '11rem',
      render: (g) => (
        g.expected === 0
          ? <span className="text-xs text-gray-400">—</span>
          : (
            <div className="flex items-center gap-2">
              <ProgressBar value={g.submitted} total={g.expected} className="flex-1" />
              <span className="text-xs text-gray-500 tabular-nums w-10 text-right">
                {g.submitted}/{g.expected}
              </span>
            </div>
          )
      ),
    },
    {
      key: 'status',
      header: 'Status',
      align: 'right',
      render: (g) => (
        <Badge tone={g.is_active ? 'ok' : 'neutral'} dot>
          {g.is_active ? 'Active' : 'Archived'}
        </Badge>
      ),
    },
  ];

  return (
    <main
      className="grow px-4 sm:px-6 lg:px-8 py-6 w-full max-w-[1180px] mx-auto"
      data-testid="admin-groups"
    >
      <PageHeader
        title={groupsCap}
        subtitle={
          selectedProgram
            ? `Who is in each ${term('group')} and who writes their logs — ${selectedProgram.name}`
            : `Who is in each ${term('group')} and who writes their logs`
        }
        backTo="/admin/home"
        actions={(
          <>
            <Button
              variant="secondary"
              disabled={!programId}
              onClick={() => setShowImport((v) => !v)}
              data-testid="group-list-import-toggle"
            >
              {showImport ? 'Close import' : 'Import CSV'}
            </Button>
            <Button
              onClick={() => setCreating(true)}
              disabled={!programId}
              data-testid="group-list-add"
            >
              New {term('group')}
            </Button>
          </>
        )}
      />

      {showImport && programId && selectedProgram && (
        <div className="mb-5">
          <GroupBulkImportPanel
            programId={programId}
            programName={selectedProgram.name}
            onDone={load}
            showToast={showToast}
          />
        </div>
      )}

      {!loading && !warningFilter && (needsAuthor > 0 || needsSubjects > 0) && (
        <div className="mb-4">
          <Note tone="warn" data-testid="group-list-attention">
            <div className="flex flex-wrap items-center gap-3">
              <AlertTriangle size={15} aria-hidden="true" className="shrink-0" />
              <span>
                {needsAuthor > 0 && `${needsAuthor} without ${authorsLo}`}
                {needsAuthor > 0 && needsSubjects > 0 && ' · '}
                {needsSubjects > 0 && `${needsSubjects} without ${subjectsLo}`}
              </span>
              {needsAuthor > 0 && (
                <button
                  type="button"
                  onClick={() => setWarningFilter('no_author')}
                  data-testid="group-filter-no-author"
                  className="text-sm font-semibold underline"
                >
                  Show the ones with no {term('counselor')}
                </button>
              )}
              {needsSubjects > 0 && (
                <button
                  type="button"
                  onClick={() => setWarningFilter('no_subjects')}
                  data-testid="group-filter-no-subjects"
                  className="text-sm font-semibold underline"
                >
                  Show the ones with no {subjectsLo}
                </button>
              )}
            </div>
          </Note>
        </div>
      )}

      <FilterBar>
        <SearchInput
          value={search}
          onChange={setSearch}
          placeholder={`Search ${groupsLo}…`}
          data-testid="group-search"
        />
        <FilterChips
          value={statusFilter}
          onChange={setStatusFilter}
          options={STATUS_FILTERS}
          testIdPrefix="group-status-"
        />
        <FilterSelect
          value={typeFilter}
          onChange={setTypeFilter}
          data-testid="group-type-filter"
          options={[
            { value: '', label: 'All types' },
            ...Object.entries(GROUP_TYPE_LABELS).map(([v, l]) => ({ value: v, label: l })),
          ]}
        />
        {warningFilter && (
          <button
            type="button"
            onClick={() => setWarningFilter('')}
            data-testid="group-clear-warning-filter"
            className="text-sm font-medium text-indigo-700 dark:text-indigo-300 hover:underline"
          >
            Clear “{warningFilter === 'no_author' ? `no ${authorsLo}` : `no ${subjectsLo}`}” filter
          </button>
        )}
      </FilterBar>

      {error && <div className="mb-4"><ErrorPanel>{error}</ErrorPanel></div>}

      {loading ? (
        <LoadingState>Loading {groupsLo}…</LoadingState>
      ) : (
        <DataTable
          columns={columns}
          rows={rows}
          rowTestId={(g) => `group-list-row-${g.id}`}
          onRowClick={(g) => navigate(`/admin/groups/${g.id}`)}
          empty={(
            <EmptyState icon={Users} title={`No ${groupsLo} match those filters`}>
              {programId
                ? <>Create one with the button above.</>
                : <>Pick a program in the header first.</>}
            </EmptyState>
          )}
          data-testid="group-list"
        />
      )}

      {creating && (
        <CreateGroupModal
          programId={programId}
          showToast={showToast}
          onClose={() => setCreating(false)}
          onCreated={(created) => {
            setCreating(false);
            navigate(`/admin/groups/${created.id}`);
          }}
        />
      )}

      <Toast message={toast} />
    </main>
  );
}
