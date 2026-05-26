/**
 * Schema-aware cell components shared between the LT Responses page
 * and the per-subject dashboard. Keeping a single implementation
 * guarantees both surfaces render reflection rows identically.
 */

import { Link } from 'react-router-dom';
import { getInitials, ratingTierClass } from './schema';

/** Avatar + name + optional subtitle. When ``linkTo`` is provided
 *  the name is rendered as a Router link (otherwise plain text). */
export function SubjectCell({ row, linkTo = null }) {
  const person = row.subject?.name ? row.subject : row.author;
  const name = person?.name ?? 'Unknown';
  const subtitle = row.subject_group ?? row.bunk_name ?? null;
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
          {subtitle && (
            <div className="text-xs text-gray-500 dark:text-gray-400">{subtitle}</div>
          )}
        </div>
      </div>
    </td>
  );
}

export function RatingCellTd({ col, answers }) {
  const raw = col.subKey
    ? (answers?.[col.key] ?? {})[col.subKey]
    : answers?.[col.key];
  const num = raw == null ? null : Number(raw);
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

export function DescriptionCell({
  row,
  flagFields,
  chipFields,
  descTextFields,
  flagTestidPrefix,
}) {
  const answers = row.answers ?? {};
  const activeFlags = flagFields.filter((f) =>
    String(answers[f.key] ?? '').toLowerCase() === 'yes',
  );
  const author = row.author?.name;
  const createdAt = row.created_at ?? row.updated_at;

  return (
    <td className="px-3 py-3 align-top border border-gray-300 dark:border-gray-700 max-w-md break-words">
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
            const isHtml = text.includes('<');
            return (
              <div key={f.key}>
                {descTextFields.length > 1 && (
                  <div className="text-[10px] uppercase tracking-wide text-gray-500 dark:text-gray-400 mb-0.5">
                    {f.label}
                  </div>
                )}
                {isHtml
                  ? <div className="whitespace-pre-line" dangerouslySetInnerHTML={{ __html: text }} />
                  : <div className="whitespace-pre-line">{text}</div>}
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
    </td>
  );
}
