import { useEffect, useState } from 'react';
import { Trash2, ChevronDown, ChevronRight, Plus, X } from 'lucide-react';
import FieldKeyAutocomplete from './FieldKeyAutocomplete';

const DASHBOARD_ROLES = ['primary_rating', 'category_ratings', 'wins', 'improvements', 'open_concern'];
const DASHBOARD_ROLE_ALLOWED_TYPES = {
  primary_rating: new Set(['single_rating']),
  category_ratings: new Set(['rating_group']),
  wins: new Set(['text_list']),
  improvements: new Set(['text_list']),
  open_concern: new Set(['text', 'textarea']),
};

function inputClass() {
  return 'w-full rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900 px-2 py-1.5 text-sm text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500';
}

function Label({ children, htmlFor }) {
  return (
    <label htmlFor={htmlFor} className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">
      {children}
    </label>
  );
}

function LanguageTabInput({ field, language, languages, onChange, fieldKey = 'prompts', multiline = false }) {
  const [active, setActive] = useState(language);
  useEffect(() => { setActive(language); }, [language]);
  const currentLang = languages.includes(active) ? active : languages[0];
  const prompts = field[fieldKey] || {};

  return (
    <div>
      <div className="flex gap-1 mb-1">
        {languages.map((lang) => (
          <button
            key={lang}
            type="button"
            onClick={() => setActive(lang)}
            className={`px-2 py-0.5 rounded text-xs font-medium transition-colors ${
              currentLang === lang
                ? 'bg-blue-600 text-white'
                : 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800'
            }`}
          >
            {lang}
          </button>
        ))}
      </div>
      {multiline ? (
        <textarea
          rows={3}
          className={inputClass()}
          value={prompts[currentLang] || ''}
          onChange={(e) =>
            onChange({ ...field, [fieldKey]: { ...prompts, [currentLang]: e.target.value } })
          }
        />
      ) : (
        <input
          type="text"
          className={inputClass()}
          value={prompts[currentLang] || ''}
          onChange={(e) =>
            onChange({ ...field, [fieldKey]: { ...prompts, [currentLang]: e.target.value } })
          }
        />
      )}
    </div>
  );
}

function OptionsEditor({ field, language, languages, onChange }) {
  const options = Array.isArray(field.options) ? field.options : [];
  const [active, setActive] = useState(language);
  const currentLang = languages.includes(active) ? active : languages[0];

  const addOption = () => {
    const key = `option_${Date.now()}`;
    const newOption = { key, labels: { [currentLang]: '' } };
    onChange({ ...field, options: [...options, newOption] });
  };

  const updateLabel = (idx, val) => {
    const updated = options.map((opt, i) => {
      if (i !== idx) return opt;
      return { ...opt, labels: { ...(opt.labels || {}), [currentLang]: val } };
    });
    onChange({ ...field, options: updated });
  };

  const updateKey = (idx, val) => {
    const updated = options.map((opt, i) => (i === idx ? { ...opt, key: val } : opt));
    onChange({ ...field, options: updated });
  };

  const removeOption = (idx) => {
    onChange({ ...field, options: options.filter((_, i) => i !== idx) });
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-1">
        <Label>Options</Label>
        <div className="flex gap-1">
          {languages.map((lang) => (
            <button
              key={lang}
              type="button"
              onClick={() => setActive(lang)}
              className={`px-1.5 py-0.5 rounded text-xs font-medium ${
                currentLang === lang ? 'bg-blue-600 text-white' : 'text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-800'
              }`}
            >
              {lang}
            </button>
          ))}
        </div>
      </div>
      <div className="space-y-1.5">
        {options.map((opt, idx) => (
          <div key={opt.key || idx} className="flex gap-1">
            <input
              type="text"
              placeholder="key"
              className="w-24 rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900 px-2 py-1 text-xs font-mono"
              value={opt.key || ''}
              onChange={(e) => updateKey(idx, e.target.value.toLowerCase().replace(/[^a-z0-9_]/g, ''))}
            />
            <input
              type="text"
              placeholder="Label"
              className="flex-1 rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900 px-2 py-1 text-xs"
              value={(opt.labels || {})[currentLang] || ''}
              onChange={(e) => updateLabel(idx, e.target.value)}
            />
            <button
              type="button"
              onClick={() => removeOption(idx)}
              className="text-red-400 hover:text-red-600 px-1"
              aria-label="Remove option"
            >
              <X size={14} />
            </button>
          </div>
        ))}
      </div>
      <button
        type="button"
        onClick={addOption}
        className="mt-1.5 text-xs text-blue-600 dark:text-blue-400 hover:underline flex items-center gap-1"
      >
        <Plus size={12} /> Add option
      </button>
    </div>
  );
}

