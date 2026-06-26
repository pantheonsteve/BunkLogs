/**
 * Camper Care request form — Step 7_6f (Story 7).
 *
 * URL:  /counselor/requests/camper-care/new
 *
 * Two pickers up top:
 *   * camper (optional) — populated from the dashboard's bunk roster.
 *     Counselors can leave this blank to file a bunk-scoped request.
 *   * item — free text with a datalist of curated suggestions
 *     (Story 7 criterion 2.ii, decision C6). An empty suggestion list
 *     just disables autocomplete; the field stays free-text.
 *
 * On submit POSTs ``/api/v1/counselor/camper-care-requests/`` with a
 * stable ``client_submission_id`` so the offline queue can replay
 * safely. On success we land back on the requests list (the dashboard's
 * "Open Requests" section also picks up the row within 60s via the
 * existing auto-refresh).
 */

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { Plus, Trash2 } from 'lucide-react';
import { useCounselorDraft } from '../../hooks/useCounselorDraft';
import { isQueuedSubmissionError } from '../../lib/submissionQueue/queue';
import { camperCareDraftKey } from '../../utils/counselor/counselorDraftStorage';
import { ItemCombobox, QuantityStepper } from '../../components/counselor/RequestFormControls';
import {
  createCamperCareRequest,
  fetchCamperCareItemSuggestions,
  fetchCamperCareRequestDetail,
  fetchCamperReflections,
  newClientSubmissionId,
  patchCamperCareRequest,
} from '../../api/counselor';

const QUICK_PICK_LIMIT = 8;

function newLine() {
  return { label: '', itemId: undefined, quantity: '1', note: '' };
}

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

function flattenCamperRoster(camperReflections) {
  // The roster source is the camper-reflections endpoint — same data the
  // dashboard counts but with per-camper records (the dashboard's
  // sections.campers only returns aggregates). Including off-camp campers
  // here is intentional: it's fine to file a Camper Care request for an
  // off-camp camper since the need (toiletries, supplies) often spans
  // their entire stay.
  const bunks = camperReflections?.bunks || [];
  const seen = new Set();
  const rows = [];
  for (const bunk of bunks) {
    const onCamp = bunk.campers || [];
    const offCamp = bunk.off_camp || [];
    for (const camper of [...onCamp, ...offCamp]) {
      if (seen.has(camper.id)) continue;
      seen.add(camper.id);
      rows.push({
        id: camper.id,
        name: camper.name,
        bunkName: bunk.name,
        bunkId: bunk.id,
      });
    }
  }
  rows.sort((a, b) => {
    if (a.bunkName !== b.bunkName) return a.bunkName.localeCompare(b.bunkName);
    return a.name.localeCompare(b.name);
  });
  return rows;
}

