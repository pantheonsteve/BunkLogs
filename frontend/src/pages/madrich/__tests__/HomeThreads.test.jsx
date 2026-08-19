/**
 * Madrich homepage threaded surfaces — Step 4_9 §4.3-4.5.
 *
 * The cards are driven off the template schema, so these fixtures use field
 * keys the frontend has never heard of: if a card only renders for `wins` or
 * `question_or_concern`, this fails.
 */
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import MadrichDashboard from '../Dashboard';

const getMock = vi.fn();
vi.mock('../../../api', () => ({
  default: { get: (...args) => getMock(...args) },
}));

vi.mock('../../../auth/AuthContext', () => ({
  useAuth: () => ({ orgSlug: 'tbe', user: { id: 42 } }),
}));

vi.mock('chart.js', () => ({
  Chart: class { destroy() {} },
}));
vi.mock('chart.js/auto', () => ({}));
HTMLCanvasElement.prototype.getContext = () => ({});

const dashboard = {
  header: { name: 'Ari Rich', program_name: 'TBE Religious School', grade_level: 9 },
  my_reflections: [],
  history_entry: { url: '/madrich/history' },
  availability: { upcoming_unset_count: 0, next_session_date: null, calendar_url: '/madrich/availability' },
  availability_nudge: false,
  entry_cards: [
    {
      // Deliberately not a TBE field key.
      field_key: 'proud_moment',
      label: 'A moment you were proud of',
      thread_scope: 'item',
      routes_to: '',
      total: 2,
      unread_count: 1,
      entries: [
        {
          thread_id: 501,
          reflection_id: 90,
          item_index: 0,
          excerpt: 'Helped a shy kid join the group game.',
          date: '2026-09-13',
          routes_to: '',
          unread: true,
          resolved_at: null,
          message_count: 1,
          awaiting_reply: false,
        },
      ],
    },
    {
      field_key: 'ask_the_director',
      label: 'Something for your Director',
      thread_scope: 'field',
      routes_to: 'director',
      total: 1,
      unread_count: 0,
      entries: [
        {
          thread_id: 502,
          reflection_id: 90,
          item_index: null,
          excerpt: 'Can we get more supplies?',
          date: '2026-09-13',
          routes_to: 'director',
          unread: false,
          resolved_at: null,
          message_count: 0,
          awaiting_reply: true,
        },
      ],
    },
  ],
  cohort: { enabled: true, unread_count: 3, url: '/madrich/cohort' },
};

const trends = {
  series: [{
    trend_key: 'w.ratings.initiative',
    field_key: 'ratings',
    category_key: 'initiative',
    label: 'Initiative',
    scale_min: 1,
    scale_max: 4,
    points: [{ date: '2026-09-13', value: 3, reflection_id: 90 }],
  }],
};

function routeResponse(url) {
  if (url.includes('/madrich/dashboard/')) return { data: dashboard };
  if (url.includes('/madrich/trends/')) return { data: trends };
  if (url.includes('/madrich/availability/')) {
    return {
      data: {
        sessions: [
          { session_date: '2026-09-20', label: 'Sun Sep 20', editable: true, commitment: { status: 'available' } },
          { session_date: '2026-09-27', label: 'Sun Sep 27', editable: true, commitment: null },
        ],
      },
    };
  }
  return { data: { classrooms: [] } };
}

beforeEach(() => {
  getMock.mockReset();
  getMock.mockImplementation((url) => Promise.resolve(routeResponse(url)));
});

function renderHome() {
  return render(<MemoryRouter><MadrichDashboard /></MemoryRouter>);
}

describe('Madrich homepage — threaded fields, trends, cohort', () => {
  it('builds a card per threaded field from the schema, whatever it is called', async () => {
    renderHome();
    await waitFor(() => screen.getByTestId('md-entry-card-proud_moment'));

    const card = screen.getByTestId('md-entry-card-proud_moment');
    expect(card).toHaveTextContent('A moment you were proud of');
    expect(card).toHaveTextContent('Helped a shy kid join the group game.');
    expect(screen.getByTestId('md-entry-card-ask_the_director')).toBeInTheDocument();
    expect(screen.getByTestId('md-entries-link-proud_moment')).toHaveAttribute(
      'href', '/madrich/entries/proud_moment',
    );
    expect(screen.getByTestId('md-entry-row-501')).toBeInTheDocument();
  });

  it('tells a Madrich their routed question has not been answered yet', async () => {
    renderHome();
    await waitFor(() => screen.getByTestId('md-awaiting-502'));
    expect(screen.getByTestId('md-awaiting-502')).toHaveTextContent('Director');
    expect(screen.queryByTestId('md-awaiting-501')).toBeNull();
  });

  it('badges unread cohort activity without fetching the feed', async () => {
    renderHome();
    await waitFor(() => screen.getByTestId('md-cohort-card'));
    expect(screen.getByTestId('md-cohort-card')).toHaveTextContent('3 new posts');
    expect(screen.getByTestId('md-cohort-cta')).toHaveAttribute('href', '/madrich/cohort');
    expect(getMock.mock.calls.some(([url]) => url.includes('/cohort/feed/'))).toBe(false);
  });

  it('shows a trend chart per rated category', async () => {
    renderHome();
    await waitFor(() => screen.getByTestId('md-trends-card'));
    expect(screen.getByTestId('trend-chart-w.ratings.initiative')).toBeInTheDocument();
  });

  it('colours the next Sundays and distinguishes unset from a no', async () => {
    renderHome();
    await waitFor(() => screen.getByTestId('md-availability-strip'));
    expect(screen.getByTestId('md-availability-pill-2026-09-20')).toHaveTextContent('Available');
    expect(screen.getByTestId('md-availability-pill-2026-09-27')).toHaveTextContent('Not set');
  });

  it('renders without threaded cards when the template declares none', async () => {
    getMock.mockImplementation((url) => Promise.resolve(
      url.includes('/madrich/dashboard/')
        ? { data: { ...dashboard, entry_cards: [], cohort: { enabled: false, unread_count: 0 } } }
        : routeResponse(url),
    ));
    renderHome();
    await waitFor(() => screen.getByTestId('md-availability-card'));
    expect(screen.queryByTestId('md-entry-card-proud_moment')).toBeNull();
    expect(screen.queryByTestId('md-cohort-card')).toBeNull();
  });
});
