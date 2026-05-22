/**
 * Specialist note form — Step 7_9, Stories 26-27.
 *
 * Two modes:
 *   - Create: route `/specialist/notes/new` — opens camper picker first,
 *     then the form with the selected camper pre-populated.
 *   - Edit: route `/specialist/notes/:noteId/edit` — populated from
 *     `location.state.note`. Direct deep-links without state show a notice.
 *
 * Fields (Story 26 criterion 2):
 *   - Body (required, plain text)
 *   - Category (optional enum)
 *   - Sensitive (boolean, default unchecked)
 *   - Flag for Camper Care (boolean, default unchecked)
 *   - Language
 *
 * AudienceDisclosure updates dynamically when Sensitive is toggled (criterion 5).
 * Flag state cannot be changed after submission (Decision S5).
 * Submit button is visible above the mobile keyboard via sticky footer.
 */

import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link, useLocation, useNavigate, useParams } from 'react-router-dom';
import AudienceDisclosure from '../../components/AudienceDisclosure';
import {
  SPECIALIST_NOTE_CATEGORIES,
  createSpecialistNote,
  fetchSpecialistNoteAudience,
  patchSpecialistNote,
} from '../../api/specialist';
import CamperPicker from './CamperPicker';

function isWithinEditWindow(createdAt) {
  if (!createdAt) return false;
  const created = new Date(createdAt).getTime();
  if (Number.isNaN(created)) return false;
  return Date.now() - created <= 24 * 60 * 60 * 1000;
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

export default function SpecialistNoteForm() {
  const { noteId } = useParams();
  const navigate = useNavigate();
  const location = useLocation();

  const initialFromState = location.state?.note || null;

  const [showPicker, setShowPicker] = useState(!initialFromState && !noteId);
  const [selectedCamper, setSelectedCamper] = useState(
    initialFromState ? { id: initialFromState.subject_id } : null,
  );
  const [noteRow, setNoteRow] = useState(initialFromState);

  const [body, setBody] = useState(initialFromState?.body ?? '');
  const [category, setCategory] = useState(initialFromState?.category ?? '');
  const [isSensitive, setIsSensitive] = useState(Boolean(initialFromState?.is_sensitive));
  const [flagForCamperCare, setFlagForCamperCare] = useState(
    Boolean(initialFromState?.flag_raised),
  );
  const [language, setLanguage] = useState(initialFromState?.language ?? 'en');

  const [audience, setAudience] = useState([]);
  const [audienceLoading, setAudienceLoading] = useState(true);
  const [fieldErrors, setFieldErrors] = useState({});
  const [submitError, setSubmitError] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [successNote, setSuccessNote] = useState(null);

  const isEditMode = Boolean(noteRow?.id || noteId);
  const editable = noteRow ? isWithinEditWindow(noteRow.created_at) : !isEditMode;
  const flagAlreadyRaised = Boolean(noteRow?.flag_raised);

  const loadAudience = useCallback(async (sensitive) => {
    setAudienceLoading(true);
    try {
      const payload = await fetchSpecialistNoteAudience({ isSensitive: sensitive });
      setAudience(payload.audience || []);
    } catch {
      setAudience([]);
    } finally {
      setAudienceLoading(false);
    }
  }, []);

  useEffect(() => {
    loadAudience(isSensitive);
  }, [isSensitive, loadAudience]);

  const handleCamperSelect = (camper) => {
    setSelectedCamper(camper);
    setShowPicker(false);
  };

  const validate = () => {
    const errs = {};
    if (!body.trim()) errs.body = 'Required.';
    if (!selectedCamper && !noteRow) errs.subject = 'Select a camper first.';
    setFieldErrors(errs);
    return Object.keys(errs).length === 0;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSubmitError('');
    setSuccessNote(null);
    if (!validate()) return;
    setSubmitting(true);
    try {
      if (noteRow?.id) {
        const updated = await patchSpecialistNote(noteRow.id, {
          body: body.trim(),
          category,
          isSensitive,
          language,
        });
        setNoteRow(updated);
        setSuccessNote(updated);
      } else {
        const { data } = await createSpecialistNote({
          subjectId: selectedCamper.id,
          body: body.trim(),
          category,
          isSensitive,
          flagForCamperCare,
          language,
        });
        setNoteRow(data);
        setSuccessNote(data);
        navigate('/specialist', { replace: false });
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
    if (noteRow?.id) return 'Edit specialist note';
    return 'New specialist note';
  }, [noteRow]);

  if (showPicker) {
    return (
      <div className="h-screen flex flex-col bg-white dark:bg-gray-900" data-testid="sp-noteform-picker">
        <header className="px-4 py-3 border-b border-gray-200 dark:border-gray-700 flex items-center gap-3">
          <button
            type="button"
            onClick={() => navigate(-1)}
            className="text-sm text-gray-500 dark:text-gray-400"
          >
            ← Back
          </button>
          <h1 className="text-lg font-semibold text-gray-900 dark:text-white">Select camper</h1>
        </header>
        <CamperPicker onSelect={handleCamperSelect} onCancel={() => navigate(-1)} />
      </div>
    );
  }

  if (isEditMode && !noteRow) {
    return (
      <div className="px-4 py-6 max-w-lg mx-auto space-y-3">
        <h1 className="text-2xl font-semibold text-gray-900 dark:text-white">Edit specialist note</h1>
        <div
          role="alert"
          className="rounded-xl border border-amber-200 bg-amber-50 dark:border-amber-900 dark:bg-amber-900/30 px-4 py-3 text-sm text-amber-900 dark:text-amber-100"
          data-testid="sp-noteform-missing-state"
        >
          This page must be opened from the note success screen or the camper view edit link.
        </div>
        <Link
          to="/specialist"
          className="inline-flex items-center px-3 min-h-[40px] rounded-lg border border-gray-300 dark:border-gray-700 text-sm text-gray-800 dark:text-gray-100"
        >
          Back to dashboard
        </Link>
      </div>
    );
  }

  const formDisabled = isEditMode && !editable;

  return (
    <div className="px-4 py-6 pb-32 max-w-lg mx-auto" data-testid="sp-noteform">
      <header className="mb-3">
        <h1 className="text-2xl font-semibold text-gray-900 dark:text-white">{heading}</h1>
        {selectedCamper && (
          <div className="flex items-center gap-2 mt-1">
            <p className="text-sm text-gray-600 dark:text-gray-400">
              {selectedCamper.display_name ||
                [selectedCamper.first_name, selectedCamper.last_name].filter(Boolean).join(' ')}
              {selectedCamper.bunk_name && ` · ${selectedCamper.bunk_name}`}
            </p>
            {!isEditMode && (
              <button
                type="button"
                onClick={() => setShowPicker(true)}
                className="text-xs text-blue-600 dark:text-blue-400 hover:underline"
              >
                Change
              </button>
            )}
          </div>
        )}
        {formDisabled && (
          <p className="text-sm text-amber-700 dark:text-amber-200 mt-1" data-testid="sp-noteform-window-closed">
            This note is past the 24-hour edit window and can no longer be changed.
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
              : 'Non-sensitive notes are visible to Counselors, Unit Heads, Camper Care, Leadership Team, and Admin.'
        }
      />

      <form onSubmit={handleSubmit} className="space-y-4 mt-4" data-testid="sp-noteform-form">
        <FieldRow
          label="Body"
          htmlFor="sp-note-body"
          required
          error={fieldErrors.body}
          hint="A sentence or two is fine."
        >
          <textarea
            id="sp-note-body"
            value={body}
            onChange={(e) => setBody(e.target.value)}
            rows={5}
            disabled={formDisabled || submitting}
            data-testid="sp-noteform-body"
            className="mt-1 block w-full rounded-md border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:ring-2 focus:ring-blue-200"
          />
        </FieldRow>

        <FieldRow label="Category" htmlFor="sp-note-category" error={fieldErrors.category}>
          <select
            id="sp-note-category"
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            disabled={formDisabled || submitting}
            data-testid="sp-noteform-category"
            className="mt-1 block w-full rounded-md border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 px-3 py-2 text-sm"
          >
            <option value="">None</option>
            {SPECIALIST_NOTE_CATEGORIES.map((c) => (
              <option key={c.value} value={c.value}>{c.label}</option>
            ))}
          </select>
        </FieldRow>

        <fieldset
          className="rounded-lg border border-gray-200 dark:border-gray-700 px-3 py-2 space-y-2"
          data-testid="sp-noteform-visibility-block"
        >
          <legend className="text-sm font-medium text-gray-800 dark:text-gray-100 px-1">Visibility & flags</legend>

          <label className="flex items-start gap-2 text-sm cursor-pointer">
            <input
              type="checkbox"
              checked={isSensitive}
              onChange={(e) => setIsSensitive(e.target.checked)}
              disabled={formDisabled || submitting}
              data-testid="sp-noteform-sensitive"
              className="mt-1 h-4 w-4 rounded border-gray-300"
            />
            <span className="text-gray-700 dark:text-gray-200">
              Sensitive — restrict to Camper Care, Health Center, Special Diets, and Admin.
            </span>
          </label>

          <label className="flex items-start gap-2 text-sm cursor-pointer">
            <input
              type="checkbox"
              checked={flagForCamperCare}
              onChange={(e) => setFlagForCamperCare(e.target.checked)}
              disabled={formDisabled || submitting || flagAlreadyRaised}
              data-testid="sp-noteform-flag"
              className="mt-1 h-4 w-4 rounded border-gray-300"
            />
            <span className="text-gray-700 dark:text-gray-200">
              Flag for Camper Care
              {flagAlreadyRaised && (
                <span className="ml-1 text-xs text-gray-400 dark:text-gray-500">(raised — cannot retract)</span>
              )}
            </span>
          </label>
        </fieldset>

        <FieldRow label="Language" htmlFor="sp-note-language">
          <select
            id="sp-note-language"
            value={language}
            onChange={(e) => setLanguage(e.target.value)}
            disabled={formDisabled || submitting}
            data-testid="sp-noteform-language"
            className="mt-1 block w-full rounded-md border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 px-3 py-2 text-sm"
          >
            <option value="en">English</option>
            <option value="es">Spanish</option>
          </select>
        </FieldRow>

        {fieldErrors.subject && (
          <p role="alert" className="text-sm text-red-700 dark:text-red-300">{fieldErrors.subject}</p>
        )}
        {submitError && (
          <p role="alert" className="text-sm text-red-700 dark:text-red-300" data-testid="sp-noteform-error">
            {submitError}
          </p>
        )}
        {successNote && (
          <div
            role="status"
            className="rounded-md border border-green-200 bg-green-50 dark:border-green-800 dark:bg-green-900/30 px-3 py-2 text-sm text-green-900 dark:text-green-100"
            data-testid="sp-noteform-success"
          >
            Note {noteRow?.id ? 'updated' : 'added'}.
          </div>
        )}

        <div className="fixed bottom-0 left-0 right-0 bg-white dark:bg-gray-900 border-t border-gray-200 dark:border-gray-700 px-4 py-3 flex items-center justify-end gap-2 max-w-lg mx-auto">
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
            data-testid="sp-noteform-submit"
            className="inline-flex items-center px-4 min-h-[44px] rounded-lg bg-blue-600 text-white text-sm font-medium hover:bg-blue-700 disabled:opacity-60"
          >
            {submitting ? 'Saving…' : (noteRow?.id ? 'Save changes' : 'Add note')}
          </button>
        </div>
      </form>
    </div>
  );
}
