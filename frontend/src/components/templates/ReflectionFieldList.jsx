/**
 * Renders a template's fields as a list of memoized <ReflectionField> rows
 * with STABLE per-field change handlers.
 *
 * Why this exists (and why every form should use it):
 * `<ReflectionField>` is memoized, but memoization only helps if each field's
 * `onChange` keeps the same identity across renders. When a page maps fields
 * with an inline `onChange={(v) => update(field.key, v)}`, every keystroke/tap
 * hands each field a brand-new function, so React re-renders and reconciles
 * the WHOLE form — including the heavy Quill rich-text editor — on every tap.
 * On mobile that blocks the main thread for 1–2s, which reads as an
 * unresponsive control and produces rage-clicks (see RUM, June 2026).
 *
 * This component keeps a per-key handler cache and reads the latest `onChange`
 * through a ref, so the handlers are stable even if the caller passes an inline
 * `onChange`. Tapping one input now only re-renders that one field.
 *
 * `onChange` is called as `onChange(fieldKey, value)`.
 */

import { memo, useCallback, useRef } from 'react';
import ReflectionField from './ReflectionField';

function ReflectionFieldList({
  fields,
  answers,
  errors,
  language,
  onChange,
  readonly = false,
  dimmed = false,
  fieldClassName,
  renderBefore,
}) {
  const onChangeRef = useRef(onChange);
  onChangeRef.current = onChange;

  const handlersRef = useRef(new Map());
  const getHandler = useCallback((key) => {
    const cache = handlersRef.current;
    let handler = cache.get(key);
    if (!handler) {
      handler = (val) => onChangeRef.current?.(key, val);
      cache.set(key, handler);
    }
    return handler;
  }, []);

  return (fields || []).map((field, idx) => {
    const rowKey = field?.key || `field_${idx}`;
    const fieldEl = (
      <ReflectionField
        key={fieldClassName || renderBefore ? undefined : rowKey}
        field={field}
        language={language}
        answer={answers?.[field?.key]}
        onChange={getHandler(field?.key)}
        error={errors?.[field?.key]}
        readonly={readonly}
        dimmed={dimmed}
      />
    );

    if (fieldClassName || renderBefore) {
      return (
        <div key={rowKey} className={fieldClassName}>
          {renderBefore ? renderBefore(field) : null}
          {fieldEl}
        </div>
      );
    }
    return fieldEl;
  });
}

export default memo(ReflectionFieldList);
