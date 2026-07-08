/**
 * Schema-aware cell components shared between the LT Responses page
 * and the per-subject dashboard. Keeping a single implementation
 * guarantees both surfaces render reflection rows identically.
 */

import { Link } from 'react-router-dom';
import { getInitials, ratingTierClass, isTruthyFlag } from './schema';
import RichText from '../../../components/ui/RichText';

/** Secondary styling for staff placement labels under the subject name. */
const assignmentLabelClass =
  'text-slate-600 hover:text-slate-800 hover:underline dark:text-slate-400 dark:hover:text-slate-300';

/** Avatar + name + optional subtitle. When ``linkTo`` is provided
 *  the name is rendered as a Router link (otherwise plain text). */
export function SubjectCell({
  row,
  linkTo = null,
  groupsUnderName = false,
  groupDate = null,
}) {
  const person = row.subject?.name ? row.subject : row.author;
  const name = person?.name ?? 'Unknown';
  const subtitle = row.subject_group ?? row.bunk_name ?? null;
  const groups = row.groups ?? [];
  const nameNode = linkTo ? (
    <Link
      to={linkTo}
      className="font-medium text-indigo-700 hover:underline dark:text-indigo-300"
    >
      {name}
    </Link>
  ) : (
    <span className="font-medium text-gray-800 dark:text-gray-100">{name}</span>
  );
  return (
    <td className="px-3 py-3 whitespace-nowrap border border-gray-300 dark:border-gray-700">
      <div className="flex items-center">
        <div className="w-10 h-10 shrink-0 flex items-center justify-center bg-gray-100 dark:bg-gray-700 rounded-full mr-3">
          <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
            {getInitials(name)}
          </span>
        </div>
        <div>
          <div>{nameNode}</div>
          {groupsUnderName && groups.length > 0 ? (
            <div className="mt-0.5 space-y-0.5 text-xs">
              {groups.map((g) => {
                const label = g.name || `Group ${g.id ?? ''}`.trim();
                if (g.id) {
                  return (
                    <Link
                      key={g.id}
                      to={`/dashboards/group/${g.id}${groupDate ? `?date=${groupDate}` : ''}`}
                      title={g.group_type ? `${label} (${g.group_type})` : label}
                      className={`block ${assignmentLabelClass}`}
                    >
                      {label}
                    </Link>
                  );
                }
                return (
                  <span
                    key={`${g.group_type ?? 'group'}-${label}`}
                    title={g.group_type ? `${label} (${g.group_type})` : label}
                    className={`block ${assignmentLabelClass}`}
                  >
                    {label}
                  </span>
                );
              })}
            </div>
          ) : subtitle ? (
            <div className="text-xs text-gray-500 dark:text-gray-400">{subtitle}</div>
          ) : null}
        </div>
      </div>
    </td>
  );
}

/** Read + normalise a single rating value from an answers blob. */
function readRating(col, answers) {
  const raw = col.subKey
    ? (answers?.[col.key] ?? {})[col.subKey]
    : answers?.[col.key];
  return raw == null ? null : Number(raw);
}

export function RatingCellTd({ col, answers }) {
  const num = readRating(col, answers);
  const tone = ratingTierClass(num, col.scaleMax);
  return (
    <td
      className={`px-3 py-3 whitespace-nowrap text-center border border-gray-300 dark:border-gray-700 ${tone}`}
      title={Number.isFinite(num) ? `${col.label}: ${num} / ${col.scaleMax}` : col.label}
      aria-label={
        Number.isFinite(num)
          ? `${col.label}: ${num} of ${col.scaleMax}`
          : `${col.label}: no answer`
      }
    >
      <div className="text-base font-semibold tabular-nums">
        {Number.isFinite(num) ? num : '—'}
      </div>
    </td>
  );
}

/** Mobile score box: a colored tile with the score number and its label
 *  underneath. Shares the rating palette with the desktop `RatingCellTd`. */
export function RatingBox({ col, answers }) {
  const num = readRating(col, answers);
  const tone = ratingTierClass(num, col.scaleMax);
  return (
    <div
      className="flex-1 min-w-[4rem] flex flex-col items-center"
      aria-label={
        Number.isFinite(num)
          ? `${col.label}: ${num} of ${col.scaleMax}`
          : `${col.label}: no answer`
      }
    >
      <div className={`w-full rounded-md py-2 text-center ${tone}`}>
        <span className="text-lg font-semibold tabular-nums">
          {Number.isFinite(num) ? num : '—'}
        </span>
      </div>
      <div className="mt-1 text-[10px] uppercase tracking-wide text-gray-500 dark:text-gray-400 text-center leading-tight">
        {col.label}
      </div>
    </div>
  );
}

