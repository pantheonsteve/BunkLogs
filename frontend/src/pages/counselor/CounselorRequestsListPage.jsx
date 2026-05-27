/**
 * Counselor requests list — Step 7_6f (Stories 7 + 8).
 *
 * URL:  /counselor/requests[?status=open|all]
 *
 * Renders the combined open camper-care + maintenance request roster
 * that the dashboard's "Open Requests" tile teases (Story 7 + 8 list
 * view). Two CTA buttons up top take the counselor to the per-resource
 * "New request" forms. A status filter (open ↔ all) flips the API call
 * so counselors can confirm a request has been closed without leaving
 * the surface.
 */

import { useCallback, useEffect, useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { fetchCounselorRequests } from '../../api/counselor';

function TypeBadge({ type }) {
  if (type === 'camper_care') {
    return (
      <span
        data-testid="request-type-badge"
        className="text-xs font-medium px-2 py-0.5 rounded-full bg-purple-100 text-purple-800 dark:bg-purple-900/40 dark:text-purple-200"
      >
        Camper Care
      </span>
    );
  }
  if (type === 'maintenance') {
    return (
      <span
        data-testid="request-type-badge"
        className="text-xs font-medium px-2 py-0.5 rounded-full bg-orange-100 text-orange-800 dark:bg-orange-900/40 dark:text-orange-200"
      >
        Maintenance
      </span>
    );
  }
  return null;
}

function StatusBadge({ status, statusLabel }) {
  // Map the OrderStateMachine status to a tailwind colour palette.
  // Keep this loose; new statuses fall back to the neutral pill.
  const palette = {
    new: 'bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-200',
    in_progress: 'bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-200',
    completed: 'bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-200',
    closed: 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-200',
    cancelled: 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-200',
  };
  const cls = palette[status] || palette.closed;
  return (
    <span
      data-testid="request-status-badge"
      data-status={status}
      className={`text-xs font-medium px-2 py-0.5 rounded-full ${cls}`}
    >
      {statusLabel || status}
    </span>
  );
}

function UrgencyBadge({ urgency, urgencyLabel }) {
  if (urgency !== 'urgent') return null;
  return (
    <span
      data-testid="request-urgency-badge"
      className="text-xs font-medium px-2 py-0.5 rounded-full bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-200"
    >
      {urgencyLabel || 'Urgent'}
    </span>
  );
}

function formatRelative(iso) {
  if (!iso) return '';
  const d = new Date(iso);
  const now = new Date();
  const diffMs = now - d;
  const diffMin = Math.round(diffMs / 60000);
  if (diffMin < 1) return 'just now';
  if (diffMin < 60) return `${diffMin}m ago`;
  const diffH = Math.round(diffMin / 60);
  if (diffH < 24) return `${diffH}h ago`;
  const diffD = Math.round(diffH / 24);
  return `${diffD}d ago`;
}

function RequestRow({ row }) {
  const isCamperCare = row.type === 'camper_care';
  const title = isCamperCare
    ? row.item || 'Camper Care request'
    : (row.category_label || row.location || 'Maintenance ticket');
  const subtitle = isCamperCare
    ? (row.subject?.name
        ? `For ${row.subject.name}`
        : 'Bunk-wide request')
    : (row.location ? `Location: ${row.location}` : '');

  const submitter = row.submitter?.is_self
    ? 'you'
    : row.submitter?.name || 'a co-counselor';

  return (
    <li
      data-testid={`request-row-${row.type}-${row.id}`}
      data-type={row.type}
      data-status={row.status}
      className="py-3 border-b border-gray-100 dark:border-gray-800 last:border-b-0 flex flex-col gap-1"
    >
      <div className="flex items-center gap-2 flex-wrap">
        <TypeBadge type={row.type} />
        <StatusBadge status={row.status} statusLabel={row.status_label} />
        <UrgencyBadge urgency={row.urgency} urgencyLabel={row.urgency_label} />
      </div>
      <p className="text-sm font-medium text-gray-900 dark:text-white">{title}</p>
      {subtitle ? (
        <p className="text-xs text-gray-600 dark:text-gray-400">{subtitle}</p>
      ) : null}
      <p className="text-xs text-gray-500 dark:text-gray-400">
        Sent by {submitter}
        {row.submitted_at ? ` · ${formatRelative(row.submitted_at)}` : ''}
        {row.type === 'maintenance' && row.photo_count
          ? ` · ${row.photo_count} photo${row.photo_count === 1 ? '' : 's'}`
          : ''}
      </p>
    </li>
  );
}

export default function CounselorRequestsListPage() {
  const navigate = useNavigate();
  const [params, setParams] = useSearchParams();
  const statusParam = (params.get('status') === 'all' ? 'all' : 'open');

  const [rows, setRows] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);

  const load = useCallback(async (filterStatus) => {
    setLoading(true);
    setError('');
    try {
      const data = await fetchCounselorRequests({ status: filterStatus });
      setRows(data?.requests || []);
    } catch (err) {
      const detail = err?.response?.data?.detail;
      setError(typeof detail === 'string' ? detail : 'Could not load requests.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load(statusParam);
  }, [load, statusParam]);

  const changeFilter = (next) => {
    // Drop the param entirely on the "open" default so URLs stay clean.
    if (next === 'open') {
      params.delete('status');
    } else {
      params.set('status', next);
    }
    setParams(params, { replace: true });
  };

  return (
    <div className="px-4 sm:px-6 lg:px-8 py-8 pb-24 w-full max-w-[96rem] mx-auto space-y-4">
        <header className="flex items-start justify-between gap-3">
          <div>
            <button
              type="button"
              onClick={() => navigate('/counselor')}
              className="text-xs text-blue-600 dark:text-blue-400 mb-1 flex items-center gap-1"
            >
              ← Back to dashboard
            </button>
            <h1 className="text-2xl font-semibold text-gray-900 dark:text-white">
              Open requests
            </h1>
            <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
              Yours and your co-counselors' active requests.
            </p>
          </div>
          <div
            data-testid="requests-status-filter"
            className="flex rounded-lg border border-gray-300 dark:border-gray-600 overflow-hidden shrink-0"
          >
            <button
              type="button"
              data-testid="requests-filter-open"
              aria-pressed={statusParam === 'open'}
              onClick={() => changeFilter('open')}
              className={`px-3 py-1.5 text-sm min-h-[36px] ${
                statusParam === 'open'
                  ? 'bg-blue-600 text-white'
                  : 'bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-200'
              }`}
            >
              Open
            </button>
            <button
              type="button"
              data-testid="requests-filter-all"
              aria-pressed={statusParam === 'all'}
              onClick={() => changeFilter('all')}
              className={`px-3 py-1.5 text-sm min-h-[36px] ${
                statusParam === 'all'
                  ? 'bg-blue-600 text-white'
                  : 'bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-200'
              }`}
            >
              All
            </button>
          </div>
        </header>

        <div className="grid grid-cols-2 gap-3">
          <Link
            to="/counselor/requests/camper-care/new"
            data-testid="requests-new-camper-care"
            className="min-h-[44px] flex items-center justify-center rounded-lg bg-purple-600 text-white text-sm font-medium px-4"
          >
            + Camper Care
          </Link>
          <Link
            to="/counselor/requests/maintenance/new"
            data-testid="requests-new-maintenance"
            className="min-h-[44px] flex items-center justify-center rounded-lg bg-orange-600 text-white text-sm font-medium px-4"
          >
            + Maintenance
          </Link>
        </div>

        {loading && rows === null ? (
          <p
            className="text-gray-600 dark:text-gray-400"
            data-testid="requests-loading"
          >
            Loading requests…
          </p>
        ) : error ? (
          <div
            className="rounded-lg border border-amber-200 bg-amber-50 dark:bg-amber-950/40 dark:border-amber-800 px-4 py-3 text-sm text-amber-900 dark:text-amber-100"
            role="alert"
            data-testid="requests-error"
          >
            {error}
          </div>
        ) : (
          <section className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 px-4 py-2 shadow-sm">
            {rows && rows.length ? (
              <ul>
                {rows.map((row) => (
                  <RequestRow key={`${row.type}-${row.id}`} row={row} />
                ))}
              </ul>
            ) : (
              <p
                className="text-sm text-gray-600 dark:text-gray-400 py-4"
                data-testid="requests-empty"
              >
                {statusParam === 'open'
                  ? 'No open requests right now. Tap "+ Camper Care" or "+ Maintenance" to file a new one.'
                  : 'Nothing to show yet.'}
              </p>
            )}
          </section>
        )}
    </div>
  );
}
