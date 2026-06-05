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
import { useNavigate } from 'react-router-dom';
import {
  createCamperCareRequest,
  fetchCamperCareItemSuggestions,
  fetchCamperReflections,
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

  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState('');
  const [campers, setCampers] = useState([]);
  const [suggestions, setSuggestions] = useState([]);

  const [subjectId, setSubjectId] = useState('');
  const [bunkId, setBunkId] = useState('');
  const [item, setItem] = useState('');
  const [itemNote, setItemNote] = useState('');
  const [description, setDescription] = useState('');

  const [fieldErrors, setFieldErrors] = useState({});
  const [submitError, setSubmitError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const clientSubmissionIdRef = useRef(null);
  if (clientSubmissionIdRef.current === null) {
    clientSubmissionIdRef.current = newClientSubmissionId();
  }

  const load = useCallback(async () => {
    setLoading(true);
    setLoadError('');
    try {
      const [camperReflections, suggestionPayload] = await Promise.all([
        fetchCamperReflections(),
        fetchCamperCareItemSuggestions().catch((err) => {
          // Suggestions endpoint failure is non-fatal — the form still
          // works as free text. Log but don't block.
          // eslint-disable-next-line no-console
          console.warn('camper-care suggestions failed:', err);
          return { suggestions: [] };
        }),
      ]);
      setCampers(flattenCamperRoster(camperReflections));
      setSuggestions(suggestionPayload?.suggestions || []);
    } catch (err) {
      setLoadError(flattenError(err, 'Could not load the form.'));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const datalistOptions = useMemo(
    () => suggestions.map((s) => s.label).filter(Boolean),
    [suggestions],
  );

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSubmitError('');
    const errs = {};
    if (!item.trim()) errs.item = 'An item is required.';
    setFieldErrors(errs);
    if (Object.keys(errs).length) return;

    setSubmitting(true);
    try {
      await createCamperCareRequest({
        subjectId: subjectId ? Number(subjectId) : null,
        bunkId: bunkId ? Number(bunkId) : null,
        item: item.trim(),
        itemNote: itemNote.trim(),
        description: description.trim(),
        clientSubmissionId: clientSubmissionIdRef.current,
      });
      navigate('/counselor/requests', { replace: true });
    } catch (err) {
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
            New Camper Care request
          </h1>
          <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
            Goes to the Camper Care team. They'll see who it's for and what's
            needed; you can leave the camper blank for a bunk-wide need.
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
            className="space-y-4"
            data-testid="camper-care-form"
          >
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

            <div>
              <label
                htmlFor="cc-item"
                className="block text-sm font-medium text-gray-700 dark:text-gray-200 mb-1"
              >
                Item *
              </label>
              <input
                id="cc-item"
                data-testid="camper-care-item"
                value={item}
                onChange={(e) => setItem(e.target.value)}
                list={datalistOptions.length ? 'camper-care-item-options' : undefined}
                required
                placeholder="Toothpaste, sunscreen, …"
                className="block w-full min-h-[44px] rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm text-gray-900 dark:text-gray-100"
              />
              {datalistOptions.length ? (
                <datalist id="camper-care-item-options">
                  {datalistOptions.map((label) => (
                    <option key={label} value={label} />
                  ))}
                </datalist>
              ) : null}
              {fieldErrors.item ? (
                <p className="mt-1 text-xs text-red-600" role="alert">
                  {fieldErrors.item}
                </p>
              ) : null}
            </div>

            <div>
              <label
                htmlFor="cc-item-note"
                className="block text-sm font-medium text-gray-700 dark:text-gray-200 mb-1"
              >
                Item note
              </label>
              <input
                id="cc-item-note"
                data-testid="camper-care-item-note"
                value={itemNote}
                onChange={(e) => setItemNote(e.target.value)}
                placeholder="e.g. unscented, size 8…"
                className="block w-full min-h-[44px] rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm text-gray-900 dark:text-gray-100"
              />
            </div>

            <div>
              <label
                htmlFor="cc-description"
                className="block text-sm font-medium text-gray-700 dark:text-gray-200 mb-1"
              >
                Notes for Camper Care
              </label>
              <textarea
                id="cc-description"
                data-testid="camper-care-description"
                rows={4}
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Anything Camper Care should know to help."
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

            <button
              type="submit"
              disabled={submitting}
              data-testid="camper-care-submit"
              className="w-full sm:w-auto mt-4 min-h-[48px] px-6 rounded-lg bg-blue-600 text-white font-medium text-sm disabled:opacity-50"
            >
              {submitting ? 'Sending…' : 'Send request'}
            </button>
          </form>
        )}
    </div>
  );
}
