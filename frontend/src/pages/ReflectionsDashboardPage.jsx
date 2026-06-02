import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { FileText } from 'lucide-react';
import api from '../api';
import Header from '../partials/Header';
import Sidebar from '../partials/Sidebar';

const STATUS_TABS = [
  { id: 'active', label: 'Active' },
  { id: 'completed', label: 'Completed' },
];

function todayIso() {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}

function titleCase(s) {
  if (!s) return '';
  return s.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}

function FormTile({ template, isoDate }) {
  return (
    <Link
      to={`/admin/templates/${template.template_id}/responses?date=${isoDate}`}
      data-testid={`reflections-form-tile-${template.template_id}`}
      className="flex flex-col gap-2 rounded-2xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-5 shadow-sm hover:shadow-md hover:border-indigo-300 dark:hover:border-indigo-600 transition-shadow"
    >
      <div className="flex items-start gap-3">
        <FileText className="w-5 h-5 shrink-0 text-indigo-500 mt-0.5" />
        <div className="min-w-0">
          <h3 className="text-base font-semibold text-gray-900 dark:text-white truncate">
            {template.display_title}
          </h3>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-0.5">
            {titleCase(template.cadence)}
            {' · '}
            {template.group_count ?? template.groups?.length ?? 0} group
            {(template.group_count ?? template.groups?.length ?? 0) === 1 ? '' : 's'}
          </p>
        </div>
      </div>
    </Link>
  );
}

/**
 * ReflectionsDashboardPage — form picker hub for the Reflections Dashboard.
 *
 * Lists assigned forms visible to the viewer (filtered by status, audience,
 * program, and group). Each tile links to the template responses page.
 */
