import { useState } from 'react';
import { Link } from 'react-router-dom';
import {
  BarChart3,
  Users,
  Inbox,
  HeartPulse,
  UserCog,
  LineChart,
} from 'lucide-react';

import Header from '../../partials/Header';
import Sidebar from '../../partials/Sidebar';

const DASHBOARD_CARDS = [
  {
    id: 'coverage',
    title: 'Coverage',
    blurb:
      "Per-group / per-day completion heatmap. Which bunks / units are filing reflections on schedule.",
    to: '/dashboards/coverage',
    icon: BarChart3,
    audience: 'Supervisors, admins',
  },
  {
    id: 'authors',
    title: 'Author attribution',
    blurb:
      'Who is filing reflections, broken down by author -- catches both unfiled work and one person carrying the team.',
    to: '/dashboards/authors',
    icon: UserCog,
    audience: 'Supervisors, admins',
  },
  {
    id: 'concerns',
    title: 'Concerns inbox',
    blurb:
      'Flagged low ratings and free-text concerns that need triage, surfaced as a queue.',
    to: '/dashboards/concerns',
    icon: Inbox,
    audience: 'Supervisors, admins, wellness',
  },
  {
    id: 'logs',
    title: 'Bunk Logs',
    blurb:
      'Browse forms assigned to groups and open responses by audience, program, or group.',
    to: '/dashboards/logs',
    icon: Users,
    audience: 'Supervisors, admins',
  },
  {
    id: 'reflections',
    title: 'Reflections',
    blurb:
      'Browse self-reflection forms and open responses by audience, program, or group.',
    to: '/dashboards/reflections',
    icon: Users,
    audience: 'Supervisors, admins, staff',
  },
  {
    id: 'wellness',
    title: 'Wellness dashboard',
    blurb:
      'Camper-care / health-center / special-diets cross-team view with subject-level patterns.',
    to: '/dashboards/wellness',
    icon: HeartPulse,
    audience: 'Wellness team, admins',
  },
  {
    id: 'subjects',
    title: 'Subject trends',
    blurb:
      'Per-camper / per-staff trend grid over time. Pick a group first to see its members.',
    to: '/admin/groups',
    icon: LineChart,
    audience: 'Supervisors, admins',
    note: 'Pick a group, then click into a subject.',
  },
];

function Card({ card }) {
  const Icon = card.icon;
  return (
    <Link
      to={card.to}
      data-testid={`dashboards-hub-card-${card.id}`}
      className="group flex flex-col rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-5 shadow-sm hover:shadow-md hover:border-indigo-300 dark:hover:border-indigo-700 transition-all"
    >
      <div className="flex items-center gap-3 mb-3">
        <span className="inline-flex items-center justify-center w-10 h-10 rounded-lg bg-indigo-100 dark:bg-indigo-900/40 text-indigo-700 dark:text-indigo-300">
          <Icon size={20} aria-hidden="true" />
        </span>
        <h3 className="text-base font-semibold text-gray-900 dark:text-white">
          {card.title}
        </h3>
      </div>
      <p className="text-sm text-gray-600 dark:text-gray-400 flex-1">
        {card.blurb}
      </p>
      {card.note && (
        <p className="mt-2 text-xs italic text-gray-500 dark:text-gray-500">
          {card.note}
        </p>
      )}
      <p className="mt-4 text-xs font-medium text-gray-500 dark:text-gray-400">
        {card.audience}
      </p>
    </Link>
  );
}

export default function DashboardsHub() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} />
      <div className="relative flex flex-col flex-1 overflow-y-auto overflow-x-hidden">
        <Header sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} />
        <main className="grow px-4 sm:px-6 lg:px-8 py-8 w-full max-w-6xl mx-auto">
          <header className="mb-6">
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
              Dashboards
            </h1>
            <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">
              Aggregated views across reflections, authors, and subjects.
              Visibility on each dashboard depends on your role and the
              groups you supervise.
            </p>
          </header>
          <div
            data-testid="dashboards-hub-grid"
            className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4"
          >
            {DASHBOARD_CARDS.map((card) => (
              <Card key={card.id} card={card} />
            ))}
          </div>
        </main>
      </div>
    </div>
  );
}
