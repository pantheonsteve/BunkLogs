/**
 * Shared field renderer used by both the runtime reflection form (ReflectionFormPage)
 * and the live preview pane in the template editor. Handles all 12 field types.
 */

function getPromptText(field, language) {
  if (!field.prompts || typeof field.prompts !== 'object') return field.key || '';
  return field.prompts[language] || Object.values(field.prompts)[0] || field.key || '';
}

function getOptionLabel(opt, language) {
  if (!opt) return '';
  if (!opt.labels || typeof opt.labels !== 'object') return opt.key || '';
  return opt.labels[language] || Object.values(opt.labels)[0] || opt.key || '';
}

function getCategoryLabel(cat, language) {
  if (!cat) return '';
  if (!cat.labels || typeof cat.labels !== 'object') return cat.key || '';
  return cat.labels[language] || Object.values(cat.labels)[0] || cat.key || '';
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
  const baseInputClass =
    'w-full rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900 px-3 py-2 text-sm text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed';

  const wrapClass = `mb-5 transition-opacity ${dimmed ? 'opacity-50' : 'opacity-100'}`;

  const commonLabel = (
    <label className="block text-sm font-medium text-gray-800 dark:text-gray-200 mb-1">
      {prompt}
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
    const v = answer ?? '';
    const max = field.max_length;
    return (
      <div className={wrapClass}>
        {commonLabel}
        <textarea
          rows={4}
          data-testid={`reflect-input-${field.key}`}
          className={baseInputClass}
          value={v}
          onChange={(e) => onChange(e.target.value)}
          disabled={readonly}
          maxLength={typeof max === 'number' ? max : undefined}
        />
        <div className="flex justify-between text-xs text-gray-500 mt-1">
          <span className="text-red-600">{error || ''}</span>
          {typeof max === 'number' ? (
            <span>{v.length}/{max}</span>
          ) : (
            <span>{v.length} characters</span>
          )}
        </div>
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
          {options.map((opt) => (
            <label key={opt.key} className="flex items-center gap-2 text-sm cursor-pointer">
              <input
                type="radio"
                name={`choice_${field.key}`}
                checked={answer === opt.key}
                onChange={() => onChange(opt.key)}
                disabled={readonly}
              />
              <span>{getOptionLabel(opt, language)}</span>
            </label>
          ))}
        </div>
        {error && <p className="text-red-600 text-xs mt-1">{error}</p>}
      </div>
    );
  }

  if (field.type === 'multiple_choice') {
    const options = Array.isArray(field.options) ? field.options : [];
    const v = Array.isArray(answer) ? answer : [];
    const toggle = (key) => {
      if (readonly) return;
      onChange(v.includes(key) ? v.filter((x) => x !== key) : [...v, key]);
    };
    return (
      <div className={wrapClass}>
        {commonLabel}
        <div className="space-y-2">
          {options.map((opt) => (
            <label key={opt.key} className="flex items-center gap-2 text-sm cursor-pointer">
              <input
                type="checkbox"
                checked={v.includes(opt.key)}
                onChange={() => toggle(opt.key)}
                disabled={readonly}
              />
              <span>{getOptionLabel(opt, language)}</span>
            </label>
          ))}
        </div>
        {error && <p className="text-red-600 text-xs mt-1">{error}</p>}
      </div>
    );
  }

  if (field.type === 'yes_no') {
    const isYes = answer === 'yes' || answer === true;
    const isNo = answer === 'no' || answer === false;
    return (
      <div className={wrapClass}>
        {commonLabel}
        <div className="flex gap-2">
          {['yes', 'no'].map((val) => {
            const selected = val === 'yes' ? isYes : isNo;
            return (
              <button
                key={val}
                type="button"
                disabled={readonly}
                onClick={() => onChange(val)}
                className={`min-h-[40px] px-5 rounded-lg border text-sm font-medium transition-colors ${
                  selected
                    ? 'border-blue-600 bg-blue-600 text-white'
                    : 'border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900 text-gray-800 dark:text-gray-100'
                } disabled:opacity-50 disabled:cursor-not-allowed`}
              >
                {val === 'yes' ? 'Yes' : 'No'}
              </button>
            );
          })}
        </div>
        {isYes && field.follow_up_prompt && (
          <div className="mt-3">
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              {getPromptText({ prompts: { [language]: field.follow_up_prompt[language] || Object.values(field.follow_up_prompt)[0] } }, language)}
            </label>
            <textarea
              rows={3}
              className={baseInputClass}
              value={typeof answer === 'object' && answer?.follow_up ? answer.follow_up : ''}
              onChange={(e) => onChange({ value: 'yes', follow_up: e.target.value })}
              disabled={readonly}
            />
          </div>
        )}
        {error && <p className="text-red-600 text-xs mt-1">{error}</p>}
      </div>
    );
  }

  if (field.type === 'rating_group') {
    const scale = getScaleValues(field);
    const labels = getScaleLabels(field, language);
    const val = answer && typeof answer === 'object' ? answer : {};
    const heading = prompt || 'Ratings';
    return (
      <div className={`mb-6 ${dimmed ? 'opacity-50' : ''}`}>
        <p className="text-sm font-medium text-gray-800 dark:text-gray-200 mb-2">{heading}</p>
        <div className="space-y-3">
          {(field.categories || []).map((cat) => (
            <div key={cat.key}>
              <p className="text-xs text-gray-600 dark:text-gray-400 mb-2">
                {getCategoryLabel(cat, language)}
              </p>
              <div className="flex flex-wrap gap-2">
                {scale.map((n, idx) => {
                  const lbl = labels[idx] ?? String(n);
                  const selected = val[cat.key] === n || val[cat.key] === String(n);
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
            </div>
          ))}
        </div>
        {error && <p className="text-red-600 text-xs mt-1">{error}</p>}
      </div>
    );
  }

  if (field.type === 'single_rating') {
    const scale = getScaleValues(field);
    const labels = getScaleLabels(field, language);
    const val = answer;
    return (
      <div className={wrapClass}>
        {commonLabel}
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
        {error && <p className="text-red-600 text-xs mt-1">{error}</p>}
      </div>
    );
  }

  return null;
}
