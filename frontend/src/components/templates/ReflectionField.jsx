/**
 * Shared field renderer used by both the runtime reflection form (ReflectionFormPage)
 * and the live preview pane in the template editor. Handles all 12 field types.
 */

import Wysiwyg from '../form/Wysiwyg';
import InfoTooltip from '../common/InfoTooltip';

function getPromptText(field, language) {
  if (!field.prompts || typeof field.prompts !== 'object') return field.key || '';
  return field.prompts[language] || Object.values(field.prompts)[0] || field.key || '';
}

/** Stable option identifier — templates may use `key` or legacy `value`. */
function optionAnswerValue(opt) {
  if (!opt || typeof opt !== 'object') return '';
  const id = opt.key ?? opt.value;
  return typeof id === 'string' ? id : id != null ? String(id) : '';
}

function getOptionLabel(opt, language) {
  if (!opt) return '';
  const fallback = optionAnswerValue(opt);
  if (!opt.labels || typeof opt.labels !== 'object') return fallback;
  return opt.labels[language] || Object.values(opt.labels)[0] || fallback;
}

function getCategoryLabel(cat, language) {
  if (!cat) return '';
  if (!cat.labels || typeof cat.labels !== 'object') return cat.key || '';
  return cat.labels[language] || Object.values(cat.labels)[0] || cat.key || '';
}

function getLocalizedString(value, language) {
  if (!value) return '';
  if (typeof value === 'string') return value;
  if (typeof value === 'object') {
    return value[language] || Object.values(value)[0] || '';
  }
  return '';
}

function getScaleValues(field) {
  const labels =
    field.scale_labels && typeof field.scale_labels === 'object'
      ? Object.values(field.scale_labels)[0]
      : null;
  if (Array.isArray(labels) && labels.length > 0) {
    return labels.map((_, i) => i + 1);
  }
  if (Array.isArray(field.scale) && field.scale.length === 2) {
    const [min, max] = field.scale;
    return Array.from({ length: max - min + 1 }, (_, i) => min + i);
  }
  return [1, 2, 3, 4];
}

function getScaleLabels(field, language) {
  if (!field.scale_labels || typeof field.scale_labels !== 'object') return [];
  const row = field.scale_labels[language] || Object.values(field.scale_labels)[0];
  return Array.isArray(row) ? row : [];
}

function isFiveOneScale(scale) {
  return Array.isArray(scale) && scale.length === 5 && scale[0] === 1 && scale[4] === 5;
}

// Bunk Log "traffic-light" styling for 1–5 score buttons. Mirrors
// frontend/src/components/form/BunkLogForm.jsx so reflection forms feel
// identical to the daily Bunk Log scoring UI.
function scoreButtonClassName(score, selected, readonly) {
  const base =
    'flex-1 py-3 px-4 text-sm font-medium rounded-lg border transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-1';
  if (selected) {
    if (score === 1) return `${base} bg-[#e86946] text-white border-[#e86946] shadow-md`;
    if (score === 2) return `${base} bg-[#de8d6f] text-white border-[#de8d6f] shadow-md`;
    if (score === 3) return `${base} bg-[#e5e825] text-gray-800 border-[#e5e825] shadow-md`;
    if (score === 4) return `${base} bg-[#90d258] text-gray-800 border-[#90d258] shadow-md`;
    return `${base} bg-[#18d128] text-white border-[#18d128] shadow-md`;
  }
  if (readonly) {
    return `${base} bg-gray-100 text-gray-400 border-gray-200 cursor-not-allowed`;
  }
  return `${base} bg-gray-50 text-gray-700 border-gray-300 hover:bg-gray-100 hover:border-gray-400`;
}

/**
 * @param {object} props
 * @param {object} props.field        - field definition from schema.fields
 * @param {string} props.language     - current language code (e.g. 'en')
 * @param {*}      props.answer       - current answer value
 * @param {function} props.onChange   - callback(value) when answer changes
 * @param {string} [props.error]      - validation error message
 * @param {boolean} [props.readonly]  - disable all inputs (preview mode)
 * @param {boolean} [props.dimmed]    - reduce opacity (editor preview effect)
 */
