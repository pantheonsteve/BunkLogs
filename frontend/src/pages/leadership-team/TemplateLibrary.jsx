/**
 * LT Template Library — Step 7_12, Story 51 entrypoint.
 *
 * Lists templates the LT viewer + their co-supervisors can see, with
 * filters by status / role and quick actions (open, publish, clone,
 * archive, view responses). The detail / edit surface lives in
 * ``TemplateBuilderPage``; clone calls the LT clone endpoint and
 * redirects to the new draft.
 */

import { useCallback, useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  archiveTemplate,
  cloneTemplate,
  listTemplates,
  publishTemplate,
} from '../../api/leadershipTeam';
import { useAuth } from '../../auth/AuthContext';

const STATUS_OPTIONS = [
  { value: '', label: 'All' },
  { value: 'draft', label: 'Draft' },
  { value: 'published', label: 'Published' },
  { value: 'archived', label: 'Archived' },
];

const ROLE_OPTIONS = [
  '', 'counselor', 'junior_counselor', 'specialist', 'general_counselor',
  'unit_head', 'leadership_team', 'kitchen_staff', 'maintenance',
  'housekeeping', 'camper_care', 'health_center', 'madrich', 'faculty',
];

function statusBadge(status) {
  const map = {
    draft: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/40 dark:text-yellow-200',
    published: 'bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300',
    archived: 'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-300',
  };
  return map[status] ?? map.archived;
}

