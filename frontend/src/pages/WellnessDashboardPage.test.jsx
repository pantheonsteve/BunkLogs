import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import userEvent from '@testing-library/user-event';
import WellnessDashboardPage from './WellnessDashboardPage';

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
  sub_role_filter: null,
  by_sub_role: [
    {
      role: 'camper_care',
      program_slug: 'summer',
      total_staff: 2,
      reflections_submitted: 1,
      completion_rate: 0.5,
      prior_completion_rate: 0.25,
      completion_trend: 'up',
      category_averages: { workload: 3, morale: 4 },
      prior_category_averages: { workload: 2, morale: 3 },
      rating_trend: 'up',
      concerning: [
        {
          reflection_id: 7,
          person_id: 11,
          field_key: 'pulse',
          category: 'workload',
          value: 1,
          period_end: '2026-06-14',
        },
      ],
      open_questions: [
        {
          reflection_id: 7,
          person_id: 11,
          field_key: 'primary_concern',
          period_end: '2026-06-14',
          text: 'Need backup at meds line',
        },
      ],
    },
    {
      role: 'health_center',
      program_slug: 'summer',
      total_staff: 1,
      reflections_submitted: 0,
      completion_rate: 0,
      prior_completion_rate: 0,
      completion_trend: 'flat',
      category_averages: {},
      prior_category_averages: {},
      rating_trend: 'flat',
      concerning: [],
      open_questions: [],
    },
    {
      role: 'special_diets',
      program_slug: 'summer',
      total_staff: 0,
      reflections_submitted: 0,
      completion_rate: 0,
      prior_completion_rate: 0,
      completion_trend: 'flat',
      category_averages: {},
      prior_category_averages: {},
      rating_trend: 'flat',
      concerning: [],
      open_questions: [],
    },
  ],
  cross_team_patterns: [
    {
      reflection_id: 33,
      person_id: 99,
      program_slug: 'summer',
      field_key: 'primary_concern',
      template_slug: 'counselor-pulse',
      template_role: 'counselor',
      period_end: '2026-06-12',
      text: 'Camper Aviva needs Camper Care follow-up.',
    },
  ],
  completion: {
    total_staff: 3,
    reflections_submitted: 1,
    completion_rate: 0.3333,
    by_sub_role: [
      { role: 'camper_care', program_slug: 'summer', total_staff: 2, reflections_submitted: 1, completion_rate: 0.5 },
      { role: 'health_center', program_slug: 'summer', total_staff: 1, reflections_submitted: 0, completion_rate: 0 },
      { role: 'special_diets', program_slug: 'summer', total_staff: 0, reflections_submitted: 0, completion_rate: 0 },
    ],
  },
};

describe('WellnessDashboardPage', () => {
  beforeEach(() => {
    getMock.mockReset();
    getMock.mockResolvedValue({ data: samplePayload });
  });

  it('loads dashboard and shows sub-role rows and cross-team patterns', async () => {
    render(
      <MemoryRouter>
        <WellnessDashboardPage />
      </MemoryRouter>,
    );
    await waitFor(() => expect(getMock).toHaveBeenCalled());
    expect(screen.getByRole('heading', { name: /Wellness team/i, level: 1 })).toBeInTheDocument();
    // Each sub-role appears at least twice (dropdown option + table row)
    await waitFor(() => expect(screen.getAllByText('Camper Care').length).toBeGreaterThanOrEqual(2));
    expect(screen.getAllByText('Health Center').length).toBeGreaterThanOrEqual(2);
    expect(screen.getAllByText('Special Diets').length).toBeGreaterThanOrEqual(2);
    expect(screen.getByText(/Camper Aviva needs Camper Care follow-up/i)).toBeInTheDocument();
    expect(screen.getByText(/Need backup at meds line/i)).toBeInTheDocument();
  });

  it('passes sub_role param when filter is set', async () => {
    const user = userEvent.setup();
    render(
      <MemoryRouter>
        <WellnessDashboardPage />
      </MemoryRouter>,
    );
    await waitFor(() => expect(getMock).toHaveBeenCalled());
    getMock.mockClear();
    await user.selectOptions(screen.getByLabelText(/Filter by wellness sub-role/i), 'health_center');
    await waitFor(() => expect(getMock).toHaveBeenCalled());
    const lastCall = getMock.mock.calls.at(-1);
    expect(lastCall?.[1]?.params?.sub_role).toBe('health_center');
  });

  it('shows access message on 403', async () => {
    getMock.mockRejectedValueOnce({ response: { status: 403 } });
    render(
      <MemoryRouter>
        <WellnessDashboardPage />
      </MemoryRouter>,
    );
    await waitFor(() => expect(screen.getByText(/Access restricted/i)).toBeInTheDocument());
  });
});
