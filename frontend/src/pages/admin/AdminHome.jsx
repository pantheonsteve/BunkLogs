import { Link } from 'react-router-dom';
import {
  LayoutGrid,
  ScrollText,
  ClipboardList,
  GraduationCap,
  MessageSquare,
  Wrench,
  Heart,
  BarChart3,
  Inbox,
  UserCog,
  TrendingUp,
} from 'lucide-react';

import { useAuth } from '../../auth/AuthContext';
import { accent } from '../../components/ui/accents';
import { orgSurfaces } from '../../utils/auth/orgProfile';
import DirectorHome from './DirectorHome';

/**
 * Mirrors the top-level admin nav links (My work + Supervise), excluding Home.
 * `surface` names the org surface a tile belongs to (see `utils/auth/orgProfile`);
 * tiles without one show for every tenant. `accent` keys into
 * `components/ui/accents` for the icon badge and the tile's top rule.
 */
const NAV_TILES = [
  {
    id: 'performance',
    title: 'Group Performance',
    blurb:
      'Scores and trends across assignment groups and programs — see how groups are performing over time.',
    to: '/groups/performance',
    icon: LayoutGrid,
    surface: 'campDashboards',
    accent: 'violet',
  },
  {
    id: 'logs',
    title: 'Bunk Logs',
    blurb:
      'Browse forms assigned to groups and open responses by audience, program, or group.',
    to: '/dashboards/logs',
    icon: ScrollText,
    surface: 'campDashboards',
    accent: 'emerald',
  },
  {
    id: 'reflections',
    title: 'Reflections',
    blurb:
      'Browse self-reflection forms and open responses by audience, program, or group.',
    to: '/dashboards/reflections',
    icon: ClipboardList,
    accent: 'blue',
  },
  {
    id: 'grade-reflections',
    title: 'Madrich completion',
    blurb:
      'Weekly 3-2-1 completion for Madrichim, filtered by grade level, with a CSV export for board reporting.',
    to: '/admin/reflections',
    icon: GraduationCap,
    surface: 'gradeReflections',
    accent: 'indigo',
  },
  {
    id: 'growth-by-grade',
    title: 'Growth by grade',
    blurb:
      'What 8th graders are asking about versus 11th graders, with developmental milestones across grades 8-12.',
    to: '/admin/reflections/growth',
    icon: TrendingUp,
    surface: 'gradeReflections',
    accent: 'violet',
  },
  {
    id: 'observations',
    title: 'Observations',
    blurb:
      'Staff observations inbox — read threads, reply, and follow up on notes about campers and staff.',
    to: '/observations',
    icon: MessageSquare,
    surface: 'observations',
    accent: 'sky',
  },
  {
    id: 'maintenance',
    title: 'Maintenance Queue',
    blurb:
      'Open maintenance tickets filed by staff — triage, assign, and close work across camp.',
    to: '/maintenance',
    icon: Wrench,
    surface: 'campOps',
    accent: 'amber',
  },
  {
    id: 'camper-care-orders',
    title: 'Camper Care orders',
    blurb:
      'Camper care supply and service orders — review and fulfill requests from counselors and staff.',
    to: '/camper-care/orders',
    icon: Heart,
    surface: 'campOps',
    accent: 'rose',
  },
  {
    id: 'coverage',
    title: 'Coverage dashboard',
    blurb:
      'Per-group / per-day completion heatmap — which bunks and units are filing reflections on schedule.',
    to: '/dashboards/coverage',
    icon: BarChart3,
    surface: 'campDashboards',
    accent: 'teal',
  },
  {
    id: 'concerns',
    title: 'Concerns inbox',
    blurb:
      'Flagged low ratings and free-text concerns that need triage, surfaced as a queue.',
    to: '/dashboards/concerns',
    icon: Inbox,
    surface: 'campDashboards',
    accent: 'orange',
  },
  {
    id: 'authors',
    title: 'Author attribution',
    blurb:
      'Who is filing reflections, broken down by author — catches unfiled work and uneven load across a team.',
    to: '/dashboards/authors',
    icon: UserCog,
    surface: 'campDashboards',
    accent: 'indigo',
  },
];

function Card({ card }) {
  const Icon = card.icon;
  const tone = accent(card.accent);
  return (
    <Link
      to={card.to}
      data-testid={`admin-home-card-${card.id}`}
      className={`group flex flex-col rounded-xl border border-t-4 border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-5 shadow-sm hover:shadow-lg hover:-translate-y-0.5 transition-all ${tone.bar}`}
    >
      <div className="flex items-center gap-3 mb-3">
        <span
          className={`inline-flex items-center justify-center w-10 h-10 rounded-lg ${tone.chip}`}
        >
          <Icon size={20} aria-hidden="true" />
        </span>
        <h3 className="text-base font-semibold text-gray-900 dark:text-white">
          {card.title}
        </h3>
      </div>
      <p className="text-sm text-gray-700 dark:text-gray-300 flex-1">
        {card.blurb}
      </p>
    </Link>
  );
}

export default function AdminHome() {
  const { user } = useAuth();
  const surfaces = orgSurfaces(user);
  const tiles = NAV_TILES.filter((card) => !card.surface || surfaces[card.surface]);
  const blurb = surfaces.campDashboards
    ? 'Quick links to the main workspaces in your sidebar — performance, reflections, operations, and supervision.'
    : 'Quick links to the main workspaces in your sidebar — reflections and completion across your programs.';

  return (
    <main className="grow px-4 sm:px-6 lg:px-8 py-8 w-full max-w-6xl mx-auto">
      <header
        data-testid="admin-home-header"
        className="mb-8 rounded-2xl bg-gradient-to-r from-indigo-600 via-violet-600 to-fuchsia-600 px-6 py-6 shadow-md"
      >
        <h1 className="text-2xl font-bold text-white">Admin Home</h1>
        <p className="mt-1 text-sm text-indigo-50 max-w-3xl">{blurb}</p>
      </header>
      <div
        data-testid="admin-home-grid"
        className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4"
      >
        {tiles.map((card) => (
          <Card key={card.id} card={card} />
        ))}
      </div>
      {surfaces.gradeReflections && <DirectorHome />}
    </main>
  );
}
