import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { fetchAdminDashboard } from '../../api/admin';

/**
 * Step 7_13 PR1 — Admin home dashboard (Story 54).
 *
 * Sections per Story 54 criterion 3:
 *   - Org header (name, date, active programs)
 *   - Org snapshot (counts)
 *   - Attention required (6 conditions)
 *   - Recent activity (significant audit events)
 *
 * Visually distinct from operational role dashboards — uses a wider
 * grid + sharper section dividers so an Admin can tell they're on the
 * meta-view, not a per-team surface.
 *
 * Per-role drill-downs (People / Assignments / Templates / Settings /
 * search) are added in PR2 + PR3.
 */
const REFRESH_INTERVAL_MS = 120_000;

const ATTENTION_TINT = {
  stale_maintenance_tickets: 'border-amber-300 bg-amber-50 dark:bg-amber-900/20 dark:border-amber-700',
  stale_camper_care_orders: 'border-amber-300 bg-amber-50 dark:bg-amber-900/20 dark:border-amber-700',
  unresolved_flags: 'border-red-300 bg-red-50 dark:bg-red-900/20 dark:border-red-700',
  pending_template_review: 'border-indigo-300 bg-indigo-50 dark:bg-indigo-900/20 dark:border-indigo-700',
  digest_delivery_failures: 'border-red-300 bg-red-50 dark:bg-red-900/20 dark:border-red-700',
  translation_pipeline_failures: 'border-red-300 bg-red-50 dark:bg-red-900/20 dark:border-red-700',
};

function formatDate(iso) {
  if (!iso) return '';
  try {
    return new Date(iso).toLocaleDateString(undefined, {
      weekday: 'long',
      month: 'long',
      day: 'numeric',
      year: 'numeric',
    });
  } catch {
    return iso;
  }
}

function formatTime(iso) {
  if (!iso) return '';
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return iso;
  }
}

function OrgHeader({ org, today }) {
  if (!org) return null;
  return (
    <header
      data-testid="admin-dashboard-header"
      className="mb-6 border-b border-gray-200 dark:border-gray-700 pb-4"
    >
      <div className="flex flex-wrap items-baseline gap-3">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
          {org.name}
        </h1>
        <span className="text-sm text-gray-500 dark:text-gray-400">
          {formatDate(today)}
        </span>
      </div>
      {org.active_programs?.length > 0 && (
        <p className="mt-1 text-sm text-gray-600 dark:text-gray-300">
          {org.active_programs.length} active program{org.active_programs.length === 1 ? '' : 's'}
          {': '}
          {org.active_programs.map((p) => p.name).join(', ')}
        </p>
      )}
    </header>
  );
}

function SnapshotCard({ label, value }) {
  return (
    <div
      className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 px-4 py-3"
      data-testid={`admin-snapshot-${label.replace(/\s+/g, '-').toLowerCase()}`}
    >
      <p className="text-xs uppercase tracking-wide text-gray-500 dark:text-gray-400">
        {label}
      </p>
      <p className="mt-1 text-2xl font-semibold text-gray-900 dark:text-white">
        {value ?? 0}
      </p>
    </div>
  );
}

