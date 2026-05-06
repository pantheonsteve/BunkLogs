import { useState } from 'react';
import { ChevronDown, ChevronUp } from 'lucide-react';

/**
 * ConcernQueueWidget — for dashboard_role: open_concern (text/textarea fields).
 * Shows unread concern queue; supervisors can expand to read full text.
 */
export default function ConcernQueueWidget({ field, label }) {
  const items = field?.data?.items ?? [];
  const [expanded, setExpanded] = useState(null);

  const unread = items.filter((i) => !i.is_read).length;

  return (
    <div className="rounded-xl border border-rose-200 dark:border-rose-900/50 bg-rose-50/40 dark:bg-rose-950/20 p-5">
      <div className="flex items-center justify-between mb-3">
        <p className="text-xs font-semibold uppercase tracking-wide text-rose-600 dark:text-rose-400">
          {label ?? field?.key}
        </p>
        {unread > 0 && (
          <span className="px-2 py-0.5 rounded-full bg-rose-100 dark:bg-rose-900/50 text-xs font-medium text-rose-700 dark:text-rose-300">
            {unread} new
          </span>
        )}
      </div>
      {items.length === 0 ? (
        <p className="text-sm text-gray-400 dark:text-gray-500">No concerns this period.</p>
      ) : (
        <ul className="space-y-2">
          {items.map((item) => {
            const isExpanded = expanded === item.reflection_id;
            return (
              <li
                key={`${item.reflection_id}-${item.period_end}`}
                className="rounded-lg border border-rose-200 dark:border-rose-900/40 bg-white dark:bg-gray-900/60 overflow-hidden"
              >
                <button
                  type="button"
                  className="w-full text-left px-3 py-2 flex items-center justify-between gap-2"
                  onClick={() => setExpanded(isExpanded ? null : item.reflection_id)}
                >
                  <span className="text-xs text-gray-500 dark:text-gray-400">
                    Person {item.person_id} · {item.period_end}
                  </span>
                  {isExpanded ? (
                    <ChevronUp size={14} className="shrink-0 text-gray-400" />
                  ) : (
                    <ChevronDown size={14} className="shrink-0 text-gray-400" />
                  )}
                </button>
                {isExpanded && (
                  <div className="px-3 pb-3">
                    <p className="text-sm text-gray-800 dark:text-gray-200 whitespace-pre-wrap">
                      {item.text}
                    </p>
                  </div>
                )}
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
