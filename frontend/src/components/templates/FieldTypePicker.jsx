import { useEffect, useRef } from 'react';
import { X } from 'lucide-react';

const FIELD_GROUPS = [
  {
    label: 'Text input',
    types: [
      { type: 'text', icon: 'T', name: 'Short text', description: 'Single-line text answer' },
      { type: 'textarea', icon: '¶', name: 'Long text', description: 'Multi-line text answer' },
      { type: 'text_list', icon: '≡', name: 'List', description: 'Multiple text lines (e.g. wins)' },
      { type: 'number', icon: '#', name: 'Number', description: 'Numeric value' },
      { type: 'date', icon: '📅', name: 'Date', description: 'Date picker' },
    ],
  },
  {
    label: 'Choice',
    types: [
      { type: 'single_choice', icon: '◉', name: 'Single choice', description: 'Pick one option' },
      { type: 'multiple_choice', icon: '☑', name: 'Multiple choice', description: 'Pick one or more' },
      { type: 'yes_no', icon: '?', name: 'Yes / No', description: 'Binary answer with optional follow-up' },
    ],
  },
  {
    label: 'Structured',
    types: [
      { type: 'rating_group', icon: '★', name: 'Rating grid', description: 'Rate multiple categories on a scale' },
      { type: 'single_rating', icon: '⭐', name: 'Single rating', description: 'One overall rating on a scale' },
    ],
  },
  {
    label: 'Meta',
    types: [
      { type: 'section_header', icon: '—', name: 'Section header', description: 'Visual divider / heading' },
      { type: 'instructions', icon: 'ℹ', name: 'Instructions', description: 'Instructional text block' },
    ],
  },
];

/**
 * @param {object} props
 * @param {boolean}  props.open
 * @param {function} props.onClose
 * @param {function} props.onPick - onPick(fieldType)
 */
export default function FieldTypePicker({ open, onClose, onPick }) {
  const ref = useRef(null);

  useEffect(() => {
    if (!open) return;
    const handler = (e) => {
      if (ref.current && !ref.current.contains(e.target)) onClose();
    };
    const keyHandler = (e) => {
      if (e.key === 'Escape') onClose();
    };
    document.addEventListener('mousedown', handler);
    document.addEventListener('keydown', keyHandler);
    return () => {
      document.removeEventListener('mousedown', handler);
      document.removeEventListener('keydown', keyHandler);
    };
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 p-4">
      <div
        ref={ref}
        role="dialog"
        aria-label="Add field"
        className="bg-white dark:bg-gray-900 rounded-xl shadow-2xl w-full max-w-lg max-h-[80vh] overflow-y-auto"
      >
        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-200 dark:border-gray-700">
          <h2 className="text-base font-semibold text-gray-900 dark:text-white">Add field</h2>
          <button
            type="button"
            onClick={onClose}
            className="text-gray-500 hover:text-gray-700 dark:hover:text-gray-300"
            aria-label="Close"
          >
            <X size={18} />
          </button>
        </div>

        <div className="px-5 py-4 space-y-5">
          {FIELD_GROUPS.map((group) => (
            <div key={group.label}>
              <p className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-2">
                {group.label}
              </p>
              <div className="space-y-1">
                {group.types.map(({ type, icon, name, description }) => (
                  <button
                    key={type}
                    type="button"
                    onClick={() => { onPick(type); onClose(); }}
                    className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 text-left transition-colors"
                    data-testid={`field-type-${type}`}
                  >
                    <span className="text-lg w-7 text-center shrink-0">{icon}</span>
                    <div>
                      <p className="text-sm font-medium text-gray-900 dark:text-gray-100">{name}</p>
                      <p className="text-xs text-gray-500 dark:text-gray-400">{description}</p>
                    </div>
                  </button>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
