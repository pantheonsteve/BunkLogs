/**
 * Unit Head Camper Dashboard page — Step 7_7, Story 13.
 *
 * Hosts the shared `<CamperDashboard />` for the UH role. Date +
 * range live in the URL so a deep link to "Camper X, last 4 weeks
 * ending 2026-06-12" is shareable. Range options match the backend
 * RANGE_CHOICES.
 */

import { useCallback, useEffect, useState } from 'react';
import { useParams, useSearchParams } from 'react-router-dom';
import CamperDashboard from '../../components/CamperDashboard';
import { fetchCamperDashboard } from '../../api/unitHead';

export default function UnitHeadCamperDashboardPage() {
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

  useEffect(() => {
    load();
  }, [load]);

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
          data-testid="uh-camper-dashboard-error"
        >
          {error}
        </div>
      </div>
    );
  }

  return (
    <CamperDashboard
      data={data}
      selectedDate={dateParam || data?.header?.date}
      selectedRange={rangeParam}
      onDateChange={(next) => updateParam('date', next)}
      onRangeChange={(next) => updateParam('range', next)}
      backTo="/unit-head"
    />
  );
}
