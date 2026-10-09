import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, within, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import CounselorMobileDashboard from '../CounselorMobileDashboard';
import { camperReflectionDraftKey } from '../../../utils/counselor/counselorDraftStorage';

const getMock = vi.fn();

vi.mock('../../../api', () => ({
  default: {
    get: (...args) => getMock(...args),
  },
}));

const SELF_TEMPLATE = { id: 9, slug: 'counselor-self-reflection', name: 'Counselor self', version: 1 };

function makePayload(overrides = {}) {
  return {
    viewer: { id: 10, name: 'Mira S.', full_name: 'Mira Sandberg', role: 'counselor' },
    selected_date: '2026-07-04',
    today: '2026-07-04',
    is_today: true,
    rollover_hour: 4,
    timezone: 'America/New_York',
    program: { id: 1, slug: 'clc-summer-2026', name: 'CLC Summer 2026' },
    all_set: false,
    bunks: [
      {
        id: 100,
        name: 'Bunk Birch',
        unit_name: 'Chalutzim',
        camper_count: 5,
        off_camp_count: 1,
        co_counselor_names: ['Theo R.'],
        dashboard_path: '/dashboards/group/100?date=2026-07-04',
        assignments: [
          {
            template_id: 7,
            template_name: 'Bunk Log',
            cadence: 'daily',
            state: 'in_progress',
            covered: 2,
            total: 4,
            due_label: '2 responses needed today',
            action_path: '/counselor/camper-reflections',
          },
        ],
      },
    ],
    viewer_requests: [
      {
        type: 'camper_care',
        id: 'order-1',
        status: 'new',
        status_label: 'New',
        title: 'Toothbrush',
        subtitle: 'For Alex K.',
        bunk_name: 'Bunk Birch',
        submitted_at: '2026-07-04T10:00:00Z',
      },
      {
        type: 'maintenance',
        id: 'ticket-1',
        status: 'in_progress',
        status_label: 'In Progress',
        title: 'Bathroom leak',
        subtitle: null,
        bunk_name: null,
        submitted_at: '2026-07-04T12:00:00Z',
      },
      {
        type: 'maintenance',
        id: 'ticket-old',
        status: 'new',
        status_label: 'New',
        title: 'Old screen door',
        submitted_at: '2026-07-01T09:00:00Z',
      },
    ],
    sections: {
      camper_reflections: { state: 'in_progress', covered: 2, total: 4, off_camp: 1, bunk_count: 1 },
      self_reflection: {
        state: 'none',
        submitted: false,
        reflection_id: null,
        is_day_off: false,
        template: SELF_TEMPLATE,
      },
      requests: { state: 'in_progress', open_count: 3, by_type: { camper_care: 1, maintenance: 2 } },
      ...overrides.sections,
    },
    ...overrides,
  };
}

function camper(id, name, extra = {}) {
  const [first, last] = name.split(' ');
  return {
    id,
    name,
    first_name: first,
    preferred_name: first,
    last_initial: last[0],
    submitted: false,
    reflection_id: null,
    editable: false,
    ...extra,
  };
}

function makeRoster(overrides = {}) {
  return {
    date: '2026-07-04',
    editable: true,
    template: { id: 7 },
    bunks: [
      {
        id: 100,
        name: 'Bunk Birch',
        covered: 2,
        total: 4,
        campers: [
          camper(1, 'Theo Marcus', { submitted: true, reflection_id: 501, editable: true }),
          camper(2, 'Noah Feldman', { submitted: true, reflection_id: 502, editable: true }),
          camper(3, 'Asa Brody'),
          camper(4, 'Ethan Lowe'),
        ],
        off_camp: [{ id: 5, name: 'Max Klein', first_name: 'Max', last_initial: 'K' }],
      },
    ],
    ...overrides,
  };
}

function mockApi({ dashboard = makePayload(), roster = makeRoster(), summary = { streak: 6, template: { cadence: 'daily' } } } = {}) {
  getMock.mockImplementation((url) => {
    if (url.includes('/counselor/dashboard/')) return Promise.resolve({ data: dashboard });
    if (url.includes('/counselor/camper-reflections/')) return Promise.resolve({ data: roster });
    if (url.includes('/reflections/my-summary/')) return Promise.resolve({ data: summary });
    return Promise.reject(new Error(`unexpected ${url}`));
  });
}

function renderPage(initialEntry = '/counselor') {
  return render(
    <MemoryRouter initialEntries={[initialEntry]}>
      <CounselorMobileDashboard />
    </MemoryRouter>,
  );
}

