function shortDate(iso) {
  const d = new Date(iso + 'T00:00:00');
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleDateString(undefined, { month: 'numeric', day: 'numeric' });
}

function MiniBars({ perDay, max, ariaLabel }) {
  // Tiny inline horizontal bar strip — no chart dep needed.
  const w = perDay.length * 14;
  const h = 32;
  const barW = 10;
  const gap = 4;
  return (
    <svg
      width={w}
      height={h}
      viewBox={`0 0 ${w} ${h}`}
      role="img"
      aria-label={ariaLabel}
    >
      {perDay.map((d, i) => {
        const ratio = max > 0 ? d.count / max : 0;
        const barH = Math.max(1, Math.round(ratio * (h - 4)));
        return (
          <rect
            key={d.date}
            x={i * (barW + gap)}
            y={h - barH - 1}
            width={barW}
            height={barH}
            fill={d.count > 0 ? '#4f46e5' : '#e5e7eb'}
          >
            <title>{shortDate(d.date)}: {d.count}</title>
          </rect>
        );
      })}
    </svg>
  );
}

export default function AuthorAttribution({ payload }) {
  if (!payload) return null;
  const { authors, period, days } = payload;
  const overallMax = authors.reduce(
    (m, a) => Math.max(m, ...a.per_day.map((d) => d.count)),
    0,
  );
  return (
    <div>
      <div className="mb-4 flex items-end justify-between">
        <div>
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
            Author attribution
          </h2>
          <p className="text-xs uppercase text-gray-500 dark:text-gray-400">
            {period.start} → {period.end} · {days.length} days
          </p>
        </div>
      </div>
      {authors.length === 0 ? (
        <p className="text-sm text-gray-500 dark:text-gray-400">
          No reflections submitted in this window.
        </p>
      ) : (
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead>
              <tr className="text-left text-xs uppercase text-gray-500 dark:text-gray-400">
                <th className="px-3 py-2">Author</th>
                <th className="px-3 py-2 text-right">Total</th>
                <th className="px-3 py-2 text-right">Distinct subjects</th>
                <th className="px-3 py-2">Per day</th>
              </tr>
            </thead>
            <tbody>
              {authors.map((a) => (
                <tr
                  key={a.author_id}
                  className="border-t border-gray-200 dark:border-gray-700"
                >
                  <td className="px-3 py-2 text-gray-900 dark:text-white">
                    {a.name}
                  </td>
                  <td className="px-3 py-2 text-right font-mono">
                    {a.total_reflections}
                  </td>
                  <td className="px-3 py-2 text-right font-mono">
                    {a.distinct_subjects}
                  </td>
                  <td className="px-3 py-2">
                    <MiniBars
                      perDay={a.per_day}
                      max={overallMax}
                      ariaLabel={`Daily counts for ${a.name}`}
                    />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
