import { useEffect, useState, useCallback } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Plus, Copy, ChevronUp, ChevronDown, ArrowLeft } from 'lucide-react';
import api from '../../../api';

const STATUS_BADGE = {
  draft: 'Draft',
  published: 'Published',
  archived: 'Archived',
};

function statusInfo(tpl) {
  if (!tpl.is_active) return { label: 'Archived', cls: 'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400' };
  return { label: `Published v${tpl.version}`, cls: 'bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-400' };
}

function SortableHeader({ label, field, sort, setSort }) {
  const active = sort.field === field;
  return (
    <th
      className="px-3 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide cursor-pointer hover:text-gray-900 dark:hover:text-gray-100 select-none"
      onClick={() => setSort({ field, dir: active && sort.dir === 'asc' ? 'desc' : 'asc' })}
    >
      <span className="flex items-center gap-1">
        {label}
        {active ? (sort.dir === 'asc' ? <ChevronUp size={12} /> : <ChevronDown size={12} />) : null}
      </span>
    </th>
  );
}

const ROLE_OPTIONS = [
  '', 'counselor', 'junior_counselor', 'specialist', 'general_counselor',
  'unit_head', 'leadership_team', 'kitchen_staff', 'maintenance',
  'housekeeping', 'camper_care', 'health_center', 'madrich', 'faculty', 'admin',
];

