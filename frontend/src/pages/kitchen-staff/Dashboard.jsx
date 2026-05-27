/**
 * Kitchen Staff dashboard — Step 7_11, Story 37.
 *
 * Three top-level sections (criterion 3):
 *   1. Header — name, role label "Kitchen Staff", active program, language selector.
 *   2. My reflection — today's status card with edit/start affordance.
 *   3. My reflections — history shortcut.
 *
 * No bunk lists, roster summaries, flag aggregates, or operational signal.
 */

import { useCallback, useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { fetchDashboard } from '../../api/kitchenStaff';
import LanguagePicker from '../../components/LanguagePicker';
import { useAuth } from '../../auth/AuthContext';

function ReflectionStatusCard({ myReflection, t }) {
  if (!myReflection) return null;
  const { state, reflection_id, editable } = myReflection;

  if (state === 'no_template') {
    return (
      <section
        aria-label={t('dashboard.myReflection')}
        className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-4"
        data-testid="ks-reflection-card"
      >
        <h2 className="text-base font-semibold text-gray-900 dark:text-white mb-1">
          {t('dashboard.myReflection')}
        </h2>
        <p className="text-sm text-gray-500 dark:text-gray-400">
          {t('dashboard.status.no_template')}
        </p>
      </section>
    );
  }

  const isComplete = state === 'complete' || state === 'day_off';
  const actionPath = editable && reflection_id
    ? `/kitchen-staff/reflection/${reflection_id}/edit`
    : '/kitchen-staff/reflection/new';

  const statusColors = {
    complete: 'bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-300',
    day_off: 'bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-300',
    missing: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/40 dark:text-yellow-300',
  };

  return (
    <section
      aria-label={t('dashboard.myReflection')}
      className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-4"
      data-testid="ks-reflection-card"
    >
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-base font-semibold text-gray-900 dark:text-white">
          {t('dashboard.myReflection')}
        </h2>
        <span
          className={`text-xs font-medium px-2 py-0.5 rounded-full ${statusColors[state] ?? statusColors.missing}`}
        >
          {t(`dashboard.status.${state}`, state)}
        </span>
      </div>
      <Link
        to={actionPath}
        className="mt-2 inline-block rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium px-4 py-2 transition-colors"
        data-testid="ks-reflection-cta"
      >
        {isComplete ? t('dashboard.editReflection') : t('dashboard.startReflection')}
      </Link>
    </section>
  );
}

export default function KitchenStaffDashboard() {
  const { t } = useTranslation('kitchen_staff');
  const { orgSlug } = useAuth();
  const navigate = useNavigate();

  const [dashboard, setDashboard] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    try {
      const data = await fetchDashboard(orgSlug);
      setDashboard(data);
      setError(null);
    } catch {
      setError(t('dashboard.loadFailed'));
    } finally {
      setLoading(false);
    }
  }, [orgSlug, t]);

  useEffect(() => {
    load();
  }, [load]);

  if (loading) {
    return (
      <div className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-[96rem] mx-auto" data-testid="ks-loading">
        <p className="text-gray-500 dark:text-gray-400">{t('dashboard.loading')}</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-[96rem] mx-auto" data-testid="ks-error">
        <p className="text-red-600 dark:text-red-400">{error}</p>
        <button
          onClick={load}
          className="mt-3 text-sm text-indigo-600 dark:text-indigo-400 underline"
        >
          Retry
        </button>
      </div>
    );
  }

  const { header, my_reflection, history_entry } = dashboard;

  return (
    <div className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-[96rem] mx-auto space-y-4">
      {/* Page title row with language picker */}
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm text-gray-500 dark:text-gray-400">{header.program_name}</p>
          <h1 className="text-xl font-bold text-gray-900 dark:text-white">{header.name}</h1>
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">{t('roleLabel')}</p>
        </div>
        <LanguagePicker orgSlug={orgSlug} />
      </div>

      <ReflectionStatusCard myReflection={my_reflection} t={t} />

      <section
        aria-label={t('dashboard.myReflections')}
        className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-4"
        data-testid="ks-history-section"
      >
        <div className="flex items-center justify-between">
          <h2 className="text-base font-semibold text-gray-900 dark:text-white">
            {t('dashboard.myReflections')}
          </h2>
          <Link
            to={history_entry?.url ?? '/kitchen-staff/history'}
            className="text-sm text-indigo-600 dark:text-indigo-400 hover:underline"
            data-testid="ks-history-link"
          >
            {t('dashboard.viewHistory')} →
          </Link>
        </div>
      </section>
    </div>
  );
}
