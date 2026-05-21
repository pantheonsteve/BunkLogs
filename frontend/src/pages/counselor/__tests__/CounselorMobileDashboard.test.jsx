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
    today: '2026-07-04',
    rollover_hour: 4,
    timezone: 'America/New_York',
    program: { id: 1, slug: 'clc-summer-2026', name: 'CLC Summer 2026' },
    all_set: false,
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

function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/counselor']}>
      <CounselorMobileDashboard />
    </MemoryRouter>,
  );
}

describe('CounselorMobileDashboard', () => {
  beforeEach(() => {
    getMock.mockReset();
  });

  it('renders the three sections from the dashboard payload', async () => {
    getMock.mockResolvedValue({ data: makePayload() });
    renderPage();

    await waitFor(() => expect(screen.getByText('2026-07-04')).toBeInTheDocument());

    expect(screen.getByTestId('counselor-section-campers')).toBeInTheDocument();
    expect(screen.getByTestId('counselor-section-self')).toBeInTheDocument();
    expect(screen.getByTestId('counselor-section-requests')).toBeInTheDocument();

    expect(screen.getByTestId('counselor-section-campers-state')).toHaveTextContent('In progress');
    expect(screen.getByTestId('counselor-section-campers')).toHaveTextContent(
      /3\s*campers? still need/i,
    );
    expect(screen.getByTestId('counselor-section-campers')).toHaveTextContent(
      /1 camper off-camp today/i,
    );
  });

  it('shows the all-set banner when both required sections are complete', async () => {
    getMock.mockResolvedValue({
      data: makePayload({
        all_set: true,
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

  it('shows a friendly message for 403 without organization context', async () => {
    getMock.mockRejectedValue({ response: { status: 403, data: { detail: 'Organization context required.' } } });
    renderPage();
    await waitFor(() => expect(screen.getByTestId('counselor-dashboard-error')).toBeInTheDocument());
    expect(screen.getByTestId('counselor-dashboard-error')).toHaveTextContent('Organization context required.');
  });

  it('points the campers CTA at /counselor/camper-reflections', async () => {
    getMock.mockResolvedValue({ data: makePayload() });
    renderPage();
    await waitFor(() => expect(screen.getByTestId('counselor-section-campers-action')).toBeInTheDocument());
    expect(screen.getByTestId('counselor-section-campers-action')).toHaveAttribute(
      'href',
      '/counselor/camper-reflections',
    );
  });

  it('renders a complete-no-action self section when template is null', async () => {
    getMock.mockResolvedValue({
      data: makePayload({
        sections: {
          camper_reflections: { state: 'complete', covered: 0, total: 0, off_camp: 0, bunk_count: 0 },
          self_reflection: {
            state: 'complete',
            submitted: false,
            reflection_id: null,
            submitted_at: null,
            is_day_off: false,
            editable: false,
            template: null,
          },
          requests: { state: 'none', open_count: 0, by_type: { camper_care: 0, maintenance: 0 } },
        },
      }),
    });
    renderPage();
    await waitFor(() => expect(screen.getByTestId('counselor-section-self')).toBeInTheDocument());
    expect(screen.getByText(/No self-reflection template is configured/i)).toBeInTheDocument();
    expect(screen.queryByTestId('counselor-section-self-action')).toBeNull();
  });
});