/** Per-flag icon + colour. Keeps a small allow-list for legacy
 *  bunk-log field names so the redesign matches the screenshot. */
function flagChipStyle(fieldKey) {
  const k = String(fieldKey || '').toLowerCase();
  if (k.includes('camper_care')) {
    return 'text-red-700 bg-red-100 border-red-200 dark:bg-red-900/30 dark:text-red-200 dark:border-red-800';
  }
  if (k.includes('unit_head')) {
    return 'text-yellow-800 bg-yellow-100 border-yellow-200 dark:bg-yellow-900/30 dark:text-yellow-200 dark:border-yellow-800';
  }
  if (k.includes('not_on_camp') || k.includes('absent')) {
    return 'text-gray-700 bg-gray-100 border-gray-200 dark:bg-gray-800 dark:text-gray-200 dark:border-gray-600';
  }
  return 'text-amber-900 bg-amber-100 border-amber-200 dark:bg-amber-900/30 dark:text-amber-200 dark:border-amber-800';
}

export function FlagChip({ field, testidPrefix = 'lt-responses-flag' }) {
  return (
    <span
      className={`inline-flex items-center px-2 py-1 text-xs font-semibold rounded-full border ${flagChipStyle(field.key)}`}
      data-testid={`${testidPrefix}-${field.key}`}
    >
      {field.label}
    </span>
  );
}

/** Narrative body (flags, chips, description text, reporting author) shared
 *  by the desktop Description `<td>` and the mobile response card. */
export function DescriptionContent({
  row,
  flagFields,
  chipFields,
  descTextFields,
  flagTestidPrefix,
}) {
  const answers = row.answers ?? {};
  const activeFlags = flagFields.filter((f) => isTruthyFlag(answers[f.key]));
  const author = row.author?.name;
  const createdAt = row.created_at ?? row.updated_at;

  return (
    <>
      {activeFlags.length > 0 && (
        <div className="flex flex-wrap gap-2 mb-2">
          {activeFlags.map((f) => (
            <FlagChip key={f.key} field={f} testidPrefix={flagTestidPrefix} />
          ))}
        </div>
      )}

      {chipFields.length > 0 && (
        <div className="flex flex-wrap gap-1 mb-2">
          {chipFields.map((f) => {
            const v = answers[f.key];
            if (v == null || v === '') return null;
            const values = Array.isArray(v) ? v : [v];
            const labels = values.map((val) => {
              const match = f.options.find((o) => String(o.value) === String(val));
              return match ? match.label : String(val);
            });
            return (
              <span
                key={f.key}
                className="inline-flex items-center px-2 py-0.5 text-[11px] rounded-full bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-200 border border-gray-200 dark:border-gray-600"
                title={`${f.label}: ${labels.join(', ')}`}
              >
                {labels.join(', ')}
              </span>
            );
          })}
        </div>
      )}

      <div className="space-y-2 text-sm text-gray-700 dark:text-gray-200">
        {descTextFields.length === 0 ? (
          <span className="text-gray-400 dark:text-gray-500 italic">No description</span>
        ) : (
          descTextFields.map((f) => {
            const value = answers[f.key];
            if (value == null || value === '') return null;
            const text = String(value);
            return (
              <div key={f.key}>
                {descTextFields.length > 1 && (
                  <div className="text-[10px] uppercase tracking-wide text-gray-500 dark:text-gray-400 mb-0.5">
                    {f.label}
                  </div>
                )}
                <RichText html={text} className="whitespace-pre-line" />
              </div>
            );
          })
        )}
      </div>

      <div className="mt-2 text-xs text-gray-500 dark:text-gray-400">
        <strong>Reporting Author:</strong>{' '}
        {author ? (
          <span>
            {author}
            {row.author?.email && (
              <span className="block text-xs text-gray-400 dark:text-gray-500">{row.author.email}</span>
            )}
          </span>
        ) : (
          <span className="text-gray-400 dark:text-gray-500">Unknown</span>
        )}
        {createdAt && (
          <span className="block text-xs text-gray-400 dark:text-gray-500 mt-1">
            <strong>Created:</strong>{' '}
            {new Date(createdAt).toLocaleString('en-US', {
              year: 'numeric', month: 'short', day: 'numeric',
              hour: '2-digit', minute: '2-digit',
            })}
          </span>
        )}
      </div>
    </>
  );
}

export function DescriptionCell(props) {
  return (
    <td className="px-3 py-3 align-top border border-gray-300 dark:border-gray-700 max-w-md break-words">
      <DescriptionContent {...props} />
    </td>
  );
}
