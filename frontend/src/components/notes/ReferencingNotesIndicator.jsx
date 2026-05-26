/**
 * ReferencingNotesIndicator — back-reference badge shown on Bunk concerns
 * and Specialist note views when Notes have been started from those surfaces.
 *
 * Renders a count chip + popover list of note threads that reference the
 * source content. Filters server-side per visibility model (decision N7).
 */
import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';

export default function ReferencingNotesIndicator({ notes = [] }) {
  const [open, setOpen] = useState(false);

  if (!notes || notes.length === 0) return null;

  return (
    <div className="relative inline-block">
      <button
        type="button"
        onClick={() => setOpen(o => !o)}
        className="inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full bg-violet-50 text-violet-700 border border-violet-200 dark:bg-violet-900/30 dark:text-violet-300 dark:border-violet-700 hover:bg-violet-100 dark:hover:bg-violet-900/50 transition-colors"
      >
        <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
        </svg>
        {notes.length} note{notes.length !== 1 ? 's' : ''} started from here
      </button>

      {open && (
        <>
          <div
            className="fixed inset-0 z-10"
            onClick={() => setOpen(false)}
            aria-hidden="true"
          />
          <div className="absolute left-0 top-full mt-1 z-20 w-72 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg overflow-hidden">
            <div className="px-3 py-2 text-xs font-semibold text-gray-500 dark:text-gray-400 bg-gray-50 dark:bg-gray-700/50 border-b border-gray-200 dark:border-gray-700">
              Notes referencing this
            </div>
            <ul className="divide-y divide-gray-100 dark:divide-gray-700 max-h-48 overflow-y-auto">
              {notes.map(note => (
                <li key={note.id}>
                  <Link
                    to={`/notes/${note.id}`}
                    onClick={() => setOpen(false)}
                    className="block px-3 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700/40 truncate"
                  >
                    {note.subject}
                  </Link>
                </li>
              ))}
            </ul>
          </div>
        </>
      )}
    </div>
  );
}
