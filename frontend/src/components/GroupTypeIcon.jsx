/**
 * A small mark for each group type, shown beside a group dashboard title.
 *
 * Names stay the catalog words (Bunk, Classroom). Terminology renames
 * other nouns; the mark has to stay the type the admin turned on.
 */
import {
  Castle,
  Handshake,
  HeartHandshake,
  Palette,
  School,
  Shapes,
  Tent,
  Trees,
  UsersRound,
} from 'lucide-react';

import { groupTypeDisplayName } from '../pages/admin/groups/groupTypes';

const GROUP_TYPE_ICONS = {
  bunk: {
    Icon: Tent,
    className: 'bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-200',
  },
  classroom: {
    Icon: School,
    className: 'bg-sky-100 text-sky-800 dark:bg-sky-900/40 dark:text-sky-200',
  },
  caseload: {
    Icon: HeartHandshake,
    className: 'bg-rose-100 text-rose-800 dark:bg-rose-900/40 dark:text-rose-200',
  },
  unit: {
    Icon: Trees,
    className: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-200',
  },
  division: {
    Icon: Castle,
    className: 'bg-violet-100 text-violet-800 dark:bg-violet-900/40 dark:text-violet-200',
  },
  cohort: {
    Icon: UsersRound,
    className: 'bg-indigo-100 text-indigo-800 dark:bg-indigo-900/40 dark:text-indigo-200',
  },
  team: {
    Icon: Handshake,
    className: 'bg-teal-100 text-teal-800 dark:bg-teal-900/40 dark:text-teal-200',
  },
  specialty: {
    Icon: Palette,
    className: 'bg-orange-100 text-orange-800 dark:bg-orange-900/40 dark:text-orange-200',
  },
  custom: {
    Icon: Shapes,
    className: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/40 dark:text-yellow-200',
  },
};

export default function GroupTypeIcon({ type, className = '' }) {
  const entry = GROUP_TYPE_ICONS[type];
  if (!entry) return null;
  const { Icon } = entry;
  const label = groupTypeDisplayName(type);
  return (
    <span
      role="img"
      aria-label={label}
      title={label}
      data-testid={`group-type-icon-${type}`}
      className={`inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl ${entry.className} ${className}`.trim()}
    >
      <Icon size={20} strokeWidth={2.25} aria-hidden="true" />
    </span>
  );
}
