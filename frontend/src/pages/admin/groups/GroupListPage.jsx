import { useEffect, useState, useCallback } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { Users, ArrowLeft, ChevronRight } from 'lucide-react';
import api from '../../../api';
import { listAdminPrograms } from '../../../api/admin';
import {
  readStoredProgramId,
  resolveInitialProgramId,
  writeStoredProgramId,
} from '../../../lib/adminProgramContext';
import Button from '../../../components/ui/Button';
import EmptyState from '../../../components/ui/EmptyState';
import ErrorPanel from '../../../components/ui/ErrorPanel';
import LoadingState from '../../../components/ui/LoadingState';
import GroupDisplayName from '../../../components/GroupDisplayName';
import Toast, { useToast } from '../../../components/ui/Toast';
import { canHaveParent, parentTypesFor } from '../../../lib/groupHierarchy';

const GROUP_TYPE_LABELS = {
  bunk: 'Bunk',
  classroom: 'Classroom',
  caseload: 'Caseload',
  unit: 'Unit',
  division: 'Division',
  cohort: 'Cohort',
  team: 'Team',
  specialty: 'Specialty / Activity',
  custom: 'Custom',
};

const GROUP_TYPE_ORDER = ['division', 'unit', 'bunk', 'classroom', 'caseload', 'cohort', 'team', 'specialty', 'custom'];

function groupByType(groups) {
  const map = {};
  for (const g of groups) {
    const t = g.group_type;
    if (!map[t]) map[t] = [];
    map[t].push(g);
  }
  return map;
}

function Badge({ active }) {
  return active ? (
    <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-400">
      Active
    </span>
  ) : (
    <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-500 dark:bg-gray-800 dark:text-gray-400">
      Inactive
    </span>
  );
}

function ProgramSelect({ programs, value, onChange, id, className = '', allowAll = true, required = false }) {
  return (
    <select
      id={id}
      value={value}
      required={required}
      onChange={(e) => onChange(e.target.value)}
      className={className || 'border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-1.5 text-sm bg-white dark:bg-gray-800 text-gray-900 dark:text-white'}
      data-testid={id}
    >
      {allowAll && <option value="">All programs</option>}
      {programs.map((p) => (
        <option key={p.id} value={String(p.id)}>
          {p.name}{p.is_active ? '' : ' (Ended)'}
        </option>
      ))}
    </select>
  );
}

