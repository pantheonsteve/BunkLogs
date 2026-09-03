import { useCallback, useEffect, useState } from 'react';

import { listAdminPeople } from '../../../api/admin';
import Badge from '../../../components/ui/Badge';
import Button from '../../../components/ui/Button';
import Modal from '../../../components/ui/Modal';
import Note from '../../../components/ui/Note';
import { SearchInput } from '../../../components/ui/FilterBar';

/**
 * Add several people to a group in one pass.
 *
 * The old flow was search, pick one, click Add, repeat — which is the
 * wrong shape for September when a whole bunk arrives at once. Search
 * narrows, checkboxes accumulate across searches, and one Add commits
 * the lot with a per-person report if some fail.
 */
export default function AddMembersModal({
  title,
  roleInGroup,
  programId,
  existingPersonIds,
  onAdd,
  onClose,
  onDone,
}) {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [searching, setSearching] = useState(false);
  const [picked, setPicked] = useState(() => new Map());
  const [busy, setBusy] = useState(false);
  const [failures, setFailures] = useState([]);

  const search = useCallback(async (q) => {
    setSearching(true);
    try {
      const params = { page_size: 50 };
      if (q.trim()) params.search = q.trim();
      if (programId) params.program = String(programId);
      const data = await listAdminPeople(params);
      setResults(Array.isArray(data?.results) ? data.results : []);
    } catch {
      setResults([]);
    } finally {
      setSearching(false);
    }
  }, [programId]);

  useEffect(() => {
    const t = setTimeout(() => search(query), 250);
    return () => clearTimeout(t);
  }, [query, search]);

  const toggle = (person) => {
    setPicked((prev) => {
      const next = new Map(prev);
      if (next.has(person.id)) next.delete(person.id);
      else next.set(person.id, person);
      return next;
    });
  };

  const commit = async () => {
    setBusy(true);
    setFailures([]);
    const failed = [];
    for (const person of picked.values()) {
      try {
        await onAdd(person.id);
      } catch (err) {
        failed.push({
          id: person.id,
          name: person.full_name,
          reason: err?.response?.data?.detail || 'Could not add.',
        });
      }
    }
    setBusy(false);
    if (failed.length) {
      setFailures(failed);
      setPicked(new Map());
      return;
    }
    onDone(picked.size);
  };

  return (
    <Modal
      title={title}
      description="Search, tick everyone who belongs here, then add them together."
      onClose={onClose}
      dismissible={!busy}
      width="lg"
      data-testid="add-members-modal"
      footer={(
        <>
          <Button variant="secondary" onClick={onClose} disabled={busy}>Cancel</Button>
          <div className="flex-1" />
          <Button
            onClick={commit}
            disabled={busy || picked.size === 0}
            data-testid="add-members-confirm"
          >
            {busy ? 'Adding…' : `Add ${picked.size || ''} ${picked.size === 1 ? 'person' : 'people'}`.trim()}
          </Button>
        </>
      )}
    >
      <div className="space-y-3">
        <SearchInput
          value={query}
          onChange={setQuery}
          placeholder="Search by name or email…"
          data-testid="add-members-search"
        />

        {failures.length > 0 && (
          <Note tone="warn" title="Some people were not added" data-testid="add-members-failures">
            <ul className="mt-1 list-disc pl-5 space-y-0.5">
              {failures.map((f) => <li key={f.id}>{f.name} — {f.reason}</li>)}
            </ul>
          </Note>
        )}

        {picked.size > 0 && (
          <div className="flex flex-wrap gap-1.5" data-testid="add-members-picked">
            {[...picked.values()].map((p) => (
              <button key={p.id} type="button" onClick={() => toggle(p)}>
                <Badge tone="info">{p.full_name} ×</Badge>
              </button>
            ))}
          </div>
        )}

        {searching && results.length === 0 ? (
          <p className="text-sm text-gray-500">Searching…</p>
        ) : results.length === 0 ? (
          <p className="text-sm text-gray-500">Nobody matches that search.</p>
        ) : (
          <ul className="max-h-72 overflow-y-auto divide-y divide-gray-100 dark:divide-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
            {results.map((p) => {
              const already = existingPersonIds.has(p.id);
              return (
                <li key={p.id}>
                  <label
                    data-testid={`add-members-row-${p.id}`}
                    className={`flex items-center gap-3 px-3 py-2 text-sm ${
                      already ? 'opacity-50' : 'cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800/50'
                    }`}
                  >
                    <input
                      type="checkbox"
                      disabled={already}
                      checked={picked.has(p.id)}
                      onChange={() => toggle(p)}
                      className="w-4 h-4 accent-blue-600"
                      aria-label={`Add ${p.full_name}`}
                    />
                    <span className="flex-1 min-w-0">
                      <span className="block font-medium text-gray-900 dark:text-white">{p.full_name}</span>
                      <span className="block text-xs text-gray-500">{p.email || 'no email'}</span>
                    </span>
                    {already && <Badge tone="neutral">Already a {roleInGroup}</Badge>}
                  </label>
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </Modal>
  );
}
