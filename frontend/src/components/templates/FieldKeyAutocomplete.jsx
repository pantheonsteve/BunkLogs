import { useEffect, useRef, useState, useCallback } from 'react';
import { Plus } from 'lucide-react';
import api from '../../api';

function slugify(text) {
  return (text || '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '_')
    .replace(/^_|_$/g, '');
}

/**
 * Text input with autocomplete from the FieldKey registry.
 * @param {object} props
 * @param {string}   props.value       - current key value
 * @param {function} props.onChange    - onChange(key)
 * @param {string}   [props.promptHint] - English prompt to suggest a key from
 * @param {boolean}  [props.disabled]
 */
export default function FieldKeyAutocomplete({ value, onChange, promptHint, disabled }) {
  const [query, setQuery] = useState(value || '');
  const [suggestions, setSuggestions] = useState([]);
  const [showDropdown, setShowDropdown] = useState(false);
  const [loading, setLoading] = useState(false);
  const [newKeyModal, setNewKeyModal] = useState(false);
  const [newKeyForm, setNewKeyForm] = useState({ key: '', display_name: '', description: '' });
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState('');
  const containerRef = useRef(null);
  const debounceRef = useRef(null);

  useEffect(() => {
    setQuery(value || '');
  }, [value]);

  const fetchSuggestions = useCallback(async (q) => {
    if (!q) { setSuggestions([]); return; }
    setLoading(true);
    try {
      const { data } = await api.get('/api/v1/field-keys/', { params: { q } });
      setSuggestions(Array.isArray(data?.results) ? data.results : Array.isArray(data) ? data : []);
    } catch {
      setSuggestions([]);
    } finally {
      setLoading(false);
    }
  }, []);

  const handleInputChange = (e) => {
    const v = e.target.value;
    setQuery(v);
    onChange(v);
    setShowDropdown(true);
    clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => fetchSuggestions(v), 250);
  };

  useEffect(() => {
    const handler = (e) => {
      if (containerRef.current && !containerRef.current.contains(e.target)) {
        setShowDropdown(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  const selectSuggestion = (key) => {
    setQuery(key);
    onChange(key);
    setShowDropdown(false);
  };

  const openNewKeyModal = () => {
    const suggested = slugify(promptHint) || query;
    setNewKeyForm({ key: suggested, display_name: promptHint || '', description: '' });
    setSaveError('');
    setNewKeyModal(true);
    setShowDropdown(false);
  };

  const saveNewKey = async () => {
    if (!newKeyForm.key) { setSaveError('Key is required.'); return; }
    setSaving(true);
    setSaveError('');
    try {
      const { data } = await api.post('/api/v1/field-keys/', newKeyForm);
      onChange(data.key);
      setQuery(data.key);
      setNewKeyModal(false);
    } catch (err) {
      const body = err.response?.data;
      setSaveError(
        typeof body === 'string' ? body :
        body?.key?.[0] || body?.detail || 'Save failed.'
      );
    } finally {
      setSaving(false);
    }
  };

  return (
    <div ref={containerRef} className="relative">
      <input
        type="text"
        value={query}
        onChange={handleInputChange}
        onFocus={() => { if (query) { setShowDropdown(true); fetchSuggestions(query); } }}
        disabled={disabled}
        placeholder="e.g. weekly_wins"
        className="w-full rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900 px-3 py-1.5 text-sm font-mono text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
      />

      {showDropdown && (
        <div className="absolute z-50 top-full mt-1 w-full bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg overflow-hidden">
          {loading && (
            <p className="px-3 py-2 text-xs text-gray-500">Loading…</p>
          )}
          {!loading && suggestions.map((fk) => (
            <button
              key={fk.key}
              type="button"
              onClick={() => selectSuggestion(fk.key)}
              className="w-full text-left px-3 py-2 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
            >
              <p className="text-xs font-mono font-medium text-gray-900 dark:text-gray-100">{fk.key}</p>
              <p className="text-xs text-gray-500 dark:text-gray-400 truncate">{fk.display_name}</p>
            </button>
          ))}
          <button
            type="button"
            onClick={openNewKeyModal}
            className="w-full text-left px-3 py-2 border-t border-gray-100 dark:border-gray-800 text-blue-600 dark:text-blue-400 text-xs hover:bg-gray-50 dark:hover:bg-gray-800 flex items-center gap-1"
          >
            <Plus size={12} /> Create new key
          </button>
        </div>
      )}

      {newKeyModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div className="bg-white dark:bg-gray-900 rounded-xl shadow-2xl w-full max-w-sm p-6">
            <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-4">Register new field key</h3>
            <div className="space-y-3">
              <div>
                <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">Key *</label>
                <input
                  type="text"
                  className="w-full rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900 px-2 py-1.5 text-xs font-mono"
                  value={newKeyForm.key}
                  onChange={(e) => setNewKeyForm((f) => ({ ...f, key: e.target.value.toLowerCase().replace(/[^a-z0-9_]/g, '') }))}
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">Display name</label>
                <input
                  type="text"
                  className="w-full rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900 px-2 py-1.5 text-xs"
                  value={newKeyForm.display_name}
                  onChange={(e) => setNewKeyForm((f) => ({ ...f, display_name: e.target.value }))}
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">Description</label>
                <input
                  type="text"
                  className="w-full rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900 px-2 py-1.5 text-xs"
                  value={newKeyForm.description}
                  onChange={(e) => setNewKeyForm((f) => ({ ...f, description: e.target.value }))}
                />
              </div>
              {saveError && <p className="text-red-600 text-xs">{saveError}</p>}
            </div>
            <div className="flex justify-end gap-2 mt-5">
              <button
                type="button"
                onClick={() => setNewKeyModal(false)}
                className="text-sm text-gray-600 dark:text-gray-400 px-3 py-1.5 rounded hover:bg-gray-100 dark:hover:bg-gray-800"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={saveNewKey}
                disabled={saving}
                className="text-sm bg-blue-600 text-white px-4 py-1.5 rounded hover:bg-blue-700 disabled:opacity-50"
              >
                {saving ? 'Saving…' : 'Register'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
