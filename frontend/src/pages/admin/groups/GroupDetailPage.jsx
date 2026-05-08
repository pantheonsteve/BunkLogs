import { useEffect, useState, useCallback, useRef } from 'react';
import { Link, useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, UserPlus, Trash2, Upload, RotateCcw, CheckCircle, XCircle } from 'lucide-react';
import api from '../../../api';

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
  const [group, setGroup] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [toast, setToast] = useState('');

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

  const showToast = (msg) => {
    setToast(msg);
    setTimeout(() => setToast(''), 3500);
  };

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const { data } = await api.get(`/api/v1/assignment-groups/${id}/`);
      setGroup(data);
      setEditName(data.name);
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

  if (loading) return <div className="p-8 text-sm text-gray-400">Loading…</div>;
  if (error) return <div className="p-8 text-sm text-red-500">{error}</div>;
  if (!group) return null;

  const subjects = (group.memberships || []).filter((m) => m.role_in_group === 'subject');
  const authors = (group.memberships || []).filter((m) => m.role_in_group === 'author');

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-950 px-4 py-6">
      <div className="max-w-5xl mx-auto">
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
                <button
                  type="button"
                  onClick={handleRename}
                  className="px-3 py-1.5 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700"
                >
                  Save
                </button>
                <button
                  type="button"
                  onClick={() => setEditing(false)}
                  className="px-3 py-1.5 text-sm bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-700 dark:text-gray-300"
                >
                  Cancel
                </button>
              </div>
            ) : (
              <div className="flex items-center gap-2">
                <h1 className="text-xl font-bold text-gray-900 dark:text-white">{group.name}</h1>
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
          </div>
          <button
            type="button"
            onClick={handleDeactivate}
            disabled={!group.is_active}
            className="text-xs text-gray-400 hover:text-red-500 dark:hover:text-red-400 underline disabled:opacity-40 disabled:cursor-not-allowed"
          >
            Deactivate
          </button>
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
            <button
              type="button"
              onClick={handleAddMember}
              disabled={!selectedPerson || addingMember}
              className="px-4 py-1.5 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
              {addingMember ? 'Adding…' : 'Add'}
            </button>
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

        {toast && (
          <div className="fixed bottom-6 left-1/2 -translate-x-1/2 bg-gray-900 dark:bg-gray-100 text-white dark:text-gray-900 text-sm px-5 py-2.5 rounded-full shadow-lg z-50">
            {toast}
          </div>
        )}
      </div>
    </div>
  );
}
