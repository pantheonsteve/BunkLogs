import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import TeamDashboardPage from './TeamDashboardPage';

const getMock = vi.fn();

vi.mock('../api', () => ({
  default: { get: (...args) => getMock(...args) },
}));

vi.mock('../auth/AuthContext', () => ({
  useAuth: () => ({ user: null }),
}));

// Stub TemplateDashboard to avoid deep mock chains
vi.mock('../dashboards/TemplateDashboard', () => ({
  default: ({ templateId }) => (
    <div data-testid="template-dashboard">template-{templateId}</div>
  ),
}));

const ltTemplate = { id: 7, name: 'LT Weekly', slug: 'lt-weekly', role: 'leadership_team', is_active: true };

describe('TeamDashboardPage', () => {
  beforeEach(() => {
    getMock.mockReset();
  });

  it('loads templates and renders TemplateDashboard', async () => {
    getMock.mockResolvedValueOnce({ data: [ltTemplate] });
    render(
      <MemoryRouter>
        <TeamDashboardPage />
      </MemoryRouter>,
    );
    await waitFor(() => expect(screen.getByTestId('template-dashboard')).toBeInTheDocument());
    expect(screen.getByText('template-7')).toBeInTheDocument();
  });

  it('shows access restricted on 403', async () => {
    getMock.mockRejectedValueOnce({ response: { status: 403 } });
    render(
      <MemoryRouter>
        <TeamDashboardPage />
      </MemoryRouter>,
    );
    await waitFor(() => expect(screen.getByText(/access restricted/i)).toBeInTheDocument());
  });

  it('shows message when no LT templates exist', async () => {
    getMock.mockResolvedValueOnce({ data: [] });
    render(
      <MemoryRouter>
        <TeamDashboardPage />
      </MemoryRouter>,
    );
    await waitFor(() =>
      expect(screen.getByText(/no active leadership team templates/i)).toBeInTheDocument(),
    );
  });

  it('filters to leadership_team role only', async () => {
    getMock.mockResolvedValueOnce({
      data: [
        ltTemplate,
        { id: 99, name: 'Wellness Daily', slug: 'wl', role: 'camper_care', is_active: true },
      ],
    });
    render(
      <MemoryRouter>
        <TeamDashboardPage />
      </MemoryRouter>,
    );
    await waitFor(() => expect(screen.getByTestId('template-dashboard')).toBeInTheDocument());
    expect(screen.getByText('template-7')).toBeInTheDocument();
    expect(screen.queryByText('template-99')).not.toBeInTheDocument();
  });
});
