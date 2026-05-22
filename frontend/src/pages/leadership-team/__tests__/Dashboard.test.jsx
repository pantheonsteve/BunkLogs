import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import LeadershipTeamDashboard from '../Dashboard';

const getMock = vi.fn();
vi.mock('../../../api', () => ({
  default: { get: (...args) => getMock(...args) },
}));

vi.mock('../../../auth/AuthContext', () => ({
  useAuth: () => ({ orgSlug: 'test-org', user: { id: 1 } }),
}));

const sample = {
  today: '2026-07-10',
  teams: [
    {
      team_role: 'kitchen_staff',
      team_role_label: 'Kitchen Staff',
      program_id: 1,
      program_name: 'Summer',
      member_count: 4,
      completion: { submitted: 2, expected: 4 },
      co_supervisors: [{ membership_id: 9, person_name: 'Co-LT' }],
      badges: ['low_completion'],
    },
  ],
  bunks_and_units: {
    unit_count: 3,
    bunk_count: 12,
    completion: { submitted: 10, expected: 12 },
  },
  self_reflection: {
    state: 'missing',
    reflection_id: null,
    template_id: 50,
    editable: true,
    period_start: '2026-07-06',
    period_end: '2026-07-19',
    cadence: 'biweekly',
  },
  templates_and_assignments: { owned_template_count: 2, assignment_count: 0 },
};

beforeEach(() => { getMock.mockReset(); });

describe('LeadershipTeamDashboard', () => {
  it('renders teams, self-reflection card, bunks/units, and templates sections', async () => {
    getMock.mockResolvedValue({ data: sample });
    render(<MemoryRouter><LeadershipTeamDashboard /></MemoryRouter>);
    await waitFor(() => expect(screen.getByTestId('lt-teams-list')).toBeInTheDocument());
    expect(screen.getByTestId('lt-team-card-kitchen_staff')).toBeInTheDocument();
    expect(screen.getByTestId('lt-badge-low_completion')).toBeInTheDocument();
    expect(screen.getByTestId('lt-self-card')).toBeInTheDocument();
    expect(screen.getByTestId('lt-bunks-units-card')).toBeInTheDocument();
    expect(screen.getByTestId('lt-templates-card')).toBeInTheDocument();
    expect(screen.getByText(/2 templates you authored/)).toBeInTheDocument();
  });

  it('surfaces an access error when the API returns 403', async () => {
    getMock.mockRejectedValue({ response: { status: 403 } });
    render(<MemoryRouter><LeadershipTeamDashboard /></MemoryRouter>);
    await waitFor(() => expect(screen.getByTestId('lt-error')).toBeInTheDocument());
    expect(screen.getByText(/Leadership Team access/)).toBeInTheDocument();
  });

  it('shows an empty-state when the viewer supervises no teams', async () => {
    getMock.mockResolvedValue({ data: { ...sample, teams: [] } });
    render(<MemoryRouter><LeadershipTeamDashboard /></MemoryRouter>);
    await waitFor(() => expect(screen.getByTestId('lt-teams-empty')).toBeInTheDocument());
  });
});
