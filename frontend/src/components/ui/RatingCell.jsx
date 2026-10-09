/**
 * One colored rating block. Always prints the number so colour is never the
 * only signal; a missing rating renders the NO_DATA_FILL swatch with an em
 * dash so it reads differently from a low score.
 */
import { NO_DATA_FILL, RATING_FILLS, RATING_TEXT, ratingTier } from '../../dashboards/colors';

const SIZE_CLASSES = {
  sm: 'h-6 min-w-[26px] px-1.5 text-xs rounded-[5px]',
  md: 'h-8 min-w-8 px-2 text-sm rounded-md',
  lg: 'h-10 min-w-10 px-2.5 text-base rounded-lg',
};

function formatRating(value) {
  return Number.isInteger(value) ? String(value) : value.toFixed(1);
}

export default function RatingCell({
  value,
  scaleMax = 5,
  size = 'md',
  label,
  className = '',
  ...rest
}) {
  const numeric = value == null || value === '' ? null : Number(value);
  const tier = numeric == null ? null : ratingTier(numeric, scaleMax);
  const hasValue = tier != null;
  const text = hasValue ? formatRating(numeric) : '—';
  const style = hasValue
    ? { backgroundColor: RATING_FILLS[tier], color: RATING_TEXT[tier] }
    : { backgroundColor: NO_DATA_FILL, color: '#4b5563' };
  const ariaLabel = label
    ? `${label} ${hasValue ? `${text} of ${scaleMax}` : 'no rating'}`
    : undefined;

  return (
    <span
      data-tier={tier ?? undefined}
      aria-label={ariaLabel}
      role={ariaLabel ? 'img' : undefined}
      className={`flex items-center justify-center font-bold tabular-nums ${
        SIZE_CLASSES[size] || SIZE_CLASSES.md
      } ${className}`.trim()}
      style={style}
      {...rest}
    >
      {text}
    </span>
  );
}
