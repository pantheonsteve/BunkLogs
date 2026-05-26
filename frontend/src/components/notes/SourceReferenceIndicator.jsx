/**
 * SourceReferenceIndicator — renders the cross-reference source link.
 *
 * Shows a badge/chip linking to the source content (a Reflection concern or
 * a Specialist note). Per decision N7: viewing this note thread does NOT
 * grant access to the source. If the user doesn't have independent access,
 * the link is rendered as a disabled chip with explanatory tooltip.
 */
import { useState } from 'react';
import { Link } from 'react-router-dom';

const TYPE_LABELS = {
  reflection_concern: 'Bunk concern',
  specialist_note: 'Specialist note',
};

export default function SourceReferenceIndicator({ sourceContentType, sourceObjectId }) {
  const [showTooltip, setShowTooltip] = useState(false);

  if (!sourceContentType || !sourceObjectId) return null;

  const label = TYPE_LABELS[sourceContentType] ?? sourceContentType;

  // For now we render the link as informational; actual access gating
  // happens server-side. The href below is a best-guess deep link; the
  // server will 403 if the user doesn't have independent access.
  const href =
    sourceContentType === 'reflection_concern'
      ? `/my-reflections/${sourceObjectId}`
      : `/specialist/notes/${sourceObjectId}`;

  return (
    <div className="relative inline-block">
      <span
        className="inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full bg-amber-50 text-amber-700 border border-amber-200 dark:bg-amber-900/30 dark:text-amber-300 dark:border-amber-800"
        onMouseEnter={() => setShowTooltip(true)}
        onMouseLeave={() => setShowTooltip(false)}
      >
        <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
        </svg>
        Referenced from:{' '}
        <Link
          to={href}
          className="underline hover:text-amber-900 dark:hover:text-amber-200"
          onClick={e => e.stopPropagation()}
        >
          {label}
        </Link>
      </span>

      {showTooltip && (
        <div className="absolute left-0 top-full mt-1 z-10 w-64 p-2 text-xs bg-gray-800 text-white rounded shadow-lg">
          Viewing this note does not grant access to the referenced {label.toLowerCase()}. You need
          independent access to view the source.
        </div>
      )}
    </div>
  );
}
