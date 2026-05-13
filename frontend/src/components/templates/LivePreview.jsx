import { useCallback, useEffect, useMemo, useState } from 'react';
import ReflectionField from './ReflectionField';
import { buildDefaultAnswers } from '../../utils/reflection/reflectionFormValidation';

/**
 * Phone-frame live preview of the reflection form.
 * Updates from the parent schema are debounced 200ms.
 *
 * @param {object} props
 * @param {object}  props.schema         - { fields: [...] }
 * @param {string}  props.language       - current language code
 * @param {string}  [props.selectedFieldId] - _id of the currently-edited field (dims others)
 */
export default function LivePreview({ schema, language, selectedFieldId }) {
  const [displayed, setDisplayed] = useState(schema);

  useEffect(() => {
    const t = setTimeout(() => setDisplayed(schema), 200);
    return () => clearTimeout(t);
  }, [schema]);

  const fields = useMemo(() => (displayed?.fields || []), [displayed]);

  const defaults = useMemo(() => buildDefaultAnswers(displayed || {}), [displayed]);
  const [answers, setAnswers] = useState(defaults);

  useEffect(() => {
    setAnswers(buildDefaultAnswers(displayed || {}));
  }, [displayed]);

  const handleChange = useCallback((key, value) => {
    setAnswers((prev) => ({ ...prev, [key]: value }));
  }, []);

  const isMetaType = (type) => type === 'section_header' || type === 'instructions';

  return (
    <div className="flex justify-center">
      <div
        className="w-full max-w-[340px] rounded-2xl border-4 border-gray-800 dark:border-gray-600 bg-gray-50 dark:bg-gray-950 shadow-lg overflow-hidden"
        role="region"
        aria-label="Live preview"
      >
        {/* Fake status bar */}
        <div className="bg-gray-800 dark:bg-gray-700 text-white text-xs px-4 py-1 flex justify-between">
          <span>9:41</span>
          <span>Preview only</span>
        </div>

        <div className="px-4 py-5 overflow-y-auto max-h-[540px]">
          {fields.length === 0 ? (
            <p className="text-sm text-gray-500 dark:text-gray-400 text-center py-8">
              Add fields to see a preview
            </p>
          ) : (
            <>
              {fields.map((field, idx) => {
                const isSelected = field._id === selectedFieldId;
                const after = selectedFieldId
                  ? fields.findIndex((f) => f._id === selectedFieldId)
                  : -1;
                const dimmed = after >= 0 && idx > after && !isSelected;

                if (isMetaType(field.type)) {
                  return (
                    <ReflectionField
                      key={field._id || field.key || idx}
                      field={field}
                      language={language}
                      answer={undefined}
                      onChange={() => {}}
                      dimmed={dimmed}
                    />
                  );
                }

                // Preview is interactive (not readonly) so authors can try
                // selecting score buttons, toggling yes_no, typing into the
                // Quill editor, etc. Submit stays disabled below; the phone
                // frame + "Preview only" status bar make it clear nothing
                // gets persisted.
                return (
                  <ReflectionField
                    key={field._id || field.key || idx}
                    field={field}
                    language={language}
                    answer={answers[field.key]}
                    onChange={(val) => handleChange(field.key, val)}
                    dimmed={dimmed}
                  />
                );
              })}

              <button
                type="button"
                disabled
                title="Preview only"
                className="w-full mt-4 py-2.5 rounded-lg bg-blue-600 text-white text-sm font-medium opacity-40 cursor-not-allowed"
              >
                Submit reflection
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
