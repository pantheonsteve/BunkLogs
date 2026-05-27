/**
 * Camper Care note form — Step 7_8, Story 21.
 *
 * Two modes:
 *   - Create: route `/camper-care/notes/new?camperId=<id>`
 *   - Edit (post-create or deep-link with state): route
 *     `/camper-care/notes/:noteId/edit`. The author can keep editing
 *     within the 24h window; after expiry the form is read-only.
 *
 * The form exposes:
 *   - Body (required, textarea)
 *   - Category (required, enum select)
 *   - Sensitive (boolean checkbox)
 *   - Language (en/es)
 *
 * The AudienceDisclosure refreshes whenever Sensitive is toggled, so
 * the form authoritatively shows the reduced sensitive-variant
 * audience (no Health Center / Special Diets) before the author
 * submits.
 *
 * Backend doesn't currently expose a GET single-note endpoint, so the
 * edit mode relies on `location.state.note` (set by the create success
 * banner). A bare `/camper-care/notes/:noteId/edit` visit with no state
 * falls back to the create form with a helpful notice.
 */

import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link, useLocation, useNavigate, useParams, useSearchParams } from 'react-router-dom';
import AudienceDisclosure from '../../components/AudienceDisclosure';
import {
  NOTE_CATEGORIES,
  createCamperCareNote,
  fetchCamperCareNoteAudience,
  patchCamperCareNote,
} from '../../api/camperCare';

function camperIdFromQuery(searchParams) {
  const raw = searchParams.get('camperId') || searchParams.get('camper_id');
  if (!raw) return null;
  const n = Number(raw);
  return Number.isFinite(n) ? n : null;
}

