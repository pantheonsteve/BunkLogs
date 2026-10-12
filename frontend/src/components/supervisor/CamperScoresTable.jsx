/**
 * Compact camper-by-category table for the supervisor home's selected bunk:
 * one RatingCell per scored column, help-request flags, and a note excerpt.
 * Campers without a submitted log get one dashed span across the score
 * columns instead of a row of empty cells.
 */
import { Link } from 'react-router-dom';
import Badge from '../ui/Badge';
import RatingCell from '../ui/RatingCell';
import { camperShortName, columnLabel, noteExcerpt, scoredColumns } from './bunkStats';

export default function CamperScoresTable({ payload, camperLabel = 'Camper', linkFor, uhLabel }) {
  const columns = scoredColumns(payload);
  const rows = payload?.score_grid?.rows || [];
  const uhIds = new Set((payload?.help_requested || []).map((c) => c.id));
  const ccIds = new Set((payload?.camper_care_help_requested || []).map((c) => c.id));
  const offIds = new Set((payload?.off_camp || []).map((c) => c.id));

  if (rows.length === 0) {
    return <p className="text-sm text-muted">No campers rostered on this date.</p>;
  }

  const spanCols = Math.max(columns.length, 1);
  const cellBorder = 'border-t border-line-soft';

  return (
    <div className="overflow-x-auto" data-testid="uh-detail-table">
      <table className="w-full min-w-[760px] border-separate border-spacing-y-1 text-sm">
        <thead>
          <tr className="text-left text-xs text-muted">
            <th scope="col" className="font-semibold py-1 pr-2">{camperLabel}</th>
            {columns.map((col) => (
              <th key={col.label} scope="col" className="font-semibold p-1 text-center w-[92px]">
                {columnLabel(col)}
              </th>
            ))}
            <th scope="col" className="font-semibold py-1 px-2">Flags</th>
            <th scope="col" className="font-semibold py-1 pl-2">Note</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => {
            const camper = row.camper || {};
            const name = camperShortName(camper);
            const logged = row.reflection_id != null;
            const pendingLabel = offIds.has(camper.id) ? 'Not on camp' : 'Not started';
            return (
              <tr key={camper.id} data-testid={`uh-detail-row-${camper.id}`} data-logged={logged}>
                <th scope="row" className={`py-1.5 pr-2 text-left font-semibold ${cellBorder}`}>
                  <Link to={linkFor(camper.id)} className="text-ink hover:underline">{name}</Link>
                </th>
                {logged ? (
                  columns.map((col) => (
                    <td key={col.label} className={`px-0.5 text-center ${cellBorder}`}>
                      <RatingCell
                        value={typeof row.cells?.[col.label] === 'number' ? row.cells[col.label] : null}
                        scaleMax={col.scale_max || 5}
                        label={`${name} ${columnLabel(col)}`}
                      />
                    </td>
                  ))
                ) : (
                  <td colSpan={spanCols} className={`px-0.5 ${cellBorder}`}>
                    <span className="flex items-center justify-center h-8 rounded-md border border-dashed border-line text-[13px] text-muted">
                      {pendingLabel}
                    </span>
                  </td>
                )}
                <td className={`py-1.5 px-2 ${cellBorder}`}>
                  <span className="flex flex-wrap gap-1">
                    {uhIds.has(camper.id) && <Badge tone="warn" className="font-bold">{uhLabel}</Badge>}
                    {ccIds.has(camper.id) && <Badge tone="danger" className="font-bold">Camper Care</Badge>}
                  </span>
                </td>
                <td className={`py-1.5 pl-2 text-[13px] leading-snug text-ink-2 max-w-[380px] ${cellBorder}`}>
                  {logged ? noteExcerpt(payload, row.cells) : ''}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
