/**
 * One Sunday's availability, person by person (Step 4_9 §6.3 drill-down).
 *
 * The Director coverage grid only carries counts, so this answers the question
 * those counts raise: who is in, who is out, and who never answered. Opened
 * from a date header (whole program) or a single cell (one classroom).
 */
import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { X } from 'lucide-react';

import { fetchDirectorCoverageDetail } from '../../api/director';
import { statusMeta } from '../../utils/availabilityStatus';
import ErrorPanel from '../ui/ErrorPanel';
import LoadingState from '../ui/LoadingState';

/** Most actionable last: "nobody answered" is what a Director chases. */
const SECTIONS = [
  { status: 'available', heading: 'Available' },
  { status: 'tentative', heading: 'Tentative' },
  { status: 'unavailable', heading: 'Unavailable' },
  { status: 'unset', heading: 'No answer yet' },
];

function formatSunday(iso) {
  if (!iso) return '';
  const d = new Date(`${iso}T00:00:00`);
  return Number.isNaN(d.getTime())
    ? iso
    : d.toLocaleDateString(undefined, { weekday: 'long', month: 'long', day: 'numeric' });
}

function PersonRow({ person, showClassroom }) {
  const meta = [
    person.grade_level != null ? `Grade ${person.grade_level}` : null,
    showClassroom ? person.classroom_name : null,
  ].filter(Boolean).join(' · ');

  const body = (
    <>
      <span className="font-medium text-gray-900 dark:text-white">
        {person.display_name || 'Unnamed'}
      </span>
      {meta && <span className="ml-2 text-xs text-gray-500 dark:text-gray-400">{meta}</span>}
      {person.note && (
        <span className="block text-xs text-gray-600 dark:text-gray-300 mt-0.5">{person.note}</span>
      )}
    </>
  );

  return (
    <li data-testid={`coverage-detail-person-${person.person_id}`}>
      {person.membership_id ? (
        <Link
          to={`/admin/reflections/madrich/members/${person.membership_id}`}
          className="block rounded-lg px-2 py-1.5 hover:bg-gray-50 dark:hover:bg-gray-800"
        >
          {body}
        </Link>
      ) : (
        <div className="px-2 py-1.5">{body}</div>
      )}
    </li>
  );
}

export default function CoverageDetailModal({ sessionDate, classroomId, onClose, onClearClassroom }) {
  const [payload, setPayload] = useState(null);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    setPayload(null);
    setError(null);
    try {
      setPayload(await fetchDirectorCoverageDetail(sessionDate));
    } catch (err) {
      setError(err?.response?.status === 403
        ? 'Admin access required.'
        : 'Failed to load this Sunday.');
    }
  }, [sessionDate]);

  useEffect(() => { load(); }, [load]);

  useEffect(() => {
    const onKeyDown = (event) => { if (event.key === 'Escape') onClose(); };
    document.addEventListener('keydown', onKeyDown);
    return () => document.removeEventListener('keydown', onKeyDown);
  }, [onClose]);

  const allClassrooms = payload?.classrooms || [];
  const scoped = classroomId != null
    ? allClassrooms.filter((room) => room.id === classroomId)
    : allClassrooms;
  const people = scoped.flatMap((room) => (
    (room.people || []).map((person) => ({ ...person, classroom_name: room.name }))
  ));
  const byStatus = (status) => people.filter((p) => (p.status || 'unset') === status);
  const availableCount = byStatus('available').length;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label={`Availability for ${formatSunday(sessionDate)}`}
      data-testid="coverage-detail-modal"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
    >
      <div className="w-full max-w-xl max-h-[85vh] overflow-y-auto rounded-xl bg-white dark:bg-gray-900 shadow-lg">
        <header className="flex items-start justify-between gap-3 px-5 py-4 border-b border-gray-200 dark:border-gray-700">
          <div className="min-w-0">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
              {formatSunday(sessionDate)}
            </h2>
            {payload && (
              <p className="text-sm text-gray-600 dark:text-gray-300 mt-0.5" data-testid="coverage-detail-summary">
                {availableCount} of {people.length} available
                {scoped.length === 1 ? ` · ${scoped[0].name}` : ''}
              </p>
            )}
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close"
            data-testid="coverage-detail-close"
            className="shrink-0 rounded-lg p-1 text-gray-400 hover:text-gray-600 hover:bg-gray-100 dark:hover:bg-gray-800 dark:hover:text-gray-200"
          >
            <X className="w-5 h-5" aria-hidden="true" />
          </button>
        </header>

        <div className="px-5 py-4 space-y-4">
          {error && <ErrorPanel>{error}</ErrorPanel>}
          {!error && !payload && <LoadingState>Loading…</LoadingState>}

          {payload && people.length === 0 && (
            <p className="text-sm text-gray-500 dark:text-gray-400" data-testid="coverage-detail-empty">
              No Madrichim are rostered for this Sunday.
            </p>
          )}

          {payload && people.length > 0 && SECTIONS.map(({ status, heading }) => {
            const rows = byStatus(status);
            return (
              <section key={status} data-testid={`coverage-detail-section-${status}`}>
                <h3 className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">
                  <span className={`px-2 py-0.5 rounded-full ${statusMeta(status).pill}`}>
                    {heading}
                  </span>
                  {rows.length}
                </h3>
                {rows.length === 0 ? (
                  <p className="mt-1 px-2 text-sm text-gray-400 dark:text-gray-500">Nobody</p>
                ) : (
                  <ul className="mt-1 divide-y divide-gray-100 dark:divide-gray-800">
                    {rows.map((person) => (
                      <PersonRow
                        key={`${person.person_id}-${person.classroom_name}`}
                        person={person}
                        showClassroom={scoped.length > 1}
                      />
                    ))}
                  </ul>
                )}
              </section>
            );
          })}

          {classroomId != null && allClassrooms.length > 1 && (
            <button
              type="button"
              onClick={onClearClassroom}
              data-testid="coverage-detail-all-classrooms"
              className="text-sm font-medium text-indigo-700 dark:text-indigo-300 hover:underline"
            >
              Show all classrooms
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
