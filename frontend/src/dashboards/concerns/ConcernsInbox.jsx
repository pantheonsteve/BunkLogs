import { useState } from 'react';
import { Link } from 'react-router-dom';
import api from '../../api';

function shortDate(iso) {
  const d = new Date(iso + 'T00:00:00');
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
}

function KindBadge({ kind }) {
  const styles = kind === 'low_rating'
    ? { bg: 'bg-rose-100 dark:bg-rose-900/40', fg: 'text-rose-800 dark:text-rose-100' }
    : { bg: 'bg-amber-100 dark:bg-amber-900/40', fg: 'text-amber-900 dark:text-amber-100' };
  const label = kind === 'low_rating' ? 'Low rating' : 'Open concern';
  return (
    <span className={`inline-block rounded px-2 py-0.5 text-xs font-medium ${styles.bg} ${styles.fg}`}>
      {label}
    </span>
  );
}

export default function ConcernsInbox({ payload, onChanged }) {
  const [busyId, setBusyId] = useState(null);
  const [error, setError] = useState(null);
  if (!payload) return null;
  const { items, period, include_read } = payload;

  const markRead = async (item) => {
    const key = `${item.reflection_id}/${item.field_key}`;
    setBusyId(key);
    setError(null);
    try {
      if (item.read) {
        await api.delete(
          `/api/v1/dashboards/concerns/${item.reflection_id}/${item.field_key}/read/`,
        );
      } else {
        await api.post(
          `/api/v1/dashboards/concerns/${item.reflection_id}/${item.field_key}/read/`,
        );
      }
      onChanged?.();
    } catch (e) {
      setError(e.response?.data?.detail || e.message || 'Failed to update read state');
    } finally {
      setBusyId(null);
    }
  };

  return (
    <div>
      <div className="mb-4 flex items-end justify-between">
        <div>
          <p className="text-xs uppercase text-gray-500 dark:text-gray-400">
            {period.start} → {period.end}
            {include_read ? ' · including read items' : ''}
          </p>
          <p className="text-sm text-gray-700 dark:text-gray-200">
            {items.length} item(s) in your inbox
          </p>
        </div>
      </div>
      {error && (
        <p className="mb-3 text-rose-600 dark:text-rose-400 text-sm">{error}</p>
      )}
      {items.length === 0 ? (
        <p className="text-sm text-gray-500 dark:text-gray-400">
          No concerns in this window. Nice work!
        </p>
      ) : (
        <ul className="space-y-2">
          {items.map((it) => (
            <li
              key={`${it.reflection_id}-${it.field_key}`}
              className={`rounded-lg border ${
                it.read
                  ? 'border-gray-200 dark:border-gray-700 opacity-70'
                  : 'border-amber-300 dark:border-amber-700'
              } bg-white dark:bg-gray-900/40 p-3`}
            >
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0 flex-1">
                  <p className="text-xs text-gray-500 dark:text-gray-400 mb-1 flex flex-wrap items-center gap-2">
                    <KindBadge kind={it.kind} />
                    <span>{shortDate(it.date)}</span>
                    <span>·</span>
                    <span>{it.template_name}</span>
                    {it.assignment_group && (
                      <>
                        <span>·</span>
                        <span>{it.assignment_group.name}</span>
                      </>
                    )}
                    {it.author_name && (
                      <>
                        <span>·</span>
                        <span>by {it.author_name}</span>
                      </>
                    )}
                  </p>
                  <p className="text-sm text-gray-900 dark:text-white">
                    {it.subject_id ? (
                      <Link
                        to={`/dashboards/subject/${it.subject_id}`}
                        className="font-medium hover:underline"
                      >
                        {it.subject_name}
                      </Link>
                    ) : (
                      <span className="font-medium">{it.subject_name ?? '—'}</span>
                    )}
                    <span className="mx-1.5 text-gray-400">·</span>
                    <span className="text-gray-600 dark:text-gray-400">
                      {it.field_label}
                    </span>
                  </p>
                  {it.kind === 'open_concern' ? (
                    <p className="mt-1 text-sm text-gray-800 dark:text-gray-100 whitespace-pre-wrap">
                      {it.value}
                    </p>
                  ) : (
                    <p className="mt-1 text-sm font-mono text-rose-700 dark:text-rose-300">
                      Rating: {it.value}
                    </p>
                  )}
                  <p className="mt-2 text-xs">
                    <Link
                      to={`/reflect/summary?reflection=${it.reflection_id}`}
                      className="text-indigo-700 dark:text-indigo-300 hover:underline"
                    >
                      Open reflection
                    </Link>
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => markRead(it)}
                  disabled={busyId === `${it.reflection_id}/${it.field_key}`}
                  className={`shrink-0 rounded-md px-2 py-1 text-xs font-medium ${
                    it.read
                      ? 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-200 hover:bg-gray-200 dark:hover:bg-gray-600'
                      : 'bg-indigo-600 text-white hover:bg-indigo-500'
                  }`}
                >
                  {it.read ? 'Mark unread' : 'Mark read'}
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
