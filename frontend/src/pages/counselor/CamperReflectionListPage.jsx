/**
 * Camper reflection roster — Step 7_6d (Story 3).
 *
 * Lists each bunk the counselor authors on with per-camper submission
 * state for a given date. Two URL shapes:
 *
 *   /counselor/camper-reflections        → today's roster
 *   /counselor/camper-reflections/:date  → historical (read-only) view
 *
 * The endpoint already differentiates editable from read-only via the
 * `editable` flag on each row and on the response root. Today's view
 * shows "Add reflection" CTAs for missing campers and "Edit" for
 * submitted ones; past dates show submitted-only rows with no CTAs.
 *
 * Off-camp campers are rendered in a dedicated subsection per bunk and
 * are not actionable.
 */

import { useCallback, useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { fetchCamperReflections } from '../../api/counselor';

function CamperRow({ camper, bunkId, editable, dateIsToday }) {
  const submitted = !!camper.submitted;
  const submitter = camper.submitter;
  const wasMine = submitter?.is_self;
  const submitterName = submitter && !wasMine ? submitter.name : null;

  return (
    <li
      data-testid={`camper-row-${camper.id}`}
      data-submitted={submitted ? 'true' : 'false'}
      className="flex items-center justify-between gap-3 py-3 border-b border-gray-100 dark:border-gray-800 last:border-b-0"
    >
      <div className="min-w-0">
        <p className="text-sm font-medium text-gray-900 dark:text-white truncate">
          {camper.name}
        </p>
        {submitted ? (
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
            {wasMine ? 'Submitted by you' : submitterName ? `Submitted by ${submitterName}` : 'Submitted'}
          </p>
        ) : (
          <p className="text-xs text-amber-700 dark:text-amber-300 mt-0.5">
            Needs reflection
          </p>
        )}
      </div>
      {submitted && camper.editable && dateIsToday ? (
        <Link
          data-testid={`camper-row-${camper.id}-edit`}
          to={`/counselor/camper-reflections/${camper.reflection_id}/edit`}
          className="shrink-0 inline-flex items-center justify-center min-h-[44px] px-3 rounded-lg border border-gray-300 dark:border-gray-600 text-sm font-medium text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-800"
        >
          Edit
        </Link>
      ) : !submitted && editable ? (
        <Link
          data-testid={`camper-row-${camper.id}-new`}
          to={`/counselor/camper-reflections/new?subject=${camper.id}&bunk=${bunkId}&name=${encodeURIComponent(camper.name || '')}`}
          className="shrink-0 inline-flex items-center justify-center min-h-[44px] px-3 rounded-lg bg-blue-600 text-white text-sm font-medium hover:bg-blue-700"
        >
          Add
        </Link>
      ) : (
        <span
          data-testid={`camper-row-${camper.id}-readonly`}
          className="shrink-0 text-xs text-gray-400 dark:text-gray-500"
        >
          Read-only
        </span>
      )}
    </li>
  );
}

function OffCampList({ rows }) {
  if (!rows?.length) return null;
  return (
    <div className="mt-4 pt-3 border-t border-dashed border-gray-200 dark:border-gray-700">
      <p className="text-xs uppercase tracking-wide text-gray-500 dark:text-gray-400 mb-2">
        Off-camp today
      </p>
      <ul className="space-y-1">
        {rows.map((row) => (
          <li
            key={row.id}
            data-testid={`off-camp-row-${row.id}`}
            className="text-sm text-gray-700 dark:text-gray-300"
          >
            {row.name}
            <span className="ml-2 text-xs text-gray-400 dark:text-gray-500">(not counted)</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

function BunkCard({ bunk, editable, dateIsToday }) {
  return (
    <section
      data-testid={`bunk-card-${bunk.id}`}
      className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 px-4 py-4 shadow-sm"
    >
      <header className="flex items-center justify-between mb-2">
        <div>
          <h2 className="text-base font-semibold text-gray-900 dark:text-white">
            {bunk.name}
          </h2>
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
            {bunk.covered}/{bunk.total} covered
          </p>
        </div>
        <span
          data-testid={`bunk-card-${bunk.id}-state`}
          className={`text-xs font-medium px-2 py-0.5 rounded-full ${
            bunk.total === 0 || bunk.covered >= bunk.total
              ? 'bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-200'
              : 'bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-200'
          }`}
        >
          {bunk.total === 0 ? 'No campers' : bunk.covered >= bunk.total ? 'Done' : 'In progress'}
        </span>
      </header>

      {bunk.campers?.length ? (
        <ul>
          {bunk.campers.map((camper) => (
            <CamperRow
              key={camper.id}
              camper={camper}
              bunkId={bunk.id}
              editable={editable}
              dateIsToday={dateIsToday}
            />
          ))}
        </ul>
      ) : (
        <p className="text-sm text-gray-500 dark:text-gray-400">
          No campers on roster.
        </p>
      )}

      <OffCampList rows={bunk.off_camp} />
    </section>
  );
}

export default function CamperReflectionListPage() {
  const { date: dateParam } = useParams();
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const payload = await fetchCamperReflections({ date: dateParam });
      setData(payload);
    } catch (err) {
      const detail = err?.response?.data?.detail;
      const status = err?.response?.status;
      if (status === 400) {
        setError(typeof detail === 'string' ? detail : 'Invalid date.');
      } else if (status === 403) {
        setError(typeof detail === 'string' ? detail : 'You do not have access to camper reflections.');
      } else {
        setError(typeof detail === 'string' ? detail : 'Could not load the roster.');
      }
    } finally {
      setLoading(false);
    }
  }, [dateParam]);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <div className="px-4 sm:px-6 lg:px-8 py-8 pb-24 w-full max-w-[96rem] mx-auto space-y-4">
        <header>
          <button
            type="button"
            onClick={() => navigate('/counselor')}
            className="text-xs text-blue-600 dark:text-blue-400 mb-1 flex items-center gap-1"
          >
            ← Back to dashboard
          </button>
          <h1 className="text-2xl font-semibold text-gray-900 dark:text-white">
            Camper reflections
          </h1>
          {data?.date ? (
            <p className="text-sm text-gray-600 dark:text-gray-400">
              {data.date}
              {!data.editable ? (
                <span
                  data-testid="camper-roster-readonly-banner"
                  className="ml-2 inline-flex items-center text-xs font-medium px-2 py-0.5 rounded-full bg-gray-200 text-gray-700 dark:bg-gray-800 dark:text-gray-200"
                >
                  Read-only
                </span>
              ) : null}
            </p>
          ) : null}
        </header>

        {loading ? (
          <p
            className="text-gray-600 dark:text-gray-400"
            data-testid="camper-roster-loading"
          >
            Loading roster…
          </p>
        ) : error ? (
          <div
            className="rounded-lg border border-amber-200 bg-amber-50 dark:bg-amber-950/40 dark:border-amber-800 px-4 py-3 text-sm text-amber-900 dark:text-amber-100"
            role="alert"
            data-testid="camper-roster-error"
          >
            {error}
          </div>
        ) : data?.bunks?.length ? (
          data.bunks.map((bunk) => (
            <BunkCard
              key={bunk.id}
              bunk={bunk}
              editable={data.editable}
              dateIsToday={data.editable}
            />
          ))
        ) : (
          <p
            className="text-gray-600 dark:text-gray-400"
            data-testid="camper-roster-empty"
          >
            You aren&apos;t assigned to any bunks.
          </p>
        )}
    </div>
  );
}
