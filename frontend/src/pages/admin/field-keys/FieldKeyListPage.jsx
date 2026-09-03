import { useCallback, useEffect, useMemo, useState } from 'react';
import { Plus } from 'lucide-react';

import api from '../../../api';
import Badge from '../../../components/ui/Badge';
import Button from '../../../components/ui/Button';
import Card, { CardBody, CardHeader } from '../../../components/ui/Card';
import ConfirmDialog from '../../../components/ui/ConfirmDialog';
import DataTable from '../../../components/ui/DataTable';
import EmptyState from '../../../components/ui/EmptyState';
import ErrorPanel from '../../../components/ui/ErrorPanel';
import FilterBar, {
  FilterChips,
  FilterSelect,
  SearchInput,
} from '../../../components/ui/FilterBar';
import LoadingState from '../../../components/ui/LoadingState';
import Modal from '../../../components/ui/Modal';
import OverflowMenu, { OverflowMenuItem } from '../../../components/ui/OverflowMenu';
import PageHeader from '../../../components/ui/PageHeader';
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
    <Modal
      title="Edit field key"
      onClose={onClose}
      dismissible={!busy}
      footer={
        <>
          <div className="flex-1" />
          <Button variant="secondary" onClick={onClose} disabled={busy}>
            Cancel
          </Button>
          <Button
            disabled={busy}
            onClick={() => onSubmit(form)}
            data-testid="fk-edit-submit"
          >
            {busy ? 'Saving…' : 'Save changes'}
          </Button>
        </>
      }
    >
      <FormFields form={form} onChange={setForm} lockKey />
    </Modal>
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
  const [deleting, setDeleting] = useState(null);
  const [deleteBusy, setDeleteBusy] = useState(false);
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

  const handleDelete = useCallback(async () => {
    const row = deleting;
    if (!row) return;
    setDeleteBusy(true);
    try {
      await api.delete(`/api/v1/field-keys/${row.id}/`);
      setDeleting(null);
      showToast(`Deleted "${row.key}".`);
      await load();
    } catch (err) {
      const status = err.response?.status;
      const detail = err.response?.data?.detail;
      setDeleting(null);
      if (status === 409) {
        showToast(detail || `"${row.key}" is referenced by one or more templates.`);
      } else {
        showToast(detail || 'Delete failed.');
      }
    } finally {
      setDeleteBusy(false);
    }
  }, [deleting, load, showToast]);

  const columns = [
    {
      key: 'key',
      header: 'Key',
      render: (row) => (
        <span className="font-mono text-xs text-gray-900 dark:text-white">{row.key}</span>
      ),
    },
    {
      key: 'display_name',
      header: 'Display name',
      render: (row) => (
        <>
          <span className="text-gray-900 dark:text-white">{row.display_name}</span>
          {row.description && (
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5 line-clamp-2">
              {row.description}
            </p>
          )}
        </>
      ),
    },
    {
      key: 'type',
      header: 'Type',
      width: '9rem',
      render: (row) => (
        <span className="text-xs">{labelForType(row.expected_field_type)}</span>
      ),
    },
    {
      key: 'dashboard_role',
      header: 'Dashboard role',
      width: '10rem',
      render: (row) => (
        <span className="text-xs">{labelForRole(row.expected_dashboard_role)}</span>
      ),
    },
    {
      key: 'scope',
      header: 'Scope',
      width: '6rem',
      render: (row) => (
        <Badge tone={row.is_global ? 'info' : 'neutral'}>
          {row.is_global ? 'Global' : 'Org'}
        </Badge>
      ),
    },
    {
      key: 'created',
      header: 'Created',
      width: '7rem',
      render: (row) => (
        <span className="text-xs text-gray-500 dark:text-gray-400">
          {row.created_at ? new Date(row.created_at).toLocaleDateString() : '—'}
        </span>
      ),
    },
    {
      key: 'actions',
      header: '',
      width: '3rem',
      align: 'right',
      render: (row) => (
        <OverflowMenu
          size="sm"
          label={`Actions for ${row.key}`}
          triggerTestId={`fk-actions-${row.key}`}
        >
          <OverflowMenuItem
            onClick={() => setEditing(row)}
            data-testid={`fk-edit-${row.key}`}
          >
            Edit field key…
          </OverflowMenuItem>
          <OverflowMenuItem
            danger
            onClick={() => setDeleting(row)}
            data-testid={`fk-delete-${row.key}`}
          >
            Delete field key…
          </OverflowMenuItem>
        </OverflowMenu>
      ),
    },
  ];

  return (
    <main className="grow px-4 sm:px-6 lg:px-8 py-6 w-full max-w-6xl mx-auto">
      <PageHeader
        backTo="/admin/home"
        title="Form fields"
        subtitle="Shared field names. When two forms ask the same question under the same name, dashboards can report on both together."
        actions={
          <Button
            onClick={() => {
              setCreating((v) => !v);
              setCreateError('');
            }}
            data-testid="fk-new-btn"
          >
            <Plus size={16} /> {creating ? 'Close' : 'New field key'}
          </Button>
        }
      />

      {creating && (
        <Card className="mb-6" data-testid="fk-create-form">
          <CardHeader title="New field key" />
          <CardBody>
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
                <Button type="submit" disabled={createBusy} data-testid="fk-create-submit">
                  {createBusy ? 'Creating…' : 'Create field key'}
                </Button>
              </div>
            </form>
          </CardBody>
        </Card>
      )}

      <FilterBar>
        <SearchInput
          value={search}
          onChange={setSearch}
          placeholder="Search by key prefix…"
          data-testid="fk-search"
        />
        <FilterChips
          value={scopeFilter}
          onChange={setScopeFilter}
          options={SCOPE_FILTERS}
          testIdPrefix="fk-scope-"
        />
        <FilterSelect
          value={typeFilter}
          onChange={setTypeFilter}
          aria-label="Filter by expected field type"
          options={[
            { value: '', label: 'All types' },
            ...FIELD_TYPE_OPTIONS.filter((o) => o.value),
          ]}
        />
      </FilterBar>

      {error && (
        <div className="mb-4">
          <ErrorPanel>{error}</ErrorPanel>
        </div>
      )}

      {loading ? (
        <LoadingState>Loading field keys…</LoadingState>
      ) : (
        <DataTable
          data-testid="fk-table"
          columns={columns}
          rows={visible}
          rowTestId={(row) => `fk-row-${row.key}`}
          empty={
            <EmptyState
              title={keys.length === 0 ? 'No field keys yet' : 'No matches'}
              data-testid="fk-empty"
            >
              {keys.length === 0
                ? 'Create one to get started, or run `python manage.py seed_field_keys` to seed the standard global set.'
                : 'No field keys match the current filters.'}
            </EmptyState>
          }
        />
      )}

      <EditModal
        open={!!editing}
        initial={editing}
        busy={editBusy}
        onClose={() => setEditing(null)}
        onSubmit={submitEdit}
      />

      {deleting && (
        <ConfirmDialog
          title={`Delete "${deleting.key}"?`}
          description={
            deleting.is_global
              ? 'This is a global key shared by every organization.'
              : undefined
          }
          confirmLabel={`Delete ${deleting.key}`}
          consequences={[
            'remove the key from the registry for good',
            'stop new templates from referencing it',
          ]}
          busy={deleteBusy}
          onConfirm={handleDelete}
          onClose={() => setDeleting(null)}
        >
          <p className="text-sm text-gray-600 dark:text-gray-400">
            Keys already used by a template can&apos;t be deleted — you&apos;ll get told which
            templates hold on to it.
          </p>
        </ConfirmDialog>
      )}

      <Toast message={toast} data-testid="fk-toast" />
    </main>
  );
}
