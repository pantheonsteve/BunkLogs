import { useCallback } from 'react';
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
} from '@dnd-kit/core';
import {
  SortableContext,
  sortableKeyboardCoordinates,
  useSortable,
  verticalListSortingStrategy,
  arrayMove,
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { GripVertical, AlertCircle } from 'lucide-react';

const FIELD_TYPE_ICONS = {
  text: 'T',
  textarea: '¶',
  text_list: '≡',
  single_choice: '◉',
  multiple_choice: '☑',
  yes_no: '?',
  date: '📅',
  number: '#',
  section_header: '—',
  instructions: 'ℹ',
  rating_group: '★',
  single_rating: '⭐',
};

function hasTranslationGap(field, languages) {
  if (!languages || languages.length <= 1) return false;
  const prompts = field.prompts;
  const scaleLabels = field.scale_labels;
  const usesPrompts = ['text', 'textarea', 'text_list', 'single_choice', 'multiple_choice',
    'yes_no', 'date', 'number', 'section_header', 'instructions'].includes(field.type);
  const usesScale = ['rating_group', 'single_rating'].includes(field.type);

  if (usesPrompts && prompts && typeof prompts === 'object') {
    return languages.some((lang) => !prompts[lang]);
  }
  if (usesScale && scaleLabels && typeof scaleLabels === 'object') {
    return languages.some((lang) => !scaleLabels[lang]);
  }
  return false;
}

function getDisplayName(field, language) {
  if (field.type === 'section_header' || field.type === 'instructions') {
    if (field.prompts) {
      return field.prompts[language] || Object.values(field.prompts)[0] || field.key || 'Untitled';
    }
    return field.key || 'Untitled';
  }
  if (field.prompts) {
    return field.prompts[language] || Object.values(field.prompts)[0] || field.key || 'Untitled';
  }
  return field.key || 'Untitled';
}

function SortableFieldCard({ field, isSelected, onSelect, language, languages }) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id: field._id,
  });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    zIndex: isDragging ? 10 : undefined,
  };

  const gap = hasTranslationGap(field, languages);
  const displayName = getDisplayName(field, language);
  const icon = FIELD_TYPE_ICONS[field.type] ?? '?';

  return (
    <div
      ref={setNodeRef}
      style={style}
      role="option"
      aria-selected={isSelected}
      onClick={() => onSelect(field._id)}
      className={`flex items-center gap-2 px-3 py-2 rounded-lg border cursor-pointer select-none transition-colors ${
        isDragging ? 'opacity-50' : ''
      } ${
        isSelected
          ? 'border-blue-400 bg-blue-50 dark:bg-blue-950/40 dark:border-blue-600'
          : 'border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 hover:border-gray-300 dark:hover:border-gray-600'
      }`}
    >
      <button
        type="button"
        aria-label="Drag to reorder"
        className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 cursor-grab active:cursor-grabbing shrink-0"
        {...attributes}
        {...listeners}
        onClick={(e) => e.stopPropagation()}
      >
        <GripVertical size={16} />
      </button>

      <span className="text-gray-500 dark:text-gray-400 text-xs font-mono w-4 shrink-0 text-center">
        {icon}
      </span>

      <div className="flex-1 min-w-0">
        <p className="text-sm text-gray-900 dark:text-gray-100 truncate leading-tight">{displayName}</p>
        <p className="text-xs text-gray-500 dark:text-gray-500 mt-0.5">
          {field.type}
          {field.dashboard_role ? ` · ${field.dashboard_role}` : ''}
        </p>
      </div>

      {gap && (
        <span title="Missing translations" className="shrink-0 text-amber-500">
          <AlertCircle size={14} />
        </span>
      )}
    </div>
  );
}

/**
 * @param {object} props
 * @param {Array}    props.fields       - array of field objects with _id added
 * @param {string}   props.selectedId   - _id of the selected field
 * @param {function} props.onSelect     - onSelect(_id)
 * @param {function} props.onReorder    - onReorder(newFields)
 * @param {function} props.onAddField   - called to open the type picker
 * @param {string}   props.language     - current language
 * @param {Array}    props.languages    - all declared languages
 */
export default function FieldList({ fields, selectedId, onSelect, onReorder, onAddField, language, languages }) {
  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates }),
  );

  const handleDragEnd = useCallback(
    (event) => {
      const { active, over } = event;
      if (over && active.id !== over.id) {
        const oldIdx = fields.findIndex((f) => f._id === active.id);
        const newIdx = fields.findIndex((f) => f._id === over.id);
        onReorder(arrayMove(fields, oldIdx, newIdx));
      }
    },
    [fields, onReorder],
  );

  return (
    <div className="flex flex-col h-full">
      <div
        role="listbox"
        aria-label="Template fields"
        className="flex-1 overflow-y-auto space-y-1 pr-1"
      >
        <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
          <SortableContext items={fields.map((f) => f._id)} strategy={verticalListSortingStrategy}>
            {fields.map((field) => (
              <SortableFieldCard
                key={field._id}
                field={field}
                isSelected={selectedId === field._id}
                onSelect={onSelect}
                language={language}
                languages={languages}
              />
            ))}
          </SortableContext>
        </DndContext>

        {fields.length === 0 && (
          <p className="text-sm text-gray-500 dark:text-gray-400 text-center py-6">
            No fields yet. Add one below.
          </p>
        )}
      </div>

      <button
        type="button"
        onClick={onAddField}
        className="mt-3 w-full border-2 border-dashed border-gray-300 dark:border-gray-600 rounded-lg py-2 text-sm text-gray-600 dark:text-gray-400 hover:border-blue-400 hover:text-blue-600 dark:hover:border-blue-500 dark:hover:text-blue-400 transition-colors"
        data-testid="add-field-button"
      >
        + Add field
      </button>
    </div>
  );
}
