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
import { QuantityStepper } from '../../components/counselor/RequestFormControls';
import {
  MAINTENANCE_URGENCY_CHOICES,
  createMaintenanceTicket,
  fetchMaintenanceOptions,
  newClientSubmissionId,
} from '../../api/counselor';

// Fallback categories when no catalog is configured for the org/program, so
// the form still works. Mirrors the legacy MaintenanceTicket.Category enum;
// these values remain valid server-side for back-compat.
const LEGACY_CATEGORY_FALLBACK = [
  { value: 'plumbing', label: 'Clogged plumbing' },
  { value: 'broken_light', label: 'Broken light' },
  { value: 'pest', label: 'Pest / Insect' },
  { value: 'leak', label: 'Leak' },
  { value: 'other', label: 'Other' },
];

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

  // Catalog-driven options (Step 7_catalog). Services populate the category
  // picker; consumables get optional quantity inputs sent as line_items.
  const [serviceItems, setServiceItems] = useState([]);
  const [consumableItems, setConsumableItems] = useState([]);
  const [consumableQty, setConsumableQty] = useState({});

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

  useEffect(() => {
    let active = true;
    fetchMaintenanceOptions()
      .then((data) => {
        if (!active) return;
        const services = [];
        const consumables = [];
        for (const rt of data?.request_types || []) {
          for (const it of rt.items || []) {
            if (it.track_quantity) consumables.push(it);
            else services.push(it);
          }
        }
        setServiceItems(services);
        setConsumableItems(consumables);
      })
      .catch(() => {
        // No catalog configured / offline: fall back to legacy categories.
        setServiceItems([]);
        setConsumableItems([]);
      });
    return () => { active = false; };
  }, []);

  const categoryOptions = useMemo(() => {
    if (serviceItems.length) {
      return serviceItems.map((it) => ({ value: it.label, label: it.label }));
    }
    return LEGACY_CATEGORY_FALLBACK;
  }, [serviceItems]);

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

    const lineItems = consumableItems
      .map((it) => ({ item_id: it.id, quantity: Number(consumableQty[it.id]) || 0 }))
      .filter((li) => li.quantity > 0);

    setSubmitting(true);
    try {
      await createMaintenanceTicket({
        location: location.trim(),
        category,
        description: description.trim(),
        urgency,
        urgentReason: urgency === 'urgent' ? urgentReason.trim() : '',
        photos,
        lineItems,
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
    <div className="px-4 sm:px-6 lg:px-8 py-8 pb-28 w-full max-w-2xl mx-auto">
        <header className="mb-6">
          <button
            type="button"
            onClick={() => navigate('/counselor')}
            className="text-xs text-blue-600 dark:text-blue-400 mb-1 flex items-center gap-1"
          >
            ← Back to dashboard
          </button>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
            New Maintenance ticket
          </h1>
          <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
            Goes to the Maintenance team. Photos help triage faster.
          </p>
        </header>

        <form
          onSubmit={handleSubmit}
          data-testid="maintenance-form"
          encType="multipart/form-data"
        >
          <div className="rounded-2xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-5 sm:p-6 space-y-4 shadow-sm">
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
              {categoryOptions.map((c) => (
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

          {consumableItems.length ? (
            <fieldset
              data-testid="maintenance-supplies-group"
              className="rounded-lg border border-gray-200 dark:border-gray-700 px-3 py-3"
            >
              <legend className="text-xs font-medium text-gray-600 dark:text-gray-400 px-1">
                Supplies needed (optional)
              </legend>
              <div className="space-y-2 mt-1">
                {consumableItems.map((it) => (
                  <div key={it.id} className="flex items-center justify-between gap-3">
                    <span className="text-sm text-gray-800 dark:text-gray-200">
                      {it.label}
                      {it.unit ? (
                        <span className="text-gray-500 dark:text-gray-400"> ({it.unit})</span>
                      ) : null}
                    </span>
                    <QuantityStepper
                      value={consumableQty[it.id] ?? '0'}
                      min={0}
                      ariaLabel={`Quantity for ${it.label}`}
                      testId={`maintenance-supply-${it.id}`}
                      onChange={(q) =>
                        setConsumableQty((prev) => ({ ...prev, [it.id]: q }))
                      }
                    />
                  </div>
                ))}
              </div>
            </fieldset>
          ) : null}

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
          </div>

          <div className="sticky bottom-0 z-20 mt-4 -mx-4 sm:mx-0 border-t border-gray-200 dark:border-gray-700 bg-white/95 dark:bg-gray-900/95 backdrop-blur px-4 py-3 sm:static sm:border-0 sm:bg-transparent sm:dark:bg-transparent sm:px-0 sm:py-0 sm:backdrop-blur-none">
            <button
              type="submit"
              disabled={submitting}
              data-testid="maintenance-submit"
              className="w-full sm:w-auto min-h-[48px] px-6 rounded-lg bg-blue-600 text-white font-medium text-sm hover:bg-blue-700 disabled:opacity-50 transition-colors"
            >
              {submitting ? 'Submitting…' : 'Submit ticket'}
            </button>
          </div>
        </form>
    </div>
  );
}
