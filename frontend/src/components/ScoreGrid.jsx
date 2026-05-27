/**
 * Score Grid — Step 7_7, Story 12.
 *
 * Compact table of camper × scored-dimension cells colored by the
 * shared `ratingColor` palette. Used inside `BunkDashboard` (Story
 * 11) and reusable by future role flows.
 *
 * Story 12 conformance points:
 *
 *   - One row per camper currently rostered on the selected date.
 *   - One column per scored dimension defined by the active
 *     reflection template (extracted server-side; client just
 *     renders the columns it's handed in template order).
 *   - Camper name column is sticky during horizontal scroll
 *     (`sticky left-0`).
 *   - Missing scores are rendered visually distinct from low scores
 *     via the `NO_DATA_FILL` swatch.
 *   - Tapping a row navigates to the Camper Dashboard.
 *
 * Props:
 *   - `columns` — array of `{ label, field_key, field_type, category_key, scale_max }`.
 *   - `rows` — array of `{ camper, cells, reflection_id }`.
 *   - `onSelectCamper(camperId)` — optional callback when a row is clicked.
 */

import { Link } from 'react-router-dom';
import { NO_DATA_FILL, ratingLegend } from '../dashboards/colors';
import { ratingTierClass } from '../dashboards/subject/responseTable/schema';

function formatCamperName(camper) {
  if (!camper) return '';
  const first = camper.preferred_name || camper.first_name || '';
  const lastInitial = (camper.last_name || '').slice(0, 1);
  if (first && lastInitial) return `${first} ${lastInitial}.`;
  return first || lastInitial || '';
}

function columnHeader(col) {
  if (col.field_type === 'rating_group' && col.category_key) {
    return col.category_key;
  }
  return col.field_key;
}

function ScoreCell({ value, scaleMax }) {
  const tone = ratingTierClass(value, scaleMax);
  return (
    <td
      data-testid={value == null ? 'score-cell-empty' : 'score-cell'}
      data-value={value ?? undefined}
      className={`px-3 py-3 whitespace-nowrap text-center border border-gray-100 dark:border-gray-800 ${tone}`}
      aria-label={value != null ? `Score ${value} of ${scaleMax}` : 'No score'}
    >
      <div className="text-base font-semibold tabular-nums">
        {value != null ? (Number.isInteger(value) ? value : value.toFixed(1)) : '—'}
      </div>
    </td>
  );
}

function ScoreLegend({ scaleMax }) {
  const rows = ratingLegend(scaleMax);
  return (
    <div
      data-testid="score-grid-legend"
      className="flex items-center gap-2 flex-wrap text-xs text-gray-600 dark:text-gray-300 mt-2"
    >
      <span className="font-medium">Legend:</span>
      {rows.map(({ value, fill }) => (
        <span key={value} className="inline-flex items-center gap-1">
          <span
            className="inline-block h-3 w-4 rounded"
            style={{ backgroundColor: fill }}
            aria-hidden="true"
          />
          <span>{value}</span>
        </span>
      ))}
      <span className="inline-flex items-center gap-1">
        <span
          className="inline-block h-3 w-4 rounded"
          style={{ backgroundColor: NO_DATA_FILL }}
          aria-hidden="true"
        />
        <span>no data</span>
      </span>
    </div>
  );
}

export default function ScoreGrid({
  columns = [],
  rows = [],
  camperLinkPrefix = '/unit-head/campers',
  onSelectCamper,
}) {
  if (columns.length === 0) {
    return (
      <p data-testid="score-grid-empty" className="text-sm text-gray-600 dark:text-gray-400">
        No scored dimensions in the active template.
      </p>
    );
  }
  if (rows.length === 0) {
    return (
      <p data-testid="score-grid-no-campers" className="text-sm text-gray-600 dark:text-gray-400">
        No campers rostered on this date.
      </p>
    );
  }

  // Use the highest scale_max in any column so the legend matches the most
  // prominent dimension; mixed scales are rare in practice but supported.
  const maxScale = Math.max(...columns.map((c) => c.scale_max || 5));

  return (
    <div data-testid="score-grid" className="space-y-2">
      <div className="overflow-x-auto rounded-xl border border-gray-200 dark:border-gray-700">
        <table className="min-w-full bg-white dark:bg-gray-900">
          <thead>
            <tr className="bg-gray-50 dark:bg-gray-800">
              <th
                className="sticky left-0 z-10 bg-gray-50 dark:bg-gray-800 px-3 py-2 text-left text-xs font-semibold text-gray-700 dark:text-gray-200"
                scope="col"
              >
                Camper
              </th>
              {columns.map((col) => (
                <th
                  key={col.label}
                  className="px-2 py-2 text-center text-xs font-semibold text-gray-700 dark:text-gray-200 whitespace-nowrap"
                  scope="col"
                  data-testid={`score-col-${col.label}`}
                >
                  {columnHeader(col)}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => {
              const camper = row.camper || {};
              const linkTo = `${camperLinkPrefix}/${camper.id}`;
              return (
                <tr
                  key={camper.id}
                  data-testid={`score-row-${camper.id}`}
                  className="border-t border-gray-100 dark:border-gray-800 hover:bg-gray-50 dark:hover:bg-gray-800"
                >
                  <th
                    scope="row"
                    className="sticky left-0 z-10 bg-white dark:bg-gray-900 hover:bg-gray-50 dark:hover:bg-gray-800 px-3 py-2 text-left text-sm font-medium text-gray-900 dark:text-white whitespace-nowrap"
                  >
                    {onSelectCamper ? (
                      <button
                        type="button"
                        onClick={() => onSelectCamper(camper.id)}
                        className="text-left hover:underline"
                      >
                        {formatCamperName(camper)}
                      </button>
                    ) : (
                      <Link to={linkTo} className="hover:underline">
                        {formatCamperName(camper)}
                      </Link>
                    )}
                  </th>
                  {columns.map((col) => (
                    <ScoreCell
                      key={col.label}
                      value={row.cells?.[col.label] ?? null}
                      scaleMax={col.scale_max || 5}
                    />
                  ))}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <ScoreLegend scaleMax={maxScale} />
    </div>
  );
}
