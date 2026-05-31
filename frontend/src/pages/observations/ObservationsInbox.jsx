/**
 * ObservationsInbox — Inbox / Sent tabs with compose button (Step 7_23).
 * Route: /observations.
 */
import { useCallback, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import ObservationComposer from '../../components/observations/ObservationComposer';
import { fetchObservationInbox, fetchObservationSent } from '../../api/observations';

const TABS = [
  { key: 'inbox', label: 'Inbox' },
  { key: 'sent', label: 'Sent' },
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
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [composing, setComposing] = useState(false);

  const load = useCallback(async (tab) => {
    setLoading(true);
    setError(null);
    try {
      const data = tab === 'sent' ? await fetchObservationSent() : await fetchObservationInbox();
      setItems(data.results ?? data);
    } catch {
      setError('Failed to load observations.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load(activeTab);
  }, [activeTab, load]);

  function handleTabChange(tab) {
    setActiveTab(tab);
    setItems([]);
  }

  function handleSent(data) {
    if (data?.id) {
      navigate(`/observations/${data.id}`);
      return;
    }
    setActiveTab('sent');
  }

  return (
    <main className="grow">
      <div className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-3xl mx-auto">
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-2xl font-semibold text-gray-800 dark:text-white">Observations</h1>
          <button
            type="button"
            onClick={() => setComposing(true)}
            className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-violet-600 hover:bg-violet-700 rounded-lg transition-colors"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
            Compose
          </button>
        </div>

        <div className="flex gap-1 mb-4 border-b border-gray-200 dark:border-gray-700">
          {TABS.map((tab) => (
            <button
              key={tab.key}
              type="button"
              onClick={() => handleTabChange(tab.key)}
              className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors ${
                activeTab === tab.key
                  ? 'border-violet-600 text-violet-600 dark:text-violet-400'
                  : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {loading && <div className="py-12 text-center text-gray-400">Loading…</div>}
        {!loading && error && <div className="py-8 text-center text-red-500">{error}</div>}
        {!loading && !error && items.length === 0 && (
          <div className="py-12 text-center text-gray-400">
            {activeTab === 'inbox' && 'Your observations inbox is empty.'}
            {activeTab === 'sent' && "You haven't sent any observations yet."}
          </div>
        )}
        {!loading && !error && items.length > 0 && (
          <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden divide-y divide-gray-100 dark:divide-gray-700">
            {items.map((o) => (
              <button
                key={o.id}
                type="button"
                onClick={() => navigate(`/observations/${o.id}`)}
                className="block w-full text-left px-5 py-4 hover:bg-gray-50 dark:hover:bg-gray-700/40"
                data-testid="observation-inbox-item"
              >
                <div className="flex items-center justify-between gap-3">
                  <span className={`text-sm ${o.unread ? 'font-semibold text-gray-900 dark:text-white' : 'text-gray-700 dark:text-gray-300'}`}>
                    {o.subjects_summary || 'Observation'}
                  </span>
                  <span className="text-xs text-gray-400 shrink-0">{timeAgo(o.last_activity_at)}</span>
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
