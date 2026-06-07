function todayIso() {
  return new Date().toISOString().split('T')[0];
}

function addDays(iso, n) {
  const d = new Date(iso);
  d.setDate(d.getDate() + n);
  return d.toISOString().split('T')[0];
}

export default function AssignmentStatusPill({ row }) {
  const today = todayIso();
  const end = row.end_date;
  let label = 'Active';
  let cls = 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300';
  if (!row.is_active) {
    label = end ? 'Recently ended' : 'Inactive';
    cls = 'bg-gray-200 text-gray-700 dark:bg-gray-800 dark:text-gray-400';
  } else if (end && end >= today && end <= addDays(today, 7)) {
    label = 'Ending within 7d';
    cls = 'bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300';
  } else if (row.start_date && row.start_date > today) {
    label = 'Future-dated';
    cls = 'bg-indigo-100 text-indigo-800 dark:bg-indigo-900/40 dark:text-indigo-300';
  }
  return (
    <span className={`text-xs px-2 py-0.5 rounded-full ${cls}`}>{label}</span>
  );
}
