/**
 * Expandable counselor / staff self-reflection cards (bunk dashboard + UH staff page).
 */

import { useState } from 'react';
import CounselorSelfReflectionView from './CounselorSelfReflectionView';

const SELF_REFL_STATE = {
  complete: { label: 'Submitted', cls: 'bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-200' },
  day_off: { label: 'Day off', cls: 'bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-200' },
  missing: { label: 'Not yet', cls: 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-200' },
};

function CounselorSelfReflectionItem({ entry }) {
  const [expanded, setExpanded] = useState(false);
  const meta = SELF_REFL_STATE[entry.state] || SELF_REFL_STATE.missing;
  const hasContent = entry.state === 'complete'
    && ((entry.fields?.length || 0) > 0 || (entry.schema_fields?.length || 0) > 0);
  return (
    <li
      data-testid={`counselor-self-refl-${entry.person_id}`}
      data-state={entry.state}
      className="rounded-lg border border-gray-200 dark:border-gray-700 px-3 py-2.5"
    >
      <div className="flex items-center justify-between gap-2">
        <span className="text-sm font-semibold text-gray-900 dark:text-white">
          {entry.counselor_name}
        </span>
        <span className={`text-xs font-medium rounded-full px-2 py-0.5 ${meta.cls}`}>
          {meta.label}
        </span>
      </div>
      {entry.submitted_at && (
        <p className="text-xs text-gray-400 dark:text-gray-500 mt-0.5">
          {new Date(entry.submitted_at).toLocaleString()}
        </p>
      )}
      {hasContent && (
        <>
          <button
            type="button"
            onClick={() => setExpanded((v) => !v)}
            className="text-xs font-semibold text-blue-700 dark:text-blue-300 hover:underline mt-1.5"
          >
            {expanded ? 'Hide reflection' : 'View reflection'}
          </button>
          {expanded && (
            <CounselorSelfReflectionView entry={entry} />
          )}
        </>
      )}
    </li>
  );
}

export default function CounselorSelfReflectionsList({ entries }) {
  const list = entries || [];
  if (list.length === 0) {
    return (
      <p className="text-sm text-gray-500 dark:text-gray-400">
        No staff assigned to this bunk.
      </p>
    );
  }
  return (
    <ul className="space-y-2.5">
      {list.map((entry) => (
        <CounselorSelfReflectionItem key={entry.person_id} entry={entry} />
      ))}
    </ul>
  );
}

export function counselorSelfReflectionSummary(entries) {
  const list = entries || [];
  const submitted = list.filter((e) => e.state !== 'missing').length;
  return { submitted, expected: list.length };
}