export default function GroupListPage() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const [groups, setGroups] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [typeFilter, setTypeFilter] = useState('');
  const [activeFilter, setActiveFilter] = useState('active');
  const [programFilter, setProgramFilter] = useState('');
  const [programs, setPrograms] = useState([]);
  const [programsReady, setProgramsReady] = useState(false);
  const { toast, showToast } = useToast(3000);
  const [creating, setCreating] = useState(false);
  const [newGroup, setNewGroup] = useState({ name: '', group_type: 'bunk', program: '', parent: '' });
  const [parentFilter, setParentFilter] = useState('');
  const [parentOptions, setParentOptions] = useState([]);
  const [createParentOptions, setCreateParentOptions] = useState([]);

  const syncProgramContext = useCallback((programId) => {
    writeStoredProgramId(programId);
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev);
      if (programId) next.set('program', String(programId));
      else next.delete('program');
      return next;
    }, { replace: true });
  }, [setSearchParams]);

  const handleProgramFilterChange = useCallback((programId) => {
    setProgramFilter(programId);
    setNewGroup((g) => ({ ...g, program: programId }));
    syncProgramContext(programId);
  }, [syncProgramContext]);

  useEffect(() => {
    let cancelled = false;
    listAdminPrograms()
      .then((data) => {
        if (cancelled) return;
        const list = data.results || [];
        setPrograms(list);
        const initial = resolveInitialProgramId({
          urlProgramId: searchParams.get('program'),
          storedProgramId: readStoredProgramId(),
          programs: list,
        });
        if (initial) {
          setProgramFilter(initial);
          setNewGroup((g) => ({ ...g, program: initial }));
          if (!searchParams.get('program')) {
            syncProgramContext(initial);
          } else {
            writeStoredProgramId(initial);
          }
        }
        setProgramsReady(true);
      })
      .catch(() => {
        if (!cancelled) setProgramsReady(true);
      });
    return () => { cancelled = true; };
    // eslint-disable-next-line react-hooks/exhaustive-deps -- init once on mount
  }, []);

  const loadParentOptions = useCallback(async (programId, childType = null) => {
    if (!programId) return [];
    const types = childType ? parentTypesFor(childType) : ['division', 'unit'];
    if (!types.length) return [];
    const responses = await Promise.all(
      types.map((groupType) => api.get('/api/v1/assignment-groups/', {
        params: {
          program: programId,
          group_type: groupType,
          is_active: 'true',
          page_size: 500,
        },
      })),
    );
    const merged = responses.flatMap((r) => {
      const data = r.data;
      return Array.isArray(data?.results) ? data.results : Array.isArray(data) ? data : [];
    });
    return merged.sort((a, b) => a.name.localeCompare(b.name));
  }, []);

  useEffect(() => {
    if (!programFilter) {
      setParentOptions([]);
      return;
    }
    let cancelled = false;
    loadParentOptions(programFilter)
      .then((list) => { if (!cancelled) setParentOptions(list); })
      .catch(() => { if (!cancelled) setParentOptions([]); });
    return () => { cancelled = true; };
  }, [programFilter, loadParentOptions]);

  useEffect(() => {
    if (!creating || !newGroup.program || !canHaveParent(newGroup.group_type)) {
      setCreateParentOptions([]);
      return;
    }
    let cancelled = false;
    loadParentOptions(newGroup.program, newGroup.group_type)
      .then((list) => { if (!cancelled) setCreateParentOptions(list); })
      .catch(() => { if (!cancelled) setCreateParentOptions([]); });
    return () => { cancelled = true; };
  }, [creating, newGroup.program, newGroup.group_type, loadParentOptions]);

  const load = useCallback(async () => {
    if (!programsReady) return;
    setLoading(true);
    setError('');
    try {
      const params = {};
      if (typeFilter) params.group_type = typeFilter;
      if (programFilter) params.program = programFilter;
      if (parentFilter) {
        params.parent = parentFilter;
        params.include_descendants = 'true';
      }
      if (activeFilter === 'active') params.is_active = 'true';
      else if (activeFilter === 'inactive') params.is_active = 'false';
      const { data } = await api.get('/api/v1/assignment-groups/', { params });
      const results = Array.isArray(data?.results) ? data.results : Array.isArray(data) ? data : [];
      setGroups(results);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load groups.');
    } finally {
      setLoading(false);
    }
  }, [typeFilter, programFilter, parentFilter, activeFilter, programsReady]);

  useEffect(() => {
    load();
  }, [load]);

  const formatApiError = (data) => {
    if (!data) return 'Create failed.';
    if (typeof data.detail === 'string') return data.detail;
    if (Array.isArray(data.non_field_errors) && data.non_field_errors.length) {
      return data.non_field_errors.join(' ');
    }
    const fieldMsgs = Object.entries(data)
      .filter(([, v]) => Array.isArray(v) && v.length)
      .map(([k, v]) => `${k}: ${v.join(', ')}`);
    if (fieldMsgs.length) return fieldMsgs.join('; ');
    return 'Create failed.';
  };

  const handleCreate = async (e) => {
    e.preventDefault();
    try {
      const payload = {
        name: newGroup.name.trim(),
        group_type: newGroup.group_type,
        program: Number(newGroup.program),
      };
      if (newGroup.parent) payload.parent = Number(newGroup.parent);
      const { data } = await api.post('/api/v1/assignment-groups/', payload);
      showToast(`Created group "${data.name}"`);
      setCreating(false);
      setNewGroup({
        name: '',
        group_type: 'bunk',
        program: programFilter || '',
        parent: '',
      });
      navigate(`/admin/groups/${data.id}`);
    } catch (err) {
      showToast(formatApiError(err.response?.data));
    }
  };

  const byType = groupByType(groups);
  const typesPresent = GROUP_TYPE_ORDER.filter((t) => byType[t]?.length > 0);

  return (
    <main className="grow px-4 sm:px-6 lg:px-8 py-6 w-full max-w-screen-2xl mx-auto" data-testid="admin-groups">
      <Link
        to="/admin/home"
        className="inline-flex items-center gap-1 text-sm text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 mb-4"
      >
        <ArrowLeft size={14} /> Admin
      </Link>

        <div className="mb-6">
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Groups</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            Manage bunks, teams, classrooms, caseloads, and other assignment groups
          </p>
        </div>

        <div className="flex flex-wrap gap-1.5 mb-5" data-testid="group-list-actions">
          <Button
            onClick={() => {
              setCreating(true);
              if (programFilter) {
                setNewGroup((g) => ({ ...g, program: programFilter }));
              }
            }}
            data-testid="group-list-add"
          >
            Add Group
          </Button>
        </div>

        {/* Create form */}
        {creating && (
          <div className="mb-6 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-xl p-5">
            <h2 className="text-sm font-semibold text-gray-900 dark:text-white mb-4">Create new group</h2>
            <form onSubmit={handleCreate} className="flex flex-wrap gap-3 items-end">
              <div>
                <label className="block text-xs text-gray-500 dark:text-gray-400 mb-1">Name</label>
                <input
                  type="text"
                  required
                  value={newGroup.name}
                  onChange={(e) => setNewGroup((g) => ({ ...g, name: e.target.value }))}
                  className="border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-1.5 text-sm bg-white dark:bg-gray-800 text-gray-900 dark:text-white w-48"
                  placeholder="e.g. Bunk Aleph"
                />
              </div>
              <div>
                <label className="block text-xs text-gray-500 dark:text-gray-400 mb-1">Type</label>
                <select
                  value={newGroup.group_type}
                  onChange={(e) => setNewGroup((g) => ({
                    ...g,
                    group_type: e.target.value,
                    parent: '',
                  }))}
                  className="border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-1.5 text-sm bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
                >
                  {Object.entries(GROUP_TYPE_LABELS).map(([v, l]) => (
                    <option key={v} value={v}>{l}</option>
                  ))}
                </select>
              </div>
              <div>
                <label htmlFor="create-group-program" className="block text-xs text-gray-500 dark:text-gray-400 mb-1">Program</label>
                <ProgramSelect
                  id="create-group-program"
                  programs={programs}
                  value={newGroup.program}
                  onChange={(v) => setNewGroup((g) => ({ ...g, program: v }))}
                  allowAll={false}
                  required
                  className="border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-1.5 text-sm bg-white dark:bg-gray-800 text-gray-900 dark:text-white min-w-[12rem]"
                />
              </div>
              {canHaveParent(newGroup.group_type) && (
                <div>
                  <label htmlFor="create-group-parent" className="block text-xs text-gray-500 dark:text-gray-400 mb-1">Parent group</label>
                  <select
                    id="create-group-parent"
                    value={newGroup.parent}
                    onChange={(e) => setNewGroup((g) => ({ ...g, parent: e.target.value }))}
                    className="border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-1.5 text-sm bg-white dark:bg-gray-800 text-gray-900 dark:text-white min-w-[12rem]"
                    data-testid="create-group-parent"
                  >
                    <option value="">None</option>
                    {createParentOptions.map((g) => (
                      <option key={g.id} value={String(g.id)}>
                        {g.name} ({GROUP_TYPE_LABELS[g.group_type] || g.group_type})
                      </option>
                    ))}
                  </select>
                </div>
              )}
              <Button type="submit" size="sm" disabled={!newGroup.program}>
                Create
              </Button>
              <Button variant="secondary" size="sm" onClick={() => setCreating(false)}>
                Cancel
              </Button>
            </form>
          </div>
        )}

        {/* Filters */}
        <div className="flex flex-wrap gap-2 mb-5 items-center">
          <div className="flex gap-1">
            {['active', 'inactive', 'all'].map((v) => (
              <button
                key={v}
                type="button"
                onClick={() => setActiveFilter(v)}
                className={`px-3 py-1 rounded-full text-xs font-medium transition-colors ${
                  activeFilter === v
                    ? 'bg-blue-600 text-white'
                    : 'bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700'
                }`}
              >
                {v.charAt(0).toUpperCase() + v.slice(1)}
              </button>
            ))}
          </div>
          <select
            value={typeFilter}
            onChange={(e) => setTypeFilter(e.target.value)}
            className="px-3 py-1 rounded-full text-xs border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300"
            aria-label="Filter by type"
          >
            <option value="">All types</option>
            {Object.entries(GROUP_TYPE_LABELS).map(([v, l]) => (
              <option key={v} value={v}>{l}</option>
            ))}
          </select>
          <ProgramSelect
            id="group-list-program-filter"
            programs={programs}
            value={programFilter}
            onChange={(v) => {
              handleProgramFilterChange(v);
              setParentFilter('');
            }}
            className="px-3 py-1 rounded-full text-xs border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300"
          />
          {programFilter && parentOptions.length > 0 && (
            <select
              value={parentFilter}
              onChange={(e) => setParentFilter(e.target.value)}
              className="px-3 py-1 rounded-full text-xs border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 max-w-[14rem]"
              aria-label="Filter by parent group"
              data-testid="group-list-parent-filter"
            >
              <option value="">All parents</option>
              {parentOptions.map((g) => (
                <option key={g.id} value={String(g.id)}>
                  Under: {g.name}
                </option>
              ))}
            </select>
          )}
        </div>

        {error && (
          <div className="mb-4">
            <ErrorPanel>{error}</ErrorPanel>
          </div>
        )}

        {loading ? (
          <LoadingState>Loading groups…</LoadingState>
        ) : groups.length === 0 ? (
          <EmptyState
            icon={Users}
            title="No groups found"
          >
            Create one to get started.
          </EmptyState>
        ) : (
          <div className="space-y-8">
            {typesPresent.map((type) => (
              <section key={type}>
                <h2 className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-2">
                  {GROUP_TYPE_LABELS[type] || type} ({byType[type].length})
                </h2>
                <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-700 divide-y divide-gray-100 dark:divide-gray-800">
                  {byType[type].map((g) => (
                    <Link
                      key={g.id}
                      to={`/admin/groups/${g.id}`}
                      data-testid={`group-list-row-${g.id}`}
                      className="flex items-center justify-between px-4 py-3 hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors group"
                    >
                      <GroupDisplayName
                        group={{
                          name: g.name,
                          program_name: g.program_name,
                          parent_name: g.parent_name,
                        }}
                        nameClassName="text-sm font-medium text-gray-900 dark:text-white group-hover:text-blue-600 dark:group-hover:text-blue-400"
                        subtitleClassName="text-xs text-gray-400 dark:text-gray-500 mt-0.5"
                      />
                      <div className="flex items-center gap-3">
                        <Badge active={g.is_active} />
                        <ChevronRight size={14} className="text-gray-400" />
                      </div>
                    </Link>
                  ))}
                </div>
              </section>
            ))}
          </div>
        )}

      <Toast message={toast} />
    </main>
  );
}
