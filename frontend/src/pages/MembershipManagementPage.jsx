import { useState } from 'react';
import { Link } from 'react-router-dom';
import MembershipTagsTab from './admin/memberships/MembershipTagsTab';
import ProgramRosterTab from './admin/memberships/ProgramRosterTab';

const SUB_TABS = [
  { key: 'roster', label: 'Program roster', subtitle: 'Browse programs and enrolled people' },
  { key: 'tags', label: 'Tags & bulk ops', subtitle: 'Edit tags and bulk updates' },
];

export default function MembershipManagementPage() {
  const [subTab, setSubTab] = useState('roster');

  return (
    <main className="grow px-4 sm:px-6 lg:px-8 py-6 w-full max-w-screen-2xl mx-auto" data-testid="admin-memberships">
      <Link
        to="/admin/home"
        data-testid="memberships-admin-back-link"
        className="inline-flex items-center gap-1 text-sm text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 mb-4"
      >
        ← Admin
      </Link>

      <header className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Memberships</h1>
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
          Browse program rosters, manage people, and tag memberships for grouping and reporting.
        </p>
      </header>

      <nav
        className="flex gap-2 overflow-x-auto pb-2 mb-6"
        aria-label="Membership views"
      >
        {SUB_TABS.map((t) => {
          const active = subTab === t.key;
          return (
            <button
              key={t.key}
              type="button"
              data-testid={`membership-sub-tab-${t.key}`}
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

      {subTab === 'roster' ? <ProgramRosterTab /> : <MembershipTagsTab />}
    </main>
  );
}
