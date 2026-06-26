import { Link } from 'react-router-dom';
import {
  Users,
  FileText,
  Layers,
  BarChart3,
  Tag,
  Boxes,
} from 'lucide-react';

const ADMIN_CARDS = [
  {
    id: 'memberships',
    title: 'Memberships',
    blurb:
      'Roster, role assignments, tags, and bulk tag operations for everyone in the program.',
    to: '/admin/memberships',
    icon: Users,
  },
  {
    id: 'templates',
    title: 'Reflection templates',
    blurb:
      'Create, clone, and edit reflection forms. The split-pane editor includes a live preview and routing controls.',
    to: '/admin/templates',
    icon: FileText,
  },
  {
    id: 'groups',
    title: 'Assignment groups',
    blurb:
      'Bunks, units, divisions, caseloads, and other groups that scope reflections and dashboards.',
    to: '/admin/groups',
    icon: Layers,
  },
  {
    id: 'dashboards',
    title: 'Dashboards',
    blurb:
      'Coverage, author attribution, concerns inbox, team, wellness, and subject trends.',
    to: '/admin/home',
    icon: BarChart3,
  },
  {
    id: 'field-keys',
    title: 'Field keys',
    blurb:
      'Canonical short keys used across reflection templates so cross-template dashboards can aggregate the same field even when it lives in different templates.',
    to: '/admin/field-keys',
    icon: Tag,
  },
  {
    id: 'catalog',
    title: 'Request catalog',
    blurb:
      'Configure the stores, request types, and items behind the Maintenance and Camper Care request forms. Bulk-import via CSV and track requested quantities on the planning dashboard.',
    to: '/admin/catalog',
    icon: Boxes,
  },
];

function Card({ card }) {
  const Icon = card.icon;
  const baseClass =
    'flex flex-col rounded-xl border bg-white dark:bg-gray-900 p-5 shadow-sm transition-all';
  const interactive =
    'border-gray-200 dark:border-gray-700 hover:shadow-md hover:border-indigo-300 dark:hover:border-indigo-700';
  const deferredClass =
    'border-dashed border-gray-300 dark:border-gray-700 opacity-70 cursor-not-allowed';

  const inner = (
    <>
      <div className="flex items-center gap-3 mb-3">
        <span className="inline-flex items-center justify-center w-10 h-10 rounded-lg bg-indigo-100 dark:bg-indigo-900/40 text-indigo-700 dark:text-indigo-300">
          <Icon size={20} aria-hidden="true" />
        </span>
        <h3 className="text-base font-semibold text-gray-900 dark:text-white">
          {card.title}
        </h3>
        {card.deferred && (
          <span className="ml-auto text-[10px] font-medium uppercase tracking-wide bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300 px-2 py-0.5 rounded-full">
            Coming soon
          </span>
        )}
      </div>
      <p className="text-sm text-gray-600 dark:text-gray-400 flex-1">
        {card.blurb}
      </p>
    </>
  );

  if (card.deferred) {
    return (
      <div
        data-testid={`admin-hub-card-${card.id}`}
        aria-disabled="true"
        className={`${baseClass} ${deferredClass}`}
      >
        {inner}
      </div>
    );
  }

  return (
    <Link
      to={card.to}
      data-testid={`admin-hub-card-${card.id}`}
      className={`${baseClass} ${interactive} group`}
    >
      {inner}
    </Link>
  );
}

export default function AdminHub() {
  return (
    <main className="grow px-4 sm:px-6 lg:px-8 py-8 w-full max-w-5xl mx-auto">
      <header className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
          Admin
        </h1>
        <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">
          Org-level tooling: people, templates, groups, dashboards, and
          field keys.
        </p>
      </header>
      <div
        data-testid="admin-hub-grid"
        className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4"
      >
        {ADMIN_CARDS.map((card) => (
          <Card key={card.id} card={card} />
        ))}
      </div>
    </main>
  );
}
