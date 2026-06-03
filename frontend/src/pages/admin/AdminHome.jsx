import { Link } from 'react-router-dom';
import {
  LayoutGrid,
  ScrollText,
  ClipboardList,
  MessageSquare,
  Wrench,
  Heart,
  BarChart3,
  Inbox,
  UserCog,
} from 'lucide-react';

/** Mirrors the nine top-level admin nav links (My work + Supervise), excluding Home. */
const NAV_TILES = [
  {
    id: 'performance',
    title: 'Group Performance',
    blurb:
      'Scores and trends across assignment groups and programs — see how groups are performing over time.',
    to: '/groups/performance',
    icon: LayoutGrid,
    iconClass:
      'bg-violet-100 text-violet-700 dark:bg-violet-900/40 dark:text-violet-300',
  },
  {
    id: 'logs',
    title: 'Bunk Logs',
    blurb:
      'Browse forms assigned to groups and open responses by audience, program, or group.',
    to: '/dashboards/logs',
    icon: ScrollText,
    iconClass:
      'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300',
  },
  {
    id: 'reflections',
    title: 'Reflections',
    blurb:
      'Browse self-reflection forms and open responses by audience, program, or group.',
    to: '/dashboards/reflections',
    icon: ClipboardList,
    iconClass:
      'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300',
  },
  {
    id: 'observations',
    title: 'Observations',
    blurb:
      'Staff observations inbox — read threads, reply, and follow up on notes about campers and staff.',
    to: '/observations',
    icon: MessageSquare,
    iconClass:
      'bg-sky-100 text-sky-700 dark:bg-sky-900/40 dark:text-sky-300',
  },
  {
    id: 'maintenance',
    title: 'Maintenance Queue',
    blurb:
      'Open maintenance tickets filed by staff — triage, assign, and close work across camp.',
    to: '/maintenance',
    icon: Wrench,
    iconClass:
      'bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300',
  },
  {
    id: 'camper-care-orders',
    title: 'Camper Care orders',
    blurb:
      'Camper care supply and service orders — review and fulfill requests from counselors and staff.',
    to: '/camper-care/orders',
    icon: Heart,
    iconClass: 'bg-rose-100 text-rose-700 dark:bg-rose-900/40 dark:text-rose-300',
  },
  {
    id: 'coverage',
    title: 'Coverage dashboard',
    blurb:
      'Per-group / per-day completion heatmap — which bunks and units are filing reflections on schedule.',
    to: '/dashboards/coverage',
    icon: BarChart3,
    iconClass: 'bg-teal-100 text-teal-700 dark:bg-teal-900/40 dark:text-teal-300',
  },
  {
    id: 'concerns',
    title: 'Concerns inbox',
    blurb:
      'Flagged low ratings and free-text concerns that need triage, surfaced as a queue.',
    to: '/dashboards/concerns',
    icon: Inbox,
    iconClass:
      'bg-orange-100 text-orange-700 dark:bg-orange-900/40 dark:text-orange-300',
  },
  {
    id: 'authors',
    title: 'Author attribution',
    blurb:
      'Who is filing reflections, broken down by author — catches unfiled work and uneven load across a team.',
    to: '/dashboards/authors',
    icon: UserCog,
    iconClass:
      'bg-indigo-100 text-indigo-700 dark:bg-indigo-900/40 dark:text-indigo-300',
  },
];

function Card({ card }) {
  const Icon = card.icon;
  return (
    <Link
      to={card.to}
      data-testid={`admin-home-card-${card.id}`}
      className="group flex flex-col rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-5 shadow-sm hover:shadow-md hover:border-indigo-300 dark:hover:border-indigo-700 transition-all"
    >
      <div className="flex items-center gap-3 mb-3">
        <span
          className={`inline-flex items-center justify-center w-10 h-10 rounded-lg ${card.iconClass}`}
        >
          <Icon size={20} aria-hidden="true" />
        </span>
        <h3 className="text-base font-semibold text-gray-900 dark:text-white">
          {card.title}
        </h3>
      </div>
      <p className="text-sm text-gray-600 dark:text-gray-400 flex-1">
        {card.blurb}
      </p>
    </Link>
  );
}

export default function AdminHome() {
  return (
    <main className="grow px-4 sm:px-6 lg:px-8 py-8 w-full max-w-6xl mx-auto">
      <header
        data-testid="admin-home-header"
        className="mb-6 border-b-2 border-indigo-500/70 dark:border-indigo-400/60 pb-4"
      >
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
          Admin Home
        </h1>
        <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">
          Quick links to the main workspaces in your sidebar — performance,
          reflections, operations, and supervision.
        </p>
      </header>
      <div
        data-testid="admin-home-grid"
        className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4"
      >
        {NAV_TILES.map((card) => (
          <Card key={card.id} card={card} />
        ))}
      </div>
    </main>
  );
}
