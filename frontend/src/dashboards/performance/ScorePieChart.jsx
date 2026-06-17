import { ratingColor } from '../colors';

/**
 * Lightweight SVG pie chart for score distribution on performance cards.
 */
export default function ScorePieChart({ distribution = {}, scaleMax = 5, size = 72 }) {
  const entries = Object.entries(distribution)
    .filter(([, count]) => Number(count) > 0)
    .sort((a, b) => Number(a[0]) - Number(b[0]));

  const total = entries.reduce((sum, [, count]) => sum + Number(count), 0);
  if (total === 0) {
    return (
      <div
        className="flex items-center justify-center rounded-full bg-gray-100 dark:bg-gray-800 text-xs text-gray-400"
        style={{ width: size, height: size }}
        aria-label="No scores yet"
      >
        —
      </div>
    );
  }

  const cx = size / 2;
  const cy = size / 2;
  const r = size / 2 - 2;

  // A single bucket holding 100% of ratings must render as a circle.
  // SVG arc paths degenerate when start and end points coincide.
  if (entries.length === 1 && Number(entries[0][1]) === total) {
    const [value] = entries[0];
    const fill = ratingColor(Number(value), scaleMax) || '#9ca3af';
    return (
      <svg
        width={size}
        height={size}
        viewBox={`0 0 ${size} ${size}`}
        role="img"
        aria-label={`Score distribution: ${value}: ${total}`}
      >
        <circle cx={cx} cy={cy} r={r} fill={fill} stroke="white" strokeWidth="1" />
      </svg>
    );
  }

  let startAngle = -Math.PI / 2;
  const slices = entries.map(([value, count]) => {
    const angle = (count / total) * Math.PI * 2;
    const endAngle = startAngle + angle;
    const x1 = cx + r * Math.cos(startAngle);
    const y1 = cy + r * Math.sin(startAngle);
    const x2 = cx + r * Math.cos(endAngle);
    const y2 = cy + r * Math.sin(endAngle);
    const largeArc = angle > Math.PI ? 1 : 0;
    const path = [
      `M ${cx} ${cy}`,
      `L ${x1} ${y1}`,
      `A ${r} ${r} 0 ${largeArc} 1 ${x2} ${y2}`,
      'Z',
    ].join(' ');
    startAngle = endAngle;
    return {
      value,
      count,
      path,
      fill: ratingColor(Number(value), scaleMax) || '#9ca3af',
    };
  });

  return (
    <svg
      width={size}
      height={size}
      viewBox={`0 0 ${size} ${size}`}
      role="img"
      aria-label={`Score distribution: ${entries.map(([v, c]) => `${v}: ${c}`).join(', ')}`}
    >
      {slices.map((s) => (
        <path key={s.value} d={s.path} fill={s.fill} stroke="white" strokeWidth="1" />
      ))}
    </svg>
  );
}
