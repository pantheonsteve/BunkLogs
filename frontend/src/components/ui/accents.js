/**
 * Named colour accents for homepage cards.
 *
 * Tailwind scans source files for literal class names, so every variant has to
 * appear in full here rather than being built from a colour name at runtime.
 *
 *   bar   top rule that gives a card its identity in a grid of white boxes
 *   chip  icon badge behind a lucide glyph
 *   link  text colour for an in-card link on that accent
 */
const ACCENTS = {
  indigo: {
    bar: 'border-t-indigo-500 dark:border-t-indigo-400',
    chip: 'bg-indigo-100 text-indigo-700 dark:bg-indigo-900/50 dark:text-indigo-300',
    link: 'text-indigo-700 dark:text-indigo-300',
  },
  violet: {
    bar: 'border-t-violet-500 dark:border-t-violet-400',
    chip: 'bg-violet-100 text-violet-700 dark:bg-violet-900/50 dark:text-violet-300',
    link: 'text-violet-700 dark:text-violet-300',
  },
  blue: {
    bar: 'border-t-blue-500 dark:border-t-blue-400',
    chip: 'bg-blue-100 text-blue-700 dark:bg-blue-900/50 dark:text-blue-300',
    link: 'text-blue-700 dark:text-blue-300',
  },
  sky: {
    bar: 'border-t-sky-500 dark:border-t-sky-400',
    chip: 'bg-sky-100 text-sky-700 dark:bg-sky-900/50 dark:text-sky-300',
    link: 'text-sky-700 dark:text-sky-300',
  },
  teal: {
    bar: 'border-t-teal-500 dark:border-t-teal-400',
    chip: 'bg-teal-100 text-teal-700 dark:bg-teal-900/50 dark:text-teal-300',
    link: 'text-teal-700 dark:text-teal-300',
  },
  emerald: {
    bar: 'border-t-emerald-500 dark:border-t-emerald-400',
    chip: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/50 dark:text-emerald-300',
    link: 'text-emerald-700 dark:text-emerald-300',
  },
  amber: {
    bar: 'border-t-amber-500 dark:border-t-amber-400',
    chip: 'bg-amber-100 text-amber-800 dark:bg-amber-900/50 dark:text-amber-300',
    link: 'text-amber-700 dark:text-amber-300',
  },
  orange: {
    bar: 'border-t-orange-500 dark:border-t-orange-400',
    chip: 'bg-orange-100 text-orange-700 dark:bg-orange-900/50 dark:text-orange-300',
    link: 'text-orange-700 dark:text-orange-300',
  },
  rose: {
    bar: 'border-t-rose-500 dark:border-t-rose-400',
    chip: 'bg-rose-100 text-rose-700 dark:bg-rose-900/50 dark:text-rose-300',
    link: 'text-rose-700 dark:text-rose-300',
  },
};

export const ACCENT_NAMES = Object.keys(ACCENTS);

export function accent(name) {
  return ACCENTS[name] || ACCENTS.indigo;
}

export default ACCENTS;
