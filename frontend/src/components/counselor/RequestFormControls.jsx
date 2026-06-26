/**
 * Shared input controls for the counselor request/ticket forms.
 *
 * - QuantityStepper: touch-friendly −/+ wrapper around a number input so
 *   counselors on phones aren't fighting tiny native spinners.
 * - ItemCombobox: searchable picker over catalog suggestions that always
 *   allows free text (the catalog list never blocks a submission). Keeps
 *   the item_id link when the typed/selected label matches a known option
 *   so the planning dashboard can aggregate by catalog item.
 */

import { useEffect, useId, useMemo, useRef, useState } from 'react';
import { Minus, Plus, ChevronDown } from 'lucide-react';

export function QuantityStepper({
  value,
  onChange,
  min = 0,
  ariaLabel = 'quantity',
  testId,
  className = '',
}) {
  const num = Number(value);
  const safeNum = Number.isFinite(num) ? num : min;
  const set = (n) => onChange(String(Math.max(min, n)));
  return (
    <div className={`inline-flex items-stretch rounded-lg border border-gray-300 dark:border-gray-600 overflow-hidden ${className}`}>
      <button
        type="button"
        aria-label={`Decrease ${ariaLabel}`}
        onClick={() => set(safeNum - 1)}
        disabled={safeNum <= min}
        className="px-3 min-h-[44px] flex items-center text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 disabled:opacity-40 disabled:hover:bg-transparent"
      >
        <Minus size={16} />
      </button>
      <input
        type="number"
        min={min}
        inputMode="numeric"
        value={value}
        aria-label={ariaLabel}
        data-testid={testId}
        onChange={(e) => onChange(e.target.value)}
        className="w-14 text-center border-x border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-sm text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-inset focus:ring-blue-500"
      />
      <button
        type="button"
        aria-label={`Increase ${ariaLabel}`}
        onClick={() => set(safeNum + 1)}
        className="px-3 min-h-[44px] flex items-center text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700"
      >
        <Plus size={16} />
      </button>
    </div>
  );
}

/**
 * Controlled combobox. `value` is the free-text label string. `onChange`
 * is called with (label, matchedOption|null) — matchedOption is the catalog
 * option when the label exactly matches one (case-insensitive) or the user
 * clicked it, so callers can keep the item_id link.
 */
export function ItemCombobox({
  value,
  onChange,
  options = [],
  placeholder = '',
  inputId,
  testId,
  ariaLabel,
  required = false,
}) {
  const [open, setOpen] = useState(false);
  const [highlight, setHighlight] = useState(-1);
  const wrapRef = useRef(null);
  const listId = useId();

  const matchOption = (label) => {
    const norm = (label || '').trim().toLowerCase();
    if (!norm) return null;
    return options.find((o) => (o.label || '').trim().toLowerCase() === norm) || null;
  };

  const filtered = useMemo(() => {
    const q = (value || '').trim().toLowerCase();
    if (!q) return options;
    return options.filter((o) => (o.label || '').toLowerCase().includes(q));
  }, [value, options]);

  useEffect(() => {
    const onDocClick = (e) => {
      if (wrapRef.current && !wrapRef.current.contains(e.target)) setOpen(false);
    };
    document.addEventListener('mousedown', onDocClick);
    return () => document.removeEventListener('mousedown', onDocClick);
  }, []);

  const choose = (opt) => {
    onChange(opt.label, opt);
    setOpen(false);
    setHighlight(-1);
  };

  const onType = (text) => {
    onChange(text, matchOption(text));
    if (!open) setOpen(true);
  };

  const onKeyDown = (e) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setOpen(true);
      setHighlight((h) => Math.min(filtered.length - 1, h + 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setHighlight((h) => Math.max(0, h - 1));
    } else if (e.key === 'Enter' && open && highlight >= 0 && filtered[highlight]) {
      e.preventDefault();
      choose(filtered[highlight]);
    } else if (e.key === 'Escape') {
      setOpen(false);
    }
  };

  return (
    <div className="relative" ref={wrapRef}>
      <div className="relative">
        <input
          id={inputId}
          data-testid={testId}
          role="combobox"
          aria-expanded={open}
          aria-controls={listId}
          aria-autocomplete="list"
          aria-label={ariaLabel}
          autoComplete="off"
          required={required}
          value={value}
          placeholder={placeholder}
          onChange={(e) => onType(e.target.value)}
          onFocus={() => setOpen(true)}
          onKeyDown={onKeyDown}
          className="block w-full min-h-[44px] rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 pl-3 pr-9 py-2 text-sm text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
        {options.length > 0 && (
          <button
            type="button"
            tabIndex={-1}
            aria-label="Toggle suggestions"
            onClick={() => setOpen((v) => !v)}
            className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-200"
          >
            <ChevronDown size={16} />
          </button>
        )}
      </div>
      {open && filtered.length > 0 && (
        <ul
          id={listId}
          role="listbox"
          data-testid={testId ? `${testId}-listbox` : undefined}
          className="absolute z-30 mt-1 max-h-60 w-full overflow-auto rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 shadow-lg py-1"
        >
          {filtered.map((opt, i) => (
            <li
              key={opt.id ?? opt.label}
              role="option"
              aria-selected={i === highlight}
              onMouseDown={(e) => { e.preventDefault(); choose(opt); }}
              onMouseEnter={() => setHighlight(i)}
              className={`flex items-center justify-between gap-2 px-3 py-2 text-sm cursor-pointer ${
                i === highlight
                  ? 'bg-blue-50 dark:bg-blue-900/30 text-blue-900 dark:text-blue-100'
                  : 'text-gray-900 dark:text-gray-100'
              }`}
            >
              <span>{opt.label}</span>
              {opt.unit ? <span className="text-xs text-gray-400">{opt.unit}</span> : null}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