export default function ReflectionField({ field, language, answer, onChange, error, readonly = false, dimmed = false }) {
  const prompt = getPromptText(field, language);
  const hintText = getLocalizedString(field.hint, language);
  const baseInputClass =
    'w-full rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900 px-3 py-2 text-sm text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed';

  const wrapClass = `mb-5 transition-opacity ${dimmed ? 'opacity-50' : 'opacity-100'}`;

  const commonLabel = (
    <label className="block text-sm font-medium text-gray-800 dark:text-gray-200 mb-1">
      {prompt}
      {hintText ? <InfoTooltip text={hintText} /> : null}
    </label>
  );

  if (field.type === 'section_header') {
    return (
      <div className={`mb-4 ${dimmed ? 'opacity-50' : ''}`}>
        <h3 className="text-base font-semibold text-gray-900 dark:text-white border-b border-gray-200 dark:border-gray-700 pb-2">
          {prompt}
        </h3>
      </div>
    );
  }

  if (field.type === 'instructions') {
    return (
      <div className={`mb-4 rounded-md bg-blue-50 dark:bg-blue-950/30 px-4 py-3 ${dimmed ? 'opacity-50' : ''}`}>
        <p className="text-sm text-blue-800 dark:text-blue-200">{prompt}</p>
      </div>
    );
  }

  if (field.type === 'text') {
    return (
      <div className={wrapClass}>
        {commonLabel}
        <input
          type="text"
          data-testid={`reflect-input-${field.key}`}
          className={baseInputClass}
          value={answer ?? ''}
          onChange={(e) => onChange(e.target.value)}
          disabled={readonly}
          maxLength={typeof field.max_length === 'number' ? field.max_length : undefined}
        />
        {error && <p className="text-red-600 text-xs mt-1">{error}</p>}
      </div>
    );
  }

  if (field.type === 'textarea') {
    const v = typeof answer === 'string' ? answer : '';
    return (
      <div className={wrapClass}>
        {commonLabel}
        <div
          className={`border border-gray-300 rounded-md dark:border-gray-600 overflow-hidden ${
            readonly ? 'quill-view-only' : ''
          }`}
          data-testid={`reflect-input-${field.key}`}
        >
          <Wysiwyg
            value={v}
            readOnly={readonly}
            showToolbar={!readonly}
            onChange={(html) => onChange(html)}
          />
        </div>
        {error ? <p className="text-red-600 text-xs mt-1">{error}</p> : null}
      </div>
    );
  }

  if (field.type === 'number') {
    return (
      <div className={wrapClass}>
        {commonLabel}
        <input
          type="number"
          data-testid={`reflect-input-${field.key}`}
          className={baseInputClass}
          value={answer ?? ''}
          onChange={(e) => onChange(e.target.value === '' ? '' : Number(e.target.value))}
          disabled={readonly}
        />
        {error && <p className="text-red-600 text-xs mt-1">{error}</p>}
      </div>
    );
  }

  if (field.type === 'date') {
    return (
      <div className={wrapClass}>
        {commonLabel}
        <input
          type="date"
          data-testid={`reflect-input-${field.key}`}
          className={baseInputClass}
          value={answer ?? ''}
          onChange={(e) => onChange(e.target.value)}
          disabled={readonly}
        />
        {error && <p className="text-red-600 text-xs mt-1">{error}</p>}
      </div>
    );
  }

  if (field.type === 'text_list') {
    const items = Array.isArray(answer) ? [...answer] : [];
    const maxItems = typeof field.max_items === 'number' ? field.max_items : 12;
    const minItems = typeof field.min_items === 'number' ? field.min_items : 1;
    return (
      <div className={wrapClass}>
        {commonLabel}
        <div className="space-y-2">
          {items.map((line, idx) => (
            <input
              key={idx}
              type="text"
              className={baseInputClass}
              value={line}
              onChange={(e) => {
                const next = [...items];
                next[idx] = e.target.value;
                onChange(next);
              }}
              disabled={readonly}
            />
          ))}
        </div>
        {!readonly && (
          <div className="flex flex-wrap gap-2 mt-2">
            {items.length < maxItems && (
              <button
                type="button"
                className="text-sm text-blue-600 dark:text-blue-400 hover:underline"
                onClick={() => onChange([...items, ''])}
              >
                + Add line
              </button>
            )}
            {items.length > minItems && (
              <button
                type="button"
                className="text-sm text-gray-600 dark:text-gray-400 hover:underline"
                onClick={() => onChange(items.slice(0, -1))}
              >
                Remove last
              </button>
            )}
          </div>
        )}
        {error && <p className="text-red-600 text-xs mt-1">{error}</p>}
      </div>
    );
  }

  if (field.type === 'single_choice') {
    const options = Array.isArray(field.options) ? field.options : [];
    return (
      <div className={wrapClass}>
        {commonLabel}
        <div className="space-y-2">
          {options.map((opt, idx) => {
            const optId = optionAnswerValue(opt);
            const reactKey = optId || `single_choice_${field.key}_${idx}`;
            return (
              <label key={reactKey} className="flex items-center gap-2 text-sm cursor-pointer">
                <input
                  type="radio"
                  name={`choice_${field.key}`}
                  checked={answer === optId}
                  onChange={() => onChange(optId)}
                  disabled={readonly}
                />
                <span>{getOptionLabel(opt, language)}</span>
              </label>
            );
          })}
        </div>
        {error && <p className="text-red-600 text-xs mt-1">{error}</p>}
      </div>
    );
  }

  if (field.type === 'multiple_choice') {
    const options = Array.isArray(field.options) ? field.options : [];
    const v = Array.isArray(answer) ? answer : [];
    const toggle = (choiceId) => {
      if (readonly) return;
      onChange(v.includes(choiceId) ? v.filter((x) => x !== choiceId) : [...v, choiceId]);
    };
    return (
      <div className={wrapClass}>
        {commonLabel}
        <div className="space-y-2">
          {options.map((opt, idx) => {
            const optId = optionAnswerValue(opt);
            const reactKey = optId || `multiple_choice_${field.key}_${idx}`;
            return (
              <label key={reactKey} className="flex items-center gap-2 text-sm cursor-pointer">
                <input
                  type="checkbox"
                  checked={v.includes(optId)}
                  onChange={() => toggle(optId)}
                  disabled={readonly}
                />
                <span>{getOptionLabel(opt, language)}</span>
              </label>
            );
          })}
        </div>
        {error && <p className="text-red-600 text-xs mt-1">{error}</p>}
      </div>
    );
  }

  if (field.type === 'yes_no') {
    const isCompound = answer && typeof answer === 'object' && !Array.isArray(answer);
    const rawValue = isCompound ? answer.value : answer;
    const followUp = isCompound && typeof answer.follow_up === 'string' ? answer.follow_up : '';
    const isYes = rawValue === 'yes' || rawValue === true;
    const followUpPrompt = field.follow_up_prompt
      ? getLocalizedString(field.follow_up_prompt, language)
      : '';

    const setChecked = (checked) => {
      if (readonly) return;
      if (checked) {
        onChange(followUpPrompt ? { value: 'yes', follow_up: followUp } : 'yes');
      } else {
        onChange('no');
      }
    };

    return (
      <div className={wrapClass}>
        <div className="flex items-center">
          {readonly ? (
            <>
              <div
                className={`h-5 w-5 border ${isYes ? 'bg-blue-600' : 'bg-white'} border-gray-300 rounded`}
                data-testid={`reflect-input-${field.key}`}
              >
                {isYes && (
                  <svg
                    className="h-4 w-4 text-white mx-auto my-0.5"
                    xmlns="http://www.w3.org/2000/svg"
                    viewBox="0 0 20 20"
                    fill="currentColor"
                  >
                    <path
                      fillRule="evenodd"
                      d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                      clipRule="evenodd"
                    />
                  </svg>
                )}
              </div>
              <label className="ml-2 block text-sm font-medium text-gray-700 dark:text-gray-300">
                {prompt}
                {hintText ? <InfoTooltip text={hintText} /> : null}
              </label>
            </>
          ) : (
            <>
              <input
                id={`yesno_${field.key}`}
                type="checkbox"
                data-testid={`reflect-input-${field.key}`}
                className="h-5 w-5 text-blue-600 border-gray-300 rounded focus:ring-blue-500 dark:border-gray-600"
                checked={isYes}
                onChange={(e) => setChecked(e.target.checked)}
                disabled={readonly}
              />
              <label
                htmlFor={`yesno_${field.key}`}
                className="ml-2 block text-sm font-medium text-gray-700 dark:text-gray-300"
              >
                {prompt}
                {hintText ? <InfoTooltip text={hintText} /> : null}
              </label>
            </>
          )}
        </div>
        {isYes && followUpPrompt ? (
          <div className="mt-3">
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              {followUpPrompt}
            </label>
            <textarea
              rows={3}
              className={baseInputClass}
              value={followUp}
              onChange={(e) => onChange({ value: 'yes', follow_up: e.target.value })}
              disabled={readonly}
            />
          </div>
        ) : null}
        {error && <p className="text-red-600 text-xs mt-1">{error}</p>}
      </div>
    );
  }

  if (field.type === 'rating_group') {
    const scale = getScaleValues(field);
    const labels = getScaleLabels(field, language);
    const val = answer && typeof answer === 'object' ? answer : {};
    const heading = prompt || 'Ratings';
    const useTrafficLight = isFiveOneScale(scale);
    return (
      <div className={`mb-6 ${dimmed ? 'opacity-50' : ''}`}>
        <p className="text-sm font-medium text-gray-800 dark:text-gray-200 mb-2">
          {heading}
          {hintText ? <InfoTooltip text={hintText} /> : null}
        </p>
        <div className="space-y-4">
          {(field.categories || []).map((cat) => {
            const categoryHint = getLocalizedString(cat.hint, language);
            const selectedValue = val[cat.key];
            return (
              <div key={cat.key}>
                <p className="text-xs text-gray-600 dark:text-gray-400 mb-2">
                  {getCategoryLabel(cat, language)}
                  {categoryHint ? <InfoTooltip text={categoryHint} /> : null}
                </p>
                {useTrafficLight ? (
                  <>
                    <div className="flex space-x-2">
                      {scale.map((n, idx) => {
                        const lbl = labels[idx] ?? String(n);
                        const selected = selectedValue === n || selectedValue === String(n);
                        return (
                          <button
                            key={String(n)}
                            type="button"
                            title={lbl}
                            disabled={readonly}
                            onClick={() => onChange({ ...val, [cat.key]: n })}
                            className={scoreButtonClassName(n, selected, readonly)}
                          >
                            {n}
                          </button>
                        );
                      })}
                    </div>
                    <div className="flex justify-between text-xs text-gray-500 mt-2">
                      <span>{labels[0] || 'Poor'}</span>
                      <span>{labels[scale.length - 1] || 'Excellent'}</span>
                    </div>
                  </>
                ) : (
                  <div className="flex flex-wrap gap-2">
                    {scale.map((n, idx) => {
                      const lbl = labels[idx] ?? String(n);
                      const selected = selectedValue === n || selectedValue === String(n);
                      return (
                        <button
                          key={String(n)}
                          type="button"
                          title={lbl}
                          disabled={readonly}
                          onClick={() => onChange({ ...val, [cat.key]: n })}
                          className={`min-h-[44px] min-w-[44px] px-3 rounded-lg border text-sm font-medium transition-colors ${
                            selected
                              ? 'border-blue-600 bg-blue-600 text-white'
                              : 'border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900 text-gray-800 dark:text-gray-100'
                          } disabled:opacity-50 disabled:cursor-not-allowed`}
                        >
                          {lbl}
                        </button>
                      );
                    })}
                  </div>
                )}
              </div>
            );
          })}
        </div>
        {error && <p className="text-red-600 text-xs mt-1">{error}</p>}
      </div>
    );
  }

  if (field.type === 'single_rating') {
    const scale = getScaleValues(field);
    const labels = getScaleLabels(field, language);
    const val = answer;
    const useTrafficLight = isFiveOneScale(scale);
    return (
      <div className={wrapClass}>
        {commonLabel}
        {useTrafficLight ? (
          <>
            <div className="flex space-x-2">
              {scale.map((n, idx) => {
                const lbl = labels[idx] ?? String(n);
                const selected = val === n || val === String(n);
                return (
                  <button
                    key={String(n)}
                    type="button"
                    title={lbl}
                    disabled={readonly}
                    onClick={() => onChange(n)}
                    className={scoreButtonClassName(n, selected, readonly)}
                  >
                    {n}
                  </button>
                );
              })}
            </div>
            <div className="flex justify-between text-xs text-gray-500 mt-2">
              <span>{labels[0] || 'Poor'}</span>
              <span>{labels[scale.length - 1] || 'Excellent'}</span>
            </div>
          </>
        ) : (
          <div className="flex flex-wrap gap-2">
            {scale.map((n, idx) => {
              const lbl = labels[idx] ?? String(n);
              const selected = val === n || val === String(n);
              return (
                <button
                  key={String(n)}
                  type="button"
                  title={lbl}
                  disabled={readonly}
                  onClick={() => onChange(n)}
                  className={`min-h-[44px] min-w-[44px] px-3 rounded-lg border text-sm font-medium transition-colors ${
                    selected
                      ? 'border-blue-600 bg-blue-600 text-white'
                      : 'border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900 text-gray-800 dark:text-gray-100'
                  } disabled:opacity-50 disabled:cursor-not-allowed`}
                >
                  {lbl}
                </button>
              );
            })}
          </div>
        )}
        {error && <p className="text-red-600 text-xs mt-1">{error}</p>}
      </div>
    );
  }

  return null;
}
