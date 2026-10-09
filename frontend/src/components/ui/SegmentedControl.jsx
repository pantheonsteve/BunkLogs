/**
 * Pill group for a small set of mutually exclusive views (date ranges,
 * current/past). A real group of <button aria-pressed> so each option is
 * keyboard-reachable and announces its state.
 */

export default function SegmentedControl({
  options,
  value,
  onChange,
  ariaLabel,
  testIdPrefix,
  className = '',
  ...rest
}) {
  return (
    <div
      role="group"
      aria-label={ariaLabel}
      className={`inline-flex p-[3px] rounded-[9px] bg-line-soft ${className}`.trim()}
      {...rest}
    >
      {options.map((opt) => {
        const active = opt.value === value;
        return (
          <button
            key={opt.value}
            type="button"
            aria-pressed={active}
            onClick={() => onChange(opt.value)}
            data-testid={testIdPrefix ? `${testIdPrefix}${opt.value}` : undefined}
            className={`min-h-[34px] px-3.5 rounded-[7px] text-[13px] transition-colors ${
              active
                ? 'bg-white dark:bg-gray-700 shadow-sm font-semibold text-ink'
                : 'font-medium text-ink-2 hover:text-ink'
            }`}
          >
            {opt.label}
          </button>
        );
      })}
    </div>
  );
}
