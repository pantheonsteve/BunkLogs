import { Link } from 'react-router-dom';
import { FieldInput, PeopleListPagination } from '../../../components/admin/PersonProfilePanel';
import { profileLink } from '../../../utils/dashboardLinks';

function classNames(...args) {
  return args.filter(Boolean).join(' ');
}

export default function ProgramMembersPane({
  program,
  people,
  loading,
  error,
  search,
  onSearchChange,
  selectedPersonId,
  onSelectPerson,
  offset,
  pageSize,
  totalCount,
  onPrevious,
  onNext,
}) {
  const paneClassName = [
    'rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900/40 p-3 min-h-[20rem] flex flex-col',
    'lg:sticky lg:top-6 lg:self-start lg:max-h-[calc(100vh-8rem)]',
  ].join(' ');

  if (!program) {
    return (
      <section
        className={paneClassName}
        data-testid="membership-roster-empty"
      >
        <h2 className="text-sm font-semibold text-gray-900 dark:text-white">Enrolled people</h2>
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-4">
          Select a program to view enrolled people.
        </p>
      </section>
    );
  }

  return (
    <section className={`${paneClassName} space-y-2 min-h-0`}>
      <div className="flex items-center justify-between gap-2">
        <h2 className="text-sm font-semibold text-gray-900 dark:text-white">
          Enrolled in {program.name}
        </h2>
      </div>
      <FieldInput
        label="Search name or email"
        value={search}
        onChange={onSearchChange}
      />
      {loading ? (
        <p className="text-sm text-gray-500">Loading…</p>
      ) : error ? (
        <p className="text-sm text-red-700">Could not load people.</p>
      ) : (
        <>
          <ul className="flex-1 min-h-0 overflow-y-auto divide-y rounded-md border bg-white dark:bg-gray-900" data-testid="membership-roster-list">
            {people.length === 0 && (
              <li className="p-3 text-sm italic text-gray-500">No people enrolled in this program.</li>
            )}
            {people.map((p) => (
              <li
                key={p.id}
                data-testid={`membership-roster-person-${p.id}`}
                className={classNames(
                  'p-3 cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800',
                  String(selectedPersonId) === String(p.id) && 'bg-indigo-50 dark:bg-indigo-900/20',
                )}
                onClick={() => onSelectPerson(p.id)}
              >
                <Link
                  to={profileLink(p.id)}
                  onClick={(e) => e.stopPropagation()}
                  className="font-medium text-sm text-indigo-700 dark:text-indigo-300 hover:underline"
                >
                  {p.full_name}
                </Link>
                <p className="text-xs text-gray-500">{p.email || 'no email'}</p>
              </li>
            ))}
          </ul>
          <PeopleListPagination
            offset={offset}
            resultCount={people.length}
            totalCount={totalCount}
            loading={loading}
            onPrevious={onPrevious}
            onNext={onNext}
          />
        </>
      )}
    </section>
  );
}
