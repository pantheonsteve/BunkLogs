import { Search } from 'lucide-react';

/**
 * The row of narrowing controls above an admin list.
 *
 * Same content should get the same affordances on every screen, so
 * search, segmented chips and dropdowns are defined once here rather
 * than each page inventing its own pill styling.
 */

export function SearchInput({ value, onChange, placeholder = 'Search…', className = '', ...rest }) {
  return (
    <div className={`relative ${className}`.trim()}>
      <Search
        size={15}
        className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none"
        aria-hidden="true"
      />
      <input
        type="search"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="w-full min-w-[14rem] pl-9 pr-3 py-1.5 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-sm text-gray-900 dark:text-white placeholder:text-gray-400"
        {...rest}
      />
    </div>
  );
}

/** Segmented control for a small set of mutually exclusive states. */
export function FilterChips({ value, onChange, options, testIdPrefix, className = '', ...rest }) {
  return (
    <div
      className={`inline-flex rounded-lg border border-gray-300 dark:border-gray-600 overflow-hidden ${className}`.trim()}
      {...rest}
    >
      {options.map((opt) => (
        <button
          key={opt.value}
          type="button"
          onClick={() => onChange(opt.value)}
          aria-pressed={value === opt.value}
          data-testid={testIdPrefix ? `${testIdPrefix}${opt.value}` : undefined}
          className={`px-3 py-1.5 text-xs font-semibold transition-colors border-r last:border-r-0 border-gray-300 dark:border-gray-600 ${
            value === opt.value
              ? 'bg-blue-600 text-white'
              : 'bg-white dark:bg-gray-800 text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700'
          }`}
        >
          {opt.label}
        </button>
      ))}
    </div>
  );
}

export function FilterSelect({ value, onChange, options, className = '', ...rest }) {
  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className={`px-3 py-1.5 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-sm text-gray-700 dark:text-gray-300 ${className}`.trim()}
      {...rest}
    >
      {options.map((opt) => (
        <option key={opt.value} value={opt.value}>
          {opt.label}
        </option>
      ))}
    </select>
  );
}

export default function FilterBar({ className = '', children, ...rest }) {
  return (
    <div
      className={`flex flex-wrap items-center gap-2 mb-4 ${className}`.trim()}
      data-testid="filter-bar"
      {...rest}
    >
      {children}
    </div>
  );
}
