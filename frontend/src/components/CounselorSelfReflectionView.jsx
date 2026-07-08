/**
 * Schema-aware counselor self-reflection body for the bunk / group dashboard.
 * Reuses the same table cells and mobile score boxes as FormResponsesCard and
 * the LT Responses page so ratings, flags, and narrative text look identical.
 */

import { deriveSchemaSections } from '../dashboards/subject/responseTable/schema';
import {
  DescriptionCell,
  DescriptionContent,
  RatingBox,
  RatingCellTd,
} from '../dashboards/subject/responseTable/cells';
import RichText, { hasHtmlMarkup } from './ui/RichText';

function reflectionValueToText(value) {
  if (value === null || value === undefined) return '';
  if (typeof value === 'boolean') return value ? 'Yes' : 'No';
  if (Array.isArray(value)) return value.map((v) => reflectionValueToText(v)).join(', ');
  if (typeof value === 'object') {
    return Object.entries(value)
      .map(([k, v]) => `${k}: ${reflectionValueToText(v)}`)
      .join(' · ');
  }
  return String(value);
}

function LegacyFieldValue({ value }) {
  if (typeof value === 'string') {
    return hasHtmlMarkup(value)
      ? <RichText html={value} className="prose prose-sm dark:prose-invert max-w-none" />
      : <span className="whitespace-pre-wrap">{value}</span>;
  }
  return <span className="whitespace-pre-wrap">{reflectionValueToText(value)}</span>;
}

function LegacyFieldsList({ fields }) {
  if (!fields?.length) return null;
  return (
    <dl className="space-y-2">
      {fields.map((f) => (
        <div key={f.key}>
          <dt className="text-xs font-semibold text-gray-500 dark:text-gray-400">{f.label}</dt>
          <dd className="text-sm text-gray-800 dark:text-gray-200">
            <LegacyFieldValue value={f.value} />
          </dd>
        </div>
      ))}
    </dl>
  );
}

export default function CounselorSelfReflectionView({
  entry,
  testidPrefix = 'counselor-self-refl',
}) {
  const schemaFields = entry.schema_fields ?? [];
  const answers = entry.answers ?? {};

  if (schemaFields.length === 0) {
    return (
      <div className="mt-2" data-testid={`${testidPrefix}-body-${entry.person_id}`}>
        <LegacyFieldsList fields={entry.fields} />
      </div>
    );
  }

  const sections = deriveSchemaSections({ fields: schemaFields });
  const { ratingCols, flagFields, chipFields, descTextFields } = sections;
  const row = {
    answers,
    author: { name: entry.counselor_name },
    created_at: entry.submitted_at,
  };

  const hasRatingGroups = ratingCols.some((c) => c.subKey);
  const groupedHeader = [];
  let i = 0;
  while (i < ratingCols.length) {
    const col = ratingCols[i];
    if (col.subKey) {
      let j = i + 1;
      while (j < ratingCols.length && ratingCols[j].key === col.key && ratingCols[j].subKey) {
        j += 1;
      }
      groupedHeader.push({ label: col.groupLabel, span: j - i });
      i = j;
    } else {
      groupedHeader.push({ label: '', span: 1 });
      i += 1;
    }
  }

  return (
    <div className="mt-2" data-testid={`${testidPrefix}-body-${entry.person_id}`}>
      {/* Mobile-first: colored score tiles + narrative (matches FormResponsesCard). */}
      <div
        className="md:hidden space-y-3"
        data-testid={`${testidPrefix}-mobile-${entry.person_id}`}
      >
        {ratingCols.length > 0 && (
          <div className="flex flex-wrap gap-2">
            {ratingCols.map((c, idx) => (
              <RatingBox
                key={`${entry.person_id}-${c.key}-${c.subKey ?? ''}-${idx}`}
                col={c}
                answers={answers}
              />
            ))}
          </div>
        )}
        <div className="text-sm dark:text-gray-300">
          <DescriptionContent
            row={row}
            flagFields={flagFields}
            chipFields={chipFields}
            descTextFields={descTextFields}
            flagTestidPrefix={`${testidPrefix}-flag-${entry.person_id}`}
          />
        </div>
      </div>

      {/* Desktop / tablet: single-row responses table. */}
      <div
        className="hidden md:block overflow-x-auto rounded-lg border border-gray-200 dark:border-gray-700"
        data-testid={`${testidPrefix}-table-${entry.person_id}`}
      >
        <table className="table-auto w-full text-sm dark:text-gray-300">
          <thead className="text-xs uppercase text-gray-500 dark:text-gray-400 bg-gray-50 dark:bg-gray-700/50">
            {hasRatingGroups && (
              <tr>
                {groupedHeader.map((h, idx) => (
                  <th
                    key={`g-${idx}`}
                    colSpan={h.span}
                    className="p-2 border-b border-gray-200 dark:border-gray-700 text-center text-[10px] tracking-wide"
                  >
                    {h.label}
                  </th>
                ))}
                <th className="p-2 border-b border-gray-200 dark:border-gray-700" />
              </tr>
            )}
            <tr>
              {ratingCols.map((c, idx) => (
                <th
                  key={`${c.key}-${c.subKey ?? ''}-${idx}`}
                  className="p-2 text-center border-b border-gray-200 dark:border-gray-700 font-semibold"
                  title={c.label}
                >
                  <div className="truncate max-w-[8rem] mx-auto">{c.label}</div>
                </th>
              ))}
              <th className="p-2 text-left border-b border-gray-200 dark:border-gray-700 font-semibold">
                Description
              </th>
            </tr>
          </thead>
          <tbody>
            <tr>
              {ratingCols.map((c, idx) => (
                <RatingCellTd
                  key={`${entry.person_id}-${c.key}-${c.subKey ?? ''}-${idx}`}
                  col={c}
                  answers={answers}
                />
              ))}
              <DescriptionCell
                row={row}
                flagFields={flagFields}
                chipFields={chipFields}
                descTextFields={descTextFields}
                flagTestidPrefix={`${testidPrefix}-flag-${entry.person_id}`}
              />
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  );
}
