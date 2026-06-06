import { useEffect, useState, useCallback } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Plus, Users, ArrowLeft, ChevronRight } from 'lucide-react';
import api from '../../../api';
import Button from '../../../components/ui/Button';
import EmptyState from '../../../components/ui/EmptyState';
import ErrorPanel from '../../../components/ui/ErrorPanel';
import LoadingState from '../../../components/ui/LoadingState';
import Toast, { useToast } from '../../../components/ui/Toast';

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

export default function GroupListPage() {
  const navigate = useNavigate();
  const [groups, setGroups] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [typeFilter, setTypeFilter] = useState('');
  const [activeFilter, setActiveFilter] = useState('active');
  const [programFilter, setProgramFilter] = useState('');
  const { toast, showToast } = useToast(3000);
  const [creating, setCreating] = useState(false);
  const [newGroup, setNewGroup] = useState({ name: '', group_type: 'bunk', program: '' });
  const [programs, setPrograms] = useState([]);

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const params = {};
      if (typeFilter) params.group_type = typeFilter;
      if (programFilter) params.program = programFilter;
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
  }, [typeFilter, programFilter, activeFilter]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    api.get('/api/v1/memberships/', { params: { page_size: 1 } })
      .then(() => {})
      .catch(() => {});
    // Load programs for the create form
    api.get('/api/v1/memberships/', { params: { page_size: 1 } }).catch(() => {});
  }, []);

  const handleCreate = async (e) => {
    e.preventDefault();
    try {
      const slug = newGroup.name.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)/g, '');
      const payload = { ...newGroup, slug };
      const { data } = await api.post('/api/v1/assignment-groups/', payload);
      showToast(`Created group "${data.name}"`);
      setCreating(false);
      setNewGroup({ name: '', group_type: 'bunk', program: '' });
      navigate(`/admin/groups/${data.id}`);
    } catch (err) {
      const detail = err.response?.data?.detail || JSON.stringify(err.response?.data) || 'Create failed.';
      showToast(detail);
    }
  };

  const byType = groupByType(groups);
  const typesPresent = GROUP_TYPE_ORDER.filter((t) => byType[t]?.length > 0);

  return (
    <main className="grow px-4 sm:px-6 lg:px-8 py-6 w-full max-w-5xl mx-auto">
      <Link
        to="/admin/home"
        className="inline-flex items-center gap-1 text-sm text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 mb-4"
      >
        <ArrowLeft size={14} /> Admin
      </Link>

        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-xl font-bold text-gray-900 dark:text-white">Groups</h1>
            <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
              Manage bunks, teams, classrooms, caseloads, and other assignment groups
            </p>
          </div>
          <Button onClick={() => setCreating(true)}>
            <Plus size={16} /> New group
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
                  onChange={(e) => setNewGroup((g) => ({ ...g, group_type: e.target.value }))}
                  className="border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-1.5 text-sm bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
                >
                  {Object.entries(GROUP_TYPE_LABELS).map(([v, l]) => (
                    <option key={v} value={v}>{l}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-xs text-gray-500 dark:text-gray-400 mb-1">Program ID</label>
                <input
                  type="number"
                  required
                  value={newGroup.program}
                  onChange={(e) => setNewGroup((g) => ({ ...g, program: e.target.value }))}
                  className="border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-1.5 text-sm bg-white dark:bg-gray-800 text-gray-900 dark:text-white w-28"
                  placeholder="Program ID"
                />
              </div>
              <Button type="submit" size="sm">
                Create
              </Button>
              <Button variant="secondary" size="sm" onClick={() => setCreating(false)}>
                Cancel
              </Button>
            </form>
          </div>
        )}

        {/* Filters */}
        <div className="flex flex-wrap gap-2 mb-5">
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
                      className="flex items-center justify-between px-4 py-3 hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors group"
                    >
                      <div>
                        <span className="text-sm font-medium text-gray-900 dark:text-white group-hover:text-blue-600 dark:group-hover:text-blue-400">
                          {g.name}
                        </span>
                        {g.parent && (
                          <span className="ml-2 text-xs text-gray-400 dark:text-gray-500">
                            parent: {g.parent}
                          </span>
                        )}
                      </div>
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
