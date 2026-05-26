/**
 * AudiencePicker — multi-select audience picker inside the NoteComposer.
 *
 * Fetches available options from GET /api/v1/notes/audience-options/ and
 * renders a multi-select + optional bunk/person context fields. Resolves
 * server-side at submit time; this component only shapes the request body.
 */
import { useEffect, useState } from 'react';
import api from '../../api';

const BUNK_REQUIRED = ['co_counselors_specific_bunk', 'counselors_on_bunk'];
const PERSON_REQUIRED = ['specific_person', 'specific_counselor'];

export default function AudiencePicker({ value, onChange, bunks = [], persons = [] }) {
  const [options, setOptions] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get('/api/v1/notes/audience-options/').then(r => {
      setOptions(r.data);
    }).catch(() => {}).finally(() => setLoading(false));
  }, []);

  function toggleOption(optionKey) {
    const exists = value.find(v => v.option_key === optionKey);
    if (exists) {
      onChange(value.filter(v => v.option_key !== optionKey));
    } else {
      onChange([...value, { option_key: optionKey }]);
    }
  }

  function setContext(optionKey, field, val) {
    onChange(value.map(v =>
      v.option_key === optionKey ? { ...v, [field]: val ? Number(val) : undefined } : v
    ));
  }

  if (loading) return <div className="text-sm text-gray-400">Loading audience options…</div>;
  if (options.length === 0) return <div className="text-sm text-gray-500">No audience options available for your role.</div>;

  return (
    <div className="space-y-2">
      {options.map(opt => {
        const selected = value.find(v => v.option_key === opt.option_key);
        const needsBunk = BUNK_REQUIRED.includes(opt.option_key);
        const needsPerson = PERSON_REQUIRED.includes(opt.option_key);
        return (
          <div key={opt.option_key}>
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                className="rounded border-gray-300 text-violet-600 focus:ring-violet-500"
                checked={!!selected}
                onChange={() => toggleOption(opt.option_key)}
              />
              <span className="text-sm text-gray-700 dark:text-gray-300">{opt.label}</span>
            </label>

            {selected && needsBunk && (
              <select
                className="mt-1 ml-6 text-sm rounded border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-200"
                value={selected.bunk_id ?? ''}
                onChange={e => setContext(opt.option_key, 'bunk_id', e.target.value)}
              >
                <option value="">— select bunk —</option>
                {bunks.map(b => (
                  <option key={b.id} value={b.id}>{b.name}</option>
                ))}
              </select>
            )}

            {selected && needsPerson && (
              <select
                className="mt-1 ml-6 text-sm rounded border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-200"
                value={selected.person_id ?? ''}
                onChange={e => setContext(opt.option_key, 'person_id', e.target.value)}
              >
                <option value="">— select person —</option>
                {persons.map(p => (
                  <option key={p.id} value={p.id}>{p.full_name}</option>
                ))}
              </select>
            )}
          </div>
        );
      })}
    </div>
  );
}
