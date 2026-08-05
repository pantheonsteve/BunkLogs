import { Link } from 'react-router-dom';
import RichText from '../../components/ui/RichText';
import PrivacyChip from '../../components/reflection/PrivacyChip';
import { DescriptionCell, DescriptionContent } from './responseTable/cells';
import { deriveSchemaSections, formatShortDate } from './responseTable/schema';

function TypeBadge({ kind }) {
  const isReflection = kind === 'reflection';
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 text-[11px] font-semibold rounded-full border ${
        isReflection
          ? 'bg-indigo-50 text-indigo-800 border-indigo-200 dark:bg-indigo-900/30 dark:text-indigo-200 dark:border-indigo-800'
          : 'bg-amber-50 text-amber-900 border-amber-200 dark:bg-amber-900/30 dark:text-amber-200 dark:border-amber-800'
      }`}
    >
      {isReflection ? 'Reflection' : 'Observation'}
    </span>
  );
}

function formatScoresSummary(sections, answers) {
  const parts = [];
  for (const col of sections.ratingCols) {
    const raw = col.subKey
      ? (answers?.[col.key] ?? {})[col.subKey]
      : answers?.[col.key];
    if (raw == null || raw === '') continue;
    parts.push(`${col.label}: ${raw}`);
  }
  return parts.length ? parts.join('; ') : '—';
}

function ReflectionDateCell({ reflection }) {
  const r = reflection;
  return (
    <td className="px-3 py-3 whitespace-nowrap border border-gray-300 dark:border-gray-700">
      <div className="min-w-0 text-center">
        <div className="text-sm text-gray-800 dark:text-gray-100">
          {formatShortDate(r.date)}
        </div>
        <div className="text-[10px] text-gray-500 dark:text-gray-400 mt-0.5 inline-flex items-center gap-1">
          {r.language ?? 'en'}
          <PrivacyChip teamVisibility={r.team_visibility} size="icon" />
        </div>
        {r.assignment_group?.id && (
          <Link
            to={`/dashboards/group/${r.assignment_group.id}?date=${r.date}`}
            className="block mt-1 text-[11px] text-indigo-600 dark:text-indigo-400 hover:underline"
          >
            {r.assignment_group.name ?? 'View group'} →
          </Link>
        )}
      </div>
    </td>
  );
}

function ObservationDateCell({ observation }) {
  const o = observation;
  const whenIso = o.observed_at || o.created_at;
  const whenLabel = whenIso
    ? new Date(whenIso).toLocaleString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
    : null;
  return (
    <td className="px-3 py-3 whitespace-nowrap border border-gray-300 dark:border-gray-700">
      <div className="min-w-0 text-center">
        <div className="text-sm text-gray-800 dark:text-gray-100">
          {formatShortDate(o.date || whenIso?.slice(0, 10))}
        </div>
        {whenLabel && (
          <time
            dateTime={whenIso}
            className="block text-[10px] text-gray-500 dark:text-gray-400 mt-0.5"
          >
            {whenLabel}
          </time>
        )}
      </div>
    </td>
  );
}

function ReflectionRow({ entry, language }) {
  const r = entry.reflection;
  const schema = { fields: entry.schemaFields ?? [] };
  const sections = deriveSchemaSections(schema, language);
  const row = {
    ...r,
    author: r.author_name ? { name: r.author_name } : null,
  };

  return (
    <tr key={`reflection-${entry.id}`} data-testid={`subject-entry-row-${entry.id}`}>
      <ReflectionDateCell reflection={r} />
      <td className="px-3 py-3 border border-gray-300 dark:border-gray-700">
        <TypeBadge kind="reflection" />
      </td>
      <td className="px-3 py-3 border border-gray-300 dark:border-gray-700 text-sm text-gray-800 dark:text-gray-100">
        {entry.template?.name ?? 'Reflection'}
      </td>
      <td className="px-3 py-3 border border-gray-300 dark:border-gray-700 text-sm text-gray-700 dark:text-gray-200">
        {formatScoresSummary(sections, r.answers)}
      </td>
      <DescriptionCell
        row={row}
        flagFields={sections.flagFields}
        chipFields={sections.chipFields}
        descTextFields={sections.descTextFields}
        flagTestidPrefix="subject-entry-flag"
      />
    </tr>
  );
}

function ObservationRow({ entry }) {
  const o = entry.observation;
  const authorName = o.author?.name;

  return (
    <tr key={`observation-${entry.id}`} data-testid={`subject-entry-row-${entry.id}`}>
      <ObservationDateCell observation={{ ...o, date: entry.date }} />
      <td className="px-3 py-3 border border-gray-300 dark:border-gray-700">
        <TypeBadge kind="observation" />
      </td>
      <td className="px-3 py-3 border border-gray-300 dark:border-gray-700 text-sm text-gray-800 dark:text-gray-100">
        {o.context || 'Note'}
      </td>
      <td className="px-3 py-3 border border-gray-300 dark:border-gray-700 text-sm text-gray-500 dark:text-gray-400">
        —
      </td>
      <td className="px-3 py-3 align-top border border-gray-300 dark:border-gray-700 max-w-md break-words">
        {authorName && (
          <p className="text-xs text-gray-500 dark:text-gray-400 mb-2">
            <strong>Author:</strong> {authorName}
          </p>
        )}
        <RichText
          html={o.body}
          className="text-sm text-gray-800 dark:text-gray-200 break-words [&_p]:mb-1 last:[&_p]:mb-0"
        />
      </td>
    </tr>
  );
}

export default function SubjectEntriesTable({ entries, language = 'en' }) {
  if (!entries.length) {
    return (
      <p className="text-sm text-gray-500 dark:text-gray-400 italic" data-testid="subject-entries-empty">
        No entries in this period.
      </p>
    );
  }

  return (
    <>
      <div className="hidden md:block overflow-x-auto">
        <table
          className="table-auto w-full text-sm dark:text-gray-300"
          data-testid="subject-entries-table"
        >
          <thead className="text-xs uppercase text-gray-500 dark:text-gray-400 bg-gray-50 dark:bg-gray-700/50">
            <tr>
              <th className="p-2 text-center border-b border-gray-200 dark:border-gray-700 font-semibold">Date</th>
              <th className="p-2 text-center border-b border-gray-200 dark:border-gray-700 font-semibold">Type</th>
              <th className="p-2 text-left border-b border-gray-200 dark:border-gray-700 font-semibold">Form</th>
              <th className="p-2 text-left border-b border-gray-200 dark:border-gray-700 font-semibold">Scores</th>
              <th className="p-2 text-left border-b border-gray-200 dark:border-gray-700 font-semibold">Description</th>
            </tr>
          </thead>
          <tbody className="text-sm font-medium divide-y divide-gray-200 dark:divide-gray-700/60">
            {entries.map((entry) => (
              entry.kind === 'reflection'
                ? <ReflectionRow key={`reflection-${entry.id}`} entry={entry} language={language} />
                : <ObservationRow key={`observation-${entry.id}`} entry={entry} />
            ))}
          </tbody>
        </table>
      </div>

      <div className="md:hidden space-y-4">
        {entries.map((entry) => (
          <article
            key={`${entry.kind}-${entry.id}`}
            className="rounded-lg border border-gray-200 dark:border-gray-700 p-4 bg-gray-50/50 dark:bg-gray-900/20"
            data-testid={`subject-entry-card-${entry.id}`}
          >
            <div className="flex items-center justify-between gap-2 mb-2">
              <span className="text-sm font-medium text-gray-800 dark:text-gray-100">
                {formatShortDate(entry.date)}
              </span>
              <TypeBadge kind={entry.kind} />
            </div>
            <p className="text-xs text-gray-500 dark:text-gray-400 mb-2">
              {entry.kind === 'reflection'
                ? entry.template?.name
                : (entry.observation?.context || 'Note')}
            </p>
            {entry.kind === 'reflection' ? (
              <DescriptionContent
                row={{
                  ...entry.reflection,
                  author: entry.reflection.author_name
                    ? { name: entry.reflection.author_name }
                    : null,
                }}
                {...deriveSchemaSections({ fields: entry.schemaFields ?? [] }, language)}
                flagTestidPrefix="subject-entry-flag"
              />
            ) : (
              <RichText
                html={entry.observation.body}
                className="text-sm text-gray-800 dark:text-gray-200 break-words"
              />
            )}
          </article>
        ))}
      </div>
    </>
  );
}
