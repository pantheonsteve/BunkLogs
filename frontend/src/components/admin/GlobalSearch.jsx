import { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { searchAdmin } from '../../api/admin';

const GROUP_LABELS = {
  people: 'People',
  reflections: 'Reflections',
  notes: 'Notes',
  orders: 'Orders',
  tickets: 'Tickets',
  templates: 'Templates',
};

const MIN_LEN = 2;
const DEBOUNCE_MS = 300;

/**
 * Admin global search (Step 7_13 PR3, Story 60).
 *
 * Header-mounted input with a results dropdown grouped by content
 * type. Results are deep-linkable; keyboard nav is intentionally
 * simple (Esc closes; clicking anywhere outside closes; the
 * underlying <Link> handles Enter on a focused item).
 */
export default function GlobalSearch() {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState('');
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const containerRef = useRef(null);
  const debounceRef = useRef(null);

  useEffect(() => {
    function handleClick(e) {
      if (!containerRef.current?.contains(e.target)) {
        setOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, []);

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    const trimmed = query.trim();
    if (trimmed.length < MIN_LEN) {
      setResults(null);
      return undefined;
    }
    debounceRef.current = setTimeout(async () => {
      setLoading(true);
      setError(null);
      try {
        const data = await searchAdmin(trimmed);
        setResults(data?.groups || {});
      } catch (err) {
        setError(err);
      } finally {
        setLoading(false);
      }
    }, DEBOUNCE_MS);
    return () => debounceRef.current && clearTimeout(debounceRef.current);
  }, [query]);

  const totalHits = results
    ? Object.values(results).reduce((sum, arr) => sum + (arr?.length || 0), 0)
    : 0;

  return (
    <div ref={containerRef} className="relative" data-testid="global-search">
      <input
        type="search"
        value={query}
        onChange={(e) => { setQuery(e.target.value); setOpen(true); }}
        onFocus={() => setOpen(true)}
        onKeyDown={(e) => { if (e.key === 'Escape') setOpen(false); }}
        placeholder="Search people, reflections, notes…"
        className="w-80 rounded-md border border-gray-300 bg-white p-2 text-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
        aria-label="Admin global search"
      />
      {open && query.trim().length >= MIN_LEN && (
        <div
          role="listbox"
          data-testid="global-search-results"
          className="absolute right-0 mt-1 w-[28rem] max-h-[60vh] overflow-y-auto rounded-md border border-gray-200 bg-white shadow-xl z-50 dark:bg-gray-900 dark:border-gray-700"
        >
          {loading && <p className="p-3 text-sm text-gray-500">Searching…</p>}
          {error && <p className="p-3 text-sm text-red-700">Search failed.</p>}
          {!loading && !error && totalHits === 0 && (
            <p className="p-3 text-sm italic text-gray-500" data-testid="global-search-empty">
              No results for &ldquo;{query.trim()}&rdquo;.
            </p>
          )}
          {!loading && !error && totalHits > 0 && (
            <ul className="divide-y divide-gray-200 dark:divide-gray-700">
              {Object.entries(results || {}).map(([group, items]) => (
                (items || []).length > 0 && (
                  <li key={group} className="p-2" data-testid={`global-search-group-${group}`}>
                    <p className="text-xs font-semibold uppercase text-gray-500 px-2 pb-1">
                      {GROUP_LABELS[group] || group}
                    </p>
                    <ul>
                      {items.map((row) => (
                        <li key={`${group}-${row.id}`}>
                          <Link
                            to={row.deep_link || '/admin'}
                            onClick={() => setOpen(false)}
                            className="block rounded-md px-2 py-1.5 text-sm hover:bg-indigo-50 dark:hover:bg-indigo-900/20"
                          >
                            <span className="font-medium">{row.label}</span>
                            {row.secondary && (
                              <span className="block text-xs text-gray-500 truncate">{row.secondary}</span>
                            )}
                          </Link>
                        </li>
                      ))}
                    </ul>
                  </li>
                )
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
