import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  ArrowLeft,
  Plus,
  Pencil,
  Trash2,
  X,
  Search,
  Tag,
} from 'lucide-react';

import api from '../../../api';
import Button from '../../../components/ui/Button';
import EmptyState from '../../../components/ui/EmptyState';
import ErrorPanel from '../../../components/ui/ErrorPanel';
import LoadingState from '../../../components/ui/LoadingState';
import Toast, { useToast } from '../../../components/ui/Toast';

/**
 * Field key registry UI. Lists org + global keys, lets Super Admins
 * create, edit, and delete keys, and surfaces the 409 "key is referenced
 * by templates" error from DELETE clearly.
 *
 * Wired up at /admin/field-keys behind AdminRoute. See
 * `migration_prompts/3_29_field_key_registry_ui.md` for the contract.
 */

const FIELD_TYPE_OPTIONS = [
  { value: '', label: 'No type hint' },
  { value: 'text', label: 'Short text' },
  { value: 'textarea', label: 'Long text' },
  { value: 'text_list', label: 'Text list' },
  { value: 'single_choice', label: 'Single choice' },
  { value: 'multiple_choice', label: 'Multiple choice' },
  { value: 'yes_no', label: 'Yes / no' },
  { value: 'date', label: 'Date' },
  { value: 'number', label: 'Number' },
  { value: 'section_header', label: 'Section header' },
  { value: 'instructions', label: 'Instructions' },
  { value: 'rating_group', label: 'Rating group' },
  { value: 'single_rating', label: 'Single rating' },
];

// `expected_dashboard_role` is free-form on the backend, but the seeded
// global keys use this fixed vocabulary. Surface as a select with an
// "Other..." escape hatch.
const DASHBOARD_ROLE_OPTIONS = [
  { value: '', label: 'No dashboard role' },
  { value: 'category_ratings', label: 'Category ratings' },
  { value: 'wins', label: 'Wins' },
  { value: 'improvements', label: 'Improvements' },
  { value: 'open_concern', label: 'Open concern' },
];

const SCOPE_FILTERS = [
  { value: 'all', label: 'All' },
  { value: 'mine', label: 'Mine' },
  { value: 'global', label: 'Global' },
];

const EMPTY_FORM = {
  key: '',
  display_name: '',
  description: '',
  expected_field_type: '',
  expected_dashboard_role: '',
};

function labelForType(value) {
  const hit = FIELD_TYPE_OPTIONS.find((o) => o.value === value);
  return hit ? hit.label : value || '—';
}

function labelForRole(value) {
  const hit = DASHBOARD_ROLE_OPTIONS.find((o) => o.value === value);
  return hit ? hit.label : value || '—';
}

function inputClass() {
  return 'w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900 px-3 py-2 text-sm text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500';
}

function FormFields({ form, onChange, lockKey }) {
  const update = (field, value) => onChange({ ...form, [field]: value });
  return (
    <div className="space-y-3">
      <div>
        <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
          Key {lockKey ? '(read-only)' : '*'}
        </label>
        <input
          type="text"
          required
          readOnly={lockKey}
          value={form.key}
          onChange={(e) => update('key', e.target.value.trim().toLowerCase().replace(/\s+/g, '_'))}
          className={`${inputClass()} ${lockKey ? 'bg-gray-100 dark:bg-gray-800' : ''}`}
          placeholder="e.g. communication"
          data-testid="fk-form-key"
        />
        {!lockKey && (
          <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
            Lowercase letters, numbers, and underscores. Max 64 characters.
          </p>
        )}
      </div>
      <div>
        <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
          Display name *
        </label>
        <input
          type="text"
          required
          value={form.display_name}
          onChange={(e) => update('display_name', e.target.value)}
          className={inputClass()}
          placeholder="e.g. Communication"
          data-testid="fk-form-display-name"
        />
      </div>
      <div>
        <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
          Description
        </label>
        <textarea
          rows={2}
          value={form.description}
          onChange={(e) => update('description', e.target.value)}
          className={inputClass()}
          placeholder="What does this key represent across templates?"
        />
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <div>
          <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
            Expected field type
          </label>
          <select
            value={form.expected_field_type}
            onChange={(e) => update('expected_field_type', e.target.value)}
            className={inputClass()}
          >
            {FIELD_TYPE_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
            Dashboard role
          </label>
          <select
            value={form.expected_dashboard_role}
            onChange={(e) => update('expected_dashboard_role', e.target.value)}
            className={inputClass()}
          >
            {DASHBOARD_ROLE_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
            ))}
          </select>
        </div>
      </div>
    </div>
  );
}

