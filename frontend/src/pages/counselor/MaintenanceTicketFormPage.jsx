/**
 * Maintenance ticket form — Step 7_6f (Story 8).
 *
 * URL:  /counselor/requests/maintenance/new
 *
 * Submission is multipart/form-data so we can attach photos in the same
 * round-trip (Story 8 criterion 1.iv). ``urgency=urgent`` unlocks an
 * ``urgent_reason`` textarea which the server enforces via
 * ``MaintenanceTicket.clean()`` (Story 8 criterion 2); we mirror that
 * client-side so the user sees the requirement before hitting submit.
 *
 * Photo handling notes:
 *   * We add a small per-file preview tile so it's obvious which photos
 *     the form is about to send. Each tile has a "Remove" affordance.
 *   * No client-side resize (keeping scope tight for 7_6f). Modern
 *     mobile cameras land around 3-6MB per HEIC/JPEG which the API
 *     accepts; if it ends up being a problem we can add resize in a
 *     follow-up.
 *   * Object URLs are revoked when files change so we don't leak.
 */

import { useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useCounselorDraft } from '../../hooks/useCounselorDraft';
import { isQueuedSubmissionError } from '../../lib/submissionQueue/queue';
import { maintenanceDraftKey } from '../../utils/counselor/counselorDraftStorage';
import {
  MAINTENANCE_CATEGORIES,
  MAINTENANCE_URGENCY_CHOICES,
  createMaintenanceTicket,
  newClientSubmissionId,
} from '../../api/counselor';

function flattenError(err, fallback) {
  const body = err?.response?.data;
  if (!body) return err?.message || fallback;
  if (typeof body === 'string') return body;
  if (typeof body.detail === 'string') return body.detail;
  if (typeof body === 'object') {
    try {
      return JSON.stringify(body);
    } catch (_) {
      return fallback;
    }
  }
  return fallback;
}

function PhotoTile({ file, onRemove }) {
  const url = useMemo(() => URL.createObjectURL(file), [file]);
  useEffect(() => () => URL.revokeObjectURL(url), [url]);
  return (
    <div
      data-testid="maintenance-photo-tile"
      className="relative w-20 h-20 rounded-lg overflow-hidden border border-gray-200 dark:border-gray-700"
    >
      <img
        src={url}
        alt={file.name}
        className="w-full h-full object-cover"
      />
      <button
        type="button"
        onClick={onRemove}
        aria-label={`Remove ${file.name}`}
        data-testid="maintenance-photo-remove"
        className="absolute top-0 right-0 bg-black/60 text-white text-xs px-1.5 py-0.5 rounded-bl-md"
      >
        ✕
      </button>
    </div>
  );
}