function CategoriesEditor({ field, language, languages, onChange }) {
  const categories = Array.isArray(field.categories) ? field.categories : [];
  const [active, setActive] = useState(language);
  const currentLang = languages.includes(active) ? active : languages[0];

  const addCategory = () => {
    const key = `cat_${Date.now()}`;
    onChange({ ...field, categories: [...categories, { key, labels: { [currentLang]: '' } }] });
  };

  const updateKey = (idx, val) => {
    onChange({ ...field, categories: categories.map((c, i) => (i === idx ? { ...c, key: val } : c)) });
  };

  const updateLabel = (idx, val) => {
    onChange({
      ...field,
      categories: categories.map((c, i) =>
        i === idx ? { ...c, labels: { ...(c.labels || {}), [currentLang]: val } } : c,
      ),
    });
  };

  const removeCategory = (idx) => {
    onChange({ ...field, categories: categories.filter((_, i) => i !== idx) });
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-1">
        <Label>Categories</Label>
        <div className="flex gap-1">
          {languages.map((lang) => (
            <button
              key={lang}
              type="button"
              onClick={() => setActive(lang)}
              className={`px-1.5 py-0.5 rounded text-xs font-medium ${
                currentLang === lang ? 'bg-blue-600 text-white' : 'text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-800'
              }`}
            >
              {lang}
            </button>
          ))}
        </div>
      </div>
      <div className="space-y-1.5">
        {categories.map((cat, idx) => (
          <div key={cat.key || idx} className="flex gap-1">
            <input
              type="text"
              placeholder="key"
              className="w-24 rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900 px-2 py-1 text-xs font-mono"
              value={cat.key || ''}
              onChange={(e) => updateKey(idx, e.target.value.toLowerCase().replace(/[^a-z0-9_]/g, ''))}
            />
            <input
              type="text"
              placeholder="Label"
              className="flex-1 rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900 px-2 py-1 text-xs"
              value={(cat.labels || {})[currentLang] || ''}
              onChange={(e) => updateLabel(idx, e.target.value)}
            />
            <button
              type="button"
              onClick={() => removeCategory(idx)}
              className="text-red-400 hover:text-red-600 px-1"
              aria-label="Remove category"
            >
              <X size={14} />
            </button>
          </div>
        ))}
      </div>
      <button
        type="button"
        onClick={addCategory}
        className="mt-1.5 text-xs text-blue-600 dark:text-blue-400 hover:underline flex items-center gap-1"
      >
        <Plus size={12} /> Add category
      </button>
    </div>
  );
}

