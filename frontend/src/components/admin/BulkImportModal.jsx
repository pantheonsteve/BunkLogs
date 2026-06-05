import { useState } from 'react';
import {
  previewAdminPeopleImport,
  commitAdminPeopleImport,
} from '../../api/admin';

const SOURCES = [
  { value: 'campminder', label: 'Campminder' },
  { value: 'tbe', label: 'Temple Beth-El' },
];

/**
 * Step 7_13 PR3 — Bulk Person import affordance (Story 55 + supplemental).
 *
 * Two-step modal: 1) preview the parsed CSV against the chosen program
 * (no writes), 2) confirm to commit via the existing management command.
 *
 * Conflicts in the preview don't block the commit — the underlying
 * importer logs warnings and continues. Surface them in the preview
 * panel so the admin can decide whether to fix the CSV first.
 */
export default function BulkImportModal({ programs, onClose }) {
  const [source, setSource] = useState(SOURCES[0].value);
  const [programSlug, setProgramSlug] = useState(programs[0]?.slug || '');
  const [file, setFile] = useState(null);
  const [previewData, setPreviewData] = useState(null);
  const [committing, setCommitting] = useState(false);
  const [commitResult, setCommitResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handlePreview = async (e) => {
    e.preventDefault();
    if (!file || !programSlug) return;
    setLoading(true);
    setError(null);
    setPreviewData(null);
    setCommitResult(null);
    try {
      const data = await previewAdminPeopleImport(source, programSlug, file);
      setPreviewData(data);
    } catch (err) {
      setError(err?.response?.data?.detail || 'Preview failed.');
    } finally {
      setLoading(false);
    }
  };

  const handleCommit = async () => {
    if (!file || !programSlug) return;
    setCommitting(true);
    setError(null);
    try {
      const data = await commitAdminPeopleImport(source, programSlug, file);
      setCommitResult(data);
    } catch (err) {
      setError(err?.response?.data?.detail || 'Commit failed.');
    } finally {
      setCommitting(false);
    }
  };

  return (
    <div
      role="dialog"
      data-testid="bulk-import-modal"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
      onClick={(e) => { if (e.target === e.currentTarget && !committing) onClose(); }}
    >
      <div className="w-full max-w-2xl rounded-xl bg-white p-5 shadow-lg space-y-3 dark:bg-gray-900">
        <header className="flex items-center justify-between">
          <h2 className="text-lg font-semibold">Bulk import people</h2>
          <button type="button" onClick={onClose} className="text-sm text-gray-500 hover:underline">
            Close
          </button>
        </header>

        <form onSubmit={handlePreview} className="space-y-2" data-testid="bulk-import-form">
          <label className="block text-xs font-medium">Source
            <select
              value={source}
              onChange={(e) => setSource(e.target.value)}
              className="mt-1 w-full rounded-md border border-gray-300 p-2 text-sm"
            >
              {SOURCES.map((s) => (
                <option key={s.value} value={s.value}>{s.label}</option>
              ))}
            </select>
          </label>
          <label className="block text-xs font-medium">Program
            <select
              value={programSlug}
              onChange={(e) => setProgramSlug(e.target.value)}
              className="mt-1 w-full rounded-md border border-gray-300 p-2 text-sm"
            >
              {programs.map((p) => (
                <option key={p.id} value={p.slug}>{p.name}</option>
              ))}
            </select>
          </label>
          <label className="block text-xs font-medium">CSV file
            <input
              type="file"
              accept=".csv"
              data-testid="bulk-import-file"
              onChange={(e) => setFile(e.target.files?.[0] || null)}
              className="mt-1 w-full text-sm"
            />
          </label>
          {error && <p className="text-sm text-red-700">{error}</p>}
          <button
            type="submit"
            disabled={!file || loading}
            data-testid="bulk-import-preview"
            className="px-3 py-1.5 rounded-md text-sm bg-indigo-600 text-white disabled:opacity-60"
          >
            {loading ? 'Parsing…' : 'Preview'}
          </button>
        </form>

        {previewData && !commitResult && (
          <section data-testid="bulk-import-preview-panel" className="rounded-md border border-gray-200 p-3 space-y-2">
            <header className="flex items-center justify-between">
              <h3 className="text-sm font-medium">Preview ({previewData.summary.row_count} rows)</h3>
              <span className="text-xs text-gray-500">No writes performed</span>
            </header>
            <ul className="grid grid-cols-3 gap-2 text-xs">
              {Object.entries(previewData.summary).filter(([k]) => k !== 'row_count').map(([k, v]) => (
                <li key={k} className="rounded-md border border-gray-200 p-2">
                  <p className="font-semibold capitalize">{k}</p>
                  <p>{v}</p>
                </li>
              ))}
            </ul>
            {previewData.rows?.some((row) => ['merge', 'duplicate'].includes(row.classification)) && (
              <div className="max-h-40 overflow-y-auto rounded-md border border-amber-200 bg-amber-50 p-2 text-xs space-y-1">
                <p className="font-medium text-amber-900">Merges and duplicates</p>
                {previewData.rows
                  .filter((row) => ['merge', 'duplicate'].includes(row.classification))
                  .map((row) => (
                    <p key={`${row.external_id}-${row.full_name}`} className="text-amber-950">
                      <span className="font-semibold capitalize">{row.classification}</span>
                      {': '}
                      {row.full_name || 'Unknown'}
                      {row.email ? ` (${row.email})` : ''}
                      {row.existing_person_id ? ` → Person #${row.existing_person_id}` : ''}
                      {row.issues?.length ? ` — ${row.issues.join('; ')}` : ''}
                    </p>
                  ))}
              </div>
            )}
            <button
              type="button"
              onClick={handleCommit}
              disabled={committing}
              data-testid="bulk-import-commit"
              className="px-3 py-1.5 rounded-md text-sm bg-emerald-600 text-white disabled:opacity-60"
            >
              {committing ? 'Importing…' : 'Confirm import'}
            </button>
          </section>
        )}

        {commitResult && (
          <section data-testid="bulk-import-commit-panel" className="rounded-md border border-emerald-300 bg-emerald-50 p-3 space-y-2">
            <h3 className="text-sm font-medium">Import complete</h3>
            {commitResult.log?.summary?.duplicates_flagged?.length > 0 && (
              <div className="rounded-md border border-amber-300 bg-amber-50 p-2 text-xs text-amber-950 space-y-1">
                <p className="font-medium">
                  {commitResult.log.summary.duplicates_flagged.length} duplicate(s) flagged
                </p>
                {commitResult.log.summary.duplicates_flagged.map((item) => (
                  <p key={`${item.row}-${item.campminder_id}`}>
                    Row {item.row}: {item.full_name} ({item.reason})
                  </p>
                ))}
              </div>
            )}
            <pre className="text-xs whitespace-pre-wrap">
              {JSON.stringify(commitResult.log?.summary || {}, null, 2)}
            </pre>
          </section>
        )}
      </div>
    </div>
  );
}
