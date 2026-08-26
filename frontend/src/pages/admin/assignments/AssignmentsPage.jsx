import { useEffect, useMemo, useState } from 'react';
import { getAdminAssignmentFacets, listAdminPrograms } from '../../../api/admin';
import { useTerm } from '../../../context/OrgBrandingContext';
import { SUB_TABS, localizeSubTab, visibleSubTabs } from './assignmentTabConfig';
import GroupMembershipTab from './GroupMembershipTab';
import SupervisionTab from './SupervisionTab';
import SupervisorStatusTab from './SupervisorStatusTab';

// Spelled out so Tailwind's scanner sees every class it needs to generate.
const TAB_GRID_COLS = {
  1: 'xl:grid-cols-1',
  2: 'xl:grid-cols-2',
  3: 'xl:grid-cols-3',
  4: 'xl:grid-cols-4',
  5: 'xl:grid-cols-5',
  6: 'xl:grid-cols-6',
  7: 'xl:grid-cols-7',
};

export default function AssignmentsPage() {
  const [subTab, setSubTab] = useState(SUB_TABS[0].key);
  const [programs, setPrograms] = useState([]);
  const [facets, setFacets] = useState(null);
  const [showAllTabs, setShowAllTabs] = useState(false);

  const term = useTerm();
  const tabs = useMemo(
    () => visibleSubTabs(showAllTabs ? null : facets)
      .map((t) => localizeSubTab(t, term)),
    [facets, showAllTabs, term],
  );
  // Derive rather than sync via effect: facets arrive after first paint and may
  // hide whatever is selected, and a stale key would render an empty tab body.
  const activeKey = tabs.some((t) => t.key === subTab) ? subTab : tabs[0].key;
  const config = tabs.find((t) => t.key === activeKey) ?? tabs[0];
  const hiddenCount = SUB_TABS.length - tabs.length;

  useEffect(() => {
    listAdminPrograms().then((data) => {
      setPrograms(data.results || []);
    });
  }, []);

  useEffect(() => {
    // A failure here just means no filtering, which is the old behaviour.
    getAdminAssignmentFacets()
      .then(setFacets)
      .catch(() => setFacets(null));
  }, []);

  return (
    <main className="grow px-4 sm:px-6 lg:px-8 py-6 w-full max-w-screen-2xl mx-auto" data-testid="admin-assignments">
      <header className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Assignments</h1>
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
          Manage group memberships and supervision relationships with bulk assign and filters.
        </p>
      </header>

      <nav
        className={`grid grid-cols-2 md:grid-cols-3 ${TAB_GRID_COLS[tabs.length] || 'xl:grid-cols-7'} gap-2 mb-2`}
        aria-label="Assignment types"
      >
        {tabs.map((t) => {
          const active = activeKey === t.key;
          return (
            <button
              key={t.key}
              type="button"
              data-testid={`assignment-sub-tab-${t.key}`}
              onClick={() => setSubTab(t.key)}
              className={[
                'w-full rounded-xl px-4 py-2.5 text-left transition-colors',
                active
                  ? 'bg-indigo-600 text-white shadow-md'
                  : 'bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 text-gray-700 dark:text-gray-200 hover:border-indigo-300 dark:hover:border-indigo-600',
              ].join(' ')}
            >
              <span className="block text-sm font-semibold leading-tight">{t.label}</span>
              <span className={`block text-[11px] mt-0.5 leading-snug ${active ? 'text-indigo-100' : 'text-gray-500 dark:text-gray-400'}`}>
                {t.subtitle}
              </span>
            </button>
          );
        })}
      </nav>

      <div className="mb-6 min-h-[1.25rem]">
        {(hiddenCount > 0 || showAllTabs) && (
          <button
            type="button"
            data-testid="assignment-tabs-toggle"
            onClick={() => setShowAllTabs((v) => !v)}
            className="text-xs text-indigo-600 dark:text-indigo-400 hover:underline"
          >
            {showAllTabs
              ? 'Show only types used by this organization'
              : `Show all assignment types (${hiddenCount} hidden)`}
          </button>
        )}
      </div>

      {config.kind === 'group_membership' && (
        <GroupMembershipTab key={config.key} config={config} programs={programs} />
      )}
      {config.kind === 'supervision' && (
        <SupervisionTab key={config.key} config={config} programs={programs} />
      )}
      {config.kind === 'supervisor_status' && (
        <SupervisorStatusTab key={config.key} config={config} programs={programs} />
      )}
    </main>
  );
}
