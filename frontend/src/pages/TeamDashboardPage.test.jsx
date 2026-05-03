import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import TeamDashboardPage from './TeamDashboardPage';

const getMock = vi.fn();

vi.mock('../api', () => ({
  default: {
    get: (...args) => getMock(...args),
  },
}));

vi.mock('../auth/AuthContext', () => ({
  useAuth: () => ({ user: null }),
}));

const samplePayload = {
  period: {
    current_start: '2026-06-01',
    current_end: '2026-06-14',
    prior_start: '2026-05-18',
    prior_end: '2026-05-31',
  },
  year_round_only: false,
  units: [
    {
      unit_slug: 'alef',
      program_slug: 'summer',
      total_staff: 2,
      reflections_submitted: 1,
      completion_rate: 0.5,
      prior_completion_rate: 0.25,
      completion_trend: 'up',
      category_averages: { morale: 3 },
      prior_category_averages: { morale: 2 },
      rating_trend: 'up',
    },
  ],
  concerning: [],
  open_questions: [],
};

describe('TeamDashboardPage', () => {
  beforeEach(() => {
    getMock.mockReset();
    getMock.mockResolvedValue({ data: samplePayload });
  });

  it('loads dashboard and shows unit row', async () => {
    render(
      <MemoryRouter>
        <TeamDashboardPage />
      </MemoryRouter>,
    );
    await waitFor(() => expect(getMock).toHaveBeenCalled());
    expect(screen.getByText('Unit health')).toBeInTheDocument();
    await waitFor(() => expect(screen.getByText('alef')).toBeInTheDocument());
    expect(screen.getByText('summer')).toBeInTheDocument();
  });

  it('shows access message on 403', async () => {
    getMock.mockRejectedValueOnce({ response: { status: 403 } });
    render(
      <MemoryRouter>
        <TeamDashboardPage />
      </MemoryRouter>,
    );
    await waitFor(() => expect(screen.getByText(/Access restricted/i)).toBeInTheDocument());
  });
});
