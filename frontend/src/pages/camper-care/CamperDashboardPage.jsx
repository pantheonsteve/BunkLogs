/**
 * Camper Care Camper Dashboard page — Step 7_8c, Story 18 c.9 + Story 21.
 *
 * Wraps the shared `<CamperDashboard />` and adds the in-context
 * "Add Camper Care note" CTA above the dashboard so authors can drop
 * a note without losing context. The note form route accepts
 * `?camperId=` so the deep-linked CTA pre-fills the subject. Date +
 * range live in the URL so a deep link is shareable.
 */

import { useCallback, useEffect, useState } from 'react';
import { Link, useParams, useSearchParams } from 'react-router-dom';
import CamperDashboard from '../../components/CamperDashboard';
import { fetchCamperDashboard } from '../../api/camperCare';

export default function CamperCareCamperDashboardPage() {
  const { camperId } = useParams();
  const [searchParams, setSearchParams] = useSearchParams();
  const dateParam = searchParams.get('date') || '';
  const rangeParam = searchParams.get('range') || 'last_4_weeks';

  const [data, setData] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const payload = await fetchCamperDashboard(camperId, {
        date: dateParam || undefined,
        range: rangeParam,
      });
      setData(payload);
      setError('');
    } catch (err) {
      const detail = err?.response?.data?.detail;
      setError(typeof detail === 'string' ? detail : err?.message || 'Could not load this camper.');
    } finally {
      setLoading(false);
    }
  }, [camperId, dateParam, rangeParam]);

  useEffect(() => { load(); }, [load]);

  const updateParam = (key, value) => {
    const params = new URLSearchParams(searchParams);
    if (value) params.set(key, value);
    else params.delete(key);
    setSearchParams(params, { replace: true });
  };

  if (loading && !data) {
    return (
      <div className="px-4 py-6 max-w-3xl mx-auto">
        <p className="text-gray-600 dark:text-gray-400">Loading camper dashboard…</p>
      </div>
    );
  }

  if (error && !data) {
    return (
      <div className="px-4 py-6 max-w-3xl mx-auto">
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
      <div
        data-testid="cc-camper-add-note-bar"
        className="fixed bottom-0 inset-x-0 z-30 border-t border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 px-4 py-3 shadow-md"
      >
        <div className="max-w-3xl mx-auto flex items-center justify-end">
          <Link
            to={`/camper-care/notes/new?camperId=${encodeURIComponent(camperId)}`}
            data-testid="cc-camper-add-note"
            className="inline-flex items-center justify-center min-h-[44px] px-4 rounded-lg bg-blue-600 text-white text-sm font-medium hover:bg-blue-700"
          >
            Add Camper Care note
          </Link>
        </div>
      </div>
    </>
  );
}