export default function ReflectionsDashboardPage() {
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const [statusTab, setStatusTab] = useState('active');
  const [audience, setAudience] = useState('all');
  const [selectedProgram, setSelectedProgram] = useState('all');
  const [selectedGroup, setSelectedGroup] = useState('all');

  const [templates, setTemplates] = useState([]);
  const [loadingTemplates, setLoadingTemplates] = useState(true);
  const [templatesError, setTemplatesError] = useState(null);

  const isoDate = todayIso();

  const loadTemplates = useCallback(async () => {
    setLoadingTemplates(true);
    setTemplatesError(null);
    try {
      const { data: resp } = await api.get('/api/v1/dashboards/assignment-templates/', {
        params: {
          status: statusTab,
          date: isoDate,
        },
      });
      setTemplates(resp?.templates ?? []);
    } catch (e) {
      const status = e.response?.status;
      if (status === 403) setTemplatesError('access');
      else setTemplatesError(e.response?.data?.detail || 'Failed to load forms');
      setTemplates([]);
    } finally {
      setLoadingTemplates(false);
    }
  }, [statusTab, isoDate]);

  useEffect(() => {
    loadTemplates();
  }, [loadTemplates]);

  const audienceOptions = useMemo(() => {
    const types = new Set();
    templates.forEach((t) => (t.audience_types ?? []).forEach((x) => types.add(x)));
    return [...types].sort();
  }, [templates]);

  const filteredByAudience = useMemo(() => {
    if (audience === 'all') return templates;
    return templates.filter((t) => (t.audience_types ?? []).includes(audience));
  }, [templates, audience]);

  const programs = useMemo(() => {
    const byId = new Map();
    filteredByAudience.forEach((t) => {
      (t.groups ?? []).forEach((g) => {
        if (g.program_id != null && !byId.has(g.program_id)) {
          byId.set(g.program_id, { id: g.program_id, label: g.program_label });
        }
      });
    });
    return [...byId.values()].sort((a, b) => a.label.localeCompare(b.label));
  }, [filteredByAudience]);

  const groups = useMemo(() => {
    const scoped = filteredByAudience.flatMap((t) => t.groups ?? []);
    const filtered = selectedProgram === 'all'
      ? scoped
      : scoped.filter((g) => String(g.program_id) === selectedProgram);
    const byId = new Map();
    filtered.forEach((g) => {
      if (!byId.has(g.assignment_id)) byId.set(g.assignment_id, g);
    });
    return [...byId.values()].sort((a, b) => a.label.localeCompare(b.label));
  }, [filteredByAudience, selectedProgram]);

  useEffect(() => {
    setSelectedProgram('all');
    setSelectedGroup('all');
  }, [audience, statusTab]);

  useEffect(() => {
    setSelectedGroup('all');
  }, [selectedProgram]);

  const visibleTemplates = useMemo(() => {
    return filteredByAudience.filter((t) => {
      const templateGroups = t.groups ?? [];
      if (selectedProgram !== 'all' && !templateGroups.some(
        (g) => String(g.program_id) === selectedProgram,
      )) {
        return false;
      }
      if (selectedGroup !== 'all' && !templateGroups.some(
        (g) => String(g.assignment_id) === selectedGroup,
      )) {
        return false;
      }
      return true;
    });
  }, [filteredByAudience, selectedProgram, selectedGroup]);

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} />
      <div className="relative flex flex-col flex-1 overflow-y-auto overflow-x-hidden">
        <Header sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} />
        <main className="grow px-4 sm:px-6 lg:px-8 py-8 w-full max-w-9xl mx-auto">
          <div className="mb-6">
            <h1 className="text-2xl font-semibold text-gray-900 dark:text-white">Reflections Dashboard</h1>
            <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
              Filter by audience, program, or group, then open a form to view its responses.
            </p>
          </div>

          <div className="mb-6 rounded-2xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 shadow-sm">
            <div className="flex gap-1 border-b border-gray-100 dark:border-gray-700/60 px-4 pt-2">
              {STATUS_TABS.map((tab) => (
                <button
                  key={tab.id}
                  type="button"
                  onClick={() => setStatusTab(tab.id)}
                  className={`-mb-px border-b-2 px-4 py-2 text-sm font-medium ${
                    statusTab === tab.id
                      ? 'border-indigo-600 text-indigo-600 dark:text-indigo-400'
                      : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200'
                  }`}
                  aria-pressed={statusTab === tab.id}
                >
                  {tab.label}
                </button>
              ))}
            </div>

            <div className="flex flex-col gap-3 p-4 sm:flex-row sm:flex-wrap sm:items-end">
              <label className="flex flex-col gap-1 text-sm text-gray-700 dark:text-gray-300">
                <span className="text-xs uppercase text-gray-500 dark:text-gray-400">Audience</span>
                <select
                  value={audience}
                  onChange={(e) => setAudience(e.target.value)}
                  className="rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-1.5 text-sm"
                  aria-label="Filter by audience"
                >
                  <option value="all">All audiences</option>
                  {audienceOptions.map((t) => (
                    <option key={t} value={t}>{titleCase(t)}</option>
                  ))}
                </select>
              </label>

              {programs.length > 1 && (
                <label className="flex flex-col gap-1 text-sm text-gray-700 dark:text-gray-300">
                  <span className="text-xs uppercase text-gray-500 dark:text-gray-400">Program</span>
                  <select
                    value={selectedProgram}
                    onChange={(e) => setSelectedProgram(e.target.value)}
                    className="rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-1.5 text-sm min-w-[12rem]"
                    aria-label="Filter by program"
                  >
                    <option value="all">All programs ({programs.length})</option>
                    {programs.map((p) => (
                      <option key={p.id} value={String(p.id)}>
                        {p.label}
                      </option>
                    ))}
                  </select>
                </label>
              )}

              {groups.length > 1 && (
                <label className="flex flex-col gap-1 text-sm text-gray-700 dark:text-gray-300">
                  <span className="text-xs uppercase text-gray-500 dark:text-gray-400">Group</span>
                  <select
                    value={selectedGroup}
                    onChange={(e) => setSelectedGroup(e.target.value)}
                    className="rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-1.5 text-sm min-w-[12rem]"
                    aria-label="Filter by group"
                  >
                    <option value="all">All groups ({groups.length})</option>
                    {groups.map((g) => (
                      <option key={g.assignment_id} value={String(g.assignment_id)}>
                        {g.label}
                      </option>
                    ))}
                  </select>
                </label>
              )}
            </div>
          </div>

          {loadingTemplates && (
            <p className="text-gray-500 dark:text-gray-400 text-sm">Loading forms…</p>
          )}

          {!loadingTemplates && templatesError === 'access' && (
            <div className="rounded-lg border border-amber-200 dark:border-amber-900/40 bg-amber-50 dark:bg-amber-900/20 p-4 text-amber-900 dark:text-amber-100">
              <p className="font-medium">Access restricted</p>
              <p className="text-sm mt-1">
                This dashboard requires a multi-tenant <strong>admin</strong>, a supervising{' '}
                <strong>leadership team</strong> / <strong>unit head</strong> role, or an explicit grant.
              </p>
              <Link to="/dashboard" className="text-sm underline mt-2 inline-block">
                Back to dashboard
              </Link>
            </div>
          )}

          {!loadingTemplates && templatesError && templatesError !== 'access' && (
            <p className="text-rose-600 dark:text-rose-400 text-sm">{templatesError}</p>
          )}

          {!loadingTemplates && !templatesError && templates.length === 0 && (
            <p className="text-gray-500 dark:text-gray-400 text-sm">
              No {statusTab} forms are visible to you.
            </p>
          )}

          {!loadingTemplates && !templatesError && templates.length > 0 && visibleTemplates.length === 0 && (
            <p className="text-gray-500 dark:text-gray-400 text-sm">
              No forms match these filters.
            </p>
          )}

          {!loadingTemplates && !templatesError && visibleTemplates.length > 0 && (
            <div
              className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4"
              data-testid="reflections-form-tiles"
            >
              {visibleTemplates.map((t) => (
                <FormTile key={t.template_id} template={t} isoDate={isoDate} />
              ))}
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
