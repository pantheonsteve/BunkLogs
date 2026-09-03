/**
 * The shell behind /admin/forms and /admin/reports.
 *
 * The sidebar used to carry these destinations as text sub-headings over
 * eleven links. Turning the headings into pages keeps the nav to seven
 * rows; the cost is that each hub has to say what its links are *for*,
 * which the nav never had room to do.
 *
 * Links come from `adminNavConfig` so the hub and the nav item that
 * points at it cannot drift apart.
 */
import { ChevronRight } from 'lucide-react';
import { Link } from 'react-router-dom';

import Card from '../../components/ui/Card';
import EmptyState from '../../components/ui/EmptyState';
import PageHeader from '../../components/ui/PageHeader';

export default function HubPage({ title, subtitle, links, emptyTitle, emptyBody, testId }) {
  return (
    <main
      className="grow px-4 sm:px-6 lg:px-8 py-6 w-full max-w-[1180px] mx-auto"
      data-testid={testId}
    >
      <PageHeader title={title} subtitle={subtitle} />

      {links.length === 0 ? (
        <Card>
          <EmptyState title={emptyTitle}>{emptyBody}</EmptyState>
        </Card>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2">
          {links.map((link) => (
            <Link
              key={link.to}
              to={link.to}
              className="group block rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 shadow-sm px-[18px] py-4 transition hover:border-indigo-300 hover:shadow-md"
            >
              <div className="flex items-start gap-3">
                <div className="min-w-0 flex-1">
                  <h2 className="text-sm font-semibold text-gray-900 dark:text-white">
                    {link.label}
                  </h2>
                  <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                    {link.description}
                  </p>
                </div>
                <ChevronRight
                  size={18}
                  aria-hidden="true"
                  className="shrink-0 mt-0.5 text-gray-300 dark:text-gray-600 group-hover:text-indigo-500"
                />
              </div>
            </Link>
          ))}
        </div>
      )}
    </main>
  );
}
