import { Link } from 'react-router-dom';
import { ratingColor, ratingTextColor, NO_DATA_FILL } from '../colors';
import PrivacyChip from '../../components/reflection/PrivacyChip';

function formatShortDate(iso) {
  const d = new Date(iso + 'T00:00:00');
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
}

/**
 * Single colored cell for the Subject Trend Grid.
 *
 * Renders as a button so it's keyboard-reachable. When a reflection_id is
 * present, clicking navigates to /reflect/summary?reflection=<id>; otherwise
 * the button is disabled (no-data state).
 */
export default function TrendCell({
  cell,
  scaleMax = 5,
  subjectName = '',
  scaleLabel,
}) {
  const fill = ratingColor(cell.rating, scaleMax);
  const color = ratingTextColor(cell.rating, scaleMax);
  const dateLabel = formatShortDate(cell.date);
  const isPrivate = cell.team_visibility === 'supervisors_only';
  const privateSuffix = isPrivate ? ', filed privately' : '';

  const aria = cell.rating == null
    ? `${subjectName}, ${dateLabel}, no reflection`
    : `${subjectName}, ${dateLabel}, rating ${Math.round(cell.rating)} of ${scaleMax}` +
      (cell.author_name ? `, logged by ${cell.author_name}` : '') +
      privateSuffix;

  const tooltip = cell.rating == null
    ? `${dateLabel} — no reflection`
    : `${dateLabel} — ${Math.round(cell.rating)}${
        scaleLabel ? ` of ${scaleMax} (${scaleLabel})` : ` of ${scaleMax}`
      }${cell.author_name ? ` · by ${cell.author_name}` : ''}${
        isPrivate ? ' · filed privately' : ''
      }`;

  const baseClass =
    'border border-gray-200 dark:border-gray-700 text-[10px] font-mono text-center align-middle p-0 relative';
  const innerClass = 'block w-full h-full px-1 py-1.5 focus:outline-none focus:ring-2 focus:ring-indigo-400';
  const lockOverlay = isPrivate ? (
    <span className="pointer-events-none absolute top-0.5 right-0.5 z-10">
      <PrivacyChip teamVisibility={cell.team_visibility} size="icon" />
    </span>
  ) : null;

  if (cell.rating == null) {
    return (
      <td className={baseClass} style={{ backgroundColor: NO_DATA_FILL, color: '#6b7280' }}>
        <span aria-label={aria} title={tooltip} className={innerClass}>
          —
        </span>
        {lockOverlay}
      </td>
    );
  }

  if (!cell.reflection_id) {
    return (
      <td className={baseClass} style={{ backgroundColor: fill, color }}>
        <span aria-label={aria} title={tooltip} className={innerClass}>
          {Math.round(cell.rating)}
        </span>
        {lockOverlay}
      </td>
    );
  }

  return (
    <td className={baseClass} style={{ backgroundColor: fill, color }}>
      <Link
        to={`/reflect/summary?reflection=${cell.reflection_id}`}
        aria-label={aria}
        title={tooltip}
        className={innerClass}
        style={{ color }}
      >
        {Math.round(cell.rating)}
      </Link>
      {lockOverlay}
    </td>
  );
}
