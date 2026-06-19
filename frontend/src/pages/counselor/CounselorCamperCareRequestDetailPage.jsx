/**
 * Counselor camper-care request detail — read-only ticket view.
 *
 * URL: /counselor/requests/camper-care/:orderId
 */

import { useCallback, useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { fetchCamperCareRequestDetail } from '../../api/counselor';

const STATUS_BADGE = {
  new: 'bg-blue-100 text-blue-900 dark:bg-blue-900/40 dark:text-blue-100',
  in_progress: 'bg-amber-100 text-amber-900 dark:bg-amber-900/40 dark:text-amber-100',
  fulfilled: 'bg-green-100 text-green-900 dark:bg-green-900/40 dark:text-green-100',
  unable_to_fulfill: 'bg-gray-200 text-gray-800 dark:bg-gray-700 dark:text-gray-100',
};

const STATUS_LABEL = {
  new: 'New',
  in_progress: 'In Progress',
  fulfilled: 'Fulfilled',
  unable_to_fulfill: 'Unable to fulfill',
};

function formatTime(iso) {
  if (!iso) return '';
  return new Date(iso).toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function ActivityEvent({ event }) {
  const isStateChange = event.event_type === 'state_change' || event.from_state || event.to_state;
  return (
    <div
      data-testid={`activity-${event.id}`}
      className="flex gap-3"
    >
      <div className="w-1.5 flex-shrink-0 mt-1.5">
        <div className="w-1.5 h-1.5 rounded-full bg-gray-400" />
      </div>
      <div className="flex-1 min-w-0 pb-4 border-b border-gray-100 dark:border-gray-800 last:border-0">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-xs font-medium text-gray-700 dark:text-gray-200">
            {event.actor_name || 'System'}
          </span>
          <span className="text-xs text-gray-400">{formatTime(event.created_at)}</span>
          {isStateChange && event.from_state && event.to_state ? (
            <span className="text-xs text-gray-500 dark:text-gray-400">
              {STATUS_LABEL[event.from_state] || event.from_state}
              {' → '}
              {STATUS_LABEL[event.to_state] || event.to_state}
            </span>
          ) : null}
        </div>
        {event.note ? (
          <p className="text-sm text-gray-800 dark:text-gray-100 mt-1 whitespace-pre-wrap">
            {event.note}
          </p>
        ) : null}
        {event.reason ? (
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
            Reason: {event.reason}
          </p>
        ) : null}
      </div>
    </div>
  );
}

export default function CounselorCamperCareRequestDetailPage() {
  const { orderId } = useParams();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const result = await fetchCamperCareRequestDetail(orderId);
      setData(result);
    } catch (err) {
      setError(err?.response?.data?.detail || err?.message || 'Could not load request.');
    } finally {
      setLoading(false);
    }
  }, [orderId]);

  useEffect(() => {
    load();
  }, [load]);

  if (loading && !data) {
    return (
      <div className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-[96rem] mx-auto">
        <p className="text-gray-600 dark:text-gray-400" data-testid="camper-care-detail-loading">
          Loading request…
        </p>
      </div>
    );
  }

  if (error && !data) {
    return (
      <div className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-[96rem] mx-auto">
        <Link
          to="/counselor"
          className="text-sm text-blue-600 dark:text-blue-400 hover:underline"
        >
          ← Back to dashboard
        </Link>
        <div
          role="alert"
          className="mt-4 rounded-xl border border-red-200 bg-red-50 dark:bg-red-900/20 px-4 py-3 text-sm text-red-800 dark:text-red-200"
          data-testid="camper-care-detail-error"
        >
          {error}
        </div>
      </div>
    );
  }

  const order = data?.order;
  const activity = data?.activity || [];

  return (
    <div
      className="px-4 sm:px-6 lg:px-8 py-8 pb-24 w-full max-w-[96rem] mx-auto space-y-4"
      data-testid="camper-care-request-detail"
    >
      <header className="flex items-center gap-3 flex-wrap">
        <Link
          to="/counselor"
          className="text-sm text-blue-600 dark:text-blue-400 hover:underline"
          data-testid="camper-care-detail-back"
        >
          ← Back to dashboard
        </Link>
        {order?.editable ? (
          <Link
            to={`/counselor/requests/camper-care/${orderId}/edit`}
            className="text-sm font-medium text-blue-700 dark:text-blue-300 hover:underline"
            data-testid="camper-care-detail-edit"
          >
            Edit request
          </Link>
        ) : null}
        {order ? (
          <span
            className={`text-xs font-medium px-2 py-0.5 rounded-full ${STATUS_BADGE[order.status] || ''}`}
            data-testid="camper-care-detail-status"
          >
            {order.status_label || STATUS_LABEL[order.status] || order.status}
          </span>
        ) : null}
      </header>

      {order ? (
        <div className="space-y-4">
          <section data-testid="camper-care-detail-header">
            <p className="text-xs font-medium uppercase tracking-wide text-purple-700 dark:text-purple-300">
              Camper Care request
            </p>
            <h1 className="text-2xl font-semibold text-gray-900 dark:text-white mt-1">
              {order.item || 'Request'}
            </h1>
            {order.subject?.name ? (
              <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                For {order.subject.name}
              </p>
            ) : (
              <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">Bunk-wide request</p>
            )}
            {order.item_note ? (
              <p className="text-sm text-gray-700 dark:text-gray-300 mt-2">{order.item_note}</p>
            ) : null}
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-2">
              Submitted {formatTime(order.created_at)}
              {order.updated_at && order.updated_at !== order.created_at
                ? ` · Updated ${formatTime(order.updated_at)}`
                : ''}
            </p>
          </section>

          {order.description ? (
            <section data-testid="camper-care-detail-description">
              <h2 className="text-sm font-semibold text-gray-700 dark:text-gray-200 mb-1">
                Description
              </h2>
              <p className="text-sm text-gray-800 dark:text-gray-100 whitespace-pre-wrap">
                {order.description}
              </p>
            </section>
          ) : null}

          <section data-testid="camper-care-detail-activity">
            <h2 className="text-sm font-semibold text-gray-700 dark:text-gray-200 mb-2">
              Activity
            </h2>
            {activity.length === 0 ? (
              <p className="text-sm text-gray-500 dark:text-gray-400">No activity yet.</p>
            ) : (
              <div className="space-y-0">
                {activity.map((event) => (
                  <ActivityEvent key={event.id} event={event} />
                ))}
              </div>
            )}
          </section>
        </div>
      ) : null}
    </div>
  );
}
