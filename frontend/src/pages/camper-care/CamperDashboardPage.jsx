/**
 * Camper Care Camper Dashboard page — Step 7_8c + 7_8d.
 *
 * Wraps the shared `<CamperDashboard />` and adds CC-specific bits the
 * shared component doesn't know about:
 *   - "Add Camper Care note" sticky CTA so authors can drop a note
 *     without losing context (Story 21 in-context).
 *   - Flag history rail (Step 7_8d) that lists every CC flag this
 *     camper has ever had, newest first. When the URL contains
 *     `?flagId=`, the page auto-scrolls to the matching row so the
 *     "Flag → camper" jump from the workspace lands with context.
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import { Link, useParams, useSearchParams } from 'react-router-dom';
import CamperDashboard from '../../components/CamperDashboard';
import { fetchCamperDashboard } from '../../api/camperCare';

const STATUS_META = {
  active: { label: 'Active', cls: 'bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-200' },
  followed_up: { label: 'Followed up', cls: 'bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-200' },
  resolved: { label: 'Resolved', cls: 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-200' },
};

function formatTimestamp(iso) {
  if (!iso) return '';
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return iso;
  }
}

function FlagHistoryRow({ flag, anchored }) {
  const meta = STATUS_META[flag.status] || STATUS_META.active;
  const raisedBy = flag.raised_by?.name || 'Unknown';
  return (
    <li
      id={`flag-${flag.id}`}
      data-testid={`cc-camper-flag-${flag.id}`}
      data-anchored={anchored ? 'true' : 'false'}
      className={`rounded-lg border px-3 py-2 text-sm ${
        anchored
          ? 'border-blue-400 bg-blue-50 dark:bg-blue-900/30 dark:border-blue-700'
          : 'border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900'
      }`}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="font-medium text-gray-900 dark:text-white">
            {formatTimestamp(flag.created_at)}
          </p>
          <p className="text-xs text-gray-500 dark:text-gray-400">
            Raised by {raisedBy}
          </p>
        </div>
        <span className={`text-xs font-medium px-2 py-0.5 rounded-full shrink-0 ${meta.cls}`}>
          {meta.label}
        </span>
      </div>
      {flag.trigger_preview && (
        <blockquote className="text-xs text-gray-700 dark:text-gray-200 italic border-l-2 border-gray-300 dark:border-gray-600 pl-2 mt-1 line-clamp-3">
          {flag.trigger_preview}
        </blockquote>
      )}
    </li>
  );
}

function NotesDateRangeFilter({ from, to, onChange }) {
  const [localFrom, setLocalFrom] = useState(from);
  const [localTo, setLocalTo] = useState(to);
  // Keep local state in sync if URL params change externally (e.g. back/forward).
  useEffect(() => { setLocalFrom(from); }, [from]);
  useEffect(() => { setLocalTo(to); }, [to]);
  const apply = () => onChange({ from: localFrom, to: localTo });
  const clear = () => {
    setLocalFrom('');
    setLocalTo('');
    onChange({ from: '', to: '' });
  };
  const isFiltered = Boolean(from || to);
  return (
    <section
      data-testid="cc-camper-notes-filter"
      className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 px-4 py-3 shadow-sm"
    >
      <div className="flex flex-wrap items-end gap-3">
        <div>
          <label className="block text-xs font-medium text-gray-600 dark:text-gray-300" htmlFor="cc-notes-from">
            Notes from
          </label>
          <input
            id="cc-notes-from"
            data-testid="cc-notes-from"
            type="date"
            value={localFrom}
            max={localTo || undefined}
            onChange={(e) => setLocalFrom(e.target.value)}
            className="mt-1 rounded-lg border border-gray-300 dark:border-gray-600 dark:bg-gray-800 dark:text-white px-2 py-1 text-sm"
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-gray-600 dark:text-gray-300" htmlFor="cc-notes-to">
            Notes to
          </label>
          <input
            id="cc-notes-to"
            data-testid="cc-notes-to"
            type="date"
            value={localTo}
            min={localFrom || undefined}
            onChange={(e) => setLocalTo(e.target.value)}
            className="mt-1 rounded-lg border border-gray-300 dark:border-gray-600 dark:bg-gray-800 dark:text-white px-2 py-1 text-sm"
          />
        </div>
        <button
          type="button"
          onClick={apply}
          data-testid="cc-notes-filter-apply"
          className="inline-flex items-center px-3 py-1.5 text-sm rounded-lg bg-blue-600 text-white hover:bg-blue-700"
        >
          Apply
        </button>
        {isFiltered && (
          <button
            type="button"
            onClick={clear}
            data-testid="cc-notes-filter-clear"
            className="inline-flex items-center px-3 py-1.5 text-sm rounded-lg border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-800"
          >
            Clear
          </button>
        )}
        {isFiltered && (
          <span
            data-testid="cc-notes-filter-active"
            className="text-xs text-gray-500 dark:text-gray-400"
          >
            Notes filtered{from ? ` from ${from}` : ''}{to ? ` to ${to}` : ''}.
          </span>
        )}
      </div>
    </section>
  );
}

function FlagHistorySection({ flags, anchorFlagId }) {
  if (!flags?.length) {
    return (
      <section
        data-testid="cc-camper-flag-history-empty"
        className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 px-4 py-3 shadow-sm"
      >
        <h2 className="text-base font-semibold text-gray-900 dark:text-white">Flag history</h2>
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
          No Camper Care flags raised for this camper.
        </p>
      </section>
    );
  }
  return (
    <section
      data-testid="cc-camper-flag-history"
      className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 px-4 py-3 shadow-sm"
    >
      <h2 className="text-base font-semibold text-gray-900 dark:text-white mb-2">
        Flag history ({flags.length})
      </h2>
      <ul className="space-y-2">
        {flags.map((f) => (
          <FlagHistoryRow key={f.id} flag={f} anchored={f.id === anchorFlagId} />
        ))}
      </ul>
    </section>
  );
}

export default function CamperCareCamperDashboardPage() {
  const { camperId } = useParams();
  const [searchParams, setSearchParams] = useSearchParams();
  const dateParam = searchParams.get('date') || '';
  const rangeParam = searchParams.get('range') || 'last_4_weeks';
  const anchorFlagId = searchParams.get('flagId') || '';
  const notesFromParam = searchParams.get('notes_from') || '';
  const notesToParam = searchParams.get('notes_to') || '';

  const [data, setData] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const scrolledFlagRef = useRef(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const payload = await fetchCamperDashboard(camperId, {
        date: dateParam || undefined,
        range: rangeParam,
        notes_from: notesFromParam || undefined,
        notes_to: notesToParam || undefined,
      });
      setData(payload);
      setError('');
    } catch (err) {
      const detail = err?.response?.data?.detail;
      setError(typeof detail === 'string' ? detail : err?.message || 'Could not load this camper.');
    } finally {
      setLoading(false);
    }
  }, [camperId, dateParam, rangeParam, notesFromParam, notesToParam]);

  useEffect(() => { load(); }, [load]);

  // Once the data loads, scroll the anchored flag into view (once per
  // anchor change). The flag history section renders inline below the
  // shared CamperDashboard, so the anchor id lives in this page.
  useEffect(() => {
    if (!anchorFlagId || !data) return;
    if (scrolledFlagRef.current === anchorFlagId) return;
    const el = document.getElementById(`flag-${anchorFlagId}`);
    if (el) {
      if (typeof el.scrollIntoView === 'function') {
        el.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }
      scrolledFlagRef.current = anchorFlagId;
    }
  }, [anchorFlagId, data]);

  const updateParam = (key, value) => {
    const params = new URLSearchParams(searchParams);
    if (value) params.set(key, value);
    else params.delete(key);
    setSearchParams(params, { replace: true });
  };

  const updateParams = (next) => {
    const params = new URLSearchParams(searchParams);
    Object.entries(next).forEach(([key, value]) => {
      if (value) params.set(key, value);
      else params.delete(key);
    });
    setSearchParams(params, { replace: true });
  };

  if (loading && !data) {
    return (
      <div className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-[96rem] mx-auto">
        <p className="text-gray-600 dark:text-gray-400">Loading camper dashboard…</p>
      </div>
    );
  }

  if (error && !data) {
    return (
      <div className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-[96rem] mx-auto">
        <div
          role="alert"
          className="rounded-xl border border-amber-200 bg-amber-50 dark:border-amber-900 dark:bg-amber-900/30 px-4 py-3 text-sm text-amber-900 dark:text-amber-100"
          data-testid="cc-camper-dashboard-error"
        >
          {error}
        </div>
      </div>
    );
  }

  return (
    <>
      <CamperDashboard
        data={data}
        selectedDate={dateParam || data?.header?.date}
        selectedRange={rangeParam}
        onDateChange={(next) => updateParam('date', next)}
        onRangeChange={(next) => updateParam('range', next)}
        backTo="/camper-care"
      />
      <div className="px-4 sm:px-6 lg:px-8 pb-20 w-full max-w-[96rem] mx-auto space-y-4">
        <NotesDateRangeFilter
          from={notesFromParam}
          to={notesToParam}
          onChange={(next) => updateParams({
            notes_from: next.from,
            notes_to: next.to,
          })}
        />
        <FlagHistorySection
          flags={data?.flag_history || []}
          anchorFlagId={anchorFlagId}
        />
      </div>
      {/* TODO(7_23): Camper Care observation compose from camper dashboard */}
    </>
  );
}
