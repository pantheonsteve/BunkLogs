/**
 * Section tabs for the admin home.
 *
 * The tab names are the same for every kind of organization; only the cards
 * inside them change. A tab with no content is left out, and with a single
 * tab left there is no tab bar at all. Panels stay mounted so switching tabs
 * does not refetch a card or collapse what the director had expanded. The
 * selection lives in `?tab=` so a link or the back button lands on it.
 */
import { useSearchParams } from 'react-router-dom';

import UnreadDot from '../ui/UnreadDot';

export default function DashboardTabs({ tabs, defaultTab, 'data-testid': testId }) {
  const [searchParams, setSearchParams] = useSearchParams();
  const visible = tabs.filter((tab) => tab.content);
  if (visible.length === 0) return null;
  if (visible.length === 1) return <div data-testid={testId}>{visible[0].content}</div>;

  const fallback = visible.some((tab) => tab.id === defaultTab) ? defaultTab : visible[0].id;
  const requested = searchParams.get('tab');
  const active = visible.some((tab) => tab.id === requested) ? requested : fallback;

  const select = (id) => {
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev);
      if (id === fallback) next.delete('tab');
      else next.set('tab', id);
      return next;
    }, { replace: true });
  };

  const onKeyDown = (event, index) => {
    const step = { ArrowRight: 1, ArrowLeft: -1 }[event.key];
    if (!step) return;
    event.preventDefault();
    const next = visible[(index + step + visible.length) % visible.length];
    select(next.id);
    document.getElementById(`dashboard-tab-${next.id}`)?.focus();
  };

  return (
    <div data-testid={testId}>
      <div
        role="tablist"
        aria-label="Dashboard sections"
        className="flex gap-1 overflow-x-auto border-b border-gray-200 dark:border-gray-700 mb-5"
      >
        {visible.map((tab, index) => {
          const selected = tab.id === active;
          return (
            <button
              key={tab.id}
              id={`dashboard-tab-${tab.id}`}
              type="button"
              role="tab"
              aria-selected={selected}
              aria-controls={`dashboard-panel-${tab.id}`}
              tabIndex={selected ? 0 : -1}
              onClick={() => select(tab.id)}
              onKeyDown={(event) => onKeyDown(event, index)}
              className={`inline-flex items-center gap-2 whitespace-nowrap px-3 py-2 text-sm font-semibold border-b-2 -mb-px transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-600 ${
                selected
                  ? 'border-indigo-600 text-indigo-700 dark:text-indigo-300'
                  : 'border-transparent text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200'
              }`}
              data-testid={`dashboard-tab-${tab.id}`}
            >
              {tab.label}
              <UnreadDot count={tab.badge} label={tab.badgeLabel} />
            </button>
          );
        })}
      </div>
      {visible.map((tab) => (
        <div
          key={tab.id}
          id={`dashboard-panel-${tab.id}`}
          role="tabpanel"
          aria-labelledby={`dashboard-tab-${tab.id}`}
          hidden={tab.id !== active}
          data-testid={`dashboard-panel-${tab.id}`}
        >
          {tab.content}
        </div>
      ))}
    </div>
  );
}
