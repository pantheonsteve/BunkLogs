/**
 * Specialist camper picker — Step 7_9, Story 25.
 *
 * Two selection paths:
 *   1. Bunk-first: pick a bunk from the dropdown, then pick a camper from
 *      the filtered list.
 *   2. Name search: type a name (debounced 250ms) to search across all bunks
 *      (or within the selected bunk if one is chosen).
 *
 * The response from /api/v1/specialist/campers/ includes a `bunks` array
 * used to populate the dropdown; `bunk_id` filters results server-side.
 *
 * Recent section shows campers noted in the last 7 days (no bunk filter).
 * Zero-results copy per criterion 9. Selecting a camper calls onSelect(camper).
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
  const [selectedBunkId, setSelectedBunkId] = useState('');
  const [bunks, setBunks] = useState([]);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const debounceRef = useRef(null);
  const inputRef = useRef(null);

  const fetchCampers = useCallback(async (q, bunkId) => {
    setLoading(true);
    try {
      const result = await fetchSpecialistCampers({
        q,
        bunkId: bunkId || null,
      });
      setData(result);
      if (result.bunks?.length) {
        setBunks(result.bunks);
      }
      setError('');
    } catch (err) {
      setError(err?.message || 'Could not load campers.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchCampers('', '');
    inputRef.current?.focus();
  }, [fetchCampers]);

  const handleQueryChange = (e) => {
    const q = e.target.value;
    setQuery(q);
    clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => fetchCampers(q, selectedBunkId), DEBOUNCE_MS);
  };

  const handleBunkChange = (e) => {
    const bunkId = e.target.value;
    setSelectedBunkId(bunkId);
    clearTimeout(debounceRef.current);
    fetchCampers(query, bunkId);
  };

  const handleClearBunk = () => {
    setSelectedBunkId('');
    fetchCampers(query, '');
  };

  useEffect(() => () => clearTimeout(debounceRef.current), []);

  const selectedBunkName = bunks.find((b) => String(b.id) === String(selectedBunkId))?.name;

  return (
    <div className="flex flex-col h-full" data-testid="sp-camper-picker">
      {/* Controls */}
      <div className="px-3 py-3 border-b border-gray-200 dark:border-gray-700 sticky top-0 bg-white dark:bg-gray-800 z-10 space-y-2">

        {/* Bunk dropdown */}
        <div className="flex items-center gap-2">
          <select
            value={selectedBunkId}
            onChange={handleBunkChange}
            aria-label="Filter by bunk"
            data-testid="sp-bunk-select"
            className="flex-1 rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm focus:border-blue-500 focus:ring-2 focus:ring-blue-200 text-gray-900 dark:text-gray-100"
          >
            <option value="">All bunks</option>
            {bunks.map((b) => (
              <option key={b.id} value={b.id}>{b.name}</option>
            ))}
          </select>
          {selectedBunkId && (
            <button
              type="button"
              onClick={handleClearBunk}
              aria-label="Clear bunk filter"
              className="text-sm text-gray-500 dark:text-gray-400 px-2 py-2 hover:text-gray-700 dark:hover:text-gray-200"
              data-testid="sp-bunk-clear"
            >
              ✕
            </button>
          )}
        </div>

        {/* Name search */}
        <div className="flex items-center gap-2">
          <input
            ref={inputRef}
            type="search"
            value={query}
            onChange={handleQueryChange}
            placeholder={
              selectedBunkName
                ? `Search in ${selectedBunkName}…`
                : 'Search by name…'
            }
            aria-label="Search campers by name"
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
            {!query && !selectedBunkId && (
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
                title={query ? 'Results' : selectedBunkName ? selectedBunkName : 'All campers'}
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
