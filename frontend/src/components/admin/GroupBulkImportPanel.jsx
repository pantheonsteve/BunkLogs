import { useState } from 'react';
import { Download, Upload } from 'lucide-react';
import api from '../../api';
import Button from '../ui/Button';

function formatApiError(data, fallback) {
  if (!data) return fallback;
  if (typeof data.detail === 'string') return data.detail;
  if (Array.isArray(data.errors) && data.errors.length) return data.errors.join(' ');
  return fallback;
}

async function downloadGroupImportTemplate() {
  const response = await api.get('/api/v1/assignment-groups/import-template/', {
    responseType: 'blob',
  });
  const url = window.URL.createObjectURL(new Blob([response.data]));
  const link = document.createElement('a');
  link.href = url;
  link.setAttribute('download', 'assignment_groups_import_template.csv');
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
}

async function importGroupsCsv(file, programId, mode) {
  const form = new FormData();
  form.append('file', file);
  form.append('program', String(programId));
  form.append('mode', mode);
  const response = await api.post('/api/v1/assignment-groups/bulk-import/', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return response.data;
}

/**
 * Bulk CSV import panel for Assignment Groups (structure only).
 */
export default function GroupBulkImportPanel({ programId, programName, onDone, showToast }) {
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [busy, setBusy] = useState(false);

  const runPreview = async (selectedFile) => {
    setBusy(true);
    setPreview(null);
    try {
      const data = await importGroupsCsv(selectedFile, programId, 'preview');
      setPreview(data);
    } catch (err) {
      setPreview(err.response?.data || { valid: false, errors: ['Preview failed.'] });
    } finally {
      setBusy(false);
    }
  };

  const runCommit = async () => {
    if (!file) return;
    setBusy(true);
    try {
      const data = await importGroupsCsv(file, programId, 'commit');
      const summary = data.summary || {};
      showToast(
        `Imported groups: +${summary.groups_created || 0} new, `
        + `${summary.groups_updated || 0} updated, `
        + `${summary.parents_linked || 0} parent links`,
      );
      setFile(null);
      setPreview(null);
      onDone?.();
    } catch (err) {
      showToast(formatApiError(err.response?.data, 'Import failed.'));
    } finally {
      setBusy(false);
    }
  };

  return (
    <section
      data-testid="group-bulk-import-panel"
      className="mb-6 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-xl p-5"
    >
      <h2 className="text-sm font-semibold text-gray-900 dark:text-white mb-1 flex items-center gap-2">
        <Upload size={15} />
        Bulk import groups from CSV
      </h2>
      <p className="text-xs text-gray-500 dark:text-gray-400 mb-3">
        Import assignment groups into
        {' '}
        <span className="font-medium text-gray-700 dark:text-gray-300">{programName}</span>
        . One row per group. Columns:
        {' '}
        <code className="text-xs">name</code>
        ,
        {' '}
        <code className="text-xs">group_type</code>
        ,
        {' '}
        <code className="text-xs">parent_name</code>
        ,
        {' '}
        <code className="text-xs">parent_group_type</code>
        ,
        {' '}
        <code className="text-xs">is_active</code>
        .
      </p>
      <div className="flex flex-wrap items-center gap-3">
        <input
          type="file"
          accept=".csv,text/csv"
          data-testid="group-bulk-import-file"
          onChange={(e) => {
            const selected = e.target.files?.[0] || null;
            setFile(selected);
            if (selected) runPreview(selected);
          }}
          className="text-sm text-gray-700 dark:text-gray-300"
        />
        <Button variant="secondary" size="sm" onClick={() => downloadGroupImportTemplate()}>
          <Download size={14} />
          Template
        </Button>
      </div>

      {busy && !preview && (
        <p className="mt-3 text-xs text-gray-500 dark:text-gray-400">Validating CSV…</p>
      )}

      {preview && (
        <div className="mt-4 text-sm">
          {preview.valid ? (
            <div className="rounded-lg bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 p-3">
              <p className="text-green-800 dark:text-green-300">
                {preview.row_count} valid row(s) ready to import.
              </p>
              <div className="mt-3">
                <Button
                  size="sm"
                  onClick={runCommit}
                  disabled={busy}
                  data-testid="group-bulk-import-commit"
                >
                  {busy ? 'Importing…' : 'Import groups'}
                </Button>
              </div>
            </div>
          ) : (
            <div className="rounded-lg bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 p-3">
              <p className="font-medium text-red-800 dark:text-red-300 mb-1">
                {(preview.errors || []).length} error(s) — fix and re-upload:
              </p>
              <ul className="list-disc list-inside text-xs text-red-700 dark:text-red-300 max-h-40 overflow-auto">
                {(preview.errors || []).map((err) => <li key={err}>{err}</li>)}
              </ul>
            </div>
          )}
        </div>
      )}
    </section>
  );
}
