/**
 * AssignmentList — embedded "Form assignments" section in the LT template builder.
 *
 * Renders all TemplateAssignments for a published template. Shows status badges,
 * target name, date range, required chip, and per-status actions (Cancel for
 * scheduled, End today for active). Gated on status === 'published' in the parent.
 *
 * FA-E, Step 7_20 frontend.
 */

import { useCallback, useEffect, useState } from 'react';
import { cancelAssignment, listAssignments, patchAssignment } from '../../api/leadershipTeam';
import AssignmentRow from './AssignmentRow';

function today() {
  return new Date().toISOString().slice(0, 10);
}

function Skeleton() {
  return (
    <div className="space-y-2 animate-pulse" data-testid="assignment-list-skeleton">
      {[0, 1, 2].map((i) => (
        <div key={i} className="h-14 rounded-md bg-gray-100 dark:bg-gray-700" />
      ))}
    </div>
  );
}

/**
 * @param {object} props
 * @param {number|string} props.templateId
 * @param {string} props.orgSlug
 * @param {number} props.refreshKey — increment to force a reload (e.g. after a new assignment)
 */
export default function AssignmentList({ templateId, orgSlug, refreshKey = 0 }) {
  const [assignments, setAssignments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    if (!templateId) return;
    setLoading(true);
    setError('');
    try {
      const data = await listAssignments(orgSlug, { template: templateId });
      setAssignments(data?.assignments ?? data?.results ?? []);
    } catch {
      setError('Failed to load assignments. Refresh the page to try again.');
    } finally {
      setLoading(false);
    }
  }, [orgSlug, templateId]);

  useEffect(() => { load(); }, [load, refreshKey]);

  const handleCancelled = async (assignment) => {
    await cancelAssignment(orgSlug, assignment.id);
    await load();
  };

  const handleEnded = async (assignment) => {
    await patchAssignment(orgSlug, assignment.id, { end_date: today() });
    await load();
  };

  return (
    <section
      className="rounded-xl border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900/40 p-4 space-y-3"
      aria-label="Form assignments"
      data-testid="assignment-list-section"
    >
      <h2 className="text-base font-semibold text-gray-900 dark:text-white">
        Form assignments
      </h2>

      {loading && <Skeleton />}

      {!loading && error && (
        <p
          className="text-sm text-red-600 dark:text-red-400"
          data-testid="assignment-list-error"
        >
          {error}
        </p>
      )}

      {!loading && !error && assignments.length === 0 && (
        <p
          className="text-sm text-gray-500 dark:text-gray-400 italic"
          data-testid="assignment-list-empty"
        >
          No assignments yet — click &quot;Assign form&quot; to make this form available to staff.
        </p>
      )}

      {!loading && !error && assignments.length > 0 && (
        <ul className="space-y-2" data-testid="assignment-list">
          {assignments.map((a) => (
            <AssignmentRow
              key={a.id}
              assignment={a}
              onCancelled={handleCancelled}
              onEnded={handleEnded}
            />
          ))}
        </ul>
      )}
    </section>
  );
}