export default function CamperCareRequestFormPage() {
  const navigate = useNavigate();
  const { orderId } = useParams();
  const isEdit = Boolean(orderId);

  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState('');
  const [campers, setCampers] = useState([]);
  const [suggestions, setSuggestions] = useState([]);

  const [subjectId, setSubjectId] = useState('');
  const [bunkId, setBunkId] = useState('');
  const [lines, setLines] = useState([newLine()]);
  const [description, setDescription] = useState('');

  const [fieldErrors, setFieldErrors] = useState({});
  const [submitError, setSubmitError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const clientSubmissionIdRef = useRef(null);
  if (clientSubmissionIdRef.current === null) {
    clientSubmissionIdRef.current = newClientSubmissionId();
  }

  const { clearDraft } = useCounselorDraft({
    draftKey: isEdit ? null : camperCareDraftKey(clientSubmissionIdRef.current),
    getSnapshot: () => ({
      subjectId,
      bunkId,
      lines,
      description,
      clientSubmissionId: clientSubmissionIdRef.current,
    }),
    onRestore: (saved) => {
      if (isEdit) return;
      if (saved.subjectId != null && saved.subjectId !== '') {
        setSubjectId(String(saved.subjectId));
      }
      if (saved.bunkId != null && saved.bunkId !== '') {
        setBunkId(String(saved.bunkId));
      }
      if (Array.isArray(saved.lines) && saved.lines.length) {
        setLines(saved.lines.map((l) => ({ ...newLine(), ...l })));
      } else if (saved.item) {
        // Back-compat with single-item drafts saved before the line builder.
        setLines([{ ...newLine(), label: saved.item, note: saved.itemNote || '' }]);
      }
      if (saved.description) setDescription(saved.description);
      if (saved.clientSubmissionId) {
        clientSubmissionIdRef.current = saved.clientSubmissionId;
      }
    },
  });

  const load = useCallback(async () => {
    setLoading(true);
    setLoadError('');
    try {
      const [camperReflections, suggestionPayload, existing] = await Promise.all([
        fetchCamperReflections(),
        fetchCamperCareItemSuggestions().catch((err) => {
          // eslint-disable-next-line no-console
          console.warn('camper-care suggestions failed:', err);
          return { suggestions: [] };
        }),
        isEdit ? fetchCamperCareRequestDetail(orderId) : Promise.resolve(null),
      ]);
      setCampers(flattenCamperRoster(camperReflections));
      setSuggestions(suggestionPayload?.suggestions || []);
      if (isEdit) {
        const order = existing?.order;
        if (!order?.editable) {
          setLoadError('This request can no longer be edited.');
          return;
        }
        setSubjectId(order.subject?.id ? String(order.subject.id) : '');
        setLines([{ ...newLine(), label: order.item || '', note: order.item_note || '' }]);
        setDescription(order.description || '');
      }
    } catch (err) {
      setLoadError(flattenError(err, 'Could not load the form.'));
    } finally {
      setLoading(false);
    }
  }, [isEdit, orderId]);

  useEffect(() => {
    load();
  }, [load]);

  const comboOptions = useMemo(
    () => suggestions
      .filter((s) => s.label)
      .map((s) => ({ id: s.id, label: s.label, unit: s.unit || '' })),
    [suggestions],
  );

  const quickPicks = useMemo(
    () => comboOptions.slice(0, QUICK_PICK_LIMIT),
    [comboOptions],
  );

  const updateLine = (index, patch) => {
    setLines((prev) => prev.map((l, i) => (i === index ? { ...l, ...patch } : l)));
  };

  const addLine = () => setLines((prev) => [...prev, newLine()]);

  const removeLine = (index) => {
    setLines((prev) => (prev.length <= 1 ? prev : prev.filter((_, i) => i !== index)));
  };

  const addQuickPick = (opt) => {
    setLines((prev) => {
      const emptyIdx = prev.findIndex((l) => !l.label.trim());
      if (emptyIdx >= 0) {
        return prev.map((l, i) =>
          i === emptyIdx ? { ...l, label: opt.label, itemId: opt.id } : l);
      }
      return [...prev, { ...newLine(), label: opt.label, itemId: opt.id }];
    });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSubmitError('');
    const validLines = lines.filter((l) => l.label.trim());
    const errs = {};
    if (validLines.length === 0) errs.item = 'Add at least one item.';
    setFieldErrors(errs);
    if (Object.keys(errs).length) return;

    const first = validLines[0];
    setSubmitting(true);
    try {
      if (isEdit) {
        await patchCamperCareRequest(orderId, {
          subjectId: subjectId ? Number(subjectId) : null,
          bunkId: bunkId ? Number(bunkId) : null,
          item: first.label.trim(),
          itemNote: (first.note || '').trim(),
          description: description.trim(),
        });
        navigate(`/counselor/requests/camper-care/${orderId}`, { replace: true });
      } else {
        const lineItems = validLines.map((l) => ({
          item_id: l.itemId ? Number(l.itemId) : undefined,
          item_label: l.label.trim(),
          quantity: Number(l.quantity) || 1,
          note: (l.note || '').trim(),
        }));
        await createCamperCareRequest({
          subjectId: subjectId ? Number(subjectId) : null,
          bunkId: bunkId ? Number(bunkId) : null,
          // Mirror the first line into the legacy single-item fields so
          // existing Camper Care consumers keep working.
          item: first.label.trim(),
          itemNote: (first.note || '').trim(),
          description: description.trim(),
          lineItems,
          clientSubmissionId: clientSubmissionIdRef.current,
        });
        clearDraft();
        navigate('/counselor?nocache=1', { replace: true });
      }
    } catch (err) {
      if (!isEdit && isQueuedSubmissionError(err)) {
        clearDraft();
        navigate('/counselor?nocache=1', { replace: true });
        return;
      }
      const status = err?.response?.status;
      if (status === 403) {
        setSubmitError(
          flattenError(err, 'You can only file a request for a camper on your bunk.'),
        );
      } else if (status === 400) {
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
            onClick={() => navigate(isEdit ? `/counselor/requests/camper-care/${orderId}` : '/counselor')}
            className="text-xs text-blue-600 dark:text-blue-400 mb-1 flex items-center gap-1"
          >
            ← {isEdit ? 'Back to request' : 'Back to dashboard'}
          </button>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
            {isEdit ? 'Edit Camper Care request' : 'New Camper Care request'}
          </h1>
          <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
            {isEdit
              ? 'You can update this request while it is still New.'
              : "Goes to the Camper Care team. They'll see who it's for and what's needed; you can leave the camper blank for a bunk-wide need."}
          </p>
        </header>

        {loading ? (
          <p
            className="text-gray-600 dark:text-gray-400"
            data-testid="camper-care-loading"
          >
            Loading…
          </p>
        ) : loadError ? (
          <div
            className="rounded-lg border border-amber-200 bg-amber-50 dark:bg-amber-950/40 dark:border-amber-800 px-4 py-3 text-sm text-amber-900 dark:text-amber-100"
            role="alert"
            data-testid="camper-care-load-error"
          >
            {loadError}
          </div>
        ) : (
          <form
            onSubmit={handleSubmit}
            data-testid="camper-care-form"
          >
            <div className="rounded-2xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-5 sm:p-6 space-y-5 shadow-sm">
              <div>
                <label
                  htmlFor="cc-subject"
                  className="block text-sm font-medium text-gray-700 dark:text-gray-200 mb-1"
                >
                  Camper (optional)
                </label>
                <select
                  id="cc-subject"
                  data-testid="camper-care-subject"
                  value={subjectId}
                  onChange={(e) => {
                    const nextId = e.target.value;
                    setSubjectId(nextId);
                    const row = campers.find((c) => String(c.id) === nextId);
                    setBunkId(row?.bunkId ? String(row.bunkId) : '');
                  }}
                  className="block w-full min-h-[44px] rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm text-gray-900 dark:text-gray-100"
                >
                  <option value="">— bunk-wide / no specific camper —</option>
                  {campers.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.name} ({c.bunkName})
                    </option>
                  ))}
                </select>
                {fieldErrors.subject_id ? (
                  <p className="mt-1 text-xs text-red-600" role="alert">
                    {fieldErrors.subject_id}
                  </p>
                ) : null}
              </div>

              <div className="border-t border-gray-100 dark:border-gray-800 pt-5">
                <div className="flex items-baseline justify-between mb-1">
                  <span className="block text-sm font-medium text-gray-700 dark:text-gray-200">
                    Items *
                  </span>
                  <span className="text-xs text-gray-400">What do you need?</span>
                </div>

                {!isEdit && quickPicks.length > 0 ? (
                  <div className="flex flex-wrap gap-2 mb-3" data-testid="camper-care-quick-picks">
                    {quickPicks.map((opt, i) => (
                      <button
                        key={opt.id ?? opt.label}
                        type="button"
                        onClick={() => addQuickPick(opt)}
                        data-testid={`camper-care-chip-${i}`}
                        className="inline-flex items-center gap-1 rounded-full border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-1.5 text-xs text-gray-700 dark:text-gray-200 hover:border-blue-400 hover:text-blue-700 dark:hover:text-blue-300 transition-colors"
                      >
                        <Plus size={12} /> {opt.label}
                      </button>
                    ))}
                  </div>
                ) : null}

                <div className="space-y-3">
                  {lines.map((line, i) => (
                    <div
                      key={i}
                      data-testid={`camper-care-line-${i}`}
                      className="rounded-xl border border-gray-200 dark:border-gray-700 p-3 sm:p-4 bg-gray-50/60 dark:bg-gray-800/40"
                    >
                      <div className="flex flex-col sm:flex-row sm:items-start gap-3">
                        <div className="flex-1 min-w-0">
                          <ItemCombobox
                            inputId={i === 0 ? 'cc-item' : `cc-item-${i}`}
                            testId={i === 0 ? 'camper-care-item' : `camper-care-item-${i}`}
                            ariaLabel={`Item ${i + 1}`}
                            value={line.label}
                            options={comboOptions}
                            required={i === 0}
                            placeholder="Toothpaste, sunscreen, …"
                            onChange={(label, opt) =>
                              updateLine(i, { label, itemId: opt?.id })}
                          />
                        </div>
                        <div className="flex items-center gap-2">
                          <QuantityStepper
                            value={line.quantity}
                            min={1}
                            ariaLabel={`quantity for item ${i + 1}`}
                            testId={i === 0 ? 'camper-care-quantity' : `camper-care-quantity-${i}`}
                            onChange={(q) => updateLine(i, { quantity: q })}
                          />
                          {!isEdit && lines.length > 1 ? (
                            <button
                              type="button"
                              onClick={() => removeLine(i)}
                              aria-label={`Remove item ${i + 1}`}
                              data-testid={`camper-care-remove-${i}`}
                              className="min-h-[44px] px-2 text-gray-400 hover:text-red-600 dark:hover:text-red-400"
                            >
                              <Trash2 size={16} />
                            </button>
                          ) : null}
                        </div>
                      </div>
                      <input
                        data-testid={i === 0 ? 'camper-care-item-note' : `camper-care-item-note-${i}`}
                        value={line.note}
                        onChange={(e) => updateLine(i, { note: e.target.value })}
                        placeholder="Note for this item (e.g. unscented, size 8)"
                        aria-label={`Note for item ${i + 1}`}
                        className="mt-3 block w-full min-h-[40px] rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm text-gray-900 dark:text-gray-100"
                      />
                    </div>
                  ))}
                </div>

                {fieldErrors.item ? (
                  <p className="mt-2 text-xs text-red-600" role="alert">
                    {fieldErrors.item}
                  </p>
                ) : null}

                {!isEdit ? (
                  <button
                    type="button"
                    onClick={addLine}
                    data-testid="camper-care-add-item"
                    className="mt-3 inline-flex items-center gap-1.5 text-sm font-medium text-blue-600 dark:text-blue-400 hover:underline"
                  >
                    <Plus size={16} /> Add another item
                  </button>
                ) : null}
              </div>

              <div className="border-t border-gray-100 dark:border-gray-800 pt-5">
                <label
                  htmlFor="cc-description"
                  className="block text-sm font-medium text-gray-700 dark:text-gray-200 mb-1"
                >
                  Anything else for the Camper Care team? (optional)
                </label>
                <textarea
                  id="cc-description"
                  data-testid="camper-care-description"
                  rows={3}
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="Context that applies to the whole request — timing, where to deliver, etc."
                  className="block w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm text-gray-900 dark:text-gray-100"
                />
              </div>

              {submitError ? (
                <p
                  className="text-red-600 text-sm"
                  role="alert"
                  data-testid="camper-care-submit-error"
                >
                  {submitError}
                </p>
              ) : null}
            </div>

            <div className="sticky bottom-0 z-20 mt-4 -mx-4 sm:mx-0 border-t border-gray-200 dark:border-gray-700 bg-white/95 dark:bg-gray-900/95 backdrop-blur px-4 py-3 sm:static sm:border-0 sm:bg-transparent sm:dark:bg-transparent sm:px-0 sm:py-0 sm:backdrop-blur-none">
              <button
                type="submit"
                disabled={submitting}
                data-testid="camper-care-submit"
                className="w-full sm:w-auto min-h-[48px] px-6 rounded-lg bg-blue-600 text-white font-medium text-sm hover:bg-blue-700 disabled:opacity-50 transition-colors"
              >
                {submitting ? 'Saving…' : isEdit ? 'Save changes' : 'Send request'}
              </button>
            </div>
          </form>
        )}
    </div>
  );
}
