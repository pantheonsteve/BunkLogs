import { useEffect, useState } from 'react';
import { listAdminPrograms } from '../../../api/admin';
import { SUB_TABS, tabConfigFor } from './assignmentTabConfig';
import GroupMembershipTab from './GroupMembershipTab';
import SupervisionTab from './SupervisionTab';

export default function AssignmentsPage() {
  const [subTab, setSubTab] = useState(SUB_TABS[0].key);
  const [programs, setPrograms] = useState([]);
  const config = tabConfigFor(subTab);

  useEffect(() => {
    listAdminPrograms().then((data) => {
      setPrograms(data.results || []);
    });
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
        className="flex gap-2 overflow-x-auto pb-2 mb-6"
        aria-label="Assignment types"
      >
        {SUB_TABS.map((t) => {
          const active = subTab === t.key;
          return (
            <button
              key={t.key}
              type="button"
              data-testid={`assignment-sub-tab-${t.key}`}
              onClick={() => setSubTab(t.key)}
              className={[
                'shrink-0 rounded-xl px-4 py-2.5 text-left transition-colors min-w-[11rem]',
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

      {config.kind === 'group_membership' ? (
        <GroupMembershipTab key={config.key} config={config} programs={programs} />
      ) : (
        <SupervisionTab key={config.key} config={config} programs={programs} />
      )}
    </main>
  );
}
