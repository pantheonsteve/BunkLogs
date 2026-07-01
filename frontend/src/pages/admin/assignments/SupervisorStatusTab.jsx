import { useCallback, useEffect, useState } from 'react';
import {
  buildAdminPeopleListParams,
  getAdminSupervisorStatus,
  listAdminPeople,
} from '../../../api/admin';

function Badge({ ok, children }) {
  return (
    <span
      className={[
        'inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium',
        ok
          ? 'bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-200'
          : 'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-300',
      ].join(' ')}
    >
      {children}
    </span>
  );
}

function EntityList({ title, items }) {
  if (!items || items.length === 0) return null;
  return (
    <div>
      <h4 className="text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400 mb-1">
        {title}
      </h4>
      <ul className="flex flex-wrap gap-1.5">
        {items.map((it) => (
          <li
            key={it.id ?? `${it.target_type}-${it.target_name}`}
            className="rounded-md bg-indigo-50 dark:bg-indigo-900/30 text-indigo-800 dark:text-indigo-200 text-xs px-2 py-1"
          >
            {it.name || it.target_name || '—'}
          </li>
        ))}
      </ul>
    </div>
  );
}

export default function SupervisorStatusTab() {
  const [search, setSearch] = useState('');
  const [people, setPeople] = useState([]);
  const [loadingPeople, setLoadingPeople] = useState(true);
  const [selectedId, setSelectedId] = useState(null);
  const [status, setStatus] = useState(null);
  const [loadingStatus, setLoadingStatus] = useState(false);
  const [error, setError] = useState(null);

  const loadPeople = useCallback(async () => {
    setLoadingPeople(true);
    try {
      const params = buildAdminPeopleListParams({ search, page_size: 50 });
      const data = await listAdminPeople(params);
      setPeople(data.results || []);
    } finally {
      setLoadingPeople(false);
    }
  }, [search]);

  useEffect(() => {
    const t = setTimeout(loadPeople, 250);
    return () => clearTimeout(t);
  }, [loadPeople]);

  useEffect(() => {
    if (selectedId == null) {
      setStatus(null);
      return;
    }
    let cancelled = false;
    setLoadingStatus(true);
    setError(null);
    getAdminSupervisorStatus(selectedId)
      .then((data) => {
        if (!cancelled) setStatus(data);
      })
      .catch((err) => {
        if (!cancelled) setError(err?.response?.data?.detail || 'Failed to load supervisor status.');
      })
      .finally(() => {
        if (!cancelled) setLoadingStatus(false);
      });
    return () => {
      cancelled = true;
    };
  }, [selectedId]);

  const entities = status?.supervised_entities || {};
  const supervisedPeople = status?.supervised_people?.people || [];

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-4" data-testid="supervisor-status-tab">
      <section className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900/40 p-3 space-y-2 min-h-[20rem]">
        <h2 className="text-sm font-semibold text-gray-900 dark:text-white">People</h2>
        <input
          type="search"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search by name…"
          className="w-full text-sm rounded-md border border-gray-300 dark:border-gray-600 px-2 py-1.5 bg-white dark:bg-gray-800"
        />
        {loadingPeople ? (
          <p className="text-sm text-gray-500">Loading…</p>
        ) : (
          <ul className="max-h-96 overflow-y-auto space-y-1">
            {people.map((p) => (
              <li key={p.id}>
                <button
                  type="button"
                  onClick={() => setSelectedId(p.id)}
                  className={[
                    'w-full text-left rounded-lg px-3 py-2 text-sm transition-colors',
                    selectedId === p.id
                      ? 'bg-indigo-100 dark:bg-indigo-900/40 text-indigo-900 dark:text-indigo-100 font-medium'
                      : 'hover:bg-gray-50 dark:hover:bg-gray-800 text-gray-800 dark:text-gray-200',
                  ].join(' ')}
                >
                  {p.full_name || `${p.first_name} ${p.last_name}`}
                </button>
              </li>
            ))}
            {people.length === 0 && (
              <li className="text-sm text-gray-500 px-3 py-2">No people found.</li>
            )}
          </ul>
        )}
      </section>

      <section className="lg:col-span-2 rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900/40 p-4 space-y-4 min-h-[20rem]">
        {selectedId == null && (
          <p className="text-sm text-gray-500">
            Select a person to inspect what they supervise and whether they can view reflections.
          </p>
        )}
        {error && <p className="text-sm text-red-600">{error}</p>}
        {loadingStatus && <p className="text-sm text-gray-500">Loading…</p>}
        {status && !loadingStatus && (
          <>
            <div className="flex flex-wrap items-center gap-2">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                {status.person?.name}
              </h3>
              <Badge ok={status.is_supervisor}>
                {status.is_supervisor ? 'Supervisor' : 'Not a supervisor'}
              </Badge>
              <Badge ok={status.can_view_reflections}>
                {status.can_view_reflections
                  ? 'Can view self + other reflections'
                  : 'No reflection visibility'}
              </Badge>
            </div>

            <div className="space-y-3">
              <EntityList title="Units" items={entities.units} />
              <EntityList title="Bunks" items={entities.bunks} />
              <EntityList title="Teams" items={entities.teams} />
              <EntityList title="Supervision rows" items={entities.supervisions} />
              {(!entities.units?.length
                && !entities.bunks?.length
                && !entities.teams?.length
                && !entities.supervisions?.length) && (
                <p className="text-sm text-gray-500">
                  No supervised entities. This person is not assigned as a unit head / supervisor.
                </p>
              )}
            </div>

            <div>
              <h4 className="text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400 mb-1">
                Supervised people ({status.supervised_people?.count ?? 0})
              </h4>
              {supervisedPeople.length === 0 ? (
                <p className="text-sm text-gray-500">None.</p>
              ) : (
                <ul className="max-h-72 overflow-y-auto grid grid-cols-1 sm:grid-cols-2 gap-1">
                  {supervisedPeople.map((sp) => (
                    <li
                      key={sp.id}
                      className="flex items-center justify-between rounded-md bg-gray-50 dark:bg-gray-800 px-2.5 py-1.5 text-sm"
                    >
                      <span className="text-gray-800 dark:text-gray-200 truncate">{sp.name}</span>
                      {sp.role && (
                        <span className="text-xs text-gray-500 ml-2">{sp.role}</span>
                      )}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </>
        )}
      </section>
    </div>
  );
}