export default function TemplateListPage() {
  const navigate = useNavigate();
  const [templates, setTemplates] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [roleFilter, setRoleFilter] = useState('');
  const [scopeFilter, setScopeFilter] = useState('all'); // 'all' | 'mine' | 'global'
  const [sort, setSort] = useState({ field: 'name', dir: 'asc' });
  const [cloning, setCloning] = useState(null);
  const [toast, setToast] = useState('');

  const showToast = (msg) => {
    setToast(msg);
    setTimeout(() => setToast(''), 3000);
  };

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const params = {};
      if (roleFilter) params.role = roleFilter;
      const { data } = await api.get('/api/v1/templates/', { params });
      const results = Array.isArray(data?.results) ? data.results : Array.isArray(data) ? data : [];
      setTemplates(results);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load templates.');
    } finally {
      setLoading(false);
    }
  }, [roleFilter]);

  useEffect(() => {
    load();
  }, [load]);

  const filteredAndSorted = templates
    .filter((t) => {
      if (scopeFilter === 'global') return t.organization === null || t.organization === undefined;
      if (scopeFilter === 'mine') return t.organization !== null && t.organization !== undefined;
      return true;
    })
    .sort((a, b) => {
      const dir = sort.dir === 'asc' ? 1 : -1;
      if (sort.field === 'name') return dir * a.name.localeCompare(b.name);
      if (sort.field === 'version') return dir * (a.version - b.version);
      if (sort.field === 'role') return dir * (a.role || '').localeCompare(b.role || '');
      if (sort.field === 'created_at') return dir * a.created_at.localeCompare(b.created_at);
      return 0;
    });

  const handleClone = async (tpl) => {
    setCloning(tpl.id);
    try {
      const { data } = await api.post(`/api/v1/templates/${tpl.id}/clone/`);
      showToast(`Cloned as "${data.name}" (v${data.version})`);
      load();
    } catch (err) {
      showToast(err.response?.data?.detail || 'Clone failed.');
    } finally {
      setCloning(null);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-950 px-4 py-6">
      <div className="max-w-6xl mx-auto">
        {/* Breadcrumb */}
        <Link
          to="/admin"
          className="inline-flex items-center gap-1 text-sm text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 mb-4"
        >
          <ArrowLeft size={14} /> Admin
        </Link>

        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-xl font-bold text-gray-900 dark:text-white">Reflection Templates</h1>
            <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
              Manage templates used across programs
            </p>
          </div>
          <Link
            to="/admin/templates/new"
            className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition-colors"
            data-testid="new-template-btn"
          >
            <Plus size={16} /> New template
          </Link>
        </div>

        {/* Filters */}
        <div className="flex flex-wrap gap-2 mb-4">
          {['all', 'mine', 'global'].map((v) => (
            <button
              key={v}
              type="button"
              onClick={() => setScopeFilter(v)}
              className={`px-3 py-1 rounded-full text-sm font-medium transition-colors ${
                scopeFilter === v
                  ? 'bg-blue-600 text-white'
                  : 'bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700'
              }`}
            >
              {v === 'all' ? 'All' : v === 'mine' ? 'Mine' : 'Global'}
            </button>
          ))}
          <select
            className="px-3 py-1 rounded-full text-sm border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300"
            value={roleFilter}
            onChange={(e) => setRoleFilter(e.target.value)}
            aria-label="Filter by role"
          >
            <option value="">All roles</option>
            {ROLE_OPTIONS.filter(Boolean).map((r) => (
              <option key={r} value={r}>{r.replace(/_/g, ' ')}</option>
            ))}
          </select>
        </div>

        {error && (
          <div className="rounded-lg bg-red-50 dark:bg-red-950/30 border border-red-200 dark:border-red-800 px-4 py-3 text-sm text-red-700 dark:text-red-300 mb-4">
            {error}
          </div>
        )}

        {loading ? (
          <div className="text-center py-12 text-gray-500 dark:text-gray-400 text-sm">Loading…</div>
        ) : filteredAndSorted.length === 0 ? (
          <div className="text-center py-16 text-gray-500 dark:text-gray-400">
            <p className="text-base mb-4">No templates found.</p>
            <Link
              to="/admin/templates/new"
              className="text-blue-600 dark:text-blue-400 underline text-sm"
            >
              Create your first template
            </Link>
          </div>
        ) : (
          <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
            <table className="w-full text-sm" data-testid="template-table">
              <thead className="bg-gray-50 dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
                <tr>
                  <SortableHeader label="Name" field="name" sort={sort} setSort={setSort} />
                  <SortableHeader label="Role" field="role" sort={sort} setSort={setSort} />
                  <SortableHeader label="Version" field="version" sort={sort} setSort={setSort} />
                  <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide">Status</th>
                  <SortableHeader label="Created" field="created_at" sort={sort} setSort={setSort} />
                  <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 dark:divide-gray-800">
                {filteredAndSorted.map((tpl) => {
                  const { label, cls } = statusInfo(tpl);
                  const isGlobal = tpl.organization === null || tpl.organization === undefined;
                  return (
                    <tr key={tpl.id} className="hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors">
                      <td className="px-3 py-3">
                        <Link
                          to={`/admin/templates/${tpl.id}/edit`}
                          className="font-medium text-gray-900 dark:text-white hover:text-blue-600 dark:hover:text-blue-400"
                        >
                          {tpl.name}
                        </Link>
                        {isGlobal && (
                          <span className="ml-2 text-xs text-gray-500 dark:text-gray-400 italic">global</span>
                        )}
                      </td>
                      <td className="px-3 py-3 text-gray-600 dark:text-gray-400">
                        {tpl.role ? tpl.role.replace(/_/g, ' ') : '—'}
                      </td>
                      <td className="px-3 py-3 text-gray-600 dark:text-gray-400">{tpl.version}</td>
                      <td className="px-3 py-3">
                        <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium ${cls}`}>
                          {label}
                        </span>
                      </td>
                      <td className="px-3 py-3 text-gray-500 dark:text-gray-400">
                        {tpl.created_at ? new Date(tpl.created_at).toLocaleDateString() : '—'}
                      </td>
                      <td className="px-3 py-3">
                        <div className="flex items-center gap-2">
                          <Link
                            to={`/admin/templates/${tpl.id}/edit`}
                            className="text-blue-600 dark:text-blue-400 hover:underline text-xs"
                          >
                            Edit
                          </Link>
                          <button
                            type="button"
                            onClick={() => handleClone(tpl)}
                            disabled={cloning === tpl.id}
                            className="text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white disabled:opacity-50 text-xs flex items-center gap-1"
                          >
                            <Copy size={12} />
                            {cloning === tpl.id ? 'Cloning…' : 'Clone'}
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}

        {toast && (
          <div
            role="status"
            className="fixed bottom-6 right-6 bg-gray-900 dark:bg-gray-100 text-white dark:text-gray-900 px-4 py-2 rounded-lg shadow-lg text-sm"
          >
            {toast}
          </div>
        )}
      </div>
    </div>
  );
}
