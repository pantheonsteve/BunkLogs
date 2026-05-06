import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import WellnessDashboardPage from './WellnessDashboardPage';

const getMock = vi.fn();

vi.mock('../api', () => ({
  default: { get: (...args) => getMock(...args) },
}));

vi.mock('../auth/AuthContext', () => ({
  useAuth: () => ({ user: null }),
}));

vi.mock('../dashboards/TemplateDashboard', () => ({
  default: ({ templateId }) => (
    <div data-testid="template-dashboard">template-{templateId}</div>
  ),
}));

const wellnessTemplate = { id: 12, name: 'Wellness Daily', slug: 'wellness-daily', role: 'camper_care', is_active: true };

describe('WellnessDashboardPage', () => {
  beforeEach(() => {
    getMock.mockReset();
  });

  it('loads templates and renders TemplateDashboard for wellness role', async () => {
    getMock.mockResolvedValueOnce({ data: [wellnessTemplate] });
    render(
      <MemoryRouter>
        <WellnessDashboardPage />
      </MemoryRouter>,
    );
    await waitFor(() => expect(screen.getByTestId('template-dashboard')).toBeInTheDocument());
    expect(screen.getByText('template-12')).toBeInTheDocument();
  });

  it('shows access restricted on 403', async () => {
    getMock.mockRejectedValueOnce({ response: { status: 403 } });
    render(
      <MemoryRouter>
        <WellnessDashboardPage />
      </MemoryRouter>,
    );
    await waitFor(() => expect(screen.getByText(/access restricted/i)).toBeInTheDocument());
  });

  it('shows message when no wellness templates found', async () => {
    getMock.mockResolvedValueOnce({ data: [] });
    render(
      <MemoryRouter>
        <WellnessDashboardPage />
      </MemoryRouter>,
    );
    await waitFor(() =>
      expect(screen.getByText(/no active wellness team templates/i)).toBeInTheDocument(),
    );
  });

  it('filters to wellness roles only', async () => {
    getMock.mockResolvedValueOnce({
      data: [
        wellnessTemplate,
        { id: 5, name: 'LT Weekly', slug: 'lt-weekly', role: 'leadership_team', is_active: true },
      ],
    });
    render(
      <MemoryRouter>
        <WellnessDashboardPage />
      </MemoryRouter>,
    );
    await waitFor(() => expect(screen.getByTestId('template-dashboard')).toBeInTheDocument());
    expect(screen.getByText('template-12')).toBeInTheDocument();
    expect(screen.queryByText('template-5')).not.toBeInTheDocument();
  });
});
