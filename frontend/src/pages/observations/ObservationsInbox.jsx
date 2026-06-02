/**
 * ObservationsInbox — Inbox / Sent tabs with compose button (Step 7_23).
 * Route: /observations.
 */
import { useCallback, useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import ObservationComposer from '../../components/observations/ObservationComposer';
import { fetchObservationInbox, fetchObservationSent } from '../../api/observations';

const TABS = [
  { key: 'inbox', label: 'Inbox' },
  { key: 'sent', label: 'Sent' },
];

const SORT_OPTIONS = [
  { value: 'recent', label: 'Newest first' },
  { value: 'oldest', label: 'Oldest first' },
  { value: 'unread', label: 'Unread first' },
];

const SENSITIVITY_LABEL = {
  normal: 'Normal',
  sensitive: 'Sensitive',
  domain: 'Domain',
  confidential: 'Confidential',
};

function timeAgo(iso) {
  if (!iso) return '';
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

export default function ObservationsInbox() {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState('inbox');
  const [itemsByTab, setItemsByTab] = useState({ inbox: [], sent: [] });
  const [counts, setCounts] = useState({ inbox: null, sent: null });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [composing, setComposing] = useState(false);
  const [query, setQuery] = useState('');
  const [sort, setSort] = useState('recent');

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [inbox, sent] = await Promise.all([
        fetchObservationInbox(),
        fetchObservationSent(),
      ]);
      const inboxItems = inbox.results ?? inbox ?? [];
      const sentItems = sent.results ?? sent ?? [];
      setItemsByTab({ inbox: inboxItems, sent: sentItems });
      setCounts({
        inbox: inbox.count ?? inboxItems.length,
        sent: sent.count ?? sentItems.length,
      });
    } catch {
      setError('Failed to load observations.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  function handleSent(data) {
    if (data?.id) {
      navigate(`/observations/${data.id}`);
      return;
    }
    setActiveTab('sent');
    load();
  }

  const items = itemsByTab[activeTab] ?? [];

  const visibleItems = useMemo(() => {
    const q = query.trim().toLowerCase();
    const filtered = q
      ? items.filter((o) => {
          const subjects = (o.subjects_summary || '').toLowerCase();
          const author = (o.author?.full_name || '').toLowerCase();
          return subjects.includes(q) || author.includes(q);
        })
      : items;
    return [...filtered].sort((a, b) => {
      if (sort === 'unread' && !!a.unread !== !!b.unread) {
        return a.unread ? -1 : 1;
      }
      const at = new Date(a.last_activity_at || 0).getTime();
      const bt = new Date(b.last_activity_at || 0).getTime();
      return sort === 'oldest' ? at - bt : bt - at;
    });
  }, [items, query, sort]);

  return (
    <main className="grow">
      <div className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-9xl mx-auto">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mb-6">
          <div>
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Observations</h1>
            <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">
              Messages you have received and sent about campers and staff.
            </p>
          </div>
          <button
            type="button"
            onClick={() => setComposing(true)}
            className="inline-flex items-center justify-center gap-2 px-4 py-2 text-sm font-medium text-white bg-violet-600 hover:bg-violet-700 rounded-lg shadow-sm transition-colors shrink-0"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
            Compose
          </button>
        </div>

        <div className="flex flex-wrap gap-2 mb-5">
          {TABS.map((tab) => {
            const isActive = activeTab === tab.key;
            const count = counts[tab.key];
            return (
              <button
                key={tab.key}
                type="button"
                onClick={() => setActiveTab(tab.key)}
                aria-pressed={isActive}
                className={`inline-flex items-center gap-2 rounded-lg border px-4 py-2 text-sm font-medium transition-colors ${
                  isActive
                    ? 'border-violet-600 bg-violet-600 text-white shadow-sm'
                    : 'border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-700/60'
                }`}
              >
                {tab.label}
                {count != null && (
                  <span
                    data-testid={`observations-tab-count-${tab.key}`}
                    className={`inline-flex items-center justify-center min-w-[1.5rem] h-5 px-1.5 rounded-full text-xs font-bold leading-none ${
                      isActive
                        ? 'bg-white/25 text-white'
                        : 'bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-200'
                    }`}
                  >
                    {count}
                  </span>
                )}
              </button>
            );
          })}
        </div>

        {!loading && !error && items.length > 0 && (
          <div className="flex flex-col sm:flex-row sm:items-center gap-3 mb-4">
            <div className="relative flex-1">
              <svg
                className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
                aria-hidden="true"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-4.35-4.35M11 19a8 8 0 100-16 8 8 0 000 16z" />
              </svg>
              <input
                type="search"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Search by subject or author…"
                aria-label="Search observations"
                data-testid="observations-search"
                className="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 pl-9 pr-3 py-2 text-sm text-gray-800 dark:text-gray-100 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-violet-500/40 focus:border-violet-500"
              />
            </div>
            <label className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400 shrink-0">
              <span className="hidden sm:inline">Sort</span>
              <select
                value={sort}
                onChange={(e) => setSort(e.target.value)}
                aria-label="Sort observations"
                data-testid="observations-sort"
                className="rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm text-gray-800 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-violet-500/40 focus:border-violet-500"
              >
                {SORT_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>{opt.label}</option>
                ))}
              </select>
            </label>
          </div>
        )}

        {loading && (
          <div className="py-12 text-center text-gray-500 dark:text-gray-400">Loading…</div>
        )}
        {!loading && error && (
          <div className="rounded-xl border border-rose-200 dark:border-rose-900/40 bg-rose-50 dark:bg-rose-900/20 p-4 text-center text-sm text-rose-700 dark:text-rose-300">
            {error}
          </div>
        )}
        {!loading && !error && items.length === 0 && (
          <div className="rounded-xl border border-dashed border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 py-12 text-center text-gray-500 dark:text-gray-400">
            {activeTab === 'inbox' && 'Your observations inbox is empty.'}
            {activeTab === 'sent' && "You haven't sent any observations yet."}
          </div>
        )}
        {!loading && !error && items.length > 0 && visibleItems.length === 0 && (
          <div className="rounded-xl border border-dashed border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 py-12 text-center text-gray-500 dark:text-gray-400">
            No observations match your search.
          </div>
        )}
        {!loading && !error && visibleItems.length > 0 && (
          <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 shadow-sm overflow-hidden divide-y divide-gray-100 dark:divide-gray-700">
            {visibleItems.map((o) => (
              <button
                key={o.id}
                type="button"
                onClick={() => navigate(`/observations/${o.id}`)}
                className="block w-full text-left px-5 py-4 hover:bg-gray-50 dark:hover:bg-gray-700/40 transition-colors"
                data-testid="observation-inbox-item"
              >
                <div className="flex items-center justify-between gap-3">
                  <span className="flex items-center gap-2 min-w-0">
                    {o.unread && (
                      <span
                        className="h-2 w-2 shrink-0 rounded-full bg-violet-600"
                        aria-label="Unread"
                      />
                    )}
                    <span
                      className={`text-sm truncate ${
                        o.unread
                          ? 'font-semibold text-gray-900 dark:text-white'
                          : 'text-gray-700 dark:text-gray-300'
                      }`}
                    >
                      {o.subjects_summary || 'Observation'}
                    </span>
                  </span>
                  <span className="text-xs text-gray-400 dark:text-gray-500 shrink-0">
                    {timeAgo(o.last_activity_at)}
                  </span>
                </div>
                <div className="flex items-center gap-2 mt-1">
                  <span className="text-xs text-gray-500 dark:text-gray-400">
                    {o.viewer_is_author || activeTab === 'sent'
                      ? 'You wrote this'
                      : `From ${o.author?.full_name}`}
                  </span>
                  <span className="text-xs rounded-full bg-amber-50 dark:bg-amber-900/20 px-2 py-0.5 text-amber-800 dark:text-amber-200">
                    {SENSITIVITY_LABEL[o.sensitivity] ?? o.sensitivity}
                  </span>
                </div>
              </button>
            ))}
          </div>
        )}
      </div>

      {composing && (
        <ObservationComposer
          onClose={() => setComposing(false)}
          onSent={handleSent}
        />
      )}
    </main>
  );
}
