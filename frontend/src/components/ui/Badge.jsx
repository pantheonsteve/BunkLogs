/**
 * The one pill primitive. Owns pill layout, size, and the space between a
 * pill and the text it trails, so those can't drift per-screen.
 *
 * `tone` names the meaning, not the colour, so a status keeps one
 * treatment everywhere: `ok` for healthy/active, `warn` for "needs the
 * director's attention", `danger` for a blocking problem, `neutral` for
 * a plain label, `info` for a brand-tinted count or role.
 *
 * `colors` fully replaces the tone classes. It exists for *categorical*
 * pills — "Care" vs "Maintenance", "Bunk concern" vs "Specialist report" —
 * where the colour distinguishes a kind rather than a health state, and the
 * semantic tones can't express it. Prefer `tone`; pass a raw class string
 * (background, text, and border together) only when the pill is categorical.
 *
 * `inline` is required whenever the pill trails inline text rather than
 * sitting in a flex row that already sets a `gap`. Without it the pill
 * butts up against the last word.
 *
 * `dot` prefixes a small filled circle — used where the row already has
 * a lot of text and the colour alone is easy to miss.
 */

import { twMerge } from 'tailwind-merge';

const TONE_CLASSES = {
  ok: 'bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-400',
  warn: 'bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300',
  danger: 'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-400',
  neutral: 'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400',
  info: 'bg-indigo-100 text-indigo-700 dark:bg-indigo-900/40 dark:text-indigo-300',
};

// The hand-rolled pills these replaced used px-1.5 and px-2 interchangeably at
// 10px type; standardising on the roomier of the two so no pill gets tighter.
const SIZE_CLASSES = {
  xs: 'text-[10px] px-2 py-0.5',
  sm: 'text-xs px-2 py-0.5',
  md: 'text-xs px-3 py-1',
};

// Space between a pill and the word before it. 8px (the old hand-rolled
// `ml-2`) reads as touching at these font sizes.
const INLINE_GAP = 'ml-2.5';

export default function Badge({
  tone = 'neutral',
  colors = null,
  size = 'sm',
  inline = false,
  dot = false,
  className = '',
  children,
  ...rest
}) {
  const toneCls = colors || TONE_CLASSES[tone] || TONE_CLASSES.neutral;
  return (
    <span
      // twMerge, not string concatenation: a call site passing `font-semibold`
      // or `py-1` has to beat the base classes regardless of CSS source order.
      className={twMerge(
        'inline-flex items-center gap-1.5 rounded-full font-medium whitespace-nowrap',
        SIZE_CLASSES[size] || SIZE_CLASSES.sm,
        toneCls,
        inline && INLINE_GAP,
        className,
      )}
      {...rest}
    >
      {dot && (
        <span
          className="w-1.5 h-1.5 rounded-full bg-current opacity-80"
          aria-hidden="true"
        />
      )}
      {children}
    </span>
  );
}
