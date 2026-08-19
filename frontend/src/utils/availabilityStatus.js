/**
 * Sunday availability status vocabulary and palette (Step 4_9).
 *
 * Shared so the Madrich, Faculty, and Director surfaces cannot drift into
 * three different colour schemes for the same three statuses. `unset` is not
 * a stored value — it stands for "no MadrichAvailability row yet", which the
 * coverage grid has to render distinctly from a deliberate "unavailable".
 */
export const AVAILABILITY_STATUSES = ['available', 'tentative', 'unavailable', 'unset'];

const META = {
  available: {
    label: 'Available',
    pill: 'bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-300',
    cell: 'bg-green-500',
  },
  tentative: {
    label: 'Tentative',
    pill: 'bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300',
    cell: 'bg-amber-500',
  },
  unavailable: {
    label: 'Unavailable',
    pill: 'bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-300',
    cell: 'bg-red-500',
  },
  unset: {
    label: 'Not set',
    pill: 'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300',
    cell: 'bg-slate-300 dark:bg-slate-600',
  },
};

export function statusMeta(status) {
  return META[status] || META.unset;
}

export function statusLabel(status) {
  return statusMeta(status).label;
}
