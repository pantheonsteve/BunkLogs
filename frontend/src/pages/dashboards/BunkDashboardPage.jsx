/**
 * Unified Bunk Dashboard page at `/dashboards/bunk/:bunkId`.
 *
 * Replaces the per-role `/unit-head/bunks/:bunkId` and
 * `/camper-care/bunks/:bunkId` wrappers. Counselor, Camper Care, Unit
 * Head, Leadership Team, and Admin all read here; access resolution
 * happens server-side in
 * `bunk_logs.api.dashboards.bunk_dashboard_common.resolve_bunk_dashboard_context`
 * and the response's `role_context.role` drives the back link (and,
 * in a future PR, edit affordances).
 *
 * URL contract: date is in the query string (`?date=YYYY-MM-DD`) so a
 * deep link to a past day is shareable. Auto-refreshes today's view
 * every 60s; past dates are static.
 */

import { useCallback, useEffect, useMemo, useState } from 'react';
import { useParams, useSearchParams } from 'react-router-dom';
import BunkDashboard from '../../components/BunkDashboard';
import { fetchBunkDashboard } from '../../api/dashboards';

const REFRESH_INTERVAL_MS = 60_000;

const FALLBACK_BACK_TO = '/dashboards';

const BACK_TO_BY_ROLE = Object.freeze({
  counselor: '/counselor',
  camper_care: '/camper-care',
  unit_head: '/unit-head',
  leadership_team: '/leadership-team',
  admin: '/admin',
});

function backToFor(role) {
  return BACK_TO_BY_ROLE[role] ?? FALLBACK_BACK_TO;
}

export default function BunkDashboardPage() {
  const { bunkId } = useParams();
  const [searchParams, setSearchParams] = useSearchParams();
  const dateParam = searchParams.get('date') || '';

  const [data, setData] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const payload = await fetchBunkDashboard(bunkId, {
        date: dateParam || undefined,
      });
      setData(payload);
      setError('');
    } catch (err) {
      const detail = err?.response?.data?.detail;
      setError(
        typeof detail === 'string'
          ? detail
          : err?.message || 'Could not load this bunk.',
      );
    } finally {
      setLoading(false);
    }
  }, [bunkId, dateParam]);

  useEffect(() => {
    load();
  }, [load]);

  const isToday = useMemo(() => {
    if (!data?.header?.date || !data?.header?.today) return false;
    return data.header.date === data.header.today;
  }, [data]);

  useEffect(() => {
    if (!isToday) return undefined;
    const id = setInterval(load, REFRESH_INTERVAL_MS);
    return () => clearInterval(id);
  }, [isToday, load]);

  const handleDateChange = (next) => {
    const params = new URLSearchParams(searchParams);
    if (next) params.set('date', next);
    else params.delete('date');
    setSearchParams(params, { replace: true });
  };

  if (loading && !data) {
    return (
      <div className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-[96rem] mx-auto">
        <p className="text-gray-600 dark:text-gray-400">Loading bunk dashboard…</p>
      </div>
    );
  }

  if (error && !data) {
    return (
      <div className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-[96rem] mx-auto">
        <div
          role="alert"
          className="rounded-xl border border-amber-200 bg-amber-50 dark:border-amber-900 dark:bg-amber-900/30 px-4 py-3 text-sm text-amber-900 dark:text-amber-100"
          data-testid="bunk-dashboard-error"
        >
          {error}
        </div>
      </div>
    );
  }

  const role = data?.role_context?.role;

  return (
    <BunkDashboard
      data={data}
      selectedDate={dateParam || data?.header?.date}
      onDateChange={handleDateChange}
      camperDashboardPath="/dashboards/subject"
      backTo={backToFor(role)}
    />
  );
}
