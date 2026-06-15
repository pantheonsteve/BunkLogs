import { useEffect, useState, useCallback, useRef } from 'react';
import { Link, useParams, useNavigate, useSearchParams } from 'react-router-dom';
import { ArrowLeft, BarChart3, UserPlus, Trash2, Upload, RotateCcw, CheckCircle, XCircle } from 'lucide-react';
import api from '../../../api';
import Button from '../../../components/ui/Button';
import ErrorPanel from '../../../components/ui/ErrorPanel';
import LoadingState from '../../../components/ui/LoadingState';
import Toast, { useToast } from '../../../components/ui/Toast';
import { canHaveParent, parentTypesFor } from '../../../lib/groupHierarchy';

function PersonSearchInput({ orgContext, onSelect }) {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [searching, setSearching] = useState(false);

  const search = useCallback(async (q) => {
    if (!q.trim() || q.length < 2) { setResults([]); return; }
    setSearching(true);
    try {
      const { data } = await api.get('/api/v1/memberships/', { params: { search: q, page_size: 20 } });
      const list = Array.isArray(data?.results) ? data.results : Array.isArray(data) ? data : [];
      setResults(list.map((m) => m.person).filter(Boolean));
    } catch {
      setResults([]);
    } finally {
      setSearching(false);
    }
  }, []);

  useEffect(() => {
    const t = setTimeout(() => search(query), 300);
    return () => clearTimeout(t);
  }, [query, search]);

  return (
    <div className="relative">
      <input
        type="text"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder="Search by name…"
        className="w-full border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-1.5 text-sm bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
      />
      {results.length > 0 && (
        <div className="absolute z-10 mt-1 w-full bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg max-h-48 overflow-y-auto">
          {results.map((p) => (
            <button
              key={p.id}
              type="button"
              onClick={() => { onSelect(p); setQuery(''); setResults([]); }}
              className="w-full text-left px-3 py-2 text-sm text-gray-900 dark:text-white hover:bg-gray-50 dark:hover:bg-gray-700"
            >
              {p.first_name} {p.last_name}
              {p.preferred_name && p.preferred_name !== p.first_name && (
                <span className="text-gray-400 ml-1">({p.preferred_name})</span>
              )}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

function MemberList({ title, members, onRemove, removing }) {
  if (!members.length) {
    return (
      <div>
        <h3 className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-2">
          {title} <span className="font-normal">(0)</span>
        </h3>
        <p className="text-sm text-gray-400 dark:text-gray-600 italic">None yet.</p>
      </div>
    );
  }
  return (
    <div>
      <h3 className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-2">
        {title} <span className="font-normal">({members.length})</span>
      </h3>
      <ul className="space-y-1">
        {members.map((m) => (
          <li
            key={m.id}
            className="flex items-center justify-between bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-lg px-3 py-2"
          >
            <span className="text-sm text-gray-900 dark:text-white">
              {m.person.first_name} {m.person.last_name}
              {m.person.preferred_name && m.person.preferred_name !== m.person.first_name && (
                <span className="text-gray-400 ml-1 text-xs">({m.person.preferred_name})</span>
              )}
              {!m.is_active && (
                <span className="ml-2 text-xs text-gray-400 italic">inactive</span>
              )}
            </span>
            <button
              type="button"
              onClick={() => onRemove(m.id)}
              disabled={removing === m.id}
              className="text-gray-400 hover:text-red-500 dark:hover:text-red-400 transition-colors disabled:opacity-40"
              aria-label="Remove member"
            >
              <Trash2 size={14} />
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}

function ImportStatus({ log }) {
  if (!log) return null;
  const color = log.status === 'completed' ? 'green' : log.status === 'failed' ? 'red' : 'yellow';
  const Icon = log.status === 'completed' ? CheckCircle : log.status === 'failed' ? XCircle : RotateCcw;
  return (
    <div className={`rounded-lg border px-4 py-3 text-sm flex gap-2 items-start
      ${color === 'green' ? 'bg-green-50 dark:bg-green-950/30 border-green-200 dark:border-green-800 text-green-700 dark:text-green-300' : ''}
      ${color === 'red' ? 'bg-red-50 dark:bg-red-950/30 border-red-200 dark:border-red-800 text-red-700 dark:text-red-300' : ''}
      ${color === 'yellow' ? 'bg-yellow-50 dark:bg-yellow-950/30 border-yellow-200 dark:border-yellow-800 text-yellow-700 dark:text-yellow-300' : ''}
    `}>
      <Icon size={16} className="mt-0.5 shrink-0" />
      <div>
        <p className="font-medium capitalize">{log.status}: {log.csv_filename}</p>
        {log.summary?.persons_created !== undefined && (
          <p className="text-xs mt-0.5">
            Persons created: {log.summary.persons_created} · updated: {log.summary.persons_updated} · unchanged: {log.summary.persons_unchanged}
          </p>
        )}
        {log.summary?.memberships_created !== undefined && (
          <p className="text-xs">Memberships created: {log.summary.memberships_created}</p>
        )}
        {log.summary?.warnings?.length > 0 && (
          <p className="text-xs mt-1 font-medium">{log.summary.warnings.length} warning(s)</p>
        )}
        {log.summary?.error && (
          <p className="text-xs mt-1 font-medium">Error: {log.summary.error}</p>
        )}
      </div>
    </div>
  );
}

export default function GroupDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [group, setGroup] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const { toast, showToast } = useToast(3500);

  // Add member state
  const [addRole, setAddRole] = useState('subject');
  const [selectedPerson, setSelectedPerson] = useState(null);
  const [addingMember, setAddingMember] = useState(false);

  // Remove member state
  const [removing, setRemoving] = useState(null);

  // Import roster state
  const fileRef = useRef(null);
  const [importerType, setImporterType] = useState('campminder');
  const [reconcile, setReconcile] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [lastLog, setLastLog] = useState(null);
  const [pollInterval, setPollInterval] = useState(null);

  // Edit state
  const [editing, setEditing] = useState(false);
  const [editName, setEditName] = useState('');
  const [editParent, setEditParent] = useState('');
  const [parentOptions, setParentOptions] = useState([]);
  const [editingParent, setEditingParent] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const { data } = await api.get(`/api/v1/assignment-groups/${id}/`);
      setGroup(data);
      setEditName(data.name);
      setEditParent(data.parent_id ? String(data.parent_id) : '');
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load group.');
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    load();
    return () => { if (pollInterval) clearInterval(pollInterval); };
  }, [load]);

  useEffect(() => {
    if (searchParams.get('edit') === '1') {
      setEditing(true);
    }
  }, [searchParams]);

  useEffect(() => {
    if (!group?.program || !canHaveParent(group.group_type)) {
      setParentOptions([]);
      return;
    }
    let cancelled = false;
    const types = parentTypesFor(group.group_type);
    Promise.all(
      types.map((groupType) => api.get('/api/v1/assignment-groups/', {
        params: {
          program: group.program,
          group_type: groupType,
          is_active: 'true',
          page_size: 500,
        },
      })),
    )
      .then((responses) => {
        if (cancelled) return;
        const merged = responses.flatMap((r) => {
          const data = r.data;
          return Array.isArray(data?.results) ? data.results : Array.isArray(data) ? data : [];
        })
          .filter((g) => g.id !== group.id)
          .sort((a, b) => a.name.localeCompare(b.name));
        setParentOptions(merged);
      })
      .catch(() => { if (!cancelled) setParentOptions([]); });
    return () => { cancelled = true; };
  }, [group?.id, group?.program, group?.group_type]);

  const handleAddMember = async () => {
    if (!selectedPerson) return;
    setAddingMember(true);
    try {
      await api.post(`/api/v1/assignment-groups/${id}/memberships/`, {
        person_id: selectedPerson.id,
        role_in_group: addRole,
      });
      setSelectedPerson(null);
      showToast(`Added ${selectedPerson.first_name} ${selectedPerson.last_name} as ${addRole}`);
      load();
    } catch (err) {
      showToast(err.response?.data?.detail || 'Failed to add member.');
    } finally {
      setAddingMember(false);
    }
  };

  const handleRemoveMember = async (membershipId) => {
    setRemoving(membershipId);
    try {
      await api.delete(`/api/v1/assignment-groups/${id}/memberships/${membershipId}/`);
      showToast('Member removed.');
      load();
    } catch (err) {
      showToast(err.response?.data?.detail || 'Failed to remove member.');
    } finally {
      setRemoving(null);
    }
  };

  const handleDeactivate = async () => {
    if (!window.confirm('Deactivate this group? It will be hidden but not deleted.')) return;
    try {
      await api.patch(`/api/v1/assignment-groups/${id}/`, { is_active: false });
      showToast('Group deactivated.');
      navigate('/admin/groups');
    } catch (err) {
      showToast(err.response?.data?.detail || 'Failed to deactivate.');
    }
  };

  const handleRename = async () => {
    try {
      await api.patch(`/api/v1/assignment-groups/${id}/`, { name: editName });
      setEditing(false);
      showToast('Name updated.');
      load();
    } catch (err) {
      showToast(err.response?.data?.detail || 'Failed to update name.');
    }
  };

  const handleParentSave = async () => {
    try {
      const payload = { parent: editParent ? Number(editParent) : null };
      await api.patch(`/api/v1/assignment-groups/${id}/`, payload);
      setEditingParent(false);
      showToast('Parent group updated.');
      load();
    } catch (err) {
      showToast(err.response?.data?.detail || 'Failed to update parent.');
    }
  };

  const pollLog = useCallback((logId) => {
    const interval = setInterval(async () => {
      try {
        const { data } = await api.get(`/api/v1/assignment-groups/import-logs/${logId}/`);
        setLastLog(data);
        if (data.status === 'completed' || data.status === 'failed') {
          clearInterval(interval);
          setPollInterval(null);
          if (data.status === 'completed') {
            load();
          }
        }
      } catch {
        clearInterval(interval);
        setPollInterval(null);
      }
    }, 2000);
    setPollInterval(interval);
  }, [load]);

  const handleImport = async () => {
    const file = fileRef.current?.files?.[0];
    if (!file) { showToast('Please select a CSV file first.'); return; }
    setUploading(true);
    setLastLog(null);
    try {
      const form = new FormData();
      form.append('file', file);
      form.append('importer_type', importerType);
      form.append('reconcile', reconcile ? 'true' : 'false');
      const { data } = await api.post(`/api/v1/assignment-groups/${id}/import-roster/`, form, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      setLastLog({ ...data, status: 'pending', csv_filename: file.name });
      pollLog(data.log_id);
      showToast('Import started. Polling for status…');
      if (fileRef.current) fileRef.current.value = '';
    } catch (err) {
      showToast(err.response?.data?.detail || 'Import failed.');
    } finally {
      setUploading(false);
    }
  };

  if (loading) {
    return (
      <main className="grow px-4 sm:px-6 lg:px-8 py-6 w-full max-w-screen-2xl mx-auto">
        <LoadingState>Loading…</LoadingState>
      </main>
    );
  }
  if (error) {
    return (
      <main className="grow px-4 sm:px-6 lg:px-8 py-6 w-full max-w-screen-2xl mx-auto">
        <ErrorPanel>{error}</ErrorPanel>
      </main>
    );
  }
  if (!group) return null;

  const subjects = (group.memberships || []).filter((m) => m.role_in_group === 'subject');
  const authors = (group.memberships || []).filter((m) => m.role_in_group === 'author');

  return (
    <main className="grow px-4 sm:px-6 lg:px-8 py-6 w-full max-w-screen-2xl mx-auto" data-testid="admin-group-detail">
      <Link
        to="/admin/groups"
        className="inline-flex items-center gap-1 text-sm text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 mb-4"
      >
        <ArrowLeft size={14} /> Groups
      </Link>

        {/* Header */}
        <div className="flex items-start justify-between mb-6">
          <div>
            {editing ? (
              <div className="flex items-center gap-2">
                <input
                  type="text"
                  value={editName}
                  onChange={(e) => setEditName(e.target.value)}
                  className="border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-1.5 text-lg font-bold bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
                />
                <Button size="sm" onClick={handleRename}>
                  Save
                </Button>
                <Button size="sm" variant="secondary" onClick={() => setEditing(false)}>
                  Cancel
                </Button>
              </div>
            ) : (
              <div className="flex items-center gap-2">
                <h1 className="text-2xl font-bold text-gray-900 dark:text-white">{group.name}</h1>
                <button
                  type="button"
                  onClick={() => setEditing(true)}
                  className="text-xs text-gray-400 hover:text-blue-500 dark:hover:text-blue-400 underline"
                >
                  rename
                </button>
              </div>
            )}
            <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
              {group.group_type} · slug: {group.slug}
              {!group.is_active && <span className="ml-2 text-red-500">(inactive)</span>}
            </p>
            {canHaveParent(group.group_type) && (
              <div className="mt-2 flex flex-wrap items-center gap-2 text-sm">
                <span className="text-gray-500 dark:text-gray-400">Parent:</span>
                {editingParent ? (
                  <>
                    <select
                      value={editParent}
                      onChange={(e) => setEditParent(e.target.value)}
                      className="border border-gray-300 dark:border-gray-600 rounded-lg px-2 py-1 text-sm bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
                      data-testid="group-edit-parent"
                    >
                      <option value="">None</option>
                      {parentOptions.map((g) => (
                        <option key={g.id} value={String(g.id)}>
                          {g.name} ({g.group_type})
                        </option>
                      ))}
                    </select>
                    <Button size="sm" onClick={handleParentSave}>Save</Button>
                    <Button
                      size="sm"
                      variant="secondary"
                      onClick={() => {
                        setEditingParent(false);
                        setEditParent(group.parent_id ? String(group.parent_id) : '');
                      }}
                    >
                      Cancel
                    </Button>
                  </>
                ) : group.parent_id ? (
                  <>
                    <Link
                      to={`/admin/groups/${group.parent_id}`}
                      className="text-blue-600 dark:text-blue-400 hover:underline"
                      data-testid="group-parent-link"
                    >
                      {group.parent_name || `Group #${group.parent_id}`}
                    </Link>
                    <button
                      type="button"
                      onClick={() => setEditingParent(true)}
                      className="text-xs text-gray-400 hover:text-blue-500 dark:hover:text-blue-400 underline"
                    >
                      change
                    </button>
                  </>
                ) : (
                  <>
                    <span className="text-gray-400 italic">None</span>
                    <button
                      type="button"
                      onClick={() => setEditingParent(true)}
                      className="text-xs text-gray-400 hover:text-blue-500 dark:hover:text-blue-400 underline"
                    >
                      set parent
                    </button>
                  </>
                )}
              </div>
            )}
          </div>
          <div className="flex items-center gap-3">
            <Link
              to={`/dashboards/subject-trends/${id}`}
              data-testid="group-subject-trends-link"
              className="inline-flex items-center gap-1.5 rounded-lg border border-gray-200 dark:border-gray-700 px-3 py-1.5 text-xs font-medium text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
            >
              <BarChart3 size={14} aria-hidden="true" />
              View subject trends →
            </Link>
            <button
              type="button"
              onClick={handleDeactivate}
              disabled={!group.is_active}
              className="text-xs text-gray-400 hover:text-red-500 dark:hover:text-red-400 underline disabled:opacity-40 disabled:cursor-not-allowed"
            >
              Deactivate
            </button>
          </div>
        </div>

        {/* Add member */}
        <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-xl p-5 mb-6">
          <h2 className="text-sm font-semibold text-gray-900 dark:text-white mb-3 flex items-center gap-2">
            <UserPlus size={15} /> Add member
          </h2>
          <div className="flex flex-wrap gap-3 items-end">
            <div className="flex-1 min-w-48">
              <label className="block text-xs text-gray-500 dark:text-gray-400 mb-1">Search person</label>
              <PersonSearchInput onSelect={setSelectedPerson} />
              {selectedPerson && (
                <p className="text-xs text-blue-600 dark:text-blue-400 mt-1">
                  Selected: {selectedPerson.first_name} {selectedPerson.last_name}
                </p>
              )}
            </div>
            <div>
              <label className="block text-xs text-gray-500 dark:text-gray-400 mb-1">Role in group</label>
              <select
                value={addRole}
                onChange={(e) => setAddRole(e.target.value)}
                className="border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-1.5 text-sm bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
              >
                <option value="subject">Subject (observed)</option>
                <option value="author">Author (observer)</option>
              </select>
            </div>
            <Button
              size="sm"
              onClick={handleAddMember}
              disabled={!selectedPerson || addingMember}
            >
              {addingMember ? 'Adding…' : 'Add'}
            </Button>
          </div>
        </div>

        {/* Roster columns */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
          <MemberList title="Subjects (observed)" members={subjects} onRemove={handleRemoveMember} removing={removing} />
          <MemberList title="Authors (observers)" members={authors} onRemove={handleRemoveMember} removing={removing} />
        </div>

        {/* CSV import */}
        <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-xl p-5">
          <h2 className="text-sm font-semibold text-gray-900 dark:text-white mb-3 flex items-center gap-2">
            <Upload size={15} /> Import roster from CSV
          </h2>
          <div className="flex flex-wrap gap-3 items-end mb-3">
            <div>
              <label className="block text-xs text-gray-500 dark:text-gray-400 mb-1">Importer</label>
              <select
                value={importerType}
                onChange={(e) => setImporterType(e.target.value)}
                className="border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-1.5 text-sm bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
              >
                <option value="campminder">Campminder</option>
                <option value="tbe_shulcloud">TBE ShulCloud</option>
              </select>
            </div>
            <div className="flex items-center gap-2 pb-1">
              <input
                type="checkbox"
                id="reconcile"
                checked={reconcile}
                onChange={(e) => setReconcile(e.target.checked)}
                className="rounded border-gray-300 dark:border-gray-600"
              />
              <label htmlFor="reconcile" className="text-sm text-gray-700 dark:text-gray-300">
                Reconcile (deactivate removed members)
              </label>
            </div>
            <div>
              <label className="block text-xs text-gray-500 dark:text-gray-400 mb-1">CSV file</label>
              <input
                type="file"
                accept=".csv"
                ref={fileRef}
                className="text-sm text-gray-700 dark:text-gray-300 file:mr-3 file:py-1 file:px-3 file:rounded-lg file:border-0 file:text-sm file:font-medium file:bg-blue-50 file:text-blue-700 dark:file:bg-blue-900/40 dark:file:text-blue-300 hover:file:bg-blue-100 dark:hover:file:bg-blue-900/60"
              />
            </div>
            <button
              type="button"
              onClick={handleImport}
              disabled={uploading}
              className="px-4 py-1.5 bg-green-600 text-white text-sm font-medium rounded-lg hover:bg-green-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
              {uploading ? 'Uploading…' : 'Import'}
            </button>
          </div>
        <ImportStatus log={lastLog} />
      </div>

      <Toast message={toast} />
    </main>
  );
}
