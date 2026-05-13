import { Link } from 'react-router-dom';
import TrendCell from './TrendCell';
import { ratingLegend } from '../colors';

function formatShortDate(iso) {
  const d = new Date(iso + 'T00:00:00');
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleDateString(undefined, { month: 'numeric', day: 'numeric' });
}

function Legend({ scaleMax }) {
  const rows = ratingLegend(scaleMax);
  return (
    <div className="flex items-center gap-3 text-xs text-gray-700 dark:text-gray-300">
      <span>Rating scale:</span>
      {rows.map((r) => (
        <span key={r.value} className="inline-flex items-center gap-1">
          <span
            className="inline-block w-4 h-4 border border-gray-300"
            style={{ backgroundColor: r.fill }}
            aria-hidden="true"
          />
          {r.value}
        </span>
      ))}
      <span className="inline-flex items-center gap-1 ml-2">
        <span
          className="inline-block w-4 h-4 border border-gray-300"
          style={{ backgroundColor: '#e5e7eb' }}
          aria-hidden="true"
        />
        no reflection
      </span>
    </div>
  );
}

/**
 * SubjectTrendGrid — the signature "color patterns" view.
 *
 * Props:
 *   payload: shape returned by GET /api/v1/dashboards/subject-trends/
 *   category: currently-selected category key (or '' for "average across all")
 *   onCategoryChange: handler when the user picks a different category
 */
export default function SubjectTrendGrid({ payload, category = '', onCategoryChange }) {
  if (!payload) return null;
  const { subjects, period, scale_max: scaleMax, template, group } = payload;
  const days = subjects[0]?.cells?.map((c) => c.date) ?? [];
  const categoryKeys = template.category_keys ?? [];

  return (
    <div>
      <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
            {group.name}
          </h2>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            {template.name} · {period.start} → {period.end}
          </p>
        </div>
        {categoryKeys.length > 0 && template.category_ratings_key && (
          <label className="flex items-center gap-2 text-sm text-gray-700 dark:text-gray-300">
            <span>Category</span>
            <select
              value={category}
              onChange={(e) => onCategoryChange?.(e.target.value)}
              className="rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-2 py-1 text-sm"
            >
              <option value="">Average across all</option>
              {categoryKeys.map((k) => (
                <option key={k} value={k}>{k}</option>
              ))}
            </select>
          </label>
        )}
      </div>
      <div className="mb-3">
        <Legend scaleMax={scaleMax} />
      </div>
      <div className="overflow-x-auto">
        <table className="min-w-full border-collapse text-sm">
          <thead>
            <tr>
              <th
                scope="col"
                className="sticky left-0 z-10 bg-white dark:bg-gray-900 px-3 py-2 text-left font-medium text-gray-700 dark:text-gray-200 border-b border-gray-200 dark:border-gray-700"
              >
                Subject
              </th>
              {days.map((d) => (
                <th
                  key={d}
                  scope="col"
                  className="px-1 py-2 text-[10px] font-mono text-gray-500 dark:text-gray-400 border-b border-gray-200 dark:border-gray-700 text-center"
                >
                  {formatShortDate(d)}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {subjects.map((s) => (
              <tr key={s.person_id}>
                <th
                  scope="row"
                  className="sticky left-0 z-10 bg-white dark:bg-gray-900 px-3 py-1.5 text-left text-gray-800 dark:text-gray-200 border-b border-gray-200 dark:border-gray-700 whitespace-nowrap font-normal"
                >
                  <Link
                    to={`/dashboards/subject/${s.person_id}`}
                    className="hover:underline focus:outline-none focus:ring-2 focus:ring-indigo-400 rounded"
                  >
                    {s.name}
                  </Link>
                </th>
                {s.cells.map((cell) => (
                  <TrendCell
                    key={cell.date}
                    cell={cell}
                    scaleMax={scaleMax}
                    subjectName={s.name}
                  />
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {subjects.length === 0 && (
        <p className="text-sm text-gray-500 dark:text-gray-400">
          No subjects in this group.
        </p>
      )}
    </div>
  );
}
