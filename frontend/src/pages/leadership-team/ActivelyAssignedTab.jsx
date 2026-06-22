/**
 * Org-wide view of templates with active or scheduled assignments.
 * Shown as a tab on the admin template library (/admin/templates).
 */

import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { cancelAssignment, listAssignments, patchAssignment } from '../../api/leadershipTeam';
import AssignmentRow from './AssignmentRow';

const LIVE_STATUSES = new Set(['active', 'scheduled']);

function today() {
  return new Date().toISOString().slice(0, 10);
}

function statusBadge(status) {
  const map = {
    draft: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/40 dark:text-yellow-200',
    published: 'bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300',
    archived: 'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-300',
  };
  return map[status] ?? map.archived;
}

export default function ActivelyAssignedTab({ orgSlug, templates, refreshKey = 0, onChanged }) {
  const [assignments, setAssignments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const templatesById = useMemo(
    () => new Map(templates.map((t) => [t.id, t])),
    [templates],
  );

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const data = await listAssignments(orgSlug);
      setAssignments(data?.assignments ?? data?.results ?? []);
    } catch {
      setError('Failed to load assignments.');
    } finally {
      setLoading(false);
    }
  }, [orgSlug]);

  useEffect(() => { load(); }, [load, refreshKey]);

  const grouped = useMemo(() => {
    const live = assignments.filter((a) => LIVE_STATUSES.has(a.status));
    const byTemplate = new Map();
    for (const assignment of live) {
      const key = assignment.template;
      if (!byTemplate.has(key)) byTemplate.set(key, []);
      byTemplate.get(key).push(assignment);
    }
    return [...byTemplate.entries()].sort(([idA], [idB]) => {
      const nameA = templatesById.get(idA)?.name ?? '';
      const nameB = templatesById.get(idB)?.name ?? '';
      return nameA.localeCompare(nameB);
    });
  }, [assignments, templatesById]);

  const handleCancelled = async (assignment) => {
    await cancelAssignment(orgSlug, assignment.id);
    await load();
    onChanged?.();
  };

  const handleEnded = async (assignment) => {
    await patchAssignment(orgSlug, assignment.id, { end_date: today() });
    await load();
    onChanged?.();
  };

  if (loading) {
    return (
      <p className="text-gray-500 dark:text-gray-400 text-sm" data-testid="lt-tpl-assigned-loading">
        Loading assignments…
      </p>
    );
  }

  if (error) {
    return (
      <p className="text-red-600 dark:text-red-400 text-sm" data-testid="lt-tpl-assigned-error">
        {error}
      </p>
    );
  }

  if (grouped.length === 0) {
    return (
      <div
        className="rounded-xl border border-dashed border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 p-6 text-center text-sm text-gray-500 dark:text-gray-400"
        data-testid="lt-tpl-assigned-empty"
      >
        No templates are actively assigned. Publish a template and use Assign to make forms
        available to staff.
      </div>
    );
  }

  return (
    <div className="space-y-4" data-testid="lt-tpl-assigned-list">
      {grouped.map(([templateId, rows]) => {
        const tpl = templatesById.get(templateId);
        const title = tpl?.name ?? rows[0]?.display_title ?? `Template #${templateId}`;
        return (
          <section
            key={templateId}
            className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-4 space-y-3"
            data-testid={`lt-tpl-assigned-group-${templateId}`}
          >
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="flex items-center gap-2 flex-wrap min-w-0">
                <Link
                  to={`/admin/templates/${templateId}`}
                  className="font-medium text-gray-900 dark:text-white hover:underline truncate"
                >
                  {title}
                </Link>
                {tpl?.status && (
                  <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${statusBadge(tpl.status)}`}>
                    {tpl.status} v{tpl.version}
                  </span>
                )}
                {tpl?.role && (
                  <span className="text-xs text-gray-500 dark:text-gray-400">
                    {tpl.role.replace(/_/g, ' ')}
                  </span>
                )}
                <span className="text-xs text-gray-500 dark:text-gray-400">
                  {rows.length} assignment{rows.length === 1 ? '' : 's'}
                  {' · '}
                  {rows.reduce((n, r) => n + (r.reflection_count ?? 0), 0)} response
                  {rows.reduce((n, r) => n + (r.reflection_count ?? 0), 0) === 1 ? '' : 's'}
                </span>
              </div>
              <div className="flex items-center gap-2 shrink-0">
                <Link
                  to={`/admin/templates/${templateId}/responses`}
                  className="text-xs text-indigo-600 dark:text-indigo-400 hover:underline"
                  data-testid={`lt-tpl-assigned-responses-${templateId}`}
                >
                  Responses
                </Link>
                <Link
                  to={`/admin/templates/${templateId}`}
                  className="text-xs rounded-md border border-indigo-300 dark:border-indigo-700 px-2 py-1 text-indigo-700 dark:text-indigo-300 hover:bg-indigo-50 dark:hover:bg-indigo-900/30"
                  data-testid={`lt-tpl-assigned-edit-${templateId}`}
                >
                  Edit
                </Link>
              </div>
            </div>
            <ul className="space-y-2">
              {rows.map((assignment) => (
                <AssignmentRow
                  key={assignment.id}
                  assignment={assignment}
                  onCancelled={handleCancelled}
                  onEnded={handleEnded}
                  variant="detailed"
                  endWhenLive
                />
              ))}
            </ul>
          </section>
        );
      })}
    </div>
  );
}
