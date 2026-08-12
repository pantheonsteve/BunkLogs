/**
 * TBE Director/Admin staffing matrix — Step 4_7 AC4.
 *
 * Madrichim x upcoming Sundays grid for staffing decisions, exportable to
 * CSV. Lives alongside the reflections completion dashboard (Step 4_4)
 * rather than as a standalone route, since both are org-admin TBE tools.
 * Cell status is shown with an icon + text label, never color alone (a11y).
 */
import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  exportAdminMadrichAvailabilityUrl,
  fetchAdminMadrichAvailability,
} from '../../../api/adminMadrichAvailability';

const STATUS_META = {
  available: {
    label: 'Available',
    icon: '\u2713',
    className: 'bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-200',
  },
  tentative: {
    label: 'Tentative',
    icon: '?',
    className: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/40 dark:text-yellow-200',
  },
  unavailable: {
    label: 'Unavailable',
    icon: '\u2715',
    className: 'bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-200',
  },
};
const UNSET_META = {
  label: 'Unset',
  icon: '\u2013',
  className: 'bg-gray-100 text-gray-500 dark:bg-gray-700 dark:text-gray-400',
};

function StatusCell({ status }) {
  const meta = status ? STATUS_META[status] : UNSET_META;
  return (
    <span
      className={`inline-flex items-center gap-1 text-xs font-medium px-2 py-0.5 rounded-full ${meta.className}`}
      data-testid={`availability-matrix-cell-${status || 'unset'}`}
    >
      <span aria-hidden="true">{meta.icon}</span>
      {meta.label}
    </span>
  );
}

function sessionLabel(sessionDate) {
  const d = new Date(`${sessionDate}T00:00:00`);
  return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
}

export default function AvailabilityMatrix() {
  const [payload, setPayload] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await fetchAdminMadrichAvailability();
      setPayload(data);
      setError(null);
    } catch (err) {
      const status = err?.response?.status;
      if (status === 403) setError('Admin access required.');
      else setError('Failed to load the availability matrix.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  if (loading) {
    return (
      <div className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-[96rem] mx-auto" data-testid="availability-matrix-loading">
        <p className="text-gray-500 dark:text-gray-400">Loading…</p>
      </div>
    );
  }

  if (error || !payload) {
    return (
      <div className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-[96rem] mx-auto" data-testid="availability-matrix-error">
        <p className="text-red-600 dark:text-red-400">{error || 'Failed to load the availability matrix.'}</p>
      </div>
    );
  }

  const { program, sessions, rows, summary } = payload;
  const exportUrl = exportAdminMadrichAvailabilityUrl();

  if (!program || sessions.length === 0) {
    return (
      <div className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-[96rem] mx-auto" data-testid="availability-matrix-empty">
        <h1 className="text-xl font-bold text-gray-900 dark:text-white">Availability</h1>
        <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">
          No active religious-school program with configured sessions was found.
        </p>
      </div>
    );
  }

  return (
    <div className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-[96rem] mx-auto space-y-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h1 className="text-xl font-bold text-gray-900 dark:text-white">Availability</h1>
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
            {program.name} · {rows.length} Madrichim
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Link
            to="/admin/reflections"
            className="rounded-lg border border-gray-300 dark:border-gray-600 text-sm font-medium px-3 py-1.5 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800"
            data-testid="availability-matrix-reflections-tab"
          >
            Reflections
          </Link>
          <a
            href={exportUrl}
            className="rounded-lg border border-gray-300 dark:border-gray-600 text-sm font-medium px-3 py-1.5 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800"
            data-testid="availability-matrix-export"
          >
            Export CSV
          </a>
        </div>
      </div>

      <div className="overflow-x-auto rounded-xl border border-gray-200 dark:border-gray-700" data-testid="availability-matrix-grid">
        <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700 text-sm">
          <thead className="bg-gray-50 dark:bg-gray-800">
            <tr>
              <th className="px-3 py-2 text-left font-semibold text-gray-700 dark:text-gray-300">Madrich</th>
              {sessions.map((s) => (
                <th key={s} className="px-3 py-2 text-left font-semibold text-gray-700 dark:text-gray-300 whitespace-nowrap">
                  {sessionLabel(s)}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="bg-white dark:bg-gray-900 divide-y divide-gray-200 dark:divide-gray-700">
            {rows.length === 0 ? (
              <tr>
                <td colSpan={sessions.length + 1} className="px-3 py-4 text-gray-500 dark:text-gray-400">
                  No Madrichim found for this program.
                </td>
              </tr>
            ) : (
              rows.map((row) => (
                <tr key={row.person_id} data-testid={`availability-matrix-row-${row.person_id}`}>
                  <td className="px-3 py-2 whitespace-nowrap">
                    <span className="font-medium text-gray-900 dark:text-white">{row.display_name}</span>
                    {row.grade_level != null && (
                      <span className="ml-2 text-xs text-gray-500 dark:text-gray-400">Grade {row.grade_level}</span>
                    )}
                  </td>
                  {row.cells.map((cell) => (
                    <td key={cell.session_date} className="px-3 py-2" title={cell.note || undefined}>
                      <StatusCell status={cell.status} />
                    </td>
                  ))}
                </tr>
              ))
            )}
          </tbody>
          <tfoot className="bg-gray-50 dark:bg-gray-800">
            <tr data-testid="availability-matrix-summary">
              <td className="px-3 py-2 font-semibold text-gray-700 dark:text-gray-300">Available</td>
              {sessions.map((s) => (
                <td key={s} className="px-3 py-2 text-gray-700 dark:text-gray-300">
                  {summary?.available_counts?.[s] ?? 0}
                </td>
              ))}
            </tr>
          </tfoot>
        </table>
      </div>
    </div>
  );
}
