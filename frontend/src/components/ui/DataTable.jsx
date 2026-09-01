import { ChevronRight } from 'lucide-react';

/**
 * Table primitive for admin lists.
 *
 * Columns are declared rather than hand-written as markup so every list
 * gets the same header treatment, the same row hover, and the same
 * select-all semantics.
 *
 * `selection` wires the checkbox column; it deliberately owns only the
 * selected ids, leaving the bulk actions to `BulkActionBar`. Clicking a
 * row previews it, clicking the checkbox selects it — the two are kept
 * separate so it's never ambiguous which one a click does.
 *
 * Column shape: `{ key, header, width, align, className, render(row) }`.
 */
export default function DataTable({
  columns,
  rows,
  rowKey = (row) => row.id,
  rowTestId,
  onRowClick,
  selection,
  empty,
  className = '',
  ...rest
}) {
  const allSelected =
    selection && rows.length > 0 && rows.every((r) => selection.selected.has(rowKey(r)));

  if (rows.length === 0 && empty) {
    return (
      <div
        className={`bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-xl ${className}`.trim()}
        {...rest}
      >
        {empty}
      </div>
    );
  }

  return (
    <div
      className={`bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-xl overflow-hidden ${className}`.trim()}
      {...rest}
    >
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="bg-gray-50 dark:bg-gray-800/50">
              {selection && (
                <th className="w-10 px-4 py-2.5">
                  <input
                    type="checkbox"
                    checked={allSelected}
                    onChange={(e) => selection.onToggleAll(e.target.checked)}
                    aria-label="Select all rows"
                    data-testid="data-table-select-all"
                    className="w-4 h-4 accent-blue-600 cursor-pointer"
                  />
                </th>
              )}
              {columns.map((col) => (
                <th
                  key={col.key}
                  style={col.width ? { width: col.width } : undefined}
                  className={`px-4 py-2.5 text-[11px] font-bold uppercase tracking-wider text-gray-500 dark:text-gray-400 border-b border-gray-200 dark:border-gray-700 ${
                    col.align === 'right' ? 'text-right' : 'text-left'
                  }`}
                >
                  {col.header}
                </th>
              ))}
              {onRowClick && <th className="w-10 border-b border-gray-200 dark:border-gray-700" />}
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => {
              const key = rowKey(row);
              const isSelected = selection?.selected.has(key);
              return (
                <tr
                  key={key}
                  data-testid={rowTestId ? rowTestId(row) : `data-table-row-${key}`}
                  className={`border-b border-gray-100 dark:border-gray-800 last:border-b-0 ${
                    isSelected ? 'bg-indigo-50/60 dark:bg-indigo-950/20' : ''
                  } ${onRowClick ? 'cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800/50' : ''}`}
                >
                  {selection && (
                    <td className="px-4 py-3">
                      <input
                        type="checkbox"
                        checked={Boolean(isSelected)}
                        onChange={() => selection.onToggle(key)}
                        onClick={(e) => e.stopPropagation()}
                        aria-label={`Select row ${key}`}
                        className="w-4 h-4 accent-blue-600 cursor-pointer"
                      />
                    </td>
                  )}
                  {columns.map((col) => (
                    <td
                      key={col.key}
                      onClick={onRowClick ? () => onRowClick(row) : undefined}
                      className={`px-4 py-3 text-sm text-gray-700 dark:text-gray-300 align-middle ${
                        col.align === 'right' ? 'text-right' : ''
                      } ${col.className || ''}`}
                    >
                      {col.render(row)}
                    </td>
                  ))}
                  {onRowClick && (
                    <td
                      onClick={() => onRowClick(row)}
                      className="px-4 py-3 text-right text-gray-400"
                    >
                      <ChevronRight size={14} aria-hidden="true" />
                    </td>
                  )}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
