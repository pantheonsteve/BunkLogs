/**
 * NotesPage — Inbox / Sent / Archive tabs with compose button (Story 67).
 *
 * Route: /notes. Mounted under AppLayout, which owns the Sidebar/Header chrome.
 * Open to all authenticated members with an active Membership.
 */
import { useCallback, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../../api';
import NoteComposer from '../../components/notes/NoteComposer';
import NoteListItem from '../../components/notes/NoteListItem';

const TABS = [
  { key: 'inbox', label: 'Inbox' },
  { key: 'sent', label: 'Sent' },
  { key: 'archive', label: 'Archive' },
];

export default function NotesPage() {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState('inbox');
  const [notes, setNotes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [composing, setComposing] = useState(false);
  const [nextUrl, setNextUrl] = useState(null);

  const fetchTab = useCallback(async (tab) => {
    setLoading(true);
    setError(null);
    try {
      const r = await api.get(`/api/v1/notes/${tab}/`);
      setNotes(r.data.results ?? r.data);
      setNextUrl(r.data.next ?? null);
    } catch (err) {
      if (err.response?.status === 403) {
        setError('Notes are not yet enabled for your role.');
      } else {
        setError('Failed to load notes.');
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchTab(activeTab);
  }, [activeTab, fetchTab]);

  function handleTabChange(tab) {
    setActiveTab(tab);
    setNotes([]);
  }

  function handleSent(newNote) {
    if (activeTab === 'sent') {
      setNotes(prev => [newNote, ...prev]);
    }
  }

  return (
    <main className="grow">
      <div className="px-4 sm:px-6 lg:px-8 py-8 w-full max-w-3xl mx-auto">
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-2xl font-semibold text-gray-800 dark:text-white">Notes</h1>
          <button
            type="button"
            onClick={() => setComposing(true)}
            className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-violet-600 hover:bg-violet-700 rounded-lg transition-colors"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
            Compose
          </button>
        </div>

        <div className="flex gap-1 mb-4 border-b border-gray-200 dark:border-gray-700">
          {TABS.map(tab => (
            <button
              key={tab.key}
              type="button"
              onClick={() => handleTabChange(tab.key)}
              className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors ${
                activeTab === tab.key
                  ? 'border-violet-600 text-violet-600 dark:text-violet-400'
                  : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {loading && (
          <div className="py-12 text-center text-gray-400">Loading…</div>
        )}
        {!loading && error && (
          <div className="py-8 text-center text-red-500">{error}</div>
        )}
        {!loading && !error && notes.length === 0 && (
          <div className="py-12 text-center text-gray-400">
            {activeTab === 'inbox' && 'Your inbox is empty.'}
            {activeTab === 'sent' && "You haven't sent any notes yet."}
            {activeTab === 'archive' && 'No archived notes.'}
          </div>
        )}
        {!loading && !error && notes.length > 0 && (
          <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
            {notes.map(note => (
              <NoteListItem
                key={note.id}
                note={note}
                variant={activeTab === 'inbox' ? 'inbox' : 'sent'}
              />
            ))}
          </div>
        )}
      </div>

      {composing && (
        <NoteComposer
          onClose={() => setComposing(false)}
          onSent={handleSent}
        />
      )}
    </main>
  );
}
