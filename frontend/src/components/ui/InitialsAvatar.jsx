/**
 * Round initials chip for a person. `brand` is the violet chip used for
 * people in staff lists and the top bar; `neutral` is the quieter gray chip
 * the attention-card rows use. Pass `aria-hidden` when the name is already
 * printed beside the avatar.
 */

const SIZE_CLASSES = {
  sm: 'w-7 h-7 text-[11px]',
  md: 'w-9 h-9 text-[13px]',
  lg: 'w-11 h-11 text-base',
};

const TONE_CLASSES = {
  brand: 'bg-brand-soft text-violet-800 dark:text-violet-200',
  neutral: 'bg-line-soft text-ink-2',
};

export function initialsFor(name) {
  const words = String(name || '').trim().split(/\s+/).filter(Boolean);
  if (words.length === 0) return '?';
  const first = words[0][0];
  const last = words.length > 1 ? words[words.length - 1][0] : '';
  return `${first}${last}`.toUpperCase();
}

export default function InitialsAvatar({
  name,
  initials,
  size = 'md',
  tone = 'brand',
  className = '',
  ...rest
}) {
  return (
    <span
      role="img"
      aria-label={name}
      className={`inline-flex items-center justify-center rounded-full font-bold shrink-0 ${
        SIZE_CLASSES[size] || SIZE_CLASSES.md
      } ${TONE_CLASSES[tone] || TONE_CLASSES.brand} ${className}`.trim()}
      {...rest}
    >
      {initials || initialsFor(name)}
    </span>
  );
}
