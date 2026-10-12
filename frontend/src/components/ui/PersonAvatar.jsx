/**
 * Generic round avatar for students / campers.
 *
 * Every person gets the same silhouette; the background tint is picked
 * deterministically from their id so a list reads as colorful but each
 * person keeps the same color everywhere. Pass `photoUrl` once photos
 * exist and the silhouette is replaced by the image at the same size.
 */
import { UserRound } from 'lucide-react';

const SIZE_CLASSES = {
  xs: { box: 'w-6 h-6', icon: 20 },
  sm: { box: 'w-7 h-7', icon: 24 },
  md: { box: 'w-9 h-9', icon: 30 },
  lg: { box: 'w-11 h-11', icon: 38 },
};

const PALETTE = [
  'bg-rose-100 text-rose-400 dark:bg-rose-900/50 dark:text-rose-400',
  'bg-amber-100 text-amber-400 dark:bg-amber-900/50 dark:text-amber-400',
  'bg-lime-100 text-lime-400 dark:bg-lime-900/50 dark:text-lime-400',
  'bg-emerald-100 text-emerald-400 dark:bg-emerald-900/50 dark:text-emerald-400',
  'bg-cyan-100 text-cyan-400 dark:bg-cyan-900/50 dark:text-cyan-400',
  'bg-sky-100 text-sky-400 dark:bg-sky-900/50 dark:text-sky-400',
  'bg-indigo-100 text-indigo-400 dark:bg-indigo-900/50 dark:text-indigo-400',
  'bg-violet-100 text-violet-400 dark:bg-violet-900/50 dark:text-violet-400',
  'bg-fuchsia-100 text-fuchsia-400 dark:bg-fuchsia-900/50 dark:text-fuchsia-400',
  'bg-orange-100 text-orange-400 dark:bg-orange-900/50 dark:text-orange-400',
];

export function avatarColorFor(seed) {
  const s = String(seed ?? '');
  let hash = 0;
  for (let i = 0; i < s.length; i += 1) {
    hash = (hash * 31 + s.charCodeAt(i)) >>> 0;
  }
  return PALETTE[hash % PALETTE.length];
}

export default function PersonAvatar({
  id,
  name,
  photoUrl = null,
  size = 'sm',
  className = '',
}) {
  const { box, icon } = SIZE_CLASSES[size] || SIZE_CLASSES.sm;
  const base = `inline-flex items-center justify-center rounded-full shrink-0 overflow-hidden ring-2 ring-white dark:ring-gray-900 ${box}`;

  if (photoUrl) {
    return (
      <img
        src={photoUrl}
        alt=""
        aria-hidden="true"
        className={`${base} object-cover ${className}`.trim()}
      />
    );
  }

  return (
    <span
      aria-hidden="true"
      data-testid="person-avatar"
      className={`${base} ${avatarColorFor(id ?? name)} ${className}`.trim()}
    >
      <UserRound size={icon} strokeWidth={1.5} fill="currentColor" className="shrink-0 translate-y-[22%]" />
    </span>
  );
}