function OrgSnapshot({ snapshot }) {
  if (!snapshot) return null;
  return (
    <section data-testid="admin-snapshot" className="mb-6">
      <h2 className="text-sm font-semibold uppercase tracking-wide text-gray-600 dark:text-gray-300 mb-2">
        Org snapshot
      </h2>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
        <SnapshotCard label="Active people" value={snapshot.active_people} />
        <SnapshotCard label="Open CC orders" value={snapshot.open_camper_care_orders} />
        <SnapshotCard label="Open maintenance" value={snapshot.open_maintenance_tickets} />
        <SnapshotCard label="Active flags" value={snapshot.active_flags} />
      </div>
      {snapshot.memberships_by_role?.length > 0 && (
        <div className="mt-3 rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 px-4 py-3">
          <p className="text-xs uppercase tracking-wide text-gray-500 dark:text-gray-400 mb-2">
            Memberships by role
          </p>
          <ul className="flex flex-wrap gap-x-5 gap-y-1 text-sm text-gray-800 dark:text-gray-100">
            {snapshot.memberships_by_role.map((row) => (
              <li key={row.role} data-testid={`admin-role-${row.role}`}>
                <span className="font-medium">{row.count}</span>{' '}
                <span className="text-gray-600 dark:text-gray-400">{row.role}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}

function AttentionRequired({ cards }) {
  if (!cards?.length) return null;
  return (
    <section data-testid="admin-attention" className="mb-6">
      <h2 className="text-sm font-semibold uppercase tracking-wide text-gray-600 dark:text-gray-300 mb-2">
        Attention required
      </h2>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
        {cards.map((card) => (
          <Link
            key={card.key}
            to={card.deep_link || '/admin'}
            data-testid={`admin-attention-${card.key}`}
            className={`block rounded-xl border px-4 py-3 hover:shadow-md ${ATTENTION_TINT[card.key] || 'border-gray-200 bg-white dark:bg-gray-900 dark:border-gray-700'}`}
          >
            <div className="flex items-baseline justify-between gap-2">
              <p className="text-sm font-medium text-gray-900 dark:text-white">
                {card.label}
              </p>
              <span className="text-2xl font-semibold text-gray-900 dark:text-white">
                {card.count}
              </span>
            </div>
            {card.threshold_days != null && (
              <p className="mt-1 text-xs text-gray-600 dark:text-gray-300">
                Threshold: {card.threshold_days} day{card.threshold_days === 1 ? '' : 's'}
              </p>
            )}
          </Link>
        ))}
      </div>
    </section>
  );
}

function RecentActivity({ events }) {
  return (
    <section data-testid="admin-activity" className="mb-6">
      <h2 className="text-sm font-semibold uppercase tracking-wide text-gray-600 dark:text-gray-300 mb-2">
        Recent activity
      </h2>
      {!events?.length ? (
        <p data-testid="admin-activity-empty" className="text-sm italic text-gray-500 dark:text-gray-400">
          No significant activity in the last 7 days.
        </p>
      ) : (
        <ul className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 divide-y divide-gray-100 dark:divide-gray-800">
          {events.map((event) => (
            <li
              key={event.id}
              data-testid={`admin-activity-${event.id}`}
              data-admin-override={event.is_admin_override ? 'true' : 'false'}
              className="px-4 py-2.5 text-sm"
            >
              <div className="flex items-center justify-between gap-3 flex-wrap">
                <Link
                  to={event.deep_link || '/admin'}
                  className="font-medium text-gray-900 dark:text-white hover:underline"
                >
                  {event.summary}
                </Link>
                <time className="text-xs text-gray-500 dark:text-gray-400" dateTime={event.created_at}>
                  {formatTime(event.created_at)}
                </time>
              </div>
              {event.actor && (
                <p className="text-xs text-gray-600 dark:text-gray-300 mt-0.5">
                  by {event.actor}
                </p>
              )}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

function YourReflections() {
  return (
    <section data-testid="admin-reflections" className="mb-6">
      <h2 className="text-sm font-semibold uppercase tracking-wide text-gray-600 dark:text-gray-300 mb-2">
        Your reflections
      </h2>
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
        <Link to="/reflect" className="rounded-xl border border-gray-200 bg-white dark:bg-gray-900 dark:border-gray-700 px-4 py-3 hover:shadow-md">
          <p className="text-sm font-medium text-gray-900 dark:text-white">File a reflection</p>
        </Link>
        <Link to="/my-reflections" className="rounded-xl border border-gray-200 bg-white dark:bg-gray-900 dark:border-gray-700 px-4 py-3 hover:shadow-md">
          <p className="text-sm font-medium text-gray-900 dark:text-white">My reflections</p>
        </Link>
      </div>
    </section>
  );
}

function Navigation() {
  return (
    <section data-testid="admin-navigation" className="mb-6">
      <h2 className="text-sm font-semibold uppercase tracking-wide text-gray-600 dark:text-gray-300 mb-2">
        Manage
      </h2>
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
        <Link to="/admin/memberships" className="rounded-xl border border-gray-200 bg-white dark:bg-gray-900 dark:border-gray-700 px-4 py-3 hover:shadow-md">
          <p className="text-sm font-medium text-gray-900 dark:text-white">Memberships</p>
        </Link>
        <Link to="/admin/groups" className="rounded-xl border border-gray-200 bg-white dark:bg-gray-900 dark:border-gray-700 px-4 py-3 hover:shadow-md">
          <p className="text-sm font-medium text-gray-900 dark:text-white">Assignment groups</p>
        </Link>
        <Link to="/admin/templates" className="rounded-xl border border-gray-200 bg-white dark:bg-gray-900 dark:border-gray-700 px-4 py-3 hover:shadow-md">
          <p className="text-sm font-medium text-gray-900 dark:text-white">Templates</p>
        </Link>
        <Link to="/admin/field-keys" className="rounded-xl border border-gray-200 bg-white dark:bg-gray-900 dark:border-gray-700 px-4 py-3 hover:shadow-md">
          <p className="text-sm font-medium text-gray-900 dark:text-white">Field keys</p>
        </Link>
        <Link to="/dashboards" className="rounded-xl border border-gray-200 bg-white dark:bg-gray-900 dark:border-gray-700 px-4 py-3 hover:shadow-md">
          <p className="text-sm font-medium text-gray-900 dark:text-white">Dashboards</p>
        </Link>
      </div>
    </section>
  );
}

export default function AdminDashboard() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      const payload = await fetchAdminDashboard();
      setData(payload);
    } catch (err) {
      setError(err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
    const handle = window.setInterval(load, REFRESH_INTERVAL_MS);
    return () => window.clearInterval(handle);
  }, [load]);

  return (
    <main className="grow px-4 sm:px-6 lg:px-8 py-8 w-full max-w-6xl mx-auto" data-testid="admin-dashboard">
      {loading && !data ? (
        <p className="text-sm text-gray-500 dark:text-gray-400">Loading admin dashboard…</p>
      ) : error ? (
        <div data-testid="admin-dashboard-error" className="rounded-xl border border-red-200 bg-red-50 p-4">
          <p className="text-sm text-red-800">Could not load the dashboard.</p>
          <button type="button" onClick={load} className="mt-2 text-sm font-medium text-red-700 underline">
            Retry
          </button>
        </div>
      ) : (
        <>
          <OrgHeader org={data?.org} today={data?.today} />
          <OrgSnapshot snapshot={data?.org_snapshot} />
          <AttentionRequired cards={data?.attention_required} />
          <RecentActivity events={data?.recent_activity} />
          <YourReflections />
          <Navigation />
        </>
      )}
    </main>
  );
}