function ScaleLabelsEditor({ field, language, languages, onChange }) {
  const [active, setActive] = useState(language);
  const currentLang = languages.includes(active) ? active : languages[0];
  const scaleLabels = field.scale_labels || {};
  const currentLabels = Array.isArray(scaleLabels[currentLang]) ? scaleLabels[currentLang] : [];

  const updateLabel = (idx, val) => {
    const updated = [...currentLabels];
    updated[idx] = val;
    onChange({ ...field, scale_labels: { ...scaleLabels, [currentLang]: updated } });
  };

  const addLabel = () => {
    const updated = [...currentLabels, String(currentLabels.length + 1)];
    onChange({ ...field, scale_labels: { ...scaleLabels, [currentLang]: updated } });
  };

  const removeLastLabel = () => {
    if (currentLabels.length <= 2) return;
    onChange({ ...field, scale_labels: { ...scaleLabels, [currentLang]: currentLabels.slice(0, -1) } });
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-1">
        <Label>Scale labels</Label>
        <div className="flex gap-1">
          {languages.map((lang) => (
            <button
              key={lang}
              type="button"
              onClick={() => setActive(lang)}
              className={`px-1.5 py-0.5 rounded text-xs font-medium ${
                currentLang === lang ? 'bg-blue-600 text-white' : 'text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-800'
              }`}
            >
              {lang}
            </button>
          ))}
        </div>
      </div>
      <div className="grid grid-cols-2 gap-1.5">
        {currentLabels.map((lbl, idx) => (
          <input
            key={idx}
            type="text"
            className="rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900 px-2 py-1 text-xs"
            value={lbl}
            onChange={(e) => updateLabel(idx, e.target.value)}
            placeholder={`Step ${idx + 1}`}
          />
        ))}
      </div>
      <div className="flex gap-2 mt-1.5">
        <button
          type="button"
          onClick={addLabel}
          className="text-xs text-blue-600 dark:text-blue-400 hover:underline flex items-center gap-1"
        >
          <Plus size={12} /> Add step
        </button>
        {currentLabels.length > 2 && (
          <button
            type="button"
            onClick={removeLastLabel}
            className="text-xs text-red-500 hover:underline"
          >
            Remove last
          </button>
        )}
      </div>
    </div>
  );
}

/**
 * @param {object}   props.field       - selected field object
 * @param {function} props.onChange    - onChange(updatedField)
 * @param {function} props.onDelete    - called when delete is confirmed
 * @param {string}   props.language    - current editor language
 * @param {Array}    props.languages   - all declared languages
 */
