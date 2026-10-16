import { useSearchParams } from 'react-router-dom';

import { useAuth } from '../auth/AuthContext';
import AssignmentTemplatesDashboard from '../dashboards/assignmentTemplates/AssignmentTemplatesDashboard';
import CompletionTab from './dashboards/reflections/CompletionTab';
import isSuperAdmin from '../utils/auth/isSuperAdmin';
import { hasCapability } from '../utils/auth/capability';
import { reflectionCompletionEnabled } from '../utils/auth/orgProfile';

function ReflectionTabs({ tab, onChange }) {
  const tabs = [
    { id: 'forms', label: 'Forms' },
    { id: 'completion', label: 'Completion' },
  ];
  return (
    <div className="mb-6 flex gap-1 border-b border-gray-200 dark:border-gray-700" role="tablist" aria-label="Reflections">
      {tabs.map((item) => {
        const selected = tab === item.id;
        return (
          <button
            key={item.id}
            type="button"
            role="tab"
            aria-selected={selected}
            onClick={() => onChange(item.id)}
            className={`-mb-px border-b-2 px-4 py-2 text-sm font-medium ${
              selected
                ? 'border-indigo-600 text-indigo-600 dark:text-indigo-400'
                : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200'
            }`}
            data-testid={`reflections-tab-${item.id}`}
          >
            {item.label}
          </button>
        );
      })}
    </div>
  );
}

/** Self-reflection template picker, plus a completion roster when the org has it on. */
export default function ReflectionsDashboardPage() {
  const { user } = useAuth();
  const [params, setParams] = useSearchParams();
  const isAdmin = isSuperAdmin(user) || hasCapability(user, 'admin');
  const showCompletion = isAdmin && reflectionCompletionEnabled(user);
  const tab = showCompletion && params.get('tab') === 'completion' ? 'completion' : 'forms';

  const setTab = (next) => {
    const updated = new URLSearchParams(params);
    if (next === 'completion') updated.set('tab', 'completion');
    else updated.delete('tab');
    setParams(updated, { replace: true });
  };

  const tabs = showCompletion
    ? <ReflectionTabs tab={tab} onChange={setTab} />
    : null;

  if (tab === 'completion') {
    return (
      <main className="grow px-4 sm:px-6 lg:px-8 py-8 w-full max-w-9xl mx-auto">
        {tabs}
        <CompletionTab />
      </main>
    );
  }

  return (
    <AssignmentTemplatesDashboard
      title="Reflections"
      description="Browse self-reflection forms, then open responses by audience, program, or group."
      scope="reflections"
      testIdPrefix="reflections"
      emptyLabel="reflections"
      adminBackTo="/admin/home"
      banner={tabs}
    />
  );
}
