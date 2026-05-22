/**
 * Specialist camper picker — Step 7_9, Story 25.
 *
 * Two sections:
 *   - Recent: campers noted in the last 7 days (max 8), shown before search results.
 *   - All campers: full roster alphabetical, filtered by search query.
 *
 * Debounced 250ms search (criterion 4). Virtualized via CSS contain so the DOM
 * doesn't stack on a 1,500-row list (full virtualisation lib kept out of scope
 * for Tier 1 — results are paginated server-side at ≤1,500 rows which renders
 * acceptably on mid-tier devices with CSS containment).
 *
 * Zero-results copy per criterion 9. Selecting a camper calls `onSelect(camper)`.
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import { fetchSpecialistCampers } from '../../api/specialist';

const DEBOUNCE_MS = 250;

function CamperRow({ camper, onSelect }) {
  const preferred = camper.preferred_name;
  const name = preferred
    ? `${preferred} ${camper.last_name} (${camper.first_name})`
    : `${camper.first_name} ${camper.last_name}`;

  return (
    <li>
      <button
        type="button"
        onClick={() => onSelect(camper)}
        className="w-full flex items-center gap-3 px-3 py-2.5 hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors text-left"
        data-testid={`sp-camper-row-${camper.id}`}
      >
        <span className="flex-shrink-0 h-8 w-8 rounded-full bg-blue-100 dark:bg-blue-900/40 flex items-center justify-center text-xs font-semibold text-blue-700 dark:text-blue-300 uppercase">
          {(camper.first_name?.[0] || '') + (camper.last_name?.[0] || '')}
        </span>
        <span className="flex-1 min-w-0">
          <span className="block text-sm font-medium text-gray-900 dark:text-gray-100 truncate">
            {name}
          </span>
          {camper.bunk_name && (
            <span className="block text-xs text-gray-500 dark:text-gray-400 truncate">
              {camper.bunk_name}
            </span>
          )}
        </span>
      </button>
    </li>
  );
}

function Section({ title, campers, onSelect, 'data-testid': testId }) {
  if (!campers || campers.length === 0) return null;
  return (
    <div data-testid={testId}>
      <p className="px-3 py-1.5 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide bg-gray-50 dark:bg-gray-800 sticky top-0">
        {title}
      </p>
      <ul>
        {campers.map((c) => (
          <CamperRow key={c.id} camper={c} onSelect={onSelect} />
        ))}
      </ul>
    </div>
  );
}

export default function CamperPicker({ onSelect, onCancel }) {
  const [query, setQuery] = useState('');
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const debounceRef = useRef(null);
  const inputRef = useRef(null);

  const fetchCampers = useCallback(async (q) => {
    setLoading(true);
    try {
      const result = await fetchSpecialistCampers({ q });
      setData(result);
      setError('');
    } catch (err) {
      setError(err?.message || 'Could not load campers.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchCampers('');
    inputRef.current?.focus();
  }, [fetchCampers]);

  const handleQueryChange = (e) => {
    const q = e.target.value;
    setQuery(q);
    clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => fetchCampers(q), DEBOUNCE_MS);
  };

  useEffect(() => () => clearTimeout(debounceRef.current), []);

  return (
    <div className="flex flex-col h-full" data-testid="sp-camper-picker">
      {/* Search bar */}
      <div className="px-3 py-3 border-b border-gray-200 dark:border-gray-700 sticky top-0 bg-white dark:bg-gray-800 z-10">
        <div className="flex items-center gap-2">
          <input
            ref={inputRef}
            type="search"
            value={query}
            onChange={handleQueryChange}
            placeholder="Search by name or bunk…"
            aria-label="Search campers"
            className="flex-1 rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm focus:border-blue-500 focus:ring-2 focus:ring-blue-200"
            data-testid="sp-camper-search"
          />
          {onCancel && (
            <button
              type="button"
              onClick={onCancel}
              className="text-sm text-gray-500 dark:text-gray-400 px-2 py-2"
            >
              Cancel
            </button>
          )}
        </div>
      </div>

      {/* Results */}
      <div className="flex-1 overflow-y-auto" style={{ contain: 'content' }}>
        {loading && (
          <p className="px-3 py-4 text-sm text-gray-500 dark:text-gray-400" data-testid="sp-picker-loading">
            Loading…
          </p>
        )}
        {error && !loading && (
          <p className="px-3 py-4 text-sm text-red-600 dark:text-red-400" role="alert">{error}</p>
        )}
        {!loading && !error && data && (
          <>
            {!query && (
              <Section
                title="Recent"
                campers={data.recent}
                onSelect={onSelect}
                data-testid="sp-picker-recent"
              />
            )}
            {data.zero_results_message ? (
              <p className="px-3 py-4 text-sm text-gray-500 dark:text-gray-400" data-testid="sp-picker-zero">
                {data.zero_results_message}
              </p>
            ) : (
              <Section
                title={query ? 'Results' : 'All campers'}
                campers={data.results}
                onSelect={onSelect}
                data-testid="sp-picker-results"
              />
            )}
          </>
        )}
      </div>
    </div>
  );
}