export default function FieldInspector({ field, onChange, onDelete, language, languages }) {
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);

  if (!field) {
    return (
      <div className="flex items-center justify-center h-full text-sm text-gray-500 dark:text-gray-400 px-4 text-center">
        Select a field to edit it
      </div>
    );
  }

  const validDashboardRoles = DASHBOARD_ROLES.filter(
    (role) => !DASHBOARD_ROLE_ALLOWED_TYPES[role] || DASHBOARD_ROLE_ALLOWED_TYPES[role].has(field.type),
  );

  const isMetaType = field.type === 'section_header' || field.type === 'instructions';
  const hasOptions = field.type === 'single_choice' || field.type === 'multiple_choice';
  const hasScale = field.type === 'rating_group' || field.type === 'single_rating';
  const hasCategories = field.type === 'rating_group';
  const hasFollowUp = field.type === 'yes_no';
  const usesPrompts = !['rating_group', 'single_rating'].includes(field.type);

  return (
    <div className="h-full overflow-y-auto">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-gray-900 dark:text-white">Edit field</h3>
        {confirmDelete ? (
          <div className="flex items-center gap-2">
            <span className="text-xs text-red-600">Delete?</span>
            <button
              type="button"
              onClick={() => { onDelete(); setConfirmDelete(false); }}
              className="text-xs bg-red-600 text-white px-2 py-0.5 rounded hover:bg-red-700"
            >
              Yes
            </button>
            <button
              type="button"
              onClick={() => setConfirmDelete(false)}
              className="text-xs text-gray-600 dark:text-gray-400 px-2 py-0.5 rounded hover:bg-gray-100 dark:hover:bg-gray-800"
            >
              No
            </button>
          </div>
        ) : (
          <button
            type="button"
            onClick={() => setConfirmDelete(true)}
            className="text-red-600 dark:text-red-400 hover:text-red-700 text-xs flex items-center gap-1"
            aria-label="Delete field"
          >
            <Trash2 size={14} /> Delete
          </button>
        )}
      </div>

      <div className="space-y-4">
        {usesPrompts && (
          <div>
            <Label>Prompt</Label>
            <LanguageTabInput
              field={field}
              language={language}
              languages={languages}
              onChange={onChange}
              fieldKey="prompts"
              multiline={field.type === 'textarea' || field.type === 'instructions'}
            />
          </div>
        )}

        {!isMetaType && (
          <div className="flex items-center justify-between">
            <Label>Required</Label>
            <button
              type="button"
              role="switch"
              aria-checked={field.required !== false}
              onClick={() => onChange({ ...field, required: field.required === false })}
              className={`relative inline-flex h-5 w-9 rounded-full transition-colors ${
                field.required !== false ? 'bg-blue-600' : 'bg-gray-300 dark:bg-gray-600'
              }`}
            >
              <span
                className={`inline-block h-4 w-4 mt-0.5 rounded-full bg-white shadow transition-transform ${
                  field.required !== false ? 'translate-x-4' : 'translate-x-0.5'
                }`}
              />
            </button>
          </div>
        )}

        {(field.type === 'text' || field.type === 'textarea') && (
          <div>
            <Label htmlFor="max_length">Max length</Label>
            <input
              id="max_length"
              type="number"
              min="1"
              className={inputClass()}
              value={field.max_length ?? ''}
              onChange={(e) =>
                onChange({ ...field, max_length: e.target.value ? Number(e.target.value) : undefined })
              }
            />
          </div>
        )}

        {field.type === 'text_list' && (
          <div className="grid grid-cols-2 gap-2">
            <div>
              <Label htmlFor="min_items">Min items</Label>
              <input
                id="min_items"
                type="number"
                min="0"
                className={inputClass()}
                value={field.min_items ?? 1}
                onChange={(e) => onChange({ ...field, min_items: Number(e.target.value) })}
              />
            </div>
            <div>
              <Label htmlFor="max_items">Max items</Label>
              <input
                id="max_items"
                type="number"
                min="1"
                className={inputClass()}
                value={field.max_items ?? 5}
                onChange={(e) => onChange({ ...field, max_items: Number(e.target.value) })}
              />
            </div>
          </div>
        )}

        {hasOptions && (
          <OptionsEditor field={field} language={language} languages={languages} onChange={onChange} />
        )}

        {hasScale && (
          <ScaleLabelsEditor field={field} language={language} languages={languages} onChange={onChange} />
        )}

        {hasCategories && (
          <CategoriesEditor field={field} language={language} languages={languages} onChange={onChange} />
        )}

        {hasFollowUp && (
          <div>
            <div className="flex items-center justify-between mb-1">
              <Label>Follow-up when yes</Label>
              <button
                type="button"
                role="switch"
                aria-checked={!!field.follow_up_on}
                onClick={() => onChange({ ...field, follow_up_on: !field.follow_up_on })}
                className={`relative inline-flex h-5 w-9 rounded-full transition-colors ${
                  field.follow_up_on ? 'bg-blue-600' : 'bg-gray-300 dark:bg-gray-600'
                }`}
              >
                <span
                  className={`inline-block h-4 w-4 mt-0.5 rounded-full bg-white shadow transition-transform ${
                    field.follow_up_on ? 'translate-x-4' : 'translate-x-0.5'
                  }`}
                />
              </button>
            </div>
            {field.follow_up_on && (
              <div className="mt-2">
                <Label>Follow-up prompt</Label>
                <LanguageTabInput
                  field={field}
                  language={language}
                  languages={languages}
                  onChange={onChange}
                  fieldKey="follow_up_prompt"
                  multiline={false}
                />
              </div>
            )}
          </div>
        )}

        {/* Advanced section */}
        <div className="border-t border-gray-200 dark:border-gray-700 pt-3">
          <button
            type="button"
            onClick={() => setShowAdvanced((v) => !v)}
            className="flex items-center gap-1 text-xs text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300"
          >
            {showAdvanced ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
            Advanced
          </button>

          {showAdvanced && (
            <div className="mt-3 space-y-3">
              <div>
                <Label>Field key</Label>
                <FieldKeyAutocomplete
                  value={field.key || ''}
                  onChange={(key) => onChange({ ...field, key })}
                  promptHint={field.prompts?.en || field.prompts?.[Object.keys(field.prompts || {})[0]] || ''}
                />
              </div>

              {validDashboardRoles.length > 0 && (
                <div>
                  <Label htmlFor="dashboard_role">Dashboard role</Label>
                  <select
                    id="dashboard_role"
                    className={inputClass()}
                    value={field.dashboard_role || ''}
                    onChange={(e) =>
                      onChange({ ...field, dashboard_role: e.target.value || undefined })
                    }
                  >
                    <option value="">None</option>
                    {validDashboardRoles.map((r) => (
                      <option key={r} value={r}>{r}</option>
                    ))}
                  </select>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
