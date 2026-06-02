/**
 * Reflections Dashboard responses table.
 *
 * Renders one row per reflection with a column for every answerable template
 * field (scores, flags, text) using the same grid column order and colour
 * palette as ScoreGrid / the bunk dashboard.
 */

import { Link } from 'react-router-dom';
import { FileText } from 'lucide-react';
import RichText from '../components/ui/RichText';
import {
  deriveGridColumns,
  formatGridDisplayValue,
  gridCellValue,
  isScoredGridColumn,
  ratingTierClass,
  shortColumnHeader,
} from './subject/responseTable/schema';

/** Triage yes/no fields — narrow columns with coloured pills. */
const FLAG_FIELD_KEYS = new Set([
  'not_on_camp',
  'request_unit_head_help',
  'request_camper_care_help',
]);

/** Rating categories shown at equal width (counselor daily template). */
const EQUAL_RATING_CATEGORY_KEYS = new Set(['behavior', 'participation', 'social']);

function isFlagColumn(col) {
  return FLAG_FIELD_KEYS.has(col.field_key);
}

function columnWidthClass(col) {
  if (isFlagColumn(col)) {
    return 'w-[5.5rem] min-w-[5.5rem] max-w-[5.5rem]';
  }
  if (col.field_type === 'rating_group' && EQUAL_RATING_CATEGORY_KEYS.has(col.category_key)) {
    return 'w-[5rem] min-w-[5rem] max-w-[5rem]';
  }
  if (col.field_key === 'daily_report') {
    return 'min-w-[14rem] w-[22rem] max-w-none';
  }
  if (col.field_type === 'textarea' || col.field_type === 'text' || col.field_type === 'long_text') {
    return 'min-w-[8rem]';
  }
  return 'min-w-[5rem]';
}

function YesNoPill({ value }) {
  if (value === 'Yes') {
    return (
      <span className="inline-flex items-center justify-center rounded-full px-2 py-0.5 text-xs font-semibold bg-rose-100 text-rose-800 dark:bg-rose-900/50 dark:text-rose-200">
        Yes
      </span>
    );
  }
  if (value === 'No') {
    return (
      <span className="inline-flex items-center justify-center rounded-full px-2 py-0.5 text-xs font-semibold bg-emerald-100 text-emerald-800 dark:bg-emerald-900/50 dark:text-emerald-200">
        No
      </span>
    );
  }
  return null;
}

function GridCell({ col, value }) {
  const widthClass = columnWidthClass(col);

  if (isScoredGridColumn(col)) {
    const num = value == null || value === '' ? null : Number(value);
    const tone = ratingTierClass(Number.isFinite(num) ? num : null, col.scale_max || 5);
    return (
      <td
        className={`px-2 py-3 whitespace-nowrap text-center border border-gray-300 dark:border-gray-700 ${widthClass} ${tone}`}
        title={Number.isFinite(num) ? `${col.header}: ${num} / ${col.scale_max || 5}` : col.header}
      >
        <div className="text-base font-semibold tabular-nums">
          {Number.isFinite(num) ? num : '—'}
        </div>
      </td>
    );
  }

  const display = formatGridDisplayValue(value, col.field_type);
  const isYesNo = col.field_type === 'single_choice' || col.field_type === 'yes_no';
  const isWideText = col.field_type === 'textarea' || col.field_type === 'text' || col.field_type === 'long_text';

  return (
    <td
      className={`px-2 py-3 align-top border border-gray-300 dark:border-gray-700 ${widthClass} ${
        isFlagColumn(col) ? 'text-center' : ''
      }`}
      title={display ?? col.header}
    >
      {!display ? (
        <div className="text-base font-semibold text-gray-400 dark:text-gray-500 text-center">—</div>
      ) : isWideText ? (
        <RichText html={display} className="text-sm break-words line-clamp-6" />
      ) : isYesNo && isFlagColumn(col) ? (
        <YesNoPill value={display} />
      ) : isYesNo ? (
        <span className="text-sm text-gray-800 dark:text-gray-200">{display}</span>
      ) : (
        <span className="text-sm text-gray-800 dark:text-gray-200">{display}</span>
      )}
    </td>
  );
}