function EditModal({ open, initial, busy, onClose, onSubmit }) {
  const [form, setForm] = useState(initial || EMPTY_FORM);
  useEffect(() => {
    setForm(initial || EMPTY_FORM);
  }, [initial]);

  if (!open) return null;
  return (
    <div
      role="dialog"
      aria-modal="true"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4"
      onClick={onClose}
    >
      <div
        className="w-full max-w-lg rounded-xl bg-white dark:bg-gray-900 shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <header className="flex items-center justify-between px-5 py-3 border-b border-gray-200 dark:border-gray-700">
          <h2 className="text-base font-semibold text-gray-900 dark:text-white">
            Edit field key
          </h2>
          <button
            type="button"
            onClick={onClose}
            className="text-gray-400 hover:text-gray-700 dark:hover:text-gray-200"
            aria-label="Close"
          >
            <X size={18} />
          </button>
        </header>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            onSubmit(form);
          }}
          className="px-5 py-4"
        >
          <FormFields form={form} onChange={setForm} lockKey />
          <div className="mt-5 flex items-center justify-end gap-2">
            <Button
              variant="secondary"
              onClick={onClose}
              disabled={busy}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              disabled={busy}
              data-testid="fk-edit-submit"
            >
              {busy ? 'Saving…' : 'Save changes'}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default function FieldKeyListPage() {
  const [keys, setKeys] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [search, setSearch] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [scopeFilter, setScopeFilter] = useState('all');
  const [typeFilter, setTypeFilter] = useState('');
  const [creating, setCreating] = useState(false);
  const [createForm, setCreateForm] = useState(EMPTY_FORM);
  const [createBusy, setCreateBusy] = useState(false);
  const [createError, setCreateError] = useState('');
  const [editing, setEditing] = useState(null);
  const [editBusy, setEditBusy] = useState(false);
  const { toast, showToast } = useToast();

  // Debounce search so we don't spam the API on every keystroke.
  useEffect(() => {
    const t = setTimeout(() => setDebouncedSearch(search.trim()), 250);
    return () => clearTimeout(t);
  }, [search]);

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const params = {};
      if (debouncedSearch) params.q = debouncedSearch;
      const { data } = await api.get('/api/v1/field-keys/', { params });
      const results = Array.isArray(data?.results) ? data.results : Array.isArray(data) ? data : [];
      setKeys(results);
    } catch (e) {
      const status = e.response?.status;
      if (status === 403) {
        setError('You do not have permission to view field keys.');
      } else {
        setError(e.response?.data?.detail || 'Failed to load field keys.');
      }
      setKeys([]);
    } finally {
      setLoading(false);
    }
  }, [debouncedSearch]);

  useEffect(() => {
    load();
  }, [load]);

  const visible = useMemo(
    () =>
      keys.filter((k) => {
        if (scopeFilter === 'global' && !k.is_global) return false;
        if (scopeFilter === 'mine' && k.is_global) return false;
        if (typeFilter && (k.expected_field_type || '') !== typeFilter) return false;
        return true;
      }),
    [keys, scopeFilter, typeFilter],
  );

  const submitCreate = useCallback(
    async (e) => {
      e.preventDefault();
      if (!createForm.key.trim() || !createForm.display_name.trim()) {
        setCreateError('Key and display name are required.');
        return;
      }
      setCreateBusy(true);
      setCreateError('');
      try {
        await api.post('/api/v1/field-keys/', createForm);
        showToast(`Created "${createForm.key}".`);
        setCreateForm(EMPTY_FORM);
        setCreating(false);
        await load();
      } catch (err) {
        const body = err.response?.data;
        const msg =
          typeof body === 'string'
            ? body
            : body?.key?.[0]
              || body?.display_name?.[0]
              || body?.detail
              || 'Create failed.';
        setCreateError(msg);
      } finally {
        setCreateBusy(false);
      }
    },
    [createForm, load, showToast],
  );

  const submitEdit = useCallback(
    async (form) => {
      if (!editing) return;
      setEditBusy(true);
      try {
        const payload = {
          display_name: form.display_name,
          description: form.description,
          expected_field_type: form.expected_field_type,
          expected_dashboard_role: form.expected_dashboard_role,
        };
        await api.patch(`/api/v1/field-keys/${editing.id}/`, payload);
        showToast(`Saved "${editing.key}".`);
        setEditing(null);
        await load();
      } catch (err) {
        const body = err.response?.data;
        const msg =
          typeof body === 'string'
            ? body
            : body?.detail || 'Save failed.';
        showToast(msg);
      } finally {
        setEditBusy(false);
      }
    },
    [editing, load, showToast],
  );

  const handleDelete = useCallback(
    async (row) => {
      const label = row.is_global ? `${row.key} (global)` : row.key;
      if (!window.confirm(`Delete "${label}"? This cannot be undone.`)) return;
      try {
        await api.delete(`/api/v1/field-keys/${row.id}/`);
        showToast(`Deleted "${row.key}".`);
        await load();
      } catch (err) {
        const status = err.response?.status;
        const detail = err.response?.data?.detail;
        if (status === 409) {
          showToast(detail || `"${row.key}" is referenced by one or more templates.`);
        } else {
          showToast(detail || 'Delete failed.');
        }
      }
    },
    [load, showToast],
  );

  return (
    <main className="grow px-4 sm:px-6 lg:px-8 py-6 w-full max-w-6xl mx-auto">
      <Link
        to="/admin/home"
        className="inline-flex items-center gap-1 text-sm text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 mb-4"
      >
        <ArrowLeft size={14} /> Admin
      </Link>

      <div className="flex items-start justify-between mb-6 gap-4">
        <div>
          <h1 className="text-xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
            <Tag size={18} aria-hidden="true" />
            Field keys
          </h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1 max-w-2xl">
            Canonical short identifiers used across reflection templates so
            cross-template dashboards can aggregate the same field even when
            it lives in different templates.
          </p>
        </div>
        <Button
          onClick={() => {
            setCreating((v) => !v);
            setCreateError('');
          }}
          className="shrink-0"
          data-testid="fk-new-btn"
        >
          <Plus size={16} /> {creating ? 'Close' : 'New field key'}
        </Button>
      </div>

      {creating && (
        <section
          data-testid="fk-create-form"
          className="mb-6 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-xl p-5"
        >
          <h2 className="text-sm font-semibold text-gray-900 dark:text-white mb-4">
            New field key
          </h2>
          <form onSubmit={submitCreate}>
            <FormFields form={createForm} onChange={setCreateForm} />
            {createError && (
              <p className="mt-3 text-sm text-red-600 dark:text-red-400" role="alert">
                {createError}
              </p>
            )}
            <div className="mt-4 flex items-center justify-end gap-2">
              <Button
                variant="secondary"
                onClick={() => {
                  setCreating(false);
                  setCreateError('');
                }}
                disabled={createBusy}
              >
                Cancel
              </Button>
              <Button
                type="submit"
                disabled={createBusy}
                data-testid="fk-create-submit"
              >
                {createBusy ? 'Creating…' : 'Create field key'}
              </Button>
            </div>
          </form>
        </section>
      )}

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-3 mb-4">
        <div className="relative">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            type="search"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by key prefix…"
            data-testid="fk-search"
            className="pl-8 pr-3 py-1.5 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900 text-sm text-gray-900 dark:text-gray-100 w-64 focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        <div className="flex gap-1">
          {SCOPE_FILTERS.map((s) => (
            <button
              key={s.value}
              type="button"
              onClick={() => setScopeFilter(s.value)}
              data-testid={`fk-scope-${s.value}`}
              className={`px-3 py-1 rounded-full text-xs font-medium transition-colors ${
                scopeFilter === s.value
                  ? 'bg-blue-600 text-white'
                  : 'bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700'
              }`}
            >
              {s.label}
            </button>
          ))}
        </div>
        <select
          value={typeFilter}
          onChange={(e) => setTypeFilter(e.target.value)}
          aria-label="Filter by expected field type"
          className="px-3 py-1 rounded-full text-xs border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300"
        >
          <option value="">All types</option>
          {FIELD_TYPE_OPTIONS.filter((o) => o.value).map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
      </div>

      {error && (
        <div className="mb-4">
          <ErrorPanel>{error}</ErrorPanel>
        </div>
      )}

      {loading ? (
        <LoadingState>Loading field keys…</LoadingState>
      ) : visible.length === 0 ? (
        <EmptyState
          title={keys.length === 0 ? 'No field keys yet' : 'No matches'}
          data-testid="fk-empty"
        >
          {keys.length === 0
            ? 'Create one to get started, or run `python manage.py seed_field_keys` to seed the standard global set.'
            : 'No field keys match the current filters.'}
        </EmptyState>
      ) : (
        <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
          <table className="w-full text-sm" data-testid="fk-table">
            <thead className="bg-gray-50 dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
              <tr>
                <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide">Key</th>
                <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide">Display name</th>
                <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide">Type</th>
                <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide">Dashboard role</th>
                <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide">Scope</th>
                <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide">Created</th>
                <th className="px-3 py-2 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 dark:divide-gray-800">
              {visible.map((row) => (
                <tr
                  key={row.id}
                  data-testid={`fk-row-${row.key}`}
                  className="hover:bg-gray-50 dark:hover:bg-gray-800/50"
                >
                  <td className="px-3 py-3 font-mono text-xs text-gray-900 dark:text-white">
                    {row.key}
                  </td>
                  <td className="px-3 py-3 text-gray-900 dark:text-white">
                    {row.display_name}
                    {row.description && (
                      <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5 line-clamp-2">
                        {row.description}
                      </p>
                    )}
                  </td>
                  <td className="px-3 py-3 text-gray-600 dark:text-gray-400 text-xs">
                    {labelForType(row.expected_field_type)}
                  </td>
                  <td className="px-3 py-3 text-gray-600 dark:text-gray-400 text-xs">
                    {labelForRole(row.expected_dashboard_role)}
                  </td>
                  <td className="px-3 py-3">
                    {row.is_global ? (
                      <span className="inline-block px-2 py-0.5 rounded-full text-xs font-medium bg-indigo-100 text-indigo-700 dark:bg-indigo-900/40 dark:text-indigo-300">
                        Global
                      </span>
                    ) : (
                      <span className="inline-block px-2 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300">
                        Org
                      </span>
                    )}
                  </td>
                  <td className="px-3 py-3 text-gray-500 dark:text-gray-400 text-xs">
                    {row.created_at ? new Date(row.created_at).toLocaleDateString() : '—'}
                  </td>
                  <td className="px-3 py-3 text-right">
                    <div className="inline-flex items-center gap-1">
                      <button
                        type="button"
                        onClick={() => setEditing(row)}
                        data-testid={`fk-edit-${row.key}`}
                        className="inline-flex items-center gap-1 text-blue-600 dark:text-blue-400 hover:underline text-xs px-2 py-1"
                      >
                        <Pencil size={12} /> Edit
                      </button>
                      <button
                        type="button"
                        onClick={() => handleDelete(row)}
                        data-testid={`fk-delete-${row.key}`}
                        className="inline-flex items-center gap-1 text-red-600 dark:text-red-400 hover:underline text-xs px-2 py-1"
                      >
                        <Trash2 size={12} /> Delete
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <EditModal
        open={!!editing}
        initial={editing}
        busy={editBusy}
        onClose={() => setEditing(null)}
        onSubmit={submitEdit}
      />

      <Toast message={toast} data-testid="fk-toast" />
    </main>
  );
}