describe('CounselorMobileDashboard', () => {
  beforeEach(() => {
    getMock.mockReset();
    localStorage.clear();
  });

  it('renders the bunk hero, camper chips and a CTA pointing at the draft camper', async () => {
    localStorage.setItem(
      camperReflectionDraftKey(3, '2026-07-04'),
      JSON.stringify({ answers: { mood: 4 } }),
    );
    mockApi();
    renderPage();

    const cta = await screen.findByTestId('counselor-continue-logging-100');
    expect(cta).toHaveTextContent('Continue logging · Asa B.');
    expect(cta).toHaveAttribute(
      'href',
      '/counselor/camper-reflections/new?subject=3&bunk=100&name=Asa%20Brody',
    );

    const hero = screen.getByTestId('counselor-bunk-tile-100');
    expect(hero).toHaveTextContent('With Theo R. · 5 campers · 1 off camp');
    expect(hero).toHaveTextContent('2 of 4');

    const chipFor = (id) => within(screen.getByTestId(`counselor-camper-row-${id}`)).getByTestId('camper-status-chip');
    expect(chipFor(1)).toHaveTextContent('Done');
    expect(chipFor(2)).toHaveTextContent('Done');
    expect(chipFor(3)).toHaveTextContent('Draft saved');
    expect(chipFor(4)).toHaveTextContent('Not started');
    expect(chipFor(5)).toHaveTextContent('Off camp');
    expect(within(screen.getByTestId('counselor-camper-row-5')).queryByRole('link')).toBeNull();

    expect(screen.getByTestId('counselor-section-self-subtitle')).toHaveTextContent('6-day streak');
    expect(screen.getByTestId('counselor-section-self-action')).toHaveTextContent('Start');
    expect(screen.getByTestId('counselor-action-report-issue')).toHaveAttribute('href', '/help');
  });

  it('shows the all-logged state and all-set banner when everything is done', async () => {
    const roster = makeRoster();
    roster.bunks[0].campers = roster.bunks[0].campers.map((c, i) => ({
      ...c, submitted: true, reflection_id: 600 + i, editable: true,
    }));
    roster.bunks[0].covered = 4;
    mockApi({
      roster,
      dashboard: makePayload({
        all_set: true,
        sections: {
          self_reflection: { state: 'complete', submitted: true, reflection_id: 42, template: SELF_TEMPLATE },
        },
      }),
    });
    renderPage();

    expect(await screen.findByTestId('counselor-bunk-done-100')).toHaveTextContent('All campers logged');
    expect(screen.queryByTestId('counselor-continue-logging-100')).toBeNull();
    expect(screen.getByTestId('counselor-all-set')).toBeInTheDocument();
    expect(screen.getByTestId('counselor-section-self-action')).toHaveAttribute(
      'href',
      '/counselor/self-reflection/42/edit',
    );
  });

  it('disables next on today and steps back a day via the date param', async () => {
    mockApi();
    renderPage();

    expect(await screen.findByTestId('counselor-day-next')).toBeDisabled();
    fireEvent.click(screen.getByTestId('counselor-day-prev'));

    await waitFor(() => {
      const dashboardCalls = getMock.mock.calls.filter(([url]) => url.includes('/counselor/dashboard/'));
      expect(dashboardCalls.at(-1)[1].params.date).toBe('2026-07-03');
    });
  });

  it('shows the two most recent requests and links All to the requests list', async () => {
    mockApi();
    renderPage();

    const widget = await screen.findByTestId('counselor-requests-widget');
    expect(within(widget).getByTestId('counselor-request-maintenance-ticket-1')).toHaveAttribute(
      'href',
      '/counselor/requests/maintenance/ticket-1?from=counselor',
    );
    expect(within(widget).getByTestId('counselor-request-camper_care-order-1')).toBeInTheDocument();
    expect(within(widget).queryByTestId('counselor-request-maintenance-ticket-old')).toBeNull();
    expect(screen.getByTestId('counselor-requests-all')).toHaveAttribute('href', '/counselor/requests');
  });

  it('shows day-off on the self-reflection card', async () => {
    mockApi({
      dashboard: makePayload({
        sections: {
          self_reflection: { state: 'complete', submitted: true, reflection_id: 50, is_day_off: true, template: SELF_TEMPLATE },
        },
      }),
    });
    renderPage();
    expect(await screen.findByText(/Day off recorded/i)).toBeInTheDocument();
  });

  it('still renders when the roster request fails', async () => {
    getMock.mockImplementation((url) => (
      url.includes('/counselor/dashboard/')
        ? Promise.resolve({ data: makePayload() })
        : Promise.reject(new Error('down'))
    ));
    renderPage();
    expect(await screen.findByTestId('counselor-bunk-tile-100')).toHaveTextContent('2 of 4');
    expect(screen.queryByTestId('counselor-camper-list-100')).toBeNull();
  });

  it('renders an error banner on dashboard failure', async () => {
    getMock.mockRejectedValue({ response: { status: 500, data: { detail: 'boom' } } });
    renderPage();
    expect(await screen.findByTestId('counselor-dashboard-error')).toHaveTextContent('boom');
  });

  it('renders empty bunk state when counselor has no bunks', async () => {
    mockApi({ dashboard: makePayload({ bunks: [] }), roster: makeRoster({ bunks: [] }) });
    renderPage();
    expect(await screen.findByText(/not assigned as an author on any bunk/i)).toBeInTheDocument();
  });
});
