/**
 * One Sunday's availability, person by person (Step 4_9 §6.3 drill-down).
 *
 * The Director coverage grid only carries counts, so this answers the question
 * those counts raise: who is in, who is out, and who never answered. Opened
 * from a date header (whole program) or a single cell (one classroom).
 * Classroom faculty appear alongside their Madrichim, badged, since chasing
 * an unanswered teacher is the same job as chasing an unanswered teen.
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

export function formatSunday(iso) {
  if (!iso) return '';
  const d = new Date(`${iso}T00:00:00`);
  return Number.isNaN(d.getTime())
    ? iso
    : d.toLocaleDateString(undefined, { weekday: 'long', month: 'long', day: 'numeric' });
}

function sameId(a, b) {
  return String(a) === String(b);
}

function availableCount(rows) {
  return rows.filter((p) => p.status === 'available').length;
}

/** "0 of 17 students" — the noun follows the membership role, not the grid. */
function tally(rows, noun) {
  if (!rows.length) return null;
  return `${availableCount(rows)} of ${rows.length} ${noun}`;
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
      {person.role === 'faculty' && (
        <span
          className="ml-2 text-[11px] font-medium px-1.5 py-0.5 rounded-full bg-indigo-100 text-indigo-800 dark:bg-indigo-900/40 dark:text-indigo-300"
          data-testid={`coverage-detail-faculty-${person.person_id}`}
        >
          Faculty
        </span>
      )}
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

export default function CoverageDetailModal({
  sessionDate,
  classroomId,
  classroomName = null,
  program,
  onClose,
  onClearClassroom,
}) {
  const [payload, setPayload] = useState(null);
  const [error, setError] = useState(null);
  const wantsClassroom = classroomId !== null && classroomId !== undefined && classroomId !== '';

  const load = useCallback(async () => {
    setPayload(null);
    setError(null);
    try {
      setPayload(await fetchDirectorCoverageDetail(sessionDate, { program }));
    } catch (err) {
      setError(err?.response?.status === 403
        ? 'Admin access required.'
        : 'Failed to load this Sunday.');
    }
  }, [sessionDate, program]);

  useEffect(() => { load(); }, [load]);

  useEffect(() => {
    const onKeyDown = (event) => { if (event.key === 'Escape') onClose(); };
    document.addEventListener('keydown', onKeyDown);
    return () => document.removeEventListener('keydown', onKeyDown);
  }, [onClose]);

  const allClassrooms = payload?.classrooms || [];
  const scoped = wantsClassroom
    ? allClassrooms.filter((room) => sameId(room.id, classroomId))
    : allClassrooms;
  const classroomMissing = Boolean(payload) && wantsClassroom && scoped.length === 0;
  const people = scoped.flatMap((room) => (
    (room.people || []).map((person) => ({ ...person, classroom_name: room.name }))
  ));
  const byStatus = (status) => people.filter((p) => (p.status || 'unset') === status);
  const faculty = people.filter((p) => p.role === 'faculty');
  const madrichim = people.filter((p) => p.role === 'madrich');
  const students = people.filter((p) => p.role !== 'faculty' && p.role !== 'madrich');
  const roomName = scoped.length === 1 ? scoped[0].name : classroomName;
  const summaryParts = [
    tally(students, students.length === 1 ? 'student' : 'students'),
    tally(madrichim, madrichim.length === 1 ? 'Madrich' : 'Madrichim'),
    tally(faculty, 'faculty'),
  ].filter(Boolean);
  const heading = roomName && wantsClassroom
    ? `${roomName} · ${formatSunday(sessionDate)}`
    : formatSunday(sessionDate);
  const summary = summaryParts.join(' · ');

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label={summary ? `${heading} — ${summary}` : heading}
      data-testid="coverage-detail-modal"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
    >
      <div className="w-full max-w-xl max-h-[85vh] overflow-y-auto rounded-xl bg-white dark:bg-gray-900 shadow-lg">
        <header className="flex items-start justify-between gap-3 px-5 py-4 border-b border-gray-200 dark:border-gray-700">
          <div className="min-w-0">
            <h2
              className="text-lg font-semibold text-gray-900 dark:text-white"
              data-testid="coverage-detail-summary"
            >
              {payload && summary ? `${heading} — ${summary}` : heading}
            </h2>
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

          {classroomMissing && (
            <p className="text-sm text-gray-500 dark:text-gray-400" data-testid="coverage-detail-empty">
              This group isn&apos;t on the roster for this Sunday.
            </p>
          )}

          {payload && !classroomMissing && people.length === 0 && (
            <p className="text-sm text-gray-500 dark:text-gray-400" data-testid="coverage-detail-empty">
              Nobody is rostered for this Sunday.
            </p>
          )}

          {payload && !classroomMissing && people.length > 0 && SECTIONS.map(({ status, heading: sectionHeading }) => {
            const rows = byStatus(status);
            return (
              <section key={status} data-testid={`coverage-detail-section-${status}`}>
                <h3 className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">
                  <span className={`px-2 py-0.5 rounded-full ${statusMeta(status).pill}`}>
                    {sectionHeading}
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

          {wantsClassroom && allClassrooms.length > 1 && (
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
