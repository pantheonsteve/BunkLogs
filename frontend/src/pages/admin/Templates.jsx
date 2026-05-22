import { useCallback, useEffect, useState } from 'react';
import { listAdminTemplates, reviewAdminTemplate } from '../../api/admin';

/**
 * Step 7_13 PR3 — Admin Templates oversight wrapper (Story 57).
 *
 * Wraps the LT-side template library so an Admin can see every
 * template in the org regardless of author, with Reviewed / Needs
 * revision actions for pending ones. The actual builder still lives
 * at /admin/templates/<id>/edit (TemplateEditorPage) so we don't
 * duplicate the editor — this page is purely the oversight surface.
 */

const STATUS_ORDER = ['draft', 'published', 'archived'];
const STATUS_LABELS = {
  draft: 'Draft',
  published: 'Published',
  archived: 'Archived',
  system: 'System',
};

function ReviewActions({ template, onReviewed }) {
  const [submitting, setSubmitting] = useState(null);
  const [note, setNote] = useState('');
  const [open, setOpen] = useState(false);

  const submit = async (review_status) => {
    setSubmitting(review_status);
    try {
      await reviewAdminTemplate(template.id, { review_status, review_note: note });
      onReviewed();
    } finally {
      setSubmitting(null);
      setOpen(false);
      setNote('');
    }
  };

  if (!open) {
    return (
      <button
        type="button"
        data-testid={`template-review-open-${template.id}`}
        onClick={() => setOpen(true)}
        className="text-xs px-2 py-1 rounded-md border border-indigo-200 text-indigo-700 hover:bg-indigo-50"
      >
        Review
      </button>
    );
  }
  return (
    <div className="flex flex-col gap-1" data-testid={`template-review-panel-${template.id}`}>
      <input
        value={note}
        onChange={(e) => setNote(e.target.value)}
        placeholder="Optional note"
        className="rounded-md border border-gray-300 p-1 text-xs"
      />
      <div className="flex gap-1 justify-end">
        <button
          type="button"
          onClick={() => setOpen(false)}
          className="text-xs text-gray-600 hover:underline"
        >
          Cancel
        </button>
        <button
          type="button"
          disabled={!!submitting}
          onClick={() => submit('needs_revision')}
          className="text-xs px-2 py-1 rounded-md bg-amber-500 text-white disabled:opacity-50"
          data-testid={`template-needs-revision-${template.id}`}
        >
          {submitting === 'needs_revision' ? '…' : 'Needs revision'}
        </button>
        <button
          type="button"
          disabled={!!submitting}
          onClick={() => submit('reviewed')}
          className="text-xs px-2 py-1 rounded-md bg-emerald-600 text-white disabled:opacity-50"
          data-testid={`template-mark-reviewed-${template.id}`}
        >
          {submitting === 'reviewed' ? '…' : 'Mark reviewed'}
        </button>
      </div>
    </div>
  );
}

function TemplateRow({ template, onReviewed }) {
  return (
    <li className="p-3 text-sm flex items-center justify-between gap-3" data-testid={`template-row-${template.id}`}>
      <div className="flex-1 min-w-0">
        <p className="font-medium truncate">{template.name}</p>
        <p className="text-xs text-gray-500">
          {template.role || 'any role'} · {template.cadence} ·{' '}
          {template.languages?.join(', ') || 'en'}
        </p>
      </div>
      <div className="flex items-center gap-2">
        {template.pending_review && (
          <span
            data-testid={`template-pending-${template.id}`}
            className="text-xs px-2 py-0.5 rounded-full bg-amber-100 text-amber-800"
          >
            Pending review
          </span>
        )}
        {template.review_status && (
          <span className={`text-xs px-2 py-0.5 rounded-full ${
            template.review_status === 'reviewed'
              ? 'bg-emerald-100 text-emerald-800'
              : 'bg-amber-100 text-amber-800'
          }`}>
            {template.review_status === 'reviewed' ? 'Reviewed' : 'Needs revision'}
          </span>
        )}
        {template.status === 'published' && (
          <ReviewActions template={template} onReviewed={onReviewed} />
        )}
      </div>
    </li>
  );
}

export default function AdminTemplates() {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      setData(await listAdminTemplates());
    } catch (err) {
      setError(err);
    }
  }, []);
  useEffect(() => { load(); }, [load]);

  return (
    <main
      className="grow px-4 sm:px-6 lg:px-8 py-6 w-full max-w-5xl mx-auto"
      data-testid="admin-templates"
    >
      <header className="mb-4 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Templates</h1>
          {data && data.pending_review_count > 0 && (
            <p className="text-sm text-amber-700" data-testid="templates-pending-summary">
              {data.pending_review_count} pending review
            </p>
          )}
        </div>
      </header>
      {error && <p className="text-sm text-red-700">Could not load templates.</p>}
      {!data && !error && <p className="text-sm text-gray-500">Loading…</p>}
      {data && STATUS_ORDER.map((statusKey) => (
        (data.grouped[statusKey] || []).length > 0 && (
          <section key={statusKey} className="mb-5" data-testid={`templates-section-${statusKey}`}>
            <h2 className="text-sm font-semibold uppercase text-gray-500 mb-2">{STATUS_LABELS[statusKey] || statusKey}</h2>
            <ul className="divide-y rounded-md border bg-white dark:bg-gray-900">
              {data.grouped[statusKey].map((t) => (
                <TemplateRow key={t.id} template={t} onReviewed={load} />
              ))}
            </ul>
          </section>
        )
      ))}
    </main>
  );
}
