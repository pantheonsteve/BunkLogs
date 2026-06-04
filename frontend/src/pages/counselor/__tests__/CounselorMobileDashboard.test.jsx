import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import CounselorMobileDashboard from '../CounselorMobileDashboard';

const getMock = vi.fn();

vi.mock('../../../api', () => ({
  default: {
    get: (...args) => getMock(...args),
  },
}));

function makePayload(overrides = {}) {
  return {
    viewer: {
      id: 10,
      name: 'Mira S.',
      full_name: 'Mira Sandberg',
      role: 'counselor',
    },
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
        unit_name: 'Unit A',
        camper_count: 5,
        off_camp_count: 1,
        co_counselor_names: ['Jordan P.'],
        dashboard_path: '/dashboards/group/100?date=2026-07-04',
        assignments: [
          {
            template_id: 7,
            template_name: 'Bunk Log',
            cadence: 'daily',
            state: 'in_progress',
            covered: 2,
            total: 4,
            remaining: 2,
            due_label: '2 responses needed today',
            action_path: '/counselor/camper-reflections',
          },
        ],
      },
    ],
    sections: {
      camper_reflections: {
        state: 'in_progress',
        covered: 2,
        total: 5,
        off_camp: 1,
        bunk_count: 1,
      },
      self_reflection: {
        state: 'none',
        submitted: false,
        reflection_id: null,
        submitted_at: null,
        is_day_off: false,
        editable: false,
        template: { id: 9, slug: 'counselor-self-reflection', name: 'Counselor self', version: 1 },
      },
      requests: {
        state: 'in_progress',
        open_count: 2,
        by_type: { camper_care: 1, maintenance: 1 },
      },
      ...overrides.sections,
    },
    ...overrides,
  };
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
  });

  it('renders viewer header, bunk tile, self-reflection, and quick actions', async () => {
    getMock.mockResolvedValue({ data: makePayload() });
    renderPage();

    await waitFor(() => expect(screen.getByText('Mira Sandberg')).toBeInTheDocument());

    expect(screen.getByTestId('counselor-bunk-tile-100')).toBeInTheDocument();
    expect(screen.getByText('Bunk Birch')).toBeInTheDocument();
    expect(screen.getByText(/2 responses needed today/i)).toBeInTheDocument();
    expect(screen.getByTestId('counselor-section-self')).toBeInTheDocument();
    expect(screen.getByTestId('counselor-action-tasks')).toBeInTheDocument();
    expect(screen.getByTestId('counselor-action-my-reflections')).toBeInTheDocument();
    expect(screen.getByTestId('counselor-action-camper-care')).toBeInTheDocument();
    expect(screen.getByTestId('counselor-action-maintenance')).toBeInTheDocument();
    expect(screen.getByTestId('counselor-action-requests')).toBeInTheDocument();
    expect(screen.getByTestId('counselor-action-observation')).toBeInTheDocument();
  });

  it('passes the date query param to the dashboard API', async () => {
    getMock.mockResolvedValue({
      data: makePayload({ selected_date: '2026-07-01', is_today: false }),
    });
    renderPage('/counselor?date=2026-07-01');

    await waitFor(() => expect(getMock).toHaveBeenCalled());
    const [, config] = getMock.mock.calls[0];
    expect(config.params.date).toBe('2026-07-01');
  });

  it('shows the all-set banner when both required sections are complete', async () => {
    getMock.mockResolvedValue({
      data: makePayload({
        all_set: true,
        bunks: [
          {
            id: 100,
            name: 'Bunk Birch',
            unit_name: null,
            camper_count: 0,
            off_camp_count: 0,
            co_counselor_names: [],
            dashboard_path: '/dashboards/group/100?date=2026-07-04',
            assignments: [],
          },
        ],
        sections: {
          camper_reflections: { state: 'complete', covered: 5, total: 5, off_camp: 0, bunk_count: 1 },
          self_reflection: {
            state: 'complete',
            submitted: true,
            reflection_id: 42,
            submitted_at: '2026-07-04T13:00:00Z',
            is_day_off: false,
            editable: true,
            template: { id: 9, slug: 'counselor-self-reflection', name: 'Counselor self', version: 1 },
          },
          requests: { state: 'none', open_count: 0, by_type: { camper_care: 0, maintenance: 0 } },
        },
      }),
    });
    renderPage();

    await waitFor(() => expect(screen.getByTestId('counselor-all-set')).toBeInTheDocument());
    expect(screen.getByText(/you're all set for today/i)).toBeInTheDocument();
  });

  it('shows day-off summary when self_reflection.is_day_off is true', async () => {
    getMock.mockResolvedValue({
      data: makePayload({
        sections: {
          camper_reflections: { state: 'complete', covered: 0, total: 0, off_camp: 0, bunk_count: 0 },
          self_reflection: {
            state: 'complete',
            submitted: true,
            reflection_id: 50,
            submitted_at: '2026-07-04T13:00:00Z',
            is_day_off: true,
            editable: true,
            template: { id: 9, slug: 'counselor-self-reflection', name: 'Counselor self', version: 1 },
          },
          requests: { state: 'none', open_count: 0, by_type: { camper_care: 0, maintenance: 0 } },
        },
      }),
    });
    renderPage();
    await waitFor(() => expect(screen.getByText(/Day off recorded/i)).toBeInTheDocument());
  });

  it('renders an error banner on API failure', async () => {
    getMock.mockRejectedValue({ response: { status: 500, data: { detail: 'boom' } } });
    renderPage();
    await waitFor(() => expect(screen.getByTestId('counselor-dashboard-error')).toBeInTheDocument());
    expect(screen.getByTestId('counselor-dashboard-error')).toHaveTextContent('boom');
  });

  it('points the bunk assignment CTA at camper reflections', async () => {
    getMock.mockResolvedValue({ data: makePayload() });
    renderPage();
    await waitFor(() => expect(screen.getByTestId('bunk-assignment-action-7')).toBeInTheDocument());
    expect(screen.getByTestId('bunk-assignment-action-7')).toHaveAttribute(
      'href',
      '/counselor/camper-reflections',
    );
  });

  it('shows open-request badge on the requests quick action', async () => {
    getMock.mockResolvedValue({ data: makePayload() });
    renderPage();
    await waitFor(() => expect(screen.getByTestId('counselor-action-requests')).toBeInTheDocument());
    expect(screen.getByTestId('counselor-action-requests')).toHaveTextContent('2');
  });

  it('renders empty bunk state when counselor has no bunks', async () => {
    getMock.mockResolvedValue({
      data: makePayload({ bunks: [] }),
    });
    renderPage();
    await waitFor(() => expect(screen.getByTestId('counselor-bunks-section')).toBeInTheDocument());
    expect(screen.getByText(/not assigned as an author on any bunk/i)).toBeInTheDocument();
  });
});
