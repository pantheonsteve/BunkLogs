import { useCallback, useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { CheckCircle, RotateCcw, XCircle } from 'lucide-react';

import api from '../../../api';
import { listAdminPrograms } from '../../../api/admin';
import Button from '../../../components/ui/Button';
import Card, { CardBody, CardHeader } from '../../../components/ui/Card';
import ConfirmDialog from '../../../components/ui/ConfirmDialog';
import Note from '../../../components/ui/Note';
import { useTerm } from '../../../context/OrgBrandingContext';
import { canHaveParent, parentTypesFor } from '../../../lib/groupHierarchy';
import { groupTypeLabel } from './groupTypes';

/**
 * Everything about the group that isn't its roster.
 *
 * `slug` is not editable here — it's an internal identifier nobody asked
 * for, and exposing it invited edits that break links. Archiving lives at
 * the bottom in a danger zone rather than as a header link beside
 * routine actions.
 */
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

function ImportStatus({ log }) {
  if (!log) return null;
  const tone = log.status === 'completed' ? 'ok' : log.status === 'failed' ? 'danger' : 'warn';
  const Icon = log.status === 'completed' ? CheckCircle : log.status === 'failed' ? XCircle : RotateCcw;
  return (
    <Note tone={tone} className="mt-3">
      <div className="flex gap-2 items-start">
        <Icon size={16} className="mt-0.5 shrink-0" aria-hidden="true" />
        <div>
          <p className="font-medium capitalize">{log.status}: {log.csv_filename}</p>
          {log.summary?.persons_created !== undefined && (
            <p className="text-xs mt-0.5">
              Persons created: {log.summary.persons_created} · updated: {log.summary.persons_updated}
              {' '}· unchanged: {log.summary.persons_unchanged}
            </p>
          )}
          {log.summary?.memberships_created !== undefined && (
            <p className="text-xs">Group memberships created: {log.summary.memberships_created}</p>
          )}
          {log.summary?.error && <p className="text-xs mt-1 font-medium">Error: {log.summary.error}</p>}
        </div>
      </div>
    </Note>
  );
}

function Field({ label, hint, children }) {
  return (
    <label className="block text-xs font-medium text-gray-700 dark:text-gray-300">
      {label}
      {children}
      {hint && <span className="block mt-1 text-[11px] font-normal text-gray-500">{hint}</span>}
    </label>
  );
}

const INPUT_CLS = 'mt-1 w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm text-gray-900 dark:text-white';

export default function GroupSettingsTab({ group, onChanged, showToast }) {
  const navigate = useNavigate();
  const term = useTerm();

  const [name, setName] = useState(group.name);
  const [parent, setParent] = useState(group.parent_id ? String(group.parent_id) : '');
  const [displayOrder, setDisplayOrder] = useState(String(group.display_order ?? 0));
  const [parentOptions, setParentOptions] = useState([]);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  const [clonePrograms, setClonePrograms] = useState([]);
  const [cloneTarget, setCloneTarget] = useState('');
  const [cloning, setCloning] = useState(false);

  const fileRef = useRef(null);
  const [importerType, setImporterType] = useState('campminder');
  const [importRole, setImportRole] = useState('subject');
  const [reconcile, setReconcile] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [lastLog, setLastLog] = useState(null);
  const pollRef = useRef(null);

  const [archiving, setArchiving] = useState(false);

  useEffect(() => () => { if (pollRef.current) clearInterval(pollRef.current); }, []);

  useEffect(() => {
    if (!group.program || !canHaveParent(group.group_type)) {
      setParentOptions([]);
      return undefined;
    }
    let cancelled = false;
    Promise.all(
      parentTypesFor(group.group_type).map((groupType) => api.get('/api/v1/assignment-groups/', {
        params: { program: group.program, group_type: groupType, is_active: 'true', page_size: 500 },
      })),
    )
      .then((responses) => {
        if (cancelled) return;
        const byId = new Map();
        for (const r of responses) {
          for (const g of (Array.isArray(r.data?.results) ? r.data.results : r.data || [])) {
            if (g.id !== group.id) byId.set(g.id, g);
          }
        }
        setParentOptions([...byId.values()].sort((a, b) => a.name.localeCompare(b.name)));
      })
      .catch(() => { if (!cancelled) setParentOptions([]); });
    return () => { cancelled = true; };
  }, [group.id, group.program, group.group_type]);

  useEffect(() => {
    let cancelled = false;
    listAdminPrograms()
      .then((data) => {
        if (cancelled) return;
        const list = (data.results || []).filter((p) => String(p.id) !== String(group.program));
        setClonePrograms(list);
        setCloneTarget(list.length ? String(list[0].id) : '');
      })
      .catch(() => { if (!cancelled) setClonePrograms([]); });
    return () => { cancelled = true; };
  }, [group.program]);

  const save = async () => {
    setSaving(true);
    setError('');
    try {
      await api.patch(`/api/v1/assignment-groups/${group.id}/`, {
        name: name.trim(),
        parent: parent ? Number(parent) : null,
        display_order: Number(displayOrder) || 0,
      });
      await onChanged();
      showToast('Saved.');
    } catch (err) {
      setError(formatApiError(err.response?.data, 'Could not save.'));
    } finally {
      setSaving(false);
    }
  };

  const clone = async () => {
    if (!cloneTarget) return;
    setCloning(true);
    try {
      const { data } = await api.post(`/api/v1/assignment-groups/${group.id}/clone/`, {
        target_program: Number(cloneTarget),
      });
      showToast(`Cloned with ${data.clone_summary?.memberships_copied ?? 0} roster member(s).`);
      navigate(`/admin/groups/${data.id}`);
    } catch (err) {
      showToast(formatApiError(err.response?.data, 'Clone failed.'));
    } finally {
      setCloning(false);
    }
  };

  const pollLog = useCallback((logId) => {
    const startedAt = Date.now();
    pollRef.current = setInterval(async () => {
      if (Date.now() - startedAt > 5 * 60 * 1000) {
        clearInterval(pollRef.current);
        showToast('Import is taking longer than expected. Refresh to check.');
        return;
      }
      try {
        const { data } = await api.get(`/api/v1/assignment-groups/import-logs/${logId}/`);
        setLastLog(data);
        if (data.status === 'completed' || data.status === 'failed') {
          clearInterval(pollRef.current);
          if (data.status === 'completed') {
            await onChanged();
            showToast('Import completed.');
          } else {
            showToast(data.summary?.error || 'Import failed.');
          }
        }
      } catch (err) {
        clearInterval(pollRef.current);
        showToast(formatApiError(err.response?.data, 'Failed to check import status.'));
      }
    }, 2000);
  }, [onChanged, showToast]);

  const runImport = async () => {
    const file = fileRef.current?.files?.[0];
    if (!file) { showToast('Choose a CSV file first.'); return; }
    setUploading(true);
    setLastLog(null);
    try {
      const form = new FormData();
      form.append('file', file);
      form.append('importer_type', importerType);
      form.append('default_role_in_group', importRole);
      form.append('reconcile', reconcile ? 'true' : 'false');
      const response = await api.post(
        `/api/v1/assignment-groups/${group.id}/import-roster/`,
        form,
        { headers: { 'Content-Type': 'multipart/form-data' } },
      );
      const data = { ...response.data, csv_filename: file.name };
      setLastLog(data);
      if (data.status === 'completed') {
        await onChanged();
        showToast('Import completed.');
      } else if (data.status === 'failed') {
        showToast(data.summary?.error || 'Import failed.');
      } else {
        pollLog(data.log_id ?? data.id);
        showToast('Import started.');
      }
      if (fileRef.current) fileRef.current.value = '';
    } catch (err) {
      if (err.response?.data?.status) setLastLog(err.response.data);
      showToast(formatApiError(err.response?.data, 'Import failed.'));
    } finally {
      setUploading(false);
    }
  };

  const archive = async () => {
    try {
      await api.patch(`/api/v1/assignment-groups/${group.id}/`, { is_active: false });
      showToast(`${group.name} archived.`);
      navigate('/admin/groups');
    } catch (err) {
      showToast(formatApiError(err.response?.data, 'Could not archive.'));
      setArchiving(false);
    }
  };

  const subjectCount = (group.memberships || [])
    .filter((m) => m.is_active && m.role_in_group === 'subject').length;

  return (
    <div className="space-y-5" data-testid="group-settings-tab">
      <Card>
        <CardHeader title="Details" />
        <CardBody className="space-y-3 max-w-md">
          <Field label="Name">
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              className={INPUT_CLS}
              data-testid="group-settings-name"
            />
          </Field>
          {canHaveParent(group.group_type) && (
            <Field
              label="Part of"
              hint={`The larger ${term('group')} this one sits inside.`}
            >
              <select
                value={parent}
                onChange={(e) => setParent(e.target.value)}
                className={INPUT_CLS}
                data-testid="group-settings-parent"
              >
                <option value="">Nothing</option>
                {parentOptions.map((g) => (
                  <option key={g.id} value={String(g.id)}>
                    {g.name} ({groupTypeLabel(g.group_type)})
                  </option>
                ))}
              </select>
            </Field>
          )}
          <Field
            label="Sort position"
            hint="Lower numbers come first within this type. Leave at 0 to sort by name."
          >
            <input
              type="number"
              min="0"
              value={displayOrder}
              onChange={(e) => setDisplayOrder(e.target.value)}
              className={INPUT_CLS}
              data-testid="group-settings-order"
            />
          </Field>
          {error && <Note tone="danger">{error}</Note>}
          <Button onClick={save} disabled={saving} data-testid="group-settings-save">
            {saving ? 'Saving…' : 'Save changes'}
          </Button>
        </CardBody>
      </Card>

      <Card>
        <CardHeader
          title="Import roster from CSV"
          subtitle={`Rows are added to ${group.name}; a role_in_group column overrides the default.`}
        />
        <CardBody>
          <div className="flex flex-wrap gap-3 items-end">
            <Field label="Importer">
              <select
                value={importerType}
                onChange={(e) => setImporterType(e.target.value)}
                className={INPUT_CLS}
              >
                <option value="campminder">Campminder</option>
                <option value="tbe_shulcloud">TBE ShulCloud</option>
              </select>
            </Field>
            <Field label="Import as">
              <select
                value={importRole}
                onChange={(e) => setImportRole(e.target.value)}
                className={INPUT_CLS}
                data-testid="import-role-in-group"
              >
                <option value="subject">
                  {term('camper', { capitalize: true })} (observed)
                </option>
                <option value="author">
                  {term('counselor', { capitalize: true })} (writes logs)
                </option>
              </select>
            </Field>
            <label className="flex items-center gap-2 text-sm text-gray-700 dark:text-gray-300 pb-2">
              <input
                type="checkbox"
                checked={reconcile}
                onChange={(e) => setReconcile(e.target.checked)}
              />
              Remove anyone not in the file
            </label>
            <input
              type="file"
              accept=".csv"
              ref={fileRef}
              aria-label="CSV file"
              className="text-sm text-gray-700 dark:text-gray-300 file:mr-3 file:py-1.5 file:px-3 file:rounded-lg file:border-0 file:text-sm file:font-medium file:bg-blue-50 file:text-blue-700"
            />
            <Button onClick={runImport} disabled={uploading} data-testid="group-import-run">
              {uploading ? 'Uploading…' : 'Import'}
            </Button>
          </div>
          <ImportStatus log={lastLog} />
        </CardBody>
      </Card>

      <Card>
        <CardHeader
          title={`Copy to another ${term('program')}`}
          subtitle="Creates a copy with the same roster, so next year starts from this year."
        />
        <CardBody className="flex flex-wrap gap-3 items-end">
          <Field label={term('program', { capitalize: true })}>
            <select
              value={cloneTarget}
              onChange={(e) => setCloneTarget(e.target.value)}
              className={INPUT_CLS}
              data-testid="clone-target-program"
            >
              {clonePrograms.length === 0 && <option value="">No other programs</option>}
              {clonePrograms.map((p) => (
                <option key={p.id} value={String(p.id)}>
                  {p.name}{p.is_active ? '' : ' (Ended)'}
                </option>
              ))}
            </select>
          </Field>
          <Button
            variant="secondary"
            onClick={clone}
            disabled={cloning || !cloneTarget}
            data-testid="group-clone-confirm"
          >
            {cloning ? 'Copying…' : 'Copy'}
          </Button>
        </CardBody>
      </Card>

      <Card className="border-red-200 dark:border-red-900">
        <CardHeader
          title="Danger zone"
          subtitle="Archiving hides the group from every list. Nothing is deleted."
        />
        <CardBody>
          <Button
            variant="danger"
            className="border border-red-200 dark:border-red-900"
            disabled={!group.is_active}
            onClick={() => setArchiving(true)}
            data-testid="group-archive"
          >
            {group.is_active ? `Archive ${group.name}` : 'Already archived'}
          </Button>
        </CardBody>
      </Card>

      {archiving && (
        <ConfirmDialog
          title={`Archive ${group.name}?`}
          confirmLabel="Archive"
          consequences={[
            `Hide this ${term('group')} from lists, dashboards and assignment pickers`,
            subjectCount > 0
              ? `Stop new logs being written about its ${subjectCount} ${term('camper', { plural: subjectCount !== 1 })}`
              : 'Stop new logs being written here',
          ]}
          reassurance="Every log already written stays readable, and an admin can un-archive it."
          onConfirm={archive}
          onClose={() => setArchiving(false)}
        />
      )}
    </div>
  );
}
