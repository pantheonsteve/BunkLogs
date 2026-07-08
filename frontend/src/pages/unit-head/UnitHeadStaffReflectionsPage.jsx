/**
 * Unit Head Staff Reflections — daily staff self-reflections across supervised bunks.
 */

import { useCallback, useEffect, useState } from 'react';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import { Link, useSearchParams } from 'react-router-dom';
import { fetchUnitHeadStaffReflections } from '../../api/unitHead';
import CounselorSelfReflectionsList, { counselorSelfReflectionSummary } from '../../components/CounselorSelfReflectionsList';
import SingleDatePicker from '../../components/ui/SingleDatePicker';

function todayLocalISO() {
  const now = new Date();
  const y = now.getFullYear();
  const m = String(now.getMonth() + 1).padStart(2, '0');
  const d = String(now.getDate()).padStart(2, '0');
  return `${y}-${m}-${d}`;
}

function dateFromISO(s) {
  if (!s) return null;
  const [y, m, d] = s.split('-').map(Number);
  if (!y || !m || !d) return null;
  return new Date(y, m - 1, d, 12, 0, 0, 0);
}

function isoFromDate(date) {
  if (!date) return '';
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, '0');
  const d = String(date.getDate()).padStart(2, '0');
  return `${y}-${m}-${d}`;
}

function shiftISO(iso, deltaDays) {
  const d = dateFromISO(iso);
  if (!d) return iso;
  d.setDate(d.getDate() + deltaDays);
  return isoFromDate(d);
}

function formatLongDate(iso) {
  const d = dateFromISO(iso);
  if (!d) return iso;
  return d.toLocaleDateString('en-US', {
    weekday: 'long',
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  });
}

function BunkStaffReflectionsCard({ bunk, dateIso }) {
  const { submitted, expected } = counselorSelfReflectionSummary(
    bunk.counselor_self_reflections,
  );
  return (
    <section
      data-testid={`uh-staff-refl-bunk-${bunk.id}`}
      className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 shadow-sm"
    >
      <div className="flex flex-wrap items-center justify-between gap-2 px-4 sm:px-5 pt-4 pb-3 border-b border-gray-100 dark:border-gray-800">
        <div>
          <h2 className="text-base font-semibold text-gray-900 dark:text-white">
            {bunk.name}
          </h2>
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
            {submitted}/{expected} submitted
          </p>
        </div>
        <Link
          to={`/dashboards/group/${bunk.id}?date=${encodeURIComponent(dateIso)}`}
          className="text-xs font-medium text-indigo-700 dark:text-indigo-300 hover:underline"
        >
          Open bunk dashboard
        </Link>
      </div>
      <div className="px-4 sm:px-5 py-4">
        <CounselorSelfReflectionsList entries={bunk.counselor_self_reflections} />
      </div>
    </section>
  );
}

export default function UnitHeadStaffReflectionsPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const dateParam = searchParams.get('date') || todayLocalISO();
  const [payload, setPayload] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await fetchUnitHeadStaffReflections({ date: dateParam });
      setPayload(data);
      setError('');
    } catch (err) {
      const detail = err?.response?.data?.detail;
      setError(typeof detail === 'string' ? detail : err?.message || 'Could not load staff reflections.');
      setPayload(null);
    } finally {
      setLoading(false);
    }
  }, [dateParam]);

  useEffect(() => {
    load();
  }, [load]);

  const setDate = (iso) => {
    const params = new URLSearchParams(searchParams);
    if (iso) params.set('date', iso);
    else params.delete('date');
    setSearchParams(params, { replace: true });
  };

  const bunks = payload?.bunks || [];
  const displayDate = payload?.header?.date || dateParam;

  return (
    <div
      className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-[96rem] mx-auto"
      data-testid="uh-staff-reflections-page"
    >
      <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900 dark:text-white">
            Staff Reflections
          </h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            Daily staff self-reflections for the bunks you supervise.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            aria-label="Previous day"
            onClick={() => setDate(shiftISO(dateParam, -1))}
            className="rounded-md border border-gray-300 dark:border-gray-600 p-2 text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800"
          >
            <ChevronLeft className="h-4 w-4" />
          </button>
          <SingleDatePicker
            date={dateFromISO(dateParam)}
            setDate={(d) => d && setDate(isoFromDate(d))}
          />
          <button
            type="button"
            aria-label="Next day"
            onClick={() => setDate(shiftISO(dateParam, 1))}
            className="rounded-md border border-gray-300 dark:border-gray-600 p-2 text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800"
          >
            <ChevronRight className="h-4 w-4" />
          </button>
        </div>
      </div>

      <p className="text-sm text-gray-600 dark:text-gray-300 mb-6">
        {formatLongDate(displayDate)}
      </p>

      {loading && !payload && (
        <p className="text-sm text-gray-500 dark:text-gray-400">Loading staff reflections…</p>
      )}
      {!loading && error && (
        <div
          role="alert"
          className="rounded-xl border border-amber-200 bg-amber-50 dark:border-amber-900 dark:bg-amber-900/30 px-4 py-3 text-sm text-amber-900 dark:text-amber-100"
        >
          {error}
        </div>
      )}
      {!error && payload && bunks.length === 0 && (
        <p className="text-sm text-gray-500 dark:text-gray-400">
          No supervised bunks for this date.
        </p>
      )}
      {!error && bunks.length > 0 && (
        <div className="space-y-5">
          {bunks.map((bunk) => (
            <BunkStaffReflectionsCard
              key={bunk.id}
              bunk={bunk}
              dateIso={displayDate}
            />
          ))}
        </div>
      )}
    </div>
  );
}