export default function LeadershipTeamTemplateLibrary() {
  const navigate = useNavigate();
  const { orgSlug } = useAuth();
  const [templates, setTemplates] = useState([]);
  const [statusFilter, setStatusFilter] = useState('');
  const [roleFilter, setRoleFilter] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [actionPending, setActionPending] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const data = await listTemplates(orgSlug, {
        status: statusFilter || undefined,
        role: roleFilter || undefined,
      });
      const rows = Array.isArray(data?.templates) ? data.templates
        : Array.isArray(data?.results) ? data.results
        : Array.isArray(data) ? data : [];
      setTemplates(rows);
    } catch (err) {
      if (err?.response?.status === 403) setError('You do not have LT access.');
      else setError('Failed to load templates.');
    } finally {
      setLoading(false);
    }
  }, [orgSlug, statusFilter, roleFilter]);

  useEffect(() => { load(); }, [load]);

  const doAction = async (id, action) => {
    setActionPending(id);
    try {
      if (action === 'publish') {
        await publishTemplate(orgSlug, id);
      } else if (action === 'archive') {
        await archiveTemplate(orgSlug, id);
      } else if (action === 'clone') {
        const cloned = await cloneTemplate(orgSlug, id);
        if (cloned?.id) navigate(`/leadership-team/templates/${cloned.id}`);
        return;
      }
      await load();
    } catch (err) {
      const detail = err?.response?.data?.detail
        ?? err?.response?.data?.errors?.[0]
        ?? `Failed to ${action} template.`;
      setError(typeof detail === 'string' ? detail : JSON.stringify(detail));
    } finally {
      setActionPending(null);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <header className="bg-white dark:bg-gray-800 shadow-sm">
        <div className="max-w-5xl mx-auto px-4 py-4 flex items-center justify-between">
          <div>
            <Link
              to="/leadership-team"
              className="text-sm text-indigo-600 dark:text-indigo-400 hover:underline"
            >
              ← Back to LT dashboard
            </Link>
            <h1 className="text-xl font-bold text-gray-900 dark:text-white mt-2">
              Templates
            </h1>
          </div>
          <Link
            to="/leadership-team/templates/new"
            className="rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium px-3 py-1.5"
            data-testid="lt-templates-new"
          >
            New template
          </Link>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-4 py-6 space-y-4">
        <section
          className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-3 flex flex-wrap gap-3"
          aria-label="Filters"
        >
          <label className="text-sm text-gray-700 dark:text-gray-300">
            Status{' '}
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="ml-1 rounded-md border-gray-300 dark:border-gray-600 dark:bg-gray-700 text-sm"
              data-testid="lt-tpl-status-filter"
            >
              {STATUS_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>{o.label}</option>
              ))}
            </select>
          </label>
          <label className="text-sm text-gray-700 dark:text-gray-300">
            Role{' '}
            <select
              value={roleFilter}
              onChange={(e) => setRoleFilter(e.target.value)}
              className="ml-1 rounded-md border-gray-300 dark:border-gray-600 dark:bg-gray-700 text-sm"
              data-testid="lt-tpl-role-filter"
            >
              {ROLE_OPTIONS.map((r) => (
                <option key={r} value={r}>{r ? r.replace('_', ' ') : 'All'}</option>
              ))}
            </select>
          </label>
        </section>

        {error && (
          <p className="text-red-600 dark:text-red-400 text-sm" data-testid="lt-tpl-error">
            {error}
          </p>
        )}

        {loading ? (
          <p className="text-gray-500 dark:text-gray-400 text-sm" data-testid="lt-tpl-loading">
            Loading…
          </p>
        ) : templates.length === 0 ? (
          <div
            className="rounded-xl border border-dashed border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 p-6 text-center text-sm text-gray-500 dark:text-gray-400"
            data-testid="lt-tpl-empty"
          >
            No templates match the current filters.
          </div>
        ) : (
          <ul className="space-y-2" data-testid="lt-tpl-list">
            {templates.map((tpl) => (
              <li
                key={tpl.id}
                className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-3"
                data-testid={`lt-tpl-row-${tpl.id}`}
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <Link
                        to={`/leadership-team/templates/${tpl.id}`}
                        className="font-medium text-gray-900 dark:text-white hover:underline"
                      >
                        {tpl.name}
                      </Link>
                      <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${statusBadge(tpl.status)}`}>
                        {tpl.status} v{tpl.version}
                      </span>
                      {tpl.role && (
                        <span className="text-xs text-gray-500 dark:text-gray-400">
                          {tpl.role.replace('_', ' ')}
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                      {tpl.languages?.join(', ') ?? 'en'} · {tpl.cadence ?? 'daily'}
                    </p>
                  </div>
                  <div className="flex items-center gap-2 shrink-0 flex-wrap">
                    {tpl.status === 'draft' && (
                      <button
                        type="button"
                        onClick={() => doAction(tpl.id, 'publish')}
                        disabled={actionPending === tpl.id}
                        className="text-xs rounded-md bg-indigo-600 hover:bg-indigo-700 text-white px-2 py-1"
                        data-testid={`lt-tpl-publish-${tpl.id}`}
                      >
                        Publish
                      </button>
                    )}
                    {tpl.status === 'published' && (
                      <>
                        <Link
                          to={`/leadership-team/templates/${tpl.id}/responses`}
                          className="text-xs text-indigo-600 dark:text-indigo-400 hover:underline"
                          data-testid={`lt-tpl-responses-${tpl.id}`}
                        >
                          Responses
                        </Link>
                        <button
                          type="button"
                          onClick={() => doAction(tpl.id, 'archive')}
                          disabled={actionPending === tpl.id}
                          className="text-xs rounded-md border border-gray-300 dark:border-gray-600 px-2 py-1 text-gray-700 dark:text-gray-300"
                          data-testid={`lt-tpl-archive-${tpl.id}`}
                        >
                          Archive
                        </button>
                      </>
                    )}
                    <button
                      type="button"
                      onClick={() => doAction(tpl.id, 'clone')}
                      disabled={actionPending === tpl.id}
                      className="text-xs rounded-md border border-gray-300 dark:border-gray-600 px-2 py-1 text-gray-700 dark:text-gray-300"
                      data-testid={`lt-tpl-clone-${tpl.id}`}
                    >
                      Clone
                    </button>
                  </div>
                </div>
              </li>
            ))}
          </ul>
        )}
      </main>
    </div>
  );
}