export default function AssignmentResponsesTable({
  block,
  language = 'en',
  showSubject = true,
  showGroup = true,
  subjectLinkBase = '/dashboards/subject',
}) {
  const reflections = block?.reflections ?? [];
  const columns = (block?.columns?.length ? block.columns : deriveGridColumns(
    { fields: block?.schema_fields ?? [] },
    language,
  ));
  const hasGroups = showGroup && reflections.some((r) => r.assignment_group?.name);

  // Grouped header row for rating_group parent labels (when categories share a field).
  const groupedHeader = [];
  let i = 0;
  while (i < columns.length) {
    const col = columns[i];
    if (col.field_type === 'rating_group' && col.category_key) {
      let j = i + 1;
      while (
        j < columns.length
        && columns[j].field_type === 'rating_group'
        && columns[j].field_key === col.field_key
      ) j += 1;
      const parent = block?.schema_fields?.find((f) => f.key === col.field_key);
      const groupLabel = parent?.prompts?.[language] ?? parent?.prompts?.en ?? col.field_key;
      groupedHeader.push({ label: groupLabel, span: j - i });
      i = j;
    } else {
      groupedHeader.push({ label: '', span: 1 });
      i += 1;
    }
  }
  const hasRatingGroups = groupedHeader.some((h) => h.label);
  const leadingCols = (showSubject ? 1 : 0) + (hasGroups ? 1 : 0);

  return (
    <section
      className="bg-white dark:bg-gray-800 shadow-sm rounded-2xl border border-gray-200 dark:border-gray-700 overflow-hidden"
      data-testid="assignment-responses"
    >
      <header className="flex items-center gap-2 px-5 py-4 border-b border-gray-100 dark:border-gray-700/60">
        <FileText className="w-4 h-4 text-indigo-500 shrink-0" />
        <h2 className="text-sm font-semibold text-gray-900 dark:text-white">Responses</h2>
        <span className="text-xs text-gray-400 dark:text-gray-500">
          {reflections.length} submission{reflections.length === 1 ? '' : 's'}
        </span>
      </header>

      {columns.length === 0 ? (
        <p className="px-5 py-10 text-sm text-center text-gray-400 dark:text-gray-500">
          No fields defined for this template.
        </p>
      ) : reflections.length === 0 ? (
        <p className="px-5 py-10 text-sm text-center text-gray-400 dark:text-gray-500">
          No responses for this date.
        </p>
      ) : (
        <div className="overflow-x-auto">
          <table className="table-fixed w-full text-sm dark:text-gray-300" data-testid="assignment-responses-table">
            <thead className="text-xs uppercase text-gray-500 dark:text-gray-400 bg-gray-50 dark:bg-gray-700/50">
              {hasRatingGroups && (
                <tr>
                  <th colSpan={leadingCols} className="p-2 border-b border-gray-200 dark:border-gray-700" />
                  {groupedHeader.map((h, idx) => (
                    <th
                      key={`g-${idx}`}
                      colSpan={h.span}
                      className="p-2 border-b border-gray-200 dark:border-gray-700 text-center text-[10px] tracking-wide normal-case"
                    >
                      {h.label}
                    </th>
                  ))}
                </tr>
              )}
              <tr>
                {showSubject && (
                  <th className="p-2 text-left border-b border-gray-200 dark:border-gray-700 font-semibold sticky left-0 z-10 bg-gray-50 dark:bg-gray-700/50">
                    Subject
                  </th>
                )}
                {hasGroups && (
                  <th className="p-2 text-left border-b border-gray-200 dark:border-gray-700 font-semibold w-28 min-w-[7rem]">
                    Group
                  </th>
                )}
                {columns.map((col) => (
                  <th
                    key={col.label}
                    className={`p-2 text-center border-b border-gray-200 dark:border-gray-700 font-semibold normal-case ${columnWidthClass(col)} ${
                      isFlagColumn(col) ? 'text-[10px] leading-tight' : ''
                    }`}
                    title={col.header}
                  >
                    <div className={`mx-auto ${
                      isFlagColumn(col) || col.field_key === 'daily_report'
                        ? ''
                        : 'truncate max-w-[8rem]'
                    }`}
                    >
                      {shortColumnHeader(col.header, col.field_type)}
                    </div>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="text-sm font-medium divide-y divide-gray-200 dark:divide-gray-700/60">
              {reflections.map((r) => (
                <tr key={r.id} data-testid={`assignment-response-row-${r.id}`}>
                  {showSubject && (
                    <td className="px-3 py-3 whitespace-nowrap border border-gray-300 dark:border-gray-700 sticky left-0 z-10 bg-white dark:bg-gray-800">
                      {r.subject?.id && subjectLinkBase ? (
                        <Link
                          to={`${subjectLinkBase}/${r.subject.id}`}
                          className="font-medium text-indigo-700 hover:underline dark:text-indigo-300"
                        >
                          {r.subject.name ?? 'Unknown'}
                        </Link>
                      ) : (
                        <span className="font-medium text-gray-800 dark:text-gray-100">
                          {r.subject?.name ?? r.author_name ?? '—'}
                        </span>
                      )}
                    </td>
                  )}
                  {hasGroups && (
                    <td className="px-3 py-3 whitespace-nowrap border border-gray-300 dark:border-gray-700 text-sm w-28 min-w-[7rem]">
                      {r.assignment_group?.id ? (
                        <Link
                          to={`/dashboards/group/${r.assignment_group.id}${r.date ? `?date=${r.date}` : ''}`}
                          className="font-medium text-indigo-700 hover:underline dark:text-indigo-300"
                        >
                          {r.assignment_group.name ?? '—'}
                        </Link>
                      ) : (
                        <span className="text-gray-700 dark:text-gray-200">
                          {r.assignment_group?.name ?? '—'}
                        </span>
                      )}
                    </td>
                  )}
                  {columns.map((col) => (
                    <GridCell
                      key={`${r.id}-${col.label}`}
                      col={col}
                      value={gridCellValue(r.answers, col)}
                    />
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
