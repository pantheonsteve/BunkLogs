/**
 * YesNoBreakdownWidget — generic widget for yes_no fields.
 * Shows donut-style count + yes/no breakdown.
 */
export default function YesNoBreakdownWidget({ field, label }) {
  const data = field?.data ?? {};
  const yes = data.yes_count ?? 0;
  const no = data.no_count ?? 0;
  const total = yes + no;
  const yesPct = total > 0 ? Math.round((yes / total) * 100) : null;
  const noPct = total > 0 ? 100 - yesPct : null;

  const yesDeg = total > 0 ? (yes / total) * 360 : 0;

  return (
    <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900/40 p-5">
      <p className="text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400 mb-4">
        {label ?? field?.key}
      </p>
      {total === 0 ? (
        <p className="text-sm text-gray-400 dark:text-gray-500">No responses yet.</p>
      ) : (
        <div className="flex items-center gap-6">
          {/* Simple donut via conic-gradient */}
          <div
            className="shrink-0 w-16 h-16 rounded-full"
            style={{
              background: `conic-gradient(#10b981 0deg ${yesDeg}deg, #f43f5e ${yesDeg}deg 360deg)`,
            }}
            aria-label={`${yesPct}% Yes, ${noPct}% No`}
          />
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-emerald-500 shrink-0" />
              <span className="text-sm text-gray-700 dark:text-gray-300">
                Yes — <strong className="tabular-nums">{yes}</strong>
                {yesPct != null && <span className="text-gray-400 ml-1">({yesPct}%)</span>}
              </span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-rose-500 shrink-0" />
              <span className="text-sm text-gray-700 dark:text-gray-300">
                No — <strong className="tabular-nums">{no}</strong>
                {noPct != null && <span className="text-gray-400 ml-1">({noPct}%)</span>}
              </span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