export default function MaintenanceTicketFormPage() {
  const navigate = useNavigate();

  const [location, setLocation] = useState('');
  const [category, setCategory] = useState('');
  const [description, setDescription] = useState('');
  const [urgency, setUrgency] = useState('normal');
  const [urgentReason, setUrgentReason] = useState('');
  const [photos, setPhotos] = useState([]);

  const [fieldErrors, setFieldErrors] = useState({});
  const [submitError, setSubmitError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const clientSubmissionIdRef = useRef(null);
  if (clientSubmissionIdRef.current === null) {
    clientSubmissionIdRef.current = newClientSubmissionId();
  }
  const fileInputRef = useRef(null);

  const { clearDraft } = useCounselorDraft({
    draftKey: maintenanceDraftKey(clientSubmissionIdRef.current),
    getSnapshot: () => ({
      location,
      category,
      description,
      urgency,
      urgentReason,
      clientSubmissionId: clientSubmissionIdRef.current,
    }),
    onRestore: (saved) => {
      if (saved.location) setLocation(saved.location);
      if (saved.category) setCategory(saved.category);
      if (saved.description) setDescription(saved.description);
      if (saved.urgency) setUrgency(saved.urgency);
      if (saved.urgentReason) setUrgentReason(saved.urgentReason);
      if (saved.clientSubmissionId) {
        clientSubmissionIdRef.current = saved.clientSubmissionId;
      }
    },
  });

  const handlePhotosChosen = (e) => {
    const next = Array.from(e.target.files || []);
    if (next.length === 0) return;
    setPhotos((prev) => [...prev, ...next]);
    // Reset the input value so the user can pick the same file twice if
    // they want; otherwise the change event won't fire on re-select.
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const removePhoto = (index) => {
    setPhotos((prev) => prev.filter((_, i) => i !== index));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSubmitError('');
    const errs = {};
    if (!location.trim()) errs.location = 'Location is required.';
    if (!category) errs.category = 'Pick a category.';
    if (urgency === 'urgent' && !urgentReason.trim()) {
      // Mirror MaintenanceTicket.clean() (Story 8 criterion 2).
      errs.urgent_reason = 'Required when this is urgent.';
    }
    setFieldErrors(errs);
    if (Object.keys(errs).length) return;

    setSubmitting(true);
    try {
      await createMaintenanceTicket({
        location: location.trim(),
        category,
        description: description.trim(),
        urgency,
        urgentReason: urgency === 'urgent' ? urgentReason.trim() : '',
        photos,
        clientSubmissionId: clientSubmissionIdRef.current,
      });
      clearDraft();
      navigate('/counselor?nocache=1', { replace: true });
    } catch (err) {
      if (isQueuedSubmissionError(err)) {
        clearDraft();
        navigate('/counselor?nocache=1', { replace: true });
        return;
      }
      const status = err?.response?.status;
      if (status === 400) {
        const body = err?.response?.data;
        if (body && typeof body === 'object' && !Array.isArray(body)) {
          const next = {};
          for (const k of Object.keys(body)) {
            if (k === 'detail') continue;
            const v = body[k];
            next[k] = Array.isArray(v) ? v[0] : typeof v === 'string' ? v : JSON.stringify(v);
          }
          setFieldErrors(next);
          setSubmitError(
            typeof body.detail === 'string'
              ? body.detail
              : 'Please fix the errors and try again.',
          );
        } else {
          setSubmitError(flattenError(err, 'Submit failed.'));
        }
      } else {
        setSubmitError(flattenError(err, 'Submit failed.'));
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="px-4 sm:px-6 lg:px-8 py-8 pb-24 w-full max-w-[96rem] mx-auto">
        <header className="mb-6">
          <button
            type="button"
            onClick={() => navigate('/counselor')}
            className="text-xs text-blue-600 dark:text-blue-400 mb-1 flex items-center gap-1"
          >
            ← Back to dashboard
          </button>
          <h1 className="text-xl font-semibold text-gray-900 dark:text-white">
            New Maintenance ticket
          </h1>
          <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
            Goes to the Maintenance team. Photos help triage faster.
          </p>
        </header>

        <form
          onSubmit={handleSubmit}
          className="space-y-4"
          data-testid="maintenance-form"
          encType="multipart/form-data"
        >
          <div>
            <label
              htmlFor="mt-location"
              className="block text-sm font-medium text-gray-700 dark:text-gray-200 mb-1"
            >
              Location *
            </label>
            <input
              id="mt-location"
              data-testid="maintenance-location"
              value={location}
              onChange={(e) => setLocation(e.target.value)}
              placeholder="Bunk Pine, dining hall, …"
              required
              className="block w-full min-h-[44px] rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm text-gray-900 dark:text-gray-100"
            />
            {fieldErrors.location ? (
              <p className="mt-1 text-xs text-red-600" role="alert">
                {fieldErrors.location}
              </p>
            ) : null}
          </div>

          <div>
            <label
              htmlFor="mt-category"
              className="block text-sm font-medium text-gray-700 dark:text-gray-200 mb-1"
            >
              Category *
            </label>
            <select
              id="mt-category"
              data-testid="maintenance-category"
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              required
              className="block w-full min-h-[44px] rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm text-gray-900 dark:text-gray-100"
            >
              <option value="">— pick one —</option>
              {MAINTENANCE_CATEGORIES.map((c) => (
                <option key={c.value} value={c.value}>{c.label}</option>
              ))}
            </select>
            {fieldErrors.category ? (
              <p className="mt-1 text-xs text-red-600" role="alert">
                {fieldErrors.category}
              </p>
            ) : null}
          </div>

          <fieldset
            data-testid="maintenance-urgency-group"
            className="rounded-lg border border-gray-200 dark:border-gray-700 px-3 py-3"
          >
            <legend className="text-xs font-medium text-gray-600 dark:text-gray-400 px-1">
              Urgency
            </legend>
            <div className="flex gap-3 mt-1">
              {MAINTENANCE_URGENCY_CHOICES.map((u) => (
                <label
                  key={u.value}
                  className="flex items-center gap-2 cursor-pointer text-sm text-gray-800 dark:text-gray-200"
                >
                  <input
                    type="radio"
                    name="urgency"
                    value={u.value}
                    checked={urgency === u.value}
                    onChange={() => setUrgency(u.value)}
                    data-testid={`maintenance-urgency-${u.value}`}
                    className="h-4 w-4 text-blue-600 focus:ring-blue-500"
                  />
                  {u.label}
                </label>
              ))}
            </div>
            {urgency === 'urgent' ? (
              <div className="mt-3">
                <label
                  htmlFor="mt-urgent-reason"
                  className="block text-sm font-medium text-gray-700 dark:text-gray-200 mb-1"
                >
                  Why is this urgent? *
                </label>
                <textarea
                  id="mt-urgent-reason"
                  data-testid="maintenance-urgent-reason"
                  rows={3}
                  value={urgentReason}
                  onChange={(e) => setUrgentReason(e.target.value)}
                  placeholder="What's at stake if this waits?"
                  className="block w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm text-gray-900 dark:text-gray-100"
                />
                {fieldErrors.urgent_reason ? (
                  <p className="mt-1 text-xs text-red-600" role="alert">
                    {fieldErrors.urgent_reason}
                  </p>
                ) : null}
              </div>
            ) : null}
          </fieldset>

          <div>
            <label
              htmlFor="mt-description"
              className="block text-sm font-medium text-gray-700 dark:text-gray-200 mb-1"
            >
              Description
            </label>
            <textarea
              id="mt-description"
              data-testid="maintenance-description"
              rows={4}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="What's broken, where to look, anything Maintenance needs to know."
              className="block w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm text-gray-900 dark:text-gray-100"
            />
          </div>

          <div>
            <span className="block text-sm font-medium text-gray-700 dark:text-gray-200 mb-1">
              Photos
            </span>
            <div className="flex flex-wrap items-center gap-2">
              {photos.map((file, index) => (
                <PhotoTile
                  key={`${file.name}-${file.lastModified}-${index}`}
                  file={file}
                  onRemove={() => removePhoto(index)}
                />
              ))}
              <label
                htmlFor="mt-photo-input"
                data-testid="maintenance-photo-add"
                className="w-20 h-20 rounded-lg border-2 border-dashed border-gray-300 dark:border-gray-600 flex items-center justify-center text-xs text-gray-500 dark:text-gray-400 cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800"
              >
                + Photo
              </label>
              <input
                id="mt-photo-input"
                data-testid="maintenance-photo-input"
                ref={fileInputRef}
                type="file"
                accept="image/*"
                multiple
                onChange={handlePhotosChosen}
                className="sr-only"
              />
            </div>
            <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
              Tap to add — you can pick multiple at once.
            </p>
          </div>

          {submitError ? (
            <p
              className="text-red-600 text-sm"
              role="alert"
              data-testid="maintenance-submit-error"
            >
              {submitError}
            </p>
          ) : null}

          <button
            type="submit"
            disabled={submitting}
            data-testid="maintenance-submit"
            className="w-full sm:w-auto mt-4 min-h-[48px] px-6 rounded-lg bg-blue-600 text-white font-medium text-sm disabled:opacity-50"
          >
            {submitting ? 'Submitting…' : 'Submit ticket'}
          </button>
        </form>
    </div>
  );
}