function FieldRow({ label, htmlFor, required, error, children, hint }) {
  return (
    <label htmlFor={htmlFor} className="block text-sm">
      <span className="text-gray-800 dark:text-gray-100 font-medium">
        {label}
        {required && <span aria-hidden="true" className="text-red-600 ml-1">*</span>}
      </span>
      {hint && <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">{hint}</p>}
      <div className="mt-1">{children}</div>
      {error && (
        <p role="alert" className="text-xs text-red-700 dark:text-red-300 mt-1">{error}</p>
      )}
    </label>
  );
}

function isWithinEditWindow(createdAt) {
  if (!createdAt) return false;
  const created = new Date(createdAt).getTime();
  if (Number.isNaN(created)) return false;
  return Date.now() - created <= 24 * 60 * 60 * 1000;
}

export default function CamperCareNoteForm() {
  const { noteId } = useParams();
  const navigate = useNavigate();
  const location = useLocation();
  const [searchParams] = useSearchParams();

  const initialFromState = location.state?.note || null;
  const initialCamperId = initialFromState?.subject_id || camperIdFromQuery(searchParams);

  const [noteRow, setNoteRow] = useState(initialFromState);
  const [subjectId] = useState(initialCamperId);

  const [body, setBody] = useState(initialFromState?.body ?? '');
  const [category, setCategory] = useState(initialFromState?.category ?? '');
  const [isSensitive, setIsSensitive] = useState(Boolean(initialFromState?.is_sensitive));
  const [language, setLanguage] = useState(initialFromState?.language ?? 'en');

  const [audience, setAudience] = useState([]);
  const [audienceLoading, setAudienceLoading] = useState(true);
  const [fieldErrors, setFieldErrors] = useState({});
  const [submitError, setSubmitError] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [successMessage, setSuccessMessage] = useState('');

  const isEditMode = Boolean(noteRow?.id || noteId);
  const editable = noteRow ? isWithinEditWindow(noteRow.created_at) : !isEditMode;

  const loadAudience = useCallback(async (sensitive) => {
    setAudienceLoading(true);
    try {
      const payload = await fetchCamperCareNoteAudience({ isSensitive: sensitive });
      setAudience(payload.audience || []);
    } catch (err) {
      setAudience([]);
    } finally {
      setAudienceLoading(false);
    }
  }, []);

  useEffect(() => {
    loadAudience(isSensitive);
  }, [isSensitive, loadAudience]);

  const validate = () => {
    const errs = {};
    if (!body.trim()) errs.body = 'Required.';
    if (!category) errs.category = 'Required.';
    if (!noteRow && subjectId == null) errs.subject = 'Camper id is required (link from camper dashboard).';
    setFieldErrors(errs);
    return Object.keys(errs).length === 0;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSubmitError('');
    setSuccessMessage('');
    if (!validate()) return;
    setSubmitting(true);
    try {
      if (noteRow?.id) {
        const updated = await patchCamperCareNote(noteRow.id, {
          body: body.trim(),
          category,
          isSensitive,
          language,
        });
        setNoteRow(updated);
        setSuccessMessage('Note updated.');
      } else {
        const { data } = await createCamperCareNote({
          subjectId,
          body: body.trim(),
          category,
          isSensitive,
          language,
        });
        setNoteRow(data);
        setSuccessMessage('Note added.');
      }
    } catch (err) {
      const respData = err?.response?.data;
      if (respData && typeof respData === 'object' && !Array.isArray(respData)) {
        const flat = {};
        Object.entries(respData).forEach(([k, v]) => {
          flat[k] = Array.isArray(v) ? v.join(' ') : String(v);
        });
        setFieldErrors((prev) => ({ ...prev, ...flat }));
        setSubmitError(respData.detail || 'Could not save note.');
      } else {
        setSubmitError(err?.message || 'Could not save note.');
      }
    } finally {
      setSubmitting(false);
    }
  };

  const heading = useMemo(() => {
    if (noteRow?.id) return 'Edit Camper Care note';
    return 'New Camper Care note';
  }, [noteRow]);

  if (isEditMode && !noteRow) {
    return (
      <div className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-[96rem] mx-auto space-y-3">
        <h1 className="text-2xl font-semibold text-gray-900 dark:text-white">Edit Camper Care note</h1>
        <div
          role="alert"
          className="rounded-xl border border-amber-200 bg-amber-50 dark:border-amber-900 dark:bg-amber-900/30 px-4 py-3 text-sm text-amber-900 dark:text-amber-100"
          data-testid="cc-noteform-missing-state"
        >
          This page must be opened from the create form's success banner or the camper dashboard's edit link. Direct deep links don't have the note context yet.
        </div>
        <Link
          to="/camper-care"
          className="inline-flex items-center px-3 min-h-[40px] rounded-lg border border-gray-300 dark:border-gray-700 text-sm text-gray-800 dark:text-gray-100"
        >
          Back to dashboard
        </Link>
      </div>
    );
  }

  const formDisabled = isEditMode && !editable;

  return (
    <div className="px-4 sm:px-6 lg:px-8 py-8 pb-24 w-full max-w-[96rem] mx-auto" data-testid="cc-noteform">
      <header className="mb-3">
        <h1 className="text-2xl font-semibold text-gray-900 dark:text-white">{heading}</h1>
        {subjectId != null && (
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
            Camper id: {subjectId}
          </p>
        )}
        {formDisabled && (
          <p className="text-sm text-amber-700 dark:text-amber-200 mt-1" data-testid="cc-noteform-window-closed">
            This note is past the 24-hour edit window and can no longer be changed. Add a follow-up note instead.
          </p>
        )}
      </header>

      <AudienceDisclosure
        audience={audienceLoading ? [] : audience}
        contextHint={
          audienceLoading
            ? 'Resolving audience…'
            : isSensitive
              ? 'Sensitive notes are visible only to Camper Care, Health Center, Special Diets, and Admin.'
              : 'Non-sensitive notes are visible to Camper Care, Leadership Team, and Admin.'
        }
      />

      <form onSubmit={handleSubmit} className="space-y-4" data-testid="cc-noteform-form">
        <FieldRow
          label="Body"
          htmlFor="cc-note-body"
          required
          error={fieldErrors.body}
        >
          <textarea
            id="cc-note-body"
            value={body}
            onChange={(e) => setBody(e.target.value)}
            rows={6}
            disabled={formDisabled || submitting}
            data-testid="cc-noteform-body"
            className="mt-1 block w-full rounded-md border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:ring-2 focus:ring-blue-200"
          />
        </FieldRow>

        <FieldRow
          label="Category"
          htmlFor="cc-note-category"
          required
          error={fieldErrors.category}
        >
          <select
            id="cc-note-category"
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            disabled={formDisabled || submitting}
            data-testid="cc-noteform-category"
            className="mt-1 block w-full rounded-md border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 px-3 py-2 text-sm"
          >
            <option value="">Select…</option>
            {NOTE_CATEGORIES.map((c) => (
              <option key={c.value} value={c.value}>{c.label}</option>
            ))}
          </select>
        </FieldRow>

        <fieldset
          className="rounded-lg border border-gray-200 dark:border-gray-700 px-3 py-2"
          data-testid="cc-noteform-sensitive-block"
        >
          <legend className="text-sm font-medium text-gray-800 dark:text-gray-100 px-1">Visibility</legend>
          <label className="flex items-start gap-2 text-sm cursor-pointer">
            <input
              type="checkbox"
              checked={isSensitive}
              onChange={(e) => setIsSensitive(e.target.checked)}
              disabled={formDisabled || submitting}
              data-testid="cc-noteform-sensitive"
              className="mt-1 h-4 w-4 rounded border-gray-300"
            />
            <span className="text-gray-700 dark:text-gray-200">
              Sensitive — restrict to Camper Care, Health Center, Special Diets, and Admin.
            </span>
          </label>
        </fieldset>

        <FieldRow label="Language" htmlFor="cc-note-language">
          <select
            id="cc-note-language"
            value={language}
            onChange={(e) => setLanguage(e.target.value)}
            disabled={formDisabled || submitting}
            data-testid="cc-noteform-language"
            className="mt-1 block w-full rounded-md border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 px-3 py-2 text-sm"
          >
            <option value="en">English</option>
            <option value="es">Spanish</option>
          </select>
        </FieldRow>

        {submitError && (
          <p role="alert" className="text-sm text-red-700 dark:text-red-300" data-testid="cc-noteform-error">
            {submitError}
          </p>
        )}

        {successMessage && (
          <div
            role="status"
            className="rounded-md border border-green-200 bg-green-50 dark:border-green-800 dark:bg-green-900/30 px-3 py-2 text-sm text-green-900 dark:text-green-100"
            data-testid="cc-noteform-success"
          >
            {successMessage}
          </div>
        )}

        {fieldErrors.subject && (
          <p role="alert" className="text-sm text-red-700 dark:text-red-300">{fieldErrors.subject}</p>
        )}

        <div className="flex items-center justify-end gap-2">
          <button
            type="button"
            onClick={() => navigate(-1)}
            className="inline-flex items-center px-3 min-h-[44px] rounded-lg border border-gray-300 dark:border-gray-700 text-sm text-gray-800 dark:text-gray-100"
            disabled={submitting}
          >
            Back
          </button>
          <button
            type="submit"
            disabled={formDisabled || submitting}
            data-testid="cc-noteform-submit"
            className="inline-flex items-center px-4 min-h-[44px] rounded-lg bg-blue-600 text-white text-sm font-medium hover:bg-blue-700 disabled:opacity-60"
          >
            {submitting ? 'Saving…' : (noteRow?.id ? 'Save changes' : 'Add note')}
          </button>
        </div>
      </form>
    </div>
  );
}
