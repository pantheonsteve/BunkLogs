import { useState } from 'react';
import { ChevronDown, ChevronUp } from 'lucide-react';

/**
 * TextResponseListWidget — generic widget for untagged text/textarea fields.
 * Shows recent responses, truncated, click to expand.
 */
export default function TextResponseListWidget({ field, label }) {
  const items = field?.data?.items ?? [];
  const total = field?.data?.total ?? 0;
  const [expanded, setExpanded] = useState(null);

  return (
    <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900/40 p-5">
      <div className="flex items-center justify-between mb-3">
        <p className="text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">
          {label ?? field?.key}
        </p>
        <span className="text-xs text-gray-400 dark:text-gray-500">{total} response{total !== 1 ? 's' : ''}</span>
      </div>
      {items.length === 0 ? (
        <p className="text-sm text-gray-400 dark:text-gray-500">No responses this period.</p>
      ) : (
        <ul className="space-y-2">
          {items.map((item, i) => {
            const key = `${item.reflection_id ?? i}-${item.period_end}`;
            const isExpanded = expanded === key;
            const preview = item.text.length > 120 ? `${item.text.slice(0, 120)}…` : item.text;
            return (
              <li
                key={key}
                className="rounded-lg border border-gray-100 dark:border-gray-800 px-3 py-2"
              >
                <div className="flex items-start justify-between gap-2">
                  <p className="text-sm text-gray-800 dark:text-gray-200 flex-1 whitespace-pre-wrap">
                    {isExpanded ? item.text : preview}
                  </p>
                  {item.text.length > 120 && (
                    <button
                      type="button"
                      onClick={() => setExpanded(isExpanded ? null : key)}
                      className="shrink-0 text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 mt-0.5"
                      aria-label={isExpanded ? 'Collapse' : 'Expand'}
                    >
                      {isExpanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                    </button>
                  )}
                </div>
                <p className="text-xs text-gray-400 dark:text-gray-500 mt-1">{item.period_end}</p>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
