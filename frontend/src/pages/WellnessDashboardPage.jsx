import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import api from '../api';
import Header from '../partials/Header';
import Sidebar from '../partials/Sidebar';
import TemplateDashboard from '../dashboards/TemplateDashboard';

const WELLNESS_ROLES = new Set(['camper_care', 'health_center', 'special_diets', 'wellness']);

/**
 * WellnessDashboardPage — Wellness team dashboard.
 *
 * Fetches all active templates with a wellness-type role for the current org,
 * lets the user pick one, then renders TemplateDashboard for that template.
 */
export default function WellnessDashboardPage() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [templates, setTemplates] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [loadingTemplates, setLoadingTemplates] = useState(true);
  const [templatesError, setTemplatesError] = useState(null);

  const loadTemplates = useCallback(async () => {
    setLoadingTemplates(true);
    setTemplatesError(null);
    try {
      const { data } = await api.get('/api/v1/templates/', {
        params: { is_active: 'true' },
      });
      const list = Array.isArray(data) ? data : (data.results ?? []);
      const wellnessTemplates = list.filter((t) => WELLNESS_ROLES.has(t.role));
      setTemplates(wellnessTemplates);
      if (wellnessTemplates.length > 0) setSelectedId(wellnessTemplates[0].id);
    } catch (e) {
      const status = e.response?.status;
      if (status === 403) setTemplatesError('access');
      else setTemplatesError(e.response?.data?.detail || 'Failed to load templates');
    } finally {
      setLoadingTemplates(false);
    }
  }, []);

  useEffect(() => {
    loadTemplates();
  }, [loadTemplates]);

  const selected = templates.find((t) => t.id === selectedId);

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} />
      <div className="relative flex flex-col flex-1 overflow-y-auto overflow-x-hidden">
        <Header sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} />
        <main className="grow px-4 sm:px-6 lg:px-8 py-8 w-full max-w-9xl mx-auto">
          <div className="mb-6">
            <h1 className="text-2xl font-semibold text-gray-900 dark:text-white">Wellness team</h1>
            <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
              Camper Care, Health Center, and Special Diets reflection dashboard.
            </p>
          </div>

          {loadingTemplates && (
            <p className="text-gray-500 dark:text-gray-400 text-sm">Loading templates…</p>
          )}

          {!loadingTemplates && templatesError === 'access' && (
            <div className="rounded-lg border border-amber-200 dark:border-amber-900/40 bg-amber-50 dark:bg-amber-900/20 p-4 text-amber-900 dark:text-amber-100">
              <p className="font-medium">Access restricted</p>
              <p className="text-sm mt-1">
                The wellness dashboard requires a multi-tenant <strong>camper_care</strong>,{' '}
                <strong>health_center</strong>, <strong>special_diets</strong>, or{' '}
                <strong>admin</strong> program membership, or an account with the legacy{' '}
                <strong>Admin</strong> staff role.
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
              No active wellness team templates found.
            </p>
          )}

          {!loadingTemplates && templates.length > 0 && (
            <>
              {templates.length > 1 && (
                <div className="mb-6 flex items-center gap-3">
                  <label className="text-sm text-gray-700 dark:text-gray-300">Template</label>
                  <select
                    value={selectedId ?? ''}
                    onChange={(e) => setSelectedId(Number(e.target.value))}
                    className="rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-1.5 text-sm"
                    aria-label="Select template"
                  >
                    {templates.map((t) => (
                      <option key={t.id} value={t.id}>{t.name}</option>
                    ))}
                  </select>
                </div>
              )}

              {selectedId && (
                <TemplateDashboard
                  key={selectedId}
                  templateId={selectedId}
                  title={selected?.name}
                  subtitle="Wellness team aggregated reflections"
                  accentColor="teal"
                />
              )}
            </>
          )}
        </main>
      </div>
    </div>
  );
}
